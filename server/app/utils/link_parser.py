from __future__ import annotations

import re

_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_URL_RE = re.compile(r"https?://[^\s)\]\[\"'>]+")
_GEMINI_SOURCE_RE = re.compile(
    r"^\s*#\d+:\s*(?P<title>.+?)\n"
    r"\s*URL:\s*(?P<url>https?://\S+)\n"
    r"(?:\s*Snippet:\s*(?P<snippet>.*?))?(?=\n\s*#\d+:|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _clean_context(value: str) -> str:
    """Normalize whitespace and trim noisy punctuation around extracted context."""
    collapsed = " ".join(value.strip().split())
    return collapsed.strip(" -:;,.()[]{}")


def _strip_markdown_link(line: str) -> str:
    """Convert [Label](url) into [Label] so description remains readable."""
    return _MARKDOWN_LINK_RE.sub(r"[\1]", line)


def _extract_chatgpt_item_block(lines: list[str], source_line_idx: int) -> str:
    """Return the numbered item block around a ChatGPT markdown source line."""
    start = source_line_idx
    while start > 0:
        prev = lines[start - 1]
        if re.match(r"^\s*\d+\.\s", prev):
            start -= 1
            break
        if prev.strip() == "":
            break
        start -= 1

    block_lines = lines[start : source_line_idx + 1]
    cleaned = [_strip_markdown_link(line.rstrip()) for line in block_lines]
    return "\n".join(line for line in cleaned if line.strip())


def _extract_gemini_section(text: str) -> str:
    """Return the Gemini response subsection if present."""
    marker = "[GEMINI] Response:"
    index = text.find(marker)
    if index == -1:
        return text
    return text[index + len(marker) :]


def textwrap_remove_url(snippet: str) -> str:
    """Remove URLs from a snippet so context focuses on nearby descriptive text."""
    return _URL_RE.sub(" ", snippet)


def parse_chatgpt_links_with_description(text: str) -> list[tuple[str, str]]:
    """
    Parse ChatGPT-formatted list items into (link, description block).

    Each result tries to keep the full numbered item around the source line,
    e.g. product name + specs + price + source label.
    """
    if not text:
        return []

    parsed: list[tuple[str, str]] = []
    lines = text.splitlines()

    for idx, line in enumerate(lines):
        source_match = _MARKDOWN_LINK_RE.search(line)
        if not source_match:
            continue

        url = source_match.group(2).rstrip(".,;)")
        description = _extract_chatgpt_item_block(lines, idx)
        if not description:
            description = _clean_context(_strip_markdown_link(line))

        parsed.append((url, description))

    return parsed


def parse_gemini_links_with_description(text: str) -> list[tuple[str, str]]:
    """
    Parse Gemini sources blocks into (link, description block).

    Expected pattern per source:
      #N: <title>
      URL: <url>
      Snippet: <snippet>
    """
    if not text:
        return []

    gemini_text = _extract_gemini_section(text)
    parsed: list[tuple[str, str]] = []

    for match in _GEMINI_SOURCE_RE.finditer(gemini_text):
        title = _clean_context(match.group("title"))
        url = match.group("url").rstrip(".,;)")
        snippet = _clean_context(match.group("snippet") or "")

        description_lines = [f"# {title}"]
        if snippet:
            description_lines.append(f"Snippet: {snippet}")

        parsed.append((url, "\n".join(description_lines)))

    return parsed


def parse_links_for_model(text: str, model_name: str) -> list[tuple[str, str]]:
    """
    Route parsing based on model name.

    Supported model_name values (case-insensitive):
      - ChatGPT/OpenAI family: "chatgpt", "gpt-4o", "openai", etc.
      - Gemini family: "gemini", "gemini-2.5-flash", etc.
    """
    model = (model_name or "").strip().lower()

    if not model:
        raise ValueError("model_name is required.")

    if any(token in model for token in ["chatgpt", "openai", "gpt"]):
        return parse_chatgpt_links_with_description(text)

    if "gemini" in model:
        return parse_gemini_links_with_description(text)

    raise ValueError(
        f"Unsupported model_name '{model_name}'. Expected ChatGPT/OpenAI or Gemini model names."
    )


def parse_links_with_context(text: str) -> list[tuple[str, str]]:
    """Backward-compatible alias that defaults to ChatGPT-style parsing."""
    return parse_chatgpt_links_with_description(text)


def parse_chatgpt_links(text: str) -> list[tuple[str, str]]:
    """Compatibility alias for existing callers."""
    return parse_chatgpt_links_with_description(text)
