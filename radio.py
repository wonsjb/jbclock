from __future__ import annotations

import logging

import vlc
from PyQt5 import QtWidgets

from config import SmartClockConfig

logger = logging.getLogger(__name__)


class RadioPlayer:
    """Wraps libVLC for internet radio playback."""

    def __init__(self, config: SmartClockConfig) -> None:
        self.instance = vlc.Instance("--no-xlib")
        self.player = self.instance.media_player_new()
        self.volume = config.get_radio_volume()
        self.current_station: str | None = None
        self.is_playing = False

        self.stations: dict[str, str] = {
            stream.name: stream.uri for stream in config.get_radio_streams()
        }

    def play(self, station_name: str) -> bool:
        """Play selected radio station."""
        try:
            if station_name not in self.stations:
                logger.warning("Station %r not found in configuration", station_name)
                return False

            self.stop()

            url = self.stations[station_name]
            media = self.instance.media_new(url)
            self.player.set_media(media)
            self.player.play()
            self.player.audio_set_volume(self.volume)

            self.current_station = station_name
            self.is_playing = True
            return True
        except Exception as e:
            logger.error("Error playing station %s: %s", station_name, e)
            return False

    def get_current_track(self) -> str | None:
        """Get the current track metadata without re-triggering parser on every call."""
        media = self.player.get_media()
        if media is not None:
            now_playing = media.get_meta(vlc.Meta.NowPlaying)
            if now_playing:
                return str(now_playing)
            title = media.get_meta(vlc.Meta.Title)
            if title and title != self.current_station:
                return str(title)
        return None

    def stop(self) -> None:
        """Stop radio playback."""
        try:
            self.player.stop()
        except Exception as e:
            logger.warning("Error stopping VLC player: %s", e)
        self.is_playing = False
        self.current_station = None

    def set_volume(self, volume: int) -> None:
        """Set volume (0-100)."""
        self.volume = max(0, min(100, int(volume)))
        self.player.audio_set_volume(self.volume)

    def get_volume(self) -> int:
        """Get current volume."""
        vol = self.player.audio_get_volume()
        return self.volume if vol < 0 else vol

    def get_station_list(self) -> list[str]:
        """Get list of available stations."""
        return list(self.stations.keys())

    def get_current_station(self) -> str | None:
        """Get currently playing station name."""
        return self.current_station

    def is_station_playing(self) -> bool:
        """Check if radio is currently playing."""
        return self.is_playing


class RadioManager:
    """Manages radio station selection, volume control, and UI synchronization."""

    def __init__(self, config: SmartClockConfig) -> None:
        self.config = config
        self.radio_player = RadioPlayer(config)
        self.status_message = ""
        self.played_station = ""

    def update_radio_list(
        self,
        radio_list_widget: QtWidgets.QListWidget,
        volume_slider: QtWidgets.QSlider,
    ) -> None:
        """Update the radio stations list and volume slider."""
        radio_list_widget.clear()
        stations = self.radio_player.get_station_list()
        radio_list_widget.addItems(stations)
        if stations and radio_list_widget.currentRow() < 0:
            radio_list_widget.setCurrentRow(0)
        volume_slider.setValue(self.config.get_radio_volume())

    def get_stations(self) -> list[str]:
        return self.radio_player.get_station_list()

    def play_radio(self, station: str) -> bool:
        """Play radio station by name."""
        if self.radio_player.play(station):
            self.status_message = f"Playing: {station}"
            self.played_station = station
            return True
        self.status_message = "Error playing station"
        self.played_station = ""
        return False

    def stop_radio(self) -> None:
        """Stop radio playback."""
        self.radio_player.stop()
        self.status_message = "Radio stopped"
        self.played_station = ""

    def set_volume(self, value: int) -> None:
        """Set radio volume."""
        self.radio_player.set_volume(value)

    def get_volume(self) -> int:
        return self.radio_player.volume

    def get_current_track(self) -> str | None:
        return self.radio_player.get_current_track()

    def get_status_message(self) -> str:
        if self.played_station:
            track = self.get_current_track()
            if track:
                return f"📻 {self.played_station}  —  {track}"
            return f"📻 {self.played_station}"
        return ""
