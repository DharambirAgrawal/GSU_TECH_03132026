import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import anthropic
import httpx
import openai
from dotenv import load_dotenv
from google import genai

logger = logging.getLogger(__name__)


load_dotenv()
# ───────────────────────────────────────────
# CUSTOM EXCEPTIONS
# ───────────────────────────────────────────


class RateLimitError(Exception):
    """Raised when any LLM API returns a rate limit error."""

    def __init__(self, platform: str):
        self.platform = platform
        super().__init__(f"Rate limit hit on {platform}")


class LLMClientError(Exception):
    """Raised for non-rate-limit errors from any LLM client."""

    def __init__(self, platform: str, original_error: Exception):
        self.platform = platform
        self.original_error = original_error
        super().__init__(f"LLM error on {platform}: {str(original_error)}")


# ───────────────────────────────────────────
# RESPONSE DATA CLASS
# ───────────────────────────────────────────


@dataclass
class LLMResponse:
    """
    Standardized response from any LLM wrapper.

    Attributes:
        content (str): The raw text answer from the LLM.
        sources (list[dict]): When search=True, a list of source dicts, each with:
            - rank (int): Position in the results (1 = top)
            - title (str): Page/source title
            - url (str): Source URL
            - snippet (str): Relevant excerpt the LLM pulled from this source
        platform (str): Which LLM platform produced this ("chatgpt", "claude", etc.)
        search_enabled (bool): Whether search grounding was used.
        raw_response (any): The raw API response object for debugging.
    """

    content: str
    sources: list = field(default_factory=list)
    platform: str = ""
    search_enabled: bool = False
    metadata: dict = field(default_factory=dict)
    raw_response: object = None

    def __str__(self) -> str:
        """Pretty-print the response with sources when available."""
        parts = [f"[{self.platform.upper()}] Response:"]
        parts.append(self.content)

        if self.sources:
            parts.append(f"\n--- Sources ({len(self.sources)} found) ---")
            for src in self.sources:
                rank = src.get("rank", "?")
                title = src.get("title", "Untitled")
                url = src.get("url", "N/A")
                snippet = src.get("snippet", "")
                parts.append(f"  #{rank}: {title}")
                parts.append(f"       URL: {url}")
                if snippet:
                    parts.append(f"       Snippet: {snippet[:200]}...")

        return "\n".join(parts)


# ───────────────────────────────────────────
# SEARCH PROMPT BUILDER
# ───────────────────────────────────────────

# When search=True but the platform doesn't have native search grounding
# (like Claude or base GPT-4o without browsing), we inject a structured
# system prompt that asks the LLM to cite its sources in a parseable format.

SEARCH_SYSTEM_PROMPT = """You are a research assistant with web search capabilities. 
For the user's query, provide a comprehensive answer AND a list of sources.

You MUST format your response EXACTLY as follows:

ANSWER:
[Your detailed answer here, referencing sources by number like [1], [2], etc.]

SOURCES:
[1] Title of Source | https://example.com/url | Brief snippet of what this source says
[2] Title of Source | https://example.com/url | Brief snippet of what this source says
[3] Title of Source | https://example.com/url | Brief snippet of what this source says

List sources in order of relevance (most relevant first). Include at least 3-5 sources.
The ranking matters — put the most authoritative and relevant source at #1."""

NO_SEARCH_SYSTEM_PROMPT = "You are a helpful assistant."


