#!/usr/bin/env python3
"""
Search for a real French article matching a CEFR level and topic using DuckDuckGo,
then scrape and clean the article text.

Usage:
    python tools/search_french_text.py --level B1 --topic voyages_tourisme

Output (stdout JSON):
    { "text": "...", "url": "...", "site_name": "...", "word_count": 312 }

On failure, exits with code 1 and prints:
    { "error": "...", "message": "..." }
"""

import argparse
import json
import re
import sys
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

# ---------------------------------------------------------------------------
# CEFR-aware query configuration
# ---------------------------------------------------------------------------

TOPIC_LABELS = {
    "vie_quotidienne": "vie quotidienne routines",
    "voyages_tourisme": "voyages tourisme destinations",
    "environnement_ecologie": "environnement écologie nature",
    "technologie_numerique": "technologie numérique internet",
    "culture_histoire": "culture histoire France patrimoine",
}

LEVEL_MODIFIERS = {
    "A1": "texte facile débutant simple court",
    "A2": "article simple français facile enfants",
    "B1": "article presse niveau intermédiaire",
    "B2": "article analyse presse française",
    "C1": "éditorial essai opinion complexe argumentation",
}

# Target word count ranges per level
WORD_COUNT_TARGETS = {
    "A1": (100, 300),
    "A2": (120, 350),
    "B1": (200, 450),
    "B2": (300, 600),
    "C1": (350, 650),
}

# Sites that tend to have clean, level-appropriate French text
PREFERRED_SITES_BY_LEVEL = {
    "A1": ["1jour1actu.com", "monquotidien.fr", "okapi.fr"],
    "A2": ["1jour1actu.com", "ladepeche.fr", "francetvinfo.fr"],
    "B1": ["francetvinfo.fr", "lemonde.fr", "lefigaro.fr", "20minutes.fr"],
    "B2": ["lemonde.fr", "lefigaro.fr", "liberation.fr", "lexpress.fr"],
    "C1": ["lemonde.fr", "liberation.fr", "lemonde.fr", "lepoint.fr"],
}


def build_query(level: str, topic: str) -> str:
    topic_label = TOPIC_LABELS.get(topic, topic.replace("_", " "))
    level_mod = LEVEL_MODIFIERS.get(level, "article français")
    return f"{topic_label} {level_mod}"


def is_french(text: str) -> bool:
    """Heuristic: check for common French function words."""
    stopwords = {"le", "la", "les", "de", "du", "des", "et", "est", "un", "une", "en", "que", "qui"}
    tokens = set(re.findall(r"\b[a-zA-ZàâäéèêëîïôùûüçÀÂÄÉÈÊËÎÏÔÙÛÜÇ]+\b", text.lower()))
    matches = len(tokens & stopwords)
    return matches >= 4


def clean_text(raw: str) -> str:
    """Remove noise lines and preserve paragraph breaks using \\n\\n."""
    lines = raw.splitlines()
    cleaned = []
    for line in lines:
        line = line.strip()
        if len(line.split()) < 4:
            continue
        cleaned.append(line)
    # Join adjacent lines into paragraphs, keeping double newline as separator
    return "\n\n".join(cleaned)


def truncate_to_sentences(text: str, max_words: int) -> str:
    """Truncate text at a sentence boundary before max_words, preserving paragraph breaks."""
    paragraphs = text.split("\n\n")
    result_paragraphs = []
    total_count = 0

    for para in paragraphs:
        sentences = re.split(r"(?<=[.!?])\s+", para)
        para_sentences = []
        for s in sentences:
            w = len(s.split())
            if total_count + w > max_words:
                break
            para_sentences.append(s)
            total_count += w
        if para_sentences:
            result_paragraphs.append(" ".join(para_sentences))
        if total_count >= max_words:
            break

    return "\n\n".join(result_paragraphs) if result_paragraphs else text[: max_words * 6]


def scrape_article(url: str) -> str | None:
    """Fetch and extract main body text from a URL."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(resp.text, "lxml")

    # Remove noise elements
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "figure"]):
        tag.decompose()

    # Try semantic article tags first, then fall back to paragraphs
    article = soup.find("article")
    if article:
        paragraphs = article.find_all("p")
    else:
        paragraphs = soup.find_all("p")

    # Join each <p> with a newline so clean_text can preserve paragraph breaks
    text = "\n".join(p.get_text(separator=" ").strip() for p in paragraphs if p.get_text().strip())
    return clean_text(text) if text.strip() else None


def get_site_name(url: str) -> str:
    host = urlparse(url).netloc
    return host.replace("www.", "")


def search_and_fetch(level: str, topic: str) -> dict:
    query = build_query(level, topic)
    min_words, max_words = WORD_COUNT_TARGETS[level]

    results = []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region="fr-fr", max_results=6))
    except Exception as e:
        return {"error": "search_failed", "message": str(e)}

    if not results:
        return {
            "error": "no_results",
            "message": f"DuckDuckGo returned no results for query: {query}",
        }

    for result in results:
        url = result.get("href", "")
        if not url:
            continue

        text = scrape_article(url)
        if not text:
            continue

        if not is_french(text):
            continue

        word_count = len(text.split())

        if word_count < min_words:
            continue  # Too short, try next

        if word_count > max_words:
            text = truncate_to_sentences(text, max_words)
            word_count = len(text.split())

        return {
            "text": text,
            "url": url,
            "site_name": get_site_name(url),
            "word_count": word_count,
        }

    return {
        "error": "no_suitable_text",
        "message": (
            f"Could not find a French article between {min_words}–{max_words} words "
            f"for level={level}, topic={topic}. Try a different topic."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Search for a French article.")
    parser.add_argument("--level", required=True, choices=["A1", "A2", "B1", "B2", "C1"])
    parser.add_argument(
        "--topic",
        required=True,
        choices=list(TOPIC_LABELS.keys()),
    )
    args = parser.parse_args()

    result = search_and_fetch(args.level, args.topic)

    if "error" in result:
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
