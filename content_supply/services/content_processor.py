"""Content processor — dedup, tag extraction, quality scoring."""

import hashlib
import logging
import re
from collections import Counter

from content_supply.services.types import CrawledItem

logger = logging.getLogger(__name__)

# Common English stop words for tag extraction filtering
_STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "as", "be", "was", "were",
    "been", "are", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can", "shall", "not",
    "no", "nor", "so", "if", "then", "than", "that", "this", "these",
    "those", "its", "his", "her", "their", "our", "your", "my", "me",
    "we", "you", "he", "she", "they", "them", "us", "what", "which",
    "who", "whom", "how", "when", "where", "why", "all", "each", "every",
    "both", "few", "more", "most", "other", "some", "such", "only",
    "own", "same", "too", "very", "just", "about", "above", "after",
    "again", "also", "any", "because", "before", "between", "into",
    "through", "during", "here", "there", "out", "up", "down", "over",
    "under", "while", "new", "one", "two", "said", "get", "got", "go",
    "going", "like", "know", "think", "see", "make", "much", "well",
    "back", "even", "still", "way", "take", "come", "want", "look",
    "use", "find", "give", "tell", "work", "call", "try", "ask",
    "need", "feel", "become", "leave", "put", "mean", "keep", "let",
    "begin", "seem", "help", "show", "turn", "play", "run", "move",
    "live", "long", "part", "say", "thing", "things", "many",
})

# Regex: matches English words (2+ alpha chars) or individual CJK characters
_WORD_RE = re.compile(r"[a-zA-Z]{2,}|[\u4e00-\u9fff\u3400-\u4dbf]")


class ContentProcessor:
    """Process crawled items: dedup, extract tags, score quality."""

    def compute_content_hash(self, item: CrawledItem) -> str:
        """SHA256 hash of title + content for near-duplicate detection."""
        text = f"{item.title}|{item.content[:1000] if item.content else item.title}"
        return hashlib.sha256(text.encode()).hexdigest()

    def extract_tags(self, item: CrawledItem, max_tags: int = 5) -> list[str]:
        """Extract top keywords from title + content as tags.

        Strategy:
        1. Combine title + summary/content into a single string.
        2. Tokenize: extract English words (2+ letters) and individual CJK
           characters using a regex.
        3. Lowercase English tokens; filter out stop words and tokens that
           are purely numeric.
        4. Count frequencies and return the top *max_tags* keywords.
        """
        parts = [item.title, item.summary, item.content]
        text = " ".join(p for p in parts if p)
        if not text:
            return []

        tokens = _WORD_RE.findall(text.lower())

        # Filter stop words and numeric strings
        filtered = [t for t in tokens if t not in _STOP_WORDS and not t.isdigit()]

        counts = Counter(filtered)
        return [word for word, _ in counts.most_common(max_tags)]

    def score_quality(self, item: CrawledItem) -> float:
        """Score content quality 0-1.

        Formula:
        - content_length: min(len(content)/2000, 1.0) * 0.3
        - has_image:      0.2 if image_url else 0
        - source_reputation: 0.2 (default constant)
        - tag_richness:   min(len(tags)/5, 1.0) * 0.3
        """
        content_len = len(item.content) if item.content else 0
        content_score = min(content_len / 2000.0, 1.0) * 0.3

        has_image = 0.2 if item.image_url else 0.0

        source_reputation = 0.2

        tag_count = len(item.tags) if item.tags else 0
        tag_score = min(tag_count / 5.0, 1.0) * 0.3

        total = content_score + has_image + source_reputation + tag_score
        # Clamp to [0, 1]
        return round(max(0.0, min(1.0, total)), 4)

    def generate_item_id(self, item: CrawledItem) -> str:
        """Generate unique item ID from URL hash."""
        return hashlib.sha256(item.url.encode()).hexdigest()[:16]