def _parse_sources_from_text(text: str) -> tuple[str, list[dict]]:
    """
    Parse the structured ANSWER: / SOURCES: format from an LLM response
    when we used the search system prompt.

    Returns:
        (answer_text, sources_list)
    """
    sources = []
    answer = text

    # Try to split on SOURCES: section
    if "SOURCES:" in text:
        parts = text.split("SOURCES:", 1)
        answer_part = parts[0]
        sources_part = parts[1]

        # Clean up the answer part (remove "ANSWER:" prefix if present)
        if "ANSWER:" in answer_part:
            answer = answer_part.split("ANSWER:", 1)[1].strip()
        else:
            answer = answer_part.strip()

        # Parse each source line: [N] Title | URL | Snippet
        for line in sources_part.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            try:
                # Remove the [N] prefix
                rank = None
                if line.startswith("["):
                    bracket_end = line.index("]")
                    rank_str = line[1:bracket_end]
                    try:
                        rank = int(rank_str)
                    except ValueError:
                        rank = None
                    line = line[bracket_end + 1 :].strip()

                # Split by pipe: Title | URL | Snippet
                pipe_parts = [p.strip() for p in line.split("|")]

                source = {
                    "rank": rank or (len(sources) + 1),
                    "title": pipe_parts[0] if len(pipe_parts) > 0 else "Unknown",
                    "url": pipe_parts[1] if len(pipe_parts) > 1 else "N/A",
                    "snippet": pipe_parts[2] if len(pipe_parts) > 2 else "",
                }
                sources.append(source)
            except Exception as e:
                logger.debug(f"Could not parse source line: {line} — {e}")
                continue
    elif "ANSWER:" in text:
        answer = text.split("ANSWER:", 1)[1].strip()

    return answer, sources


def _extract_openai_grounded_response(response: object) -> tuple[str, list[dict], dict]:
    """Extract answer text, ranked sources, and grounding metadata from Responses API."""
    content_parts: list[str] = []
    sources: list[dict] = []
    seen_urls: set[str] = set()
    citations: list[dict] = []
    output_items: list[dict] = []
    web_search_calls: list[dict] = []

    # SDK objects expose `model_dump`; fallback to object attributes when unavailable.
    response_dict: dict[str, Any] = {}
    try:
        if hasattr(response, "model_dump"):
            response_dict = response.model_dump()
    except Exception:
        response_dict = {}

    output = getattr(response, "output", []) or []
    for item in output:
        item_type = getattr(item, "type", "unknown")
        output_items.append(
            {
                "id": getattr(item, "id", None),
                "type": item_type,
                "status": getattr(item, "status", None),
            }
        )

        # Capture web search call payloads when present.
        if item_type in {"web_search_call", "tool_call"}:
            call = {
                "id": getattr(item, "id", None),
                "type": item_type,
                "status": getattr(item, "status", None),
            }
            for attr in ["query", "action", "arguments", "name"]:
                if hasattr(item, attr):
                    call[attr] = getattr(item, attr)
            web_search_calls.append(call)

        if item_type != "message":
            continue

        for block in getattr(item, "content", []) or []:
            if getattr(block, "type", None) != "output_text":
                continue

            block_text = getattr(block, "text", "") or ""
            if block_text:
                content_parts.append(block_text)

            for ann in getattr(block, "annotations", []) or []:
                ann_type = getattr(ann, "type", None)
                citation = {
                    "type": ann_type,
                    "title": getattr(ann, "title", None),
                    "url": getattr(ann, "url", None),
                    "start_index": getattr(ann, "start_index", None),
                    "end_index": getattr(ann, "end_index", None),
                }
                citations.append(citation)

                url = citation.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    sources.append(
                        {
                            "rank": len(sources) + 1,
                            "title": citation.get("title") or "Untitled",
                            "url": url,
                            "snippet": "",
                        }
                    )

    metadata = {
        "response_id": getattr(response, "id", None),
        "model": getattr(response, "model", None),
        "status": getattr(response, "status", None),
        "usage": getattr(response, "usage", None),
        "output_items": output_items,
        "web_search_calls": web_search_calls,
        "citations": citations,
        "raw_dict": response_dict,
    }

    content = "\n".join(part for part in content_parts if part).strip()
    return content, sources, metadata


# ───────────────────────────────────────────
# FUNCTION: get_chatgpt_response
# ───────────────────────────────────────────


