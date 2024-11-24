import requests
from typing import List, Dict
from config import NewsSource
from xml.etree import ElementTree

class RssNewsFetcher:
    def __init__(self, config: NewsSource):
        """Initialize RssNewsFetcher"""
        self.url = config.url

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
            
        response = requests.get(self.url)
        response.raise_for_status()
        
        tree = ElementTree.fromstring(response.content)

        headlines = []
        for child in tree:
            if child.tag == "channel":
                for item in child:
                    if item.tag == "item":
                        headline = {}
                        for entry in item:
                            headline[entry.tag] = entry.text
                        headlines.append(headline)
                    if len(headlines) == 5:
                        break

        return headlines