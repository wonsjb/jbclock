from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Protocol

from PyQt5 import QtWidgets
from PyQt5.QtCore import QObject, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

from api_news_reader import ApiNewsFetcher
from config import SmartClockConfig
from rss_news_reader import RssNewsFetcher

logger = logging.getLogger(__name__)


class NewsSourceFetcher(Protocol):
    def get_top_headlines(self) -> list[dict[str, Any]]: ...


class NewsFetcher:
    """Manages multiple news sources and fetches headlines from the active source."""

    def __init__(self, config: SmartClockConfig) -> None:
        self.sources: list[tuple[str, NewsSourceFetcher]] = []
        self.current_source = 0
        self.news_count = config.get_max_stories()

        for src_config in config.get_news_sources():
            match src_config.type:
                case "api":
                    self.sources.append(
                        (src_config.name, ApiNewsFetcher(src_config, self.news_count))
                    )
                case "rss":
                    self.sources.append(
                        (src_config.name, RssNewsFetcher(src_config, self.news_count))
                    )
                case _:
                    logger.warning("Unknown news source type: %s", src_config.type)

    def get_current_source(self) -> str:
        if 0 <= self.current_source < len(self.sources):
            return self.sources[self.current_source][0]
        return "None"

    def next_source(self) -> None:
        if not self.sources:
            return
        self.current_source = (self.current_source + 1) % len(self.sources)

    def get_top_headlines(self) -> list[dict[str, Any]]:
        if not self.sources:
            return []
        return self.sources[self.current_source][1].get_top_headlines()[: self.news_count]


class _NewsWorker(QThread):
    finished_headlines = pyqtSignal(str, list, str)

    def __init__(self, fetcher: NewsFetcher) -> None:
        super().__init__()
        self.fetcher = fetcher

    def run(self) -> None:
        source_name = self.fetcher.get_current_source()
        try:
            headlines = self.fetcher.get_top_headlines()
            self.finished_headlines.emit(source_name, headlines, "")
        except Exception as e:
            logger.error("Failed to fetch news from %s: %s", source_name, e)
            self.finished_headlines.emit(source_name, [], str(e))


class NewsManager(QObject):
    """Coordinates news fetching in background threads and updates the UI."""

    def __init__(
        self,
        config: SmartClockConfig,
        news_header_label: QtWidgets.QLabel,
        news_layout: QtWidgets.QVBoxLayout,
    ) -> None:
        super().__init__()
        self.news_reader = NewsFetcher(config)
        self.newsHeaderLabel = news_header_label
        self.newsLayout = news_layout
        self.news_widgets: list[QtWidgets.QWidget] = []
        self.last_update = datetime.min
        self.update_every_minutes = config.get_news_update_interval()
        self._worker: _NewsWorker | None = None

        self.newsLayout.setAlignment(Qt.AlignTop)
        self.newsLayout.setSpacing(10)

    def update_news(self) -> None:
        """Start an asynchronous news update."""
        if self._worker is not None and self._worker.isRunning():
            return

        source_name = self.news_reader.get_current_source()
        self.newsHeaderLabel.setText(f"Latest News: {source_name} (Refreshing...)")
        self.last_update = datetime.now()

        self._worker = _NewsWorker(self.news_reader)
        self._worker.finished_headlines.connect(self._on_headlines_ready)
        self._worker.start()

    def _clear_widgets(self) -> None:
        for widget in self.news_widgets:
            self.newsLayout.removeWidget(widget)
            widget.deleteLater()
        self.news_widgets.clear()

    def _on_headlines_ready(
        self, source_name: str, headlines: list[dict[str, Any]], error: str
    ) -> None:
        now_str = datetime.now().strftime("%H:%M:%S")
        self.newsHeaderLabel.setText(f"Latest News: {source_name}  •  Updated {now_str}")
        self._clear_widgets()

        if error:
            err_label = QtWidgets.QLabel(f"Unable to load news: {error}")
            err_label.setWordWrap(True)
            err_label.setStyleSheet("color: #f87171; font-size: 16px; padding: 12px;")
            self.newsLayout.addWidget(err_label)
            self.news_widgets.append(err_label)
            return

        if not headlines:
            empty_label = QtWidgets.QLabel("No headlines available.")
            empty_label.setStyleSheet("color: #94a3b8; font-size: 16px; padding: 12px;")
            self.newsLayout.addWidget(empty_label)
            self.news_widgets.append(empty_label)
            return

        for idx, item in enumerate(headlines, start=1):
            title = item.get("title") or "Untitled"
            card = QtWidgets.QFrame()
            card.setStyleSheet(
                "QFrame { background-color: #1e293b; border: 1px solid #334155; "
                "border-radius: 10px; }"
            )
            card_layout = QtWidgets.QVBoxLayout(card)
            card_layout.setContentsMargins(14, 10, 14, 10)

            label = QtWidgets.QLabel(f"{idx}. {title}")
            label.setWordWrap(True)
            font = QFont("Sans Serif", 14)
            font.setBold(True)
            label.setFont(font)
            label.setStyleSheet("border: none; background: transparent; color: #f8fafc; padding: 0;")
            card_layout.addWidget(label)

            self.newsLayout.addWidget(card)
            self.news_widgets.append(card)

    def next_source(self) -> None:
        self.news_reader.next_source()
        self.update_news()

    def update(self, current_time: datetime, visible: bool) -> None:
        difference_minutes = (current_time - self.last_update).total_seconds() / 60
        if difference_minutes >= self.update_every_minutes and visible:
            self.update_news()
