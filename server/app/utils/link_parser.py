from __future__ import annotations

import re


_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_URL_RE = re.compile(r"https?://[^\s)\]\[\"'>]+")


def _clean_context(value: str) -> str:
    """Normalize whitespace and trim noisy punctuation around extracted context."""
    collapsed = " ".join(value.strip().split())
    return collapsed.strip(" -:;,.()[]{}")


def _context_around(text: str, start: int, end: int, radius: int = 90) -> str:
    """Return readable text surrounding a URL span."""
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    snippet = text[left:right]
    snippet = textwrap_remove_url(snippet)
    return _clean_context(snippet)


def textwrap_remove_url(snippet: str) -> str:
    """Remove URLs from a snippet so context focuses on nearby descriptive text."""
    return _URL_RE.sub(" ", snippet)


def parse_links_with_context(text: str) -> list[tuple[str, str]]:
    """
    Parse ChatGPT-style response text into a list of (link, text_around_link).

    Supports:
      - Markdown links: [label](https://...)
      - Raw URLs in sources blocks: URL: https://...

    Returns links in source-order as they appear in the text.
    """
    if not text:
        return []

    matches: list[tuple[int, int, str, str | None]] = []

    # 1) Markdown links include label text, which is ideal context.
    for md in _MARKDOWN_LINK_RE.finditer(text):
        label = _clean_context(md.group(1))
        url = md.group(2).rstrip(".,;)")
        matches.append((md.start(2), md.end(2), url, label or None))

    # 2) Raw URLs; skip any that overlap a markdown URL span already captured.
    for raw in _URL_RE.finditer(text):
        start, end = raw.span()
        overlaps_md = any(
            start >= m_start and end <= m_end for m_start, m_end, _, _ in matches
        )
        if overlaps_md:
            continue
        url = raw.group(0).rstrip(".,;)")
        matches.append((start, end, url, None))

    # Keep original appearance order.
    matches.sort(key=lambda item: item[0])

    parsed: list[tuple[str, str]] = []
    for start, end, url, label in matches:
        if label:
            context = label
        else:
            context = _context_around(text, start, end)
            if not context:
                context = "source"
        parsed.append((url, context))

    return parsed


def parse_chatgpt_links(text: str) -> list[tuple[str, str]]:
    """Compatibility alias for callers that expect a ChatGPT-specific parser name."""
    return parse_links_with_context(text)