def get_chatgpt_response(
    query: str,
    temperature: float = 0.3,
    search: bool = False,
) -> LLMResponse:
    """
    Sends a query to OpenAI GPT-4o and returns the response.

    When search=True:
            - Uses the OpenAI Responses API with native web search grounding.
            - Extracts all available grounding metadata: output items,
                web search call payloads, citations, URLs, and usage.
            - Falls back to prompt-based search if the grounded call fails.

    When search=False:
      - Standard completion with no web search.

    Args:
        query: The user query string.
        temperature: Sampling temperature (0.0-1.0).
        search: If True, enable web search grounding.

    Returns:
        LLMResponse with content, sources (if search=True), and metadata.

    Raises:
        RateLimitError: If OpenAI returns 429.
        LLMClientError: For any other API error.
    """
    try:
        client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

        if search:
            # ── Attempt 1: OpenAI Responses API with native web search grounding ──
            try:
                response = client.responses.create(
                    model="gpt-4o",
                    input=query,
                    tools=[{"type": "web_search_preview"}],
                )

                content, sources, metadata = _extract_openai_grounded_response(
                    response
                )

                return LLMResponse(
                    content=content,
                    sources=sources,
                    platform="chatgpt",
                    search_enabled=True,
                    metadata=metadata,
                    raw_response=response,
                )

            except Exception as e:
                logger.warning(
                    f"OpenAI Responses API (web_search) failed, "
                    f"falling back to prompt-based search: {e}"
                )
                # Fall through to prompt-based approach below

            # ── Fallback: Prompt-based search via Chat Completions ──
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": SEARCH_SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ],
                temperature=temperature,
                max_tokens=2000,
            )

            raw_text = response.choices[0].message.content
            answer, sources = _parse_sources_from_text(raw_text)

            return LLMResponse(
                content=answer,
                sources=sources,
                platform="chatgpt",
                search_enabled=True,
                metadata={"fallback": "prompt_based_search"},
                raw_response=response,
            )

        else:
            # ── Standard (no search) completion ──
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": NO_SEARCH_SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ],
                temperature=temperature,
                max_tokens=1000,
            )

            return LLMResponse(
                content=response.choices[0].message.content,
                sources=[],
                platform="chatgpt",
                search_enabled=False,
                metadata={
                    "model": "gpt-4o",
                    "usage": getattr(response, "usage", None),
                },
                raw_response=response,
            )

    except openai.RateLimitError:
        logger.warning("OpenAI rate limit hit")
        raise RateLimitError(platform="chatgpt")
    except (RateLimitError, LLMClientError):
        raise
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        raise LLMClientError(platform="chatgpt", original_error=e)


# ───────────────────────────────────────────
# FUNCTION: get_claude_response
# ───────────────────────────────────────────


