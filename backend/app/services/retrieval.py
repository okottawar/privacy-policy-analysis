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
    Tries trafilatura first, falls back to BeautifulSoup.
    """
    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    html = response.text

    if HAS_TRAFILATURA:
        extracted = trafilatura.extract(
            html,
            include_tables=True,
            include_links=False,
            include_formatting=True,  # preserve heading markers
            output_format="txt",
        )
        if extracted and len(extracted) > 500:
            return _clean_text(extracted)

    return _bs4_extract(html)


def _bs4_extract(html: str) -> str:
    """BeautifulSoup fallback extractor."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "header", "footer",
                     "aside", "form", "button", "img", "noscript"]):
        tag.decompose()

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
        if len(line) < 3:
            continue
        if re.match(r"^[^a-zA-Z0-9]*$", line):
            continue
        cleaned.append(line)

    result = "\n".join(cleaned)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()


def extract_sections(text: str) -> list[dict]:
    """
    Heuristically split the policy into named sections.
    Uses multiple heading patterns to handle different policy formats.
    Returns list of {"section": str, "content": str}
    """
    lines = text.splitlines()
    sections = []
    current_heading = "Introduction"
    buffer = []

    for line in lines:
        stripped = line.strip()
        if _is_heading(stripped):
            # Save previous section
            content = "\n".join(buffer).strip()
            if content:
                sections.append({"section": current_heading, "content": content})
            current_heading = stripped
            buffer = []
        else:
            buffer.append(line)

    # Save final section
    content = "\n".join(buffer).strip()
    if content:
        sections.append({"section": current_heading, "content": content})

    # If only 1 section detected, split by paragraph blocks instead
    # This handles policies where trafilatura strips all heading markers
    if len(sections) <= 1 and text:
        return _split_by_paragraphs(text)

    return [s for s in sections if len(s["content"]) > 50]


def _is_heading(line: str) -> bool:
    """
    Returns True if a line looks like a section heading.
    Handles multiple common privacy policy heading formats.
    """
    if not line or len(line) > 100:
        return False

    patterns = [
        # "1. Data Collection" or "1) Data Collection"
        r"^\d+[\.\)]\s+[A-Z][A-Za-z\s\-&]{2,60}$",
        # All-caps heading: "DATA COLLECTION"
        r"^[A-Z][A-Z\s\-&]{4,60}$",
        # Title case short line: "Data Collection" (max 6 words)
        r"^([A-Z][a-z]+\s){1,5}[A-Z][a-z]+$",
        # Heading with colon: "Data Collection:"
        r"^[A-Z][A-Za-z\s\-&]{3,60}:$",
        # Markdown-style: "## Data Collection"
        r"^#{1,3}\s+.{3,60}$",
    ]

    return any(re.match(p, line) for p in patterns)


def _split_by_paragraphs(text: str, min_length: int = 200) -> list[dict]:
    """
    Fallback: split text into paragraph blocks when no headings are found.
    Labels each block sequentially.
    """
    paragraphs = re.split(r"\n\n+", text)
    sections = []
    block_num = 1

    for para in paragraphs:
        para = para.strip()
        if len(para) >= min_length:
            sections.append({
                "section": f"Section {block_num}",
                "content": para,
            })
            block_num += 1

    return sections if sections else [{"section": "Privacy Policy", "content": text}]
