import tomli
import tomli_w
from typing import List, Dict, Union, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class RadioStream:
    name: str
    uri: str

@dataclass
class NewsSource:
    type: str
    name: str
    url: str
    api_key: Optional[str] = None
    params: Optional[Dict] = None

class SmartClockConfig:
    def __init__(self, config_path: str):
        """Initialize the configuration manager with the path to the TOML file."""
        self.config_path = config_path
        self.config = self._load_config()

    def __str__(self) -> str:
        """Create a human-readable string representation of the configuration."""
        sections = []
        
        # Alarms section
        alarm_lines = [
            "ALARMS:",
            f"  Enabled: {self.get_alarms_enabled()}",
            "  Weekday alarms: " + ", ".join(self.get_weekday_alarms()) if self.get_weekday_alarms() else "  Weekday alarms: None",
            "  Weekend alarms: " + ", ".join(self.get_weekend_alarms()) if self.get_weekend_alarms() else "  Weekend alarms: None"
        ]
        sections.append("\n".join(alarm_lines))

        # Radio section
        radio_streams = self.get_radio_streams()
        radio_lines = [
            "RADIO:",
            f"  Default volume: {self.get_radio_volume()}%",
            "  Available stations:"
        ]
        radio_lines.extend(f"    - {stream.name}" for stream in radio_streams)
        sections.append("\n".join(radio_lines))

        # News section
        news_sources = self.get_news_sources()
        news_lines = [
            "NEWS:",
            f"  Update interval: {self.get_news_update_interval()} minutes",
            f"  Max stories: {self.get_max_stories()}",
            "  Sources:"
        ]
        news_lines.extend(f"    - {source.name} ({source.type})" for source in news_sources)
        sections.append("\n".join(news_lines))

        # Trains section
        home, destination = self.get_train_stations()
        train_lines = [
            "TRAINS:",
            f"  Home station: {home}",
            f"  Destination: {destination}",
            "  Check times: " + ", ".join(self.get_train_check_times())
        ]
        sections.append("\n".join(train_lines))

        # Weather section
        weather_lines = [
            "WEATHER:",
            f"  API key: {self.get_weather_api_key()}",
            f"  Location: {self.get_weather_location()}"
        ]
        sections.append("\n".join(weather_lines))

        return "\n\n".join(sections)

    def _load_config(self) -> Dict:
        """Load the configuration from the TOML file."""
        try:
            with open(self.config_path, "rb") as f:
                return tomli.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found at {self.config_path}")
        except Exception as e:
            raise Exception(f"Error loading configuration: {str(e)}")

    def save_config(self) -> None:
        """Save the current configuration back to the TOML file."""
        try:
            with open(self.config_path, "wb") as f:
                tomli_w.dump(self.config, f)
        except Exception as e:
            raise Exception(f"Error saving configuration: {str(e)}")

    # Alarm Methods
    def get_weekday_alarms(self) -> List[str]:
        """Get list of weekday alarm times."""
        return self.config["alarms"]["weekday"]

    def get_weekend_alarms(self) -> List[str]:
        """Get list of weekend alarm times."""
        return self.config["alarms"]["weekend"]

    def set_weekday_alarms(self, alarms: List[str]) -> None:
        """Set weekday alarm times."""
        self._validate_time_list(alarms)
        self.config["alarms"]["weekday"] = alarms

    def set_weekend_alarms(self, alarms: List[str]) -> None:
        """Set weekend alarm times."""
        self._validate_time_list(alarms)
        self.config["alarms"]["weekend"] = alarms

    def get_alarms_enabled(self) -> bool:
        """Check if alarms are enabled."""
        return self.config["alarms"]["enabled"]

    def set_alarms_enabled(self, enabled: bool) -> None:
        """Enable or disable alarms."""
        self.config["alarms"]["enabled"] = enabled

    def get_alarms_volume(self) -> int:
        """Get the alarm volume."""
        return self.config["alarms"]["volume"]

    def set_alarms_volumes(self, volume: int) -> None:
        """Set the alarm volume."""
        self.config["alarms"]["volume"] = int

    # Radio Methods
    def get_radio_volume(self) -> int:
        """Get the default radio volume."""
        return self.config["radio"]["default_volume"]

    def set_radio_volume(self, volume: int) -> None:
        """Set the default radio volume."""
        if not 0 <= volume <= 100:
            raise ValueError("Volume must be between 0 and 100")
        self.config["radio"]["default_volume"] = volume

    def get_radio_streams(self) -> List[RadioStream]:
        """Get list of radio streams."""
        return [RadioStream(**stream) for stream in self.config["radio"]["streams"]]

    def add_radio_stream(self, name: str, uri: str) -> None:
        """Add a new radio stream."""
        self.config["radio"]["streams"].append({"name": name, "uri": uri})

    def remove_radio_stream(self, name: str) -> None:
        """Remove a radio stream by name."""
        self.config["radio"]["streams"] = [
            stream for stream in self.config["radio"]["streams"]
            if stream["name"] != name
        ]

    # News Methods
    def get_news_sources(self) -> List[NewsSource]:
        """Get list of news sources."""
        return [NewsSource(**source) for source in self.config["news"]["sources"]]

    def add_news_source(self, source: NewsSource) -> None:
        """Add a new news source."""
        source_dict = {
            "type": source.type,
            "name": source.name,
            "url": source.url
        }
        if source.api_key:
            source_dict["api_key"] = source.api_key
        if source.params:
            source_dict["params"] = source.params
        self.config["news"]["sources"].append(source_dict)

    def remove_news_source(self, name: str) -> None:
        """Remove a news source by name."""
        self.config["news"]["sources"] = [
            source for source in self.config["news"]["sources"]
            if source["name"] != name
        ]

    def get_news_update_interval(self) -> int:
        """Get news update interval in minutes."""
        return self.config["news"]["update_interval"]

    def set_news_update_interval(self, interval: int) -> None:
        """Set news update interval in minutes."""
        if interval < 1:
            raise ValueError("Update interval must be at least 1 minute")
        self.config["news"]["update_interval"] = interval

    def get_max_stories(self) -> int:
        """Get maximum number of news stories."""
        return self.config["news"]["max_stories"]

    def set_max_stories(self, max_stories: int) -> None:
        """Set maximum number of news stories."""
        if max_stories < 1:
            raise ValueError("Max stories must be at least 1")
        self.config["news"]["max_stories"] = max_stories

    # Train Methods
    def get_train_stations(self) -> tuple[str, str]:
        """Get home and destination stations."""
        return (
            self.config["trains"]["home_station"],
            self.config["trains"]["destination_station"]
        )

    def set_train_stations(self, home: str, destination: str) -> None:
        """Set home and destination stations."""
        self.config["trains"]["home_station"] = home
        self.config["trains"]["destination_station"] = destination

    def get_train_api_key(self) -> str:
        """Get transport API key."""
        return self.config["trains"]["api_key"]

    def set_train_api_key(self, api_key: str) -> None:
        """Set transport API key."""
        self.config["trains"]["api_key"] = api_key

    def get_weather_location(self) -> str:
        """Get weather location."""
        return self.config["weather"]["location"]

    def set_weather_location(self, location: str) -> None:
        """Set weather location."""
        self.config["weather"]["location"] = location

    def get_weather_api_key(self) -> str:
        """Get weather API key."""
        return self.config["weather"]["api_key"]

    def set_weather_api_key(self, api_key: str) -> None:
        """Set weather API key."""
        self.config["weather"]["api_key"] = api_key

    @staticmethod
    def _validate_time_list(times: List[str]) -> None:
        """Validate a list of time strings in HH:MM format."""
        for time_str in times:
            try:
                datetime.strptime(time_str, "%H:%M")
            except ValueError:
                raise ValueError(f"Invalid time format: {time_str}. Use HH:MM format")

def main():
    config = SmartClockConfig("config.toml")
    print(str(config))


if __name__ == "__main__":
    main()