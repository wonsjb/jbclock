from __future__ import annotations

import logging
import tomllib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import tomli_w

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RadioStream:
    name: str
    uri: str


@dataclass(slots=True)
class NewsSource:
    type: str
    name: str
    url: str
    api_key: str | None = None
    params: dict[str, Any] = field(default_factory=dict)


class SmartClockConfig:
    """Manages reading, validating, and writing the TOML configuration."""

    def __init__(self, config_path: str | Path = "config.toml") -> None:
        self.config_path = Path(config_path)
        if not self.config_path.is_absolute():
            self.config_path = Path(__file__).resolve().parent / self.config_path
        self.config: dict[str, Any] = self._load_config()

    def __str__(self) -> str:
        """Create a human-readable string representation of the configuration."""
        sections: list[str] = []

        # Alarms section
        weekday = self.get_weekday_alarms()
        weekend = self.get_weekend_alarms()
        alarm_lines = [
            "ALARMS:",
            f"  Enabled: {self.get_alarms_enabled()}",
            f"  Volume: {self.get_alarms_volume()}%",
            f"  Weekday alarms: {', '.join(weekday) if weekday else 'None'}",
            f"  Weekend alarms: {', '.join(weekend) if weekend else 'None'}",
        ]
        sections.append("\n".join(alarm_lines))

        # Radio section
        radio_streams = self.get_radio_streams()
        radio_lines = [
            "RADIO:",
            f"  Default volume: {self.get_radio_volume()}%",
            "  Available stations:",
        ]
        radio_lines.extend(f"    - {stream.name}" for stream in radio_streams)
        sections.append("\n".join(radio_lines))

        # News section
        news_sources = self.get_news_sources()
        news_lines = [
            "NEWS:",
            f"  Update interval: {self.get_news_update_interval()} minutes",
            f"  Max stories: {self.get_max_stories()}",
            "  Sources:",
        ]
        news_lines.extend(f"    - {source.name} ({source.type})" for source in news_sources)
        sections.append("\n".join(news_lines))

        # Trains section
        home, destination = self.get_train_stations()
        train_lines = [
            "TRAINS:",
            f"  Home station: {home}",
            f"  Destination: {destination}",
        ]
        sections.append("\n".join(train_lines))

        # Weather section
        weather_lines = [
            "WEATHER:",
            f"  Location: {self.get_weather_location()}",
            f"  API key configured: {bool(self.get_weather_api_key())}",
        ]
        sections.append("\n".join(weather_lines))

        # Webcam section
        webcam_lines = [
            "WEBCAM:",
            f"  Enabled: {self.is_webcam_enabled()}",
            f"  PIN configured: {bool(self.get_webcam_pin())}",
        ]
        sections.append("\n".join(webcam_lines))

        return "\n\n".join(sections)

    def _load_config(self) -> dict[str, Any]:
        """Load the configuration from the TOML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {self.config_path}")
        try:
            with self.config_path.open("rb") as f:
                return tomllib.load(f)
        except Exception as e:
            raise RuntimeError(f"Error loading configuration from {self.config_path}: {e}") from e

    def save_config(self) -> None:
        """Save the current configuration back to the TOML file."""
        try:
            with self.config_path.open("wb") as f:
                tomli_w.dump(self.config, f)
        except Exception as e:
            logger.error("Error saving configuration: %s", e)
            raise RuntimeError(f"Error saving configuration: {e}") from e

    # Alarm Methods
    def get_weekday_alarms(self) -> list[str]:
        return list(self.config.get("alarms", {}).get("weekday", []))

    def get_weekend_alarms(self) -> list[str]:
        return list(self.config.get("alarms", {}).get("weekend", []))

    def set_weekday_alarms(self, alarms: list[str]) -> None:
        self._validate_time_list(alarms)
        self.config.setdefault("alarms", {})["weekday"] = alarms

    def set_weekend_alarms(self, alarms: list[str]) -> None:
        self._validate_time_list(alarms)
        self.config.setdefault("alarms", {})["weekend"] = alarms

    def get_alarms_enabled(self) -> bool:
        return bool(self.config.get("alarms", {}).get("enabled", False))

    def set_alarms_enabled(self, enabled: bool) -> None:
        self.config.setdefault("alarms", {})["enabled"] = bool(enabled)

    def get_alarms_volume(self) -> int:
        return int(self.config.get("alarms", {}).get("volume", 50))

    def set_alarms_volume(self, volume: int) -> None:
        if not 0 <= volume <= 100:
            raise ValueError("Volume must be between 0 and 100")
        self.config.setdefault("alarms", {})["volume"] = int(volume)

    # Keep backwards-compatible alias just in case
    set_alarms_volumes = set_alarms_volume

    # Radio Methods
    def get_radio_volume(self) -> int:
        return int(self.config.get("radio", {}).get("default_volume", 50))

    def set_radio_volume(self, volume: int) -> None:
        if not 0 <= volume <= 100:
            raise ValueError("Volume must be between 0 and 100")
        self.config.setdefault("radio", {})["default_volume"] = int(volume)

    def get_radio_streams(self) -> list[RadioStream]:
        streams = self.config.get("radio", {}).get("streams", [])
        return [RadioStream(name=s["name"], uri=s["uri"]) for s in streams]

    def add_radio_stream(self, name: str, uri: str) -> None:
        self.config.setdefault("radio", {}).setdefault("streams", []).append(
            {"name": name, "uri": uri}
        )

    def remove_radio_stream(self, name: str) -> None:
        streams = self.config.get("radio", {}).get("streams", [])
        self.config.setdefault("radio", {})["streams"] = [
            s for s in streams if s.get("name") != name
        ]

    # News Methods
    def get_news_sources(self) -> list[NewsSource]:
        sources = self.config.get("news", {}).get("sources", [])
        result: list[NewsSource] = []
        for s in sources:
            result.append(
                NewsSource(
                    type=s["type"],
                    name=s["name"],
                    url=s["url"],
                    api_key=s.get("api_key"),
                    params=dict(s.get("params") or {}),
                )
            )
        return result

    def add_news_source(self, source: NewsSource) -> None:
        source_dict: dict[str, Any] = {
            "type": source.type,
            "name": source.name,
            "url": source.url,
        }
        if source.api_key:
            source_dict["api_key"] = source.api_key
        if source.params:
            source_dict["params"] = source.params
        self.config.setdefault("news", {}).setdefault("sources", []).append(source_dict)

    def remove_news_source(self, name: str) -> None:
        sources = self.config.get("news", {}).get("sources", [])
        self.config.setdefault("news", {})["sources"] = [
            s for s in sources if s.get("name") != name
        ]

    def get_news_update_interval(self) -> int:
        return int(self.config.get("news", {}).get("update_interval", 30))

    def set_news_update_interval(self, interval: int) -> None:
        if interval < 1:
            raise ValueError("Update interval must be at least 1 minute")
        self.config.setdefault("news", {})["update_interval"] = int(interval)

    def get_max_stories(self) -> int:
        return int(self.config.get("news", {}).get("max_stories", 5))

    def set_max_stories(self, max_stories: int) -> None:
        if max_stories < 1:
            raise ValueError("Max stories must be at least 1")
        self.config.setdefault("news", {})["max_stories"] = int(max_stories)

    # Train Methods
    def get_train_stations(self) -> tuple[str, str]:
        trains = self.config.get("trains", {})
        return (
            trains.get("home_station", ""),
            trains.get("destination_station", ""),
        )

    def set_train_stations(self, home: str, destination: str) -> None:
        trains = self.config.setdefault("trains", {})
        trains["home_station"] = home
        trains["destination_station"] = destination

    def get_train_api_key(self) -> str:
        return str(self.config.get("trains", {}).get("api_key", ""))

    def set_train_api_key(self, api_key: str) -> None:
        self.config.setdefault("trains", {})["api_key"] = api_key

    # Weather Methods
    def get_weather_location(self) -> str:
        return str(self.config.get("weather", {}).get("location", ""))

    def set_weather_location(self, location: str) -> None:
        self.config.setdefault("weather", {})["location"] = location

    def get_weather_api_key(self) -> str:
        return str(self.config.get("weather", {}).get("api_key", ""))

    def set_weather_api_key(self, api_key: str) -> None:
        self.config.setdefault("weather", {})["api_key"] = api_key

    @staticmethod
    def _validate_time_list(times: list[str]) -> None:
        for time_str in times:
            try:
                datetime.strptime(time_str, "%H:%M")
            except ValueError as e:
                raise ValueError(f"Invalid time format: {time_str}. Use HH:MM format") from e

    # Webcam Methods
    def get_webcam_url(self) -> str:
        return str(self.config.get("webcam", {}).get("url", ""))

    def set_webcam_url(self, url: str) -> None:
        self.config.setdefault("webcam", {})["url"] = url

    def get_webcam_camera_name(self) -> str:
        return str(self.config.get("webcam", {}).get("camera_name", "Victor"))

    def is_webcam_enabled(self) -> bool:
        return bool(self.config.get("webcam", {}).get("enabled", False))

    def get_webcam_pin(self) -> str:
        return str(self.config.get("webcam", {}).get("pin_code", ""))


def main() -> None:
    config = SmartClockConfig("config.toml")
    print(config)


if __name__ == "__main__":
    main()
