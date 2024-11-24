import requests
from typing import List, Dict
from config import NewsSource

class ApiNewsFetcher:
    def __init__(self, config: NewsSource, page_size: int):
        """Initialize NewsFetcher with your API key from NewsAPI.org"""
        self.api_key = config.api_key
        self.url = config.url
        self.params = dict(config.params)
        self.params['pageSize'] = page_size
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def get_top_headlines(
        self,
    ) -> List[Dict]:
        """
        Fetch top headlines based on parameters
        
        Args:
            country: 2-letter ISO 3166-1 country code
            category: Category of news (business, entertainment, general, health, science, sports, technology)
            query: Keywords or phrases to search for
            page_size: Number of results to return (max 100)
        """
        
        response = requests.get(self.url, headers=self.headers, params=self.params)
        response.raise_for_status()
        
        return response.json()["articles"]