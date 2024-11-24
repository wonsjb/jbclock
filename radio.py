import vlc
from typing import Optional, Dict
from config import SmartClockConfig

class RadioPlayer:
    def __init__(self, config: SmartClockConfig):
        # Initialize VLC instance
        self.instance = vlc.Instance('--no-xlib')
        self.player = self.instance.media_player_new()
        self.player.audio_set_volume(config.get_radio_volume())
        self.current_station: Optional[str] = None
        self.is_playing = False
        
        # Dictionary of radio stations and their stream URLs
        self.stations: Dict[str, str] = {stream.name: stream.uri for stream in config.get_radio_streams()}

    def add_station(self, name: str, url: str):
        """Add a new radio station"""
        self.stations[name] = url
        self.save_stations()

    def remove_station(self, name: str):
        """Remove a radio station"""
        if name in self.stations:
            del self.stations[name]
            self.save_stations()

    def play(self, station_name: str) -> bool:
        """Play selected radio station"""
        try:
            if station_name in self.stations:
                # Stop current playback if any
                self.stop()
                
                # Create and play new media
                url = self.stations[station_name]
                media = self.instance.media_new(url)
                self.player.set_media(media)
                self.player.play()
                
                self.current_station = station_name
                self.is_playing = True
                return True
            return False
        except Exception as e:
            print(f"Error playing station: {e}")
            return False

    def get_current_track(self):
        """
        Get the current track information.
        
        Returns:
            str: The current track title or None if not available
        """
        media = self.player.get_media()
        if media:
            media.parse_with_options(vlc.MediaParseFlag.local, 0)
            return media.get_meta(vlc.Meta.NowPlaying)
        return None

    def stop(self):
        """Stop radio playback"""
        self.player.stop()
        self.is_playing = False
        self.current_station = None

    def set_volume(self, volume: int):
        """Set volume (0-100)"""
        self.player.audio_set_volume(volume)

    def get_volume(self) -> int:
        """Get current volume"""
        return self.player.audio_get_volume()

    def get_station_list(self) -> list:
        """Get list of available stations"""
        return list(self.stations.keys())

    def get_current_station(self) -> Optional[str]:
        """Get currently playing station name"""
        return self.current_station

    def is_station_playing(self) -> bool:
        """Check if radio is currently playing"""
        return self.is_playing


class RadioManager():

    def __init__(self, config: SmartClockConfig):
        self.config = config
        self.radio_player = RadioPlayer(config)
        self.status_message = ""
        self.played_station = ""

    def update_radio_list(self, radioListWidget, volumeSlider):
        """Update the radio stations list"""
        radioListWidget.clear()
        radioListWidget.addItems(self.radio_player.get_station_list())
        volumeSlider.setValue(self.config.get_radio_volume())

    def play_radio(self, station):
        """Play radio station"""
        if self.radio_player.play(station):
            self.status_message = f"Playing: {station}"
            self.played_station = station
        else:
            self.status_message = "Error playing station"
            self.played_station = ""

    def stop_radio(self):
        """Stop radio playback"""
        self.radio_player.stop()
        self.status_message = "Radio stopped"
        self.played_station = ""

    def set_volume(self, value):
        """Set radio volume"""
        self.radio_player.set_volume(value)

    def get_current_track(self):
        return self.radio_player.get_current_track()
    

    def get_status_message(self):
        if self.played_station != "":
            return f"Playing: {self.played_station} -- {self.get_current_track()}"
        else:
            return ""