def get_claude_response(
    query: str,
    temperature: float = 0.3,
    search: bool = False,
) -> LLMResponse:
    """
    Sends a query to Anthropic Claude (claude-3-5-sonnet-20241022).

    When search=True:
      - Uses Claude's built-in web_search tool (available in the Anthropic API).
        Claude will autonomously decide to search and returns structured
        source blocks with URLs and snippets.
      - Falls back to prompt-based search if the tool isn't available.

    When search=False:
      - Standard completion.

    Args:
        query: The user query string.
        temperature: Sampling temperature (0.0–1.0).
        search: If True, enable web search.

    Returns:
        LLMResponse with content, sources (if search=True), and metadata.

    Raises:
        RateLimitError: If Anthropic returns 429.
        LLMClientError: For any other API error.
    """
    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

        if search:
            # ── Attempt 1: Use Claude's native web_search tool ──
            try:
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=2000,
                    tools=[{"type": "web_search", "name": "web_search"}],
                    messages=[{"role": "user", "content": query}],
                )

                # Parse response: Claude returns a mix of text blocks and
                # tool_use/tool_result blocks when it searches.
                content_parts = []
                sources = []
                rank_counter = 1

                for block in response.content:
                    if block.type == "text":
                        content_parts.append(block.text)
                    elif block.type == "web_search_tool_result":
                        # Claude's web search results contain search_results
                        if hasattr(block, "search_results"):
                            for result in block.search_results:
                                sources.append(
                                    {
                                        "rank": rank_counter,
                                        "title": getattr(result, "title", "Untitled"),
                                        "url": getattr(result, "url", "N/A"),
                                        "snippet": getattr(result, "snippet", ""),
                                    }
                                )
                                rank_counter += 1

                content = "\n".join(content_parts) if content_parts else ""

                return LLMResponse(
                    content=content,
                    sources=sources,
                    platform="claude",
                    search_enabled=True,
                    raw_response=response,
                )

            except Exception as e:
                logger.warning(
                    f"Claude web_search tool failed, "
                    f"falling back to prompt-based search: {e}"
                )

            # ── Fallback: Prompt-based search ──
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                system=SEARCH_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": query}],
            )

            raw_text = response.content[0].text
            answer, sources = _parse_sources_from_text(raw_text)

            return LLMResponse(
                content=answer,
                sources=sources,
                platform="claude",
                search_enabled=True,
                raw_response=response,
            )

        else:
            # ── Standard (no search) completion ──
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": query}],
            )

            return LLMResponse(
                content=response.content[0].text,
                sources=[],
                platform="claude",
                search_enabled=False,
                raw_response=response,
            )

    except anthropic.RateLimitError:
        logger.warning("Anthropic rate limit hit")
        raise RateLimitError(platform="claude")
    except (RateLimitError, LLMClientError):
        raise
    except Exception as e:
        logger.error(f"Anthropic error: {e}")
        raise LLMClientError(platform="claude", original_error=e)


# ───────────────────────────────────────────
# FUNCTION: get_perplexity_response
# ───────────────────────────────────────────


def get_perplexity_response(
    query: str,
    search: bool = True,
) -> LLMResponse:
    """
    Sends a query to Perplexity AI via their REST API.

    Perplexity is ALWAYS search-augmented — it's fundamentally a search engine
    with an LLM layer. The `search` parameter controls whether we ask for
    structured source extraction:

    When search=True (default, recommended):
      - Uses "sonar-pro" model which returns citations natively.
      - Parses the `citations` array from the API response to build
        ranked sources list.
      - This is the most important mode for brand visibility tracking
        because Perplexity is one of the primary AI search engines
        consumers use.

    When search=False:
      - Still uses Perplexity (it always searches), but returns only
        the answer text without structured source extraction.

    Args:
        query: The user query string.
        search: If True, parse and return ranked sources from citations.

    Returns:
        LLMResponse with content, sources (if search=True), and metadata.

    Raises:
        RateLimitError: If Perplexity returns 429.
        LLMClientError: For any other API error.
    """
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        raise LLMClientError(
            platform="perplexity",
            original_error=KeyError("PERPLEXITY_API_KEY not set"),
        )

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Build the system prompt based on search mode
    if search:
        system_content = (
            "You are a helpful search assistant. Provide a comprehensive answer "
            "with inline citations like [1], [2], etc. Rank and cite your sources."
        )
    else:
        system_content = "You are a helpful assistant."

    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": query},
        ],
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)

            if response.status_code == 429:
                raise RateLimitError(platform="perplexity")

            response.raise_for_status()
            data = response.json()

        # Extract the answer content
        content = data["choices"][0]["message"]["content"]

        sources = []
        if search:
            # Perplexity returns a `citations` array at the top level of
            # the response containing the URLs it referenced.
            citations = data.get("citations", [])

            # Also check inside the message object for citations
            message_data = data["choices"][0].get("message", {})
            if not citations and "citations" in message_data:
                citations = message_data["citations"]

            # Build ranked sources from citations
            for rank, citation in enumerate(citations, start=1):
                if isinstance(citation, str):
                    # Simple URL string
                    sources.append(
                        {
                            "rank": rank,
                            "title": f"Source {rank}",
                            "url": citation,
                            "snippet": "",
                        }
                    )
                elif isinstance(citation, dict):
                    # Rich citation object
                    sources.append(
                        {
                            "rank": rank,
                            "title": citation.get("title", f"Source {rank}"),
                            "url": citation.get("url", "N/A"),
                            "snippet": citation.get(
                                "snippet", citation.get("text", "")
                            ),
                        }
                    )

            # If Perplexity didn't return structured citations but the content
            # has numbered references, try to extract them from the text
            if not sources and search:
                # Check for search_results in response
                search_results = data.get("search_results", [])
                for rank, result in enumerate(search_results, start=1):
                    sources.append(
                        {
                            "rank": rank,
                            "title": result.get("title", f"Source {rank}"),
                            "url": result.get("url", "N/A"),
                            "snippet": result.get("snippet", ""),
                        }
                    )

        return LLMResponse(
            content=content,
            sources=sources,
            platform="perplexity",
            search_enabled=search,
            raw_response=data,
        )

    except RateLimitError:
        raise
    except httpx.HTTPStatusError as e:
        logger.error(
            f"Perplexity HTTP error: {e.response.status_code} — {e.response.text}"
        )
        raise LLMClientError(platform="perplexity", original_error=e)
    except (RateLimitError, LLMClientError):
        raise
    except Exception as e:
        logger.error(f"Perplexity error: {e}")
        raise LLMClientError(platform="perplexity", original_error=e)


