from __future__ import annotations

import logging
from typing import Any

import requests
from config import NewsSource

logger = logging.getLogger(__name__)


class ApiNewsFetcher:
    """Fetches news headlines from NewsAPI.org."""

    def __init__(self, config: NewsSource, page_size: int = 5) -> None:
        self.api_key = config.api_key or ""
        self.url = config.url
        self.params: dict[str, Any] = dict(config.params or {})
        self.params["pageSize"] = page_size
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def get_top_headlines(self) -> list[dict[str, Any]]:
        """Fetch top headlines based on configured parameters."""
        response = requests.get(
            self.url,
            headers=self.headers,
            params=self.params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return list(data.get("articles", []))
