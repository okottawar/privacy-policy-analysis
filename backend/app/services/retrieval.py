"""
Document Retrieval & Cleaning Service
Fetches privacy policies from URLs, strips navigation/clutter, preserves semantic structure.
"""

import re
import requests
from bs4 import BeautifulSoup
from typing import Optional

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def fetch_policy(url: str, timeout: int = 15) -> str:
    """
    Fetch a privacy policy from a URL.
    Tries trafilatura first (better main-content extraction),
    falls back to BeautifulSoup.
    """
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    html = response.text

    # Attempt trafilatura extraction (cleaner main-content extraction)
    if HAS_TRAFILATURA:
        extracted = trafilatura.extract(
            html,
            include_tables=True,
            include_links=False,
            include_formatting=True,
            output_format="txt",
        )
        if extracted and len(extracted) > 500:
            return _clean_text(extracted)

    # Fallback: BeautifulSoup
    return _bs4_extract(html)


def _bs4_extract(html: str) -> str:
    """BeautifulSoup fallback extractor."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove boilerplate elements
    for tag in soup(["script", "style", "nav", "header", "footer",
                     "aside", "form", "button", "img", "noscript"]):
        tag.decompose()

    # Try to find the main content block
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id=re.compile(r"(content|policy|privacy|main)", re.I))
        or soup.find(class_=re.compile(r"(content|policy|privacy|main)", re.I))
        or soup.body
    )

    raw = main.get_text(separator="\n") if main else soup.get_text(separator="\n")
    return _clean_text(raw)


def _clean_text(text: str) -> str:
    """Normalize whitespace and remove junk lines."""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        line = line.strip()
        # Drop very short or purely symbolic lines
        if len(line) < 3:
            continue
        if re.match(r"^[^a-zA-Z0-9]*$", line):
            continue
        cleaned.append(line)

    # Collapse 3+ consecutive blank lines into 2
    result = "\n".join(cleaned)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def extract_sections(text: str) -> list[dict]:
    """
    Heuristically split the policy into named sections.
    Returns list of {"section": str, "content": str}
    """
    # Patterns that commonly indicate section headings in privacy policies
    heading_pattern = re.compile(
        r"^(?:\d+[\.\)]\s+)?([A-Z][A-Za-z\s\-&]{3,60})$",
        re.MULTILINE
    )

    matches = list(heading_pattern.finditer(text))
    sections = []

    if not matches:
        # No headings found — treat entire doc as one section
        return [{"section": "Privacy Policy", "content": text}]

    for i, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if content:
            sections.append({"section": heading, "content": content})

    return sections
