from typing import List, Dict
from datetime import datetime
from config import SmartClockConfig
from api_news_reader import ApiNewsFetcher
from rss_news_reader import RssNewsFetcher

from PyQt5 import QtWidgets
from PyQt5.QtGui import QFont

class NewsFetcher():
    def __init__(self, config: SmartClockConfig):
        self.sources = []
        self.current_source = 0
        self.news_count = config.get_max_stories()
        for new_config in config.get_news_sources():
            match new_config.type:
                case "api":
                   self.sources.append((new_config.name, ApiNewsFetcher(new_config, self.news_count)))
                case "rss":
                   self.sources.append((new_config.name, RssNewsFetcher(new_config)))
    
    def get_current_source(self) -> str:
        if self.current_source < len(self.sources):
            return self.sources[self.current_source][0]
        return ""

    def next_source(self):
        if len(self.sources) == 0:
            return
        self.current_source = (self.current_source + 1) % len(self.sources)

    def get_top_headlines(
        self,
    ) -> List[Dict]:
        if len(self.sources) == 0:
            return []
        return self.sources[self.current_source][1].get_top_headlines()[0:self.news_count]
    

class NewsManager():
    def __init__(self, config: SmartClockConfig, newsHeaderLabel, newsLayout):
        # setup train/news API
        self.news_reader = NewsFetcher(config)
        self.newsHeaderLabel = newsHeaderLabel
        self.newsLayout = newsLayout
        self.news_labels = []
        self.last_update = datetime.now()
        self.update_every_minutes = config.get_news_update_interval()

    def update_news(self):
        """Update news content"""
        # Get top headlines
        headlines = self.news_reader.get_top_headlines()
        self.last_update = datetime.now()
        # Update header
        self.newsHeaderLabel.setText(f"Latest News : {self.news_reader.get_current_source()} - updated @ {self.last_update.strftime('%H:%M:%S')}")


        # Update the list component with data from the news
        for label in self.news_labels:
            label.deleteLater()
        self.news_labels.clear()

        for item in headlines:
            label = QtWidgets.QLabel(item["title"])
            font = QFont('Times', 15)
            font.setBold(True)
            label.setFont(font)
            self.newsLayout.addWidget(label)
            self.news_labels.append(label)

    def next_source(self):
        self.news_reader.next_source()
        self.update_news()

    def update(self, current_time, visible):
        difference_minutes = (current_time - self.last_update).total_seconds() / 60
        if (difference_minutes > self.update_every_minutes) and visible:
            self.update_news()