# ───────────────────────────────────────────
# FUNCTION: get_gemini_response
# ───────────────────────────────────────────


def get_gemini_response(
    query: str,
    search: bool = False,
) -> LLMResponse:
    """
        Sends a query to Google Gemini 2.5 via the google-genai Client SDK.

        When search=True, prompt-based source formatting is used so we can
        parse ranked citations consistently across platforms.

    Args:
        query: The user query string.
        search: If True, enable Google Search grounding.

    Returns:
        LLMResponse with content, sources (if search=True), and metadata.

    Raises:
        RateLimitError: If Google returns a quota/rate limit error.
        LLMClientError: For any other API error.
    """
    try:
        gemini_client = genai.Client(
            api_key=(GEMINI_API_KEY := os.environ["GEMINI_API_KEY"])
        )

        def _extract_text(response_obj: object) -> str:
            text = getattr(response_obj, "text", None)
            if isinstance(text, str) and text.strip():
                return text.strip()

            try:
                candidate = response_obj.candidates[0]
                parts = candidate.content.parts
                joined = "".join(getattr(part, "text", "") for part in parts)
                if joined.strip():
                    return joined.strip()
            except Exception:
                pass

            return ""

        model_name = "gemini-2.5-flash"

        if search:
            from google.genai import types

            response = gemini_client.models.generate_content(
                model=model_name,
                contents=query,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
                ),
            )

            raw_text = _extract_text(response)
            sources = []

            try:
                candidate = response.candidates[0]
                metadata = candidate.grounding_metadata

                if (
                    metadata
                    and hasattr(metadata, "grounding_chunks")
                    and metadata.grounding_chunks
                ):
                    # Build snippets from supports if available
                    snippet_map = {}
                    if (
                        hasattr(metadata, "grounding_supports")
                        and metadata.grounding_supports
                    ):
                        for support in metadata.grounding_supports:
                            if hasattr(support, "segment") and hasattr(
                                support.segment, "text"
                            ):
                                text = support.segment.text
                                indices = getattr(
                                    support, "grounding_chunk_indices", []
                                )
                                for idx in indices:
                                    if idx not in snippet_map:
                                        snippet_map[idx] = []
                                    if text not in snippet_map[idx]:
                                        snippet_map[idx].append(text)

                    for i, chunk in enumerate(metadata.grounding_chunks):
                        if hasattr(chunk, "web") and chunk.web:
                            snippet_list = snippet_map.get(i, [])
                            snippet_text = " ... ".join(snippet_list)

                            sources.append(
                                {
                                    "rank": len(sources) + 1,
                                    "title": getattr(chunk.web, "title", "Untitled"),
                                    "url": getattr(chunk.web, "uri", "N/A"),
                                    "snippet": snippet_text,
                                }
                            )

            except Exception as e:
                logger.warning(f"Error extracting Gemini grounding metadata: {e}")

            return LLMResponse(
                content=raw_text,
                sources=sources,
                platform="gemini",
                search_enabled=True,
                raw_response=response,
            )

        response = gemini_client.models.generate_content(
            model=model_name,
            contents=query,
        )
        content = _extract_text(response)

        return LLMResponse(
            content=content,
            sources=[],
            platform="gemini",
            search_enabled=False,
            raw_response=response,
        )

    except (RateLimitError, LLMClientError):
        raise
    except Exception as e:
        error_str = str(e).lower()
        if "quota" in error_str or "rate" in error_str or "429" in error_str:
            logger.warning("Gemini rate limit / quota hit")
            raise RateLimitError(platform="gemini")
        logger.error(f"Gemini error: {e}")
        raise LLMClientError(platform="gemini", original_error=e)


