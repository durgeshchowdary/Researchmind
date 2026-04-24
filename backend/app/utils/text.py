import re
import string
from collections import Counter


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
    "in", "is", "it", "its", "of", "on", "that", "the", "to", "was", "were", "will",
    "with", "this", "these", "those", "or", "if", "then", "than", "into", "about",
    "their", "there", "here", "you", "your", "we", "our", "they", "them", "can",
}

PUNCT_TRANSLATION = str.maketrans("", "", string.punctuation)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_document_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def tokenize(text: str) -> list[str]:
    lowered = text.lower().translate(PUNCT_TRANSLATION)
    return [token for token in lowered.split() if token]


def preprocess_text(text: str) -> list[str]:
    tokens = tokenize(text)
    return [token for token in tokens if token not in STOPWORDS]


def highlight_terms(text: str, terms: list[str]) -> str:
    snippet = text
    for term in sorted(set(terms), key=len, reverse=True):
        if not term:
            continue
        snippet = re.sub(
            rf"(?i)\b({re.escape(term)})\b",
            r"**\1**",
            snippet,
        )
    return snippet


def make_snippet(text: str, max_chars: int = 240) -> str:
    cleaned = normalize_whitespace(text)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def sentence_split(text: str) -> list[str]:
    normalized = normalize_whitespace(text)
    if not normalized:
        return []
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    return [part.strip() for part in parts if part.strip()]


def lexical_overlap_score(text: str, query_terms: list[str]) -> float:
    if not text or not query_terms:
        return 0.0
    tokens = preprocess_text(text)
    if not tokens:
        return 0.0
    token_counts = Counter(tokens)
    matched_weight = sum(token_counts.get(term, 0) for term in set(query_terms))
    return matched_weight / max(len(tokens), 1)
