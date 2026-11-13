from __future__ import annotations

import logging
from typing import Any
from xml.etree import ElementTree

import requests
from config import NewsSource

logger = logging.getLogger(__name__)


class RssNewsFetcher:
    """Fetches news headlines from an RSS feed."""

    def __init__(self, config: NewsSource, max_stories: int = 5) -> None:
        self.url = config.url
        self.max_stories = max_stories

    def get_top_headlines(self) -> list[dict[str, Any]]:
        """Fetch top headlines from the RSS feed."""
        response = requests.get(
            self.url,
            headers={"User-Agent": "JbClock/0.2"},
            timeout=10,
        )
        response.raise_for_status()

        tree = ElementTree.fromstring(response.content)
        headlines: list[dict[str, Any]] = []

        for item in tree.findall(".//channel/item"):
            headline: dict[str, Any] = {}
            for entry in item:
                tag = entry.tag.split("}")[-1] if "}" in entry.tag else entry.tag
                headline[tag] = (entry.text or "").strip()
            if headline.get("title"):
                headlines.append(headline)
            if len(headlines) >= self.max_stories:
                break

        return headlines