# ───────────────────────────────────────────
# CONVENIENCE: query_all_llms
# ───────────────────────────────────────────


def query_all_llms(
    query: str,
    search: bool = False,
    platforms: Optional[list[str]] = None,
) -> dict[str, LLMResponse]:
    """
    Query multiple LLM platforms in sequence and return all responses.

    This is the main entry point for Vigil's brand monitoring — fire the
    same query at all platforms and compare how each one answers, what
    sources each one surfaces, and where a brand appears in the rankings.

    Args:
        query: The user query string.
        search: If True, enable search/grounding on all platforms.
        platforms: List of platforms to query. Defaults to all four:
                   ["chatgpt", "claude", "perplexity", "gemini"]

    Returns:
        Dict mapping platform name → LLMResponse.
        If a platform errors, its value will be an LLMResponse with
        the error message as content and no sources.

    Example:
        results = query_all_llms(
            "What are the best CRM tools for small businesses?",
            search=True
        )
        for platform, resp in results.items():
            print(resp)
            print(f"  → {len(resp.sources)} sources found")
    """
    if platforms is None:
        platforms = ["chatgpt", "claude", "perplexity", "gemini"]

    dispatch = {
        "chatgpt": lambda q, s: get_chatgpt_response(q, search=s),
        "claude": lambda q, s: get_claude_response(q, search=s),
        "perplexity": lambda q, s: get_perplexity_response(q, search=s),
        "gemini": lambda q, s: get_gemini_response(q, search=s),
    }

    results = {}

    for platform in platforms:
        if platform not in dispatch:
            logger.warning(f"Unknown platform: {platform}, skipping")
            continue

        try:
            logger.info(f"Querying {platform} (search={search})...")
            start_time = time.time()
            response = dispatch[platform](query, search)
            elapsed = time.time() - start_time
            logger.info(
                f"  {platform} responded in {elapsed:.1f}s "
                f"({len(response.sources)} sources)"
            )
            results[platform] = response

        except RateLimitError as e:
            logger.warning(f"  {platform} rate limited, skipping")
            results[platform] = LLMResponse(
                content=f"[ERROR] Rate limit hit on {platform}",
                sources=[],
                platform=platform,
                search_enabled=search,
            )

        except LLMClientError as e:
            logger.error(f"  {platform} error: {e}")
            results[platform] = LLMResponse(
                content=f"[ERROR] {str(e)}",
                sources=[],
                platform=platform,
                search_enabled=search,
            )

    return results


if __name__ == "__main__":
    print(
        get_chatgpt_response(
            "please give me hp laptops below 500 dollars that have 8gb ram and 512gb storage space",
            True,
        )
    )
