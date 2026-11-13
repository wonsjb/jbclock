from __future__ import annotations

import logging
from datetime import datetime, time
from typing import Any

import numpy as np
import pyaudio
from PyQt5 import QtWidgets

from config import SmartClockConfig

logger = logging.getLogger(__name__)


class Beeper:
    """Synthesizes and plays a modulated sine-wave alarm tone using PyAudio."""

    def __init__(self, volume: int) -> None:
        self.sample_rate = 44100
        self.frequency = 440  # Hz (A4 note)
        self.volume = max(0.0, min(1.0, volume / 100.0))
        self.alarm_running = False
        self.p: pyaudio.PyAudio | None = None
        self.stream: pyaudio.Stream | None = None
        self.current_time = 0.0

    def _ensure_pyaudio(self) -> pyaudio.PyAudio:
        if self.p is None:
            self.p = pyaudio.PyAudio()
        return self.p

    def generate_samples(self, duration: float) -> bytes:
        """Generate audio samples for a given duration."""
        num_samples = int(self.sample_rate * duration)
        t = np.linspace(
            self.current_time,
            self.current_time + duration,
            num_samples,
            endpoint=False,
        )
        samples = np.sin(2 * np.pi * self.frequency * t)
        samples *= np.sin(2 * np.pi * 2 * t)
        samples *= self.volume
        self.current_time += duration

        return samples.astype(np.float32).tobytes()

    def audio_callback(
        self,
        in_data: bytes | None,
        frame_count: int,
        time_info: dict[str, float],
        status: int,
    ) -> tuple[bytes, int]:
        """Callback for PyAudio stream."""
        samples = self.generate_samples(frame_count / self.sample_rate)
        return (samples, pyaudio.paContinue)

    def start_alarm(self) -> None:
        if self.alarm_running:
            return
        try:
            pa = self._ensure_pyaudio()
            self.current_time = 0.0
            self.stream = pa.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                output=True,
                stream_callback=self.audio_callback,
                frames_per_buffer=1024,
            )
            self.stream.start_stream()
            self.alarm_running = True
        except Exception as e:
            logger.error("Failed to start alarm audio stream: %s", e)

    def stop_alarm(self) -> None:
        if self.stream is not None:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.warning("Error closing alarm audio stream: %s", e)
            finally:
                self.stream = None
        self.alarm_running = False

    def close(self) -> None:
        self.stop_alarm()
        if self.p is not None:
            try:
                self.p.terminate()
            except Exception:
                pass
            self.p = None


class AlarmManager:
    """Manages weekday and weekend alarm schedules and triggers the beeper."""

    def __init__(self, config: SmartClockConfig) -> None:
        self.config = config
        self.enabled: bool = config.get_alarms_enabled()
        self.week_day_alarms: list[time] = [
            datetime.strptime(t, "%H:%M").time() for t in config.get_weekday_alarms()
        ]
        self.week_end_alarms: list[time] = [
            datetime.strptime(t, "%H:%M").time() for t in config.get_weekend_alarms()
        ]
        self.alarm_ringing = False
        self.beeper = Beeper(config.get_alarms_volume())
        self.last_alarm_check = datetime.now().time()

    def update_UI(
        self,
        weekday_widget: QtWidgets.QListWidget,
        weekend_widget: QtWidgets.QListWidget,
        enabled_widget: QtWidgets.QCheckBox,
    ) -> None:
        weekday_widget.clear()
        weekend_widget.clear()
        for alarm_t in self.week_day_alarms:
            weekday_widget.addItem(f"⏰  {alarm_t.strftime('%H:%M')}")
        for alarm_t in self.week_end_alarms:
            weekend_widget.addItem(f"⏰  {alarm_t.strftime('%H:%M')}")
        enabled_widget.setChecked(self.enabled)

    def start_if_necessary(self, current_datetime: datetime) -> bool:
        current_time = current_datetime.time()
        # Did we pass midnight?
        if self.last_alarm_check > current_time:
            self.last_alarm_check = time(0, 0, 0)

        current_day = current_datetime.date()
        started = False
        list_to_check = (
            self.week_day_alarms if current_day.weekday() < 5 else self.week_end_alarms
        )

        for alarm_time in list_to_check:
            if self.last_alarm_check < alarm_time <= current_time:
                if self.enabled:
                    started = self.start_alarm()
                break

        self.last_alarm_check = current_time
        return started

    def update_enabled(self, state: Any) -> None:
        self.enabled = bool(state)
        self.config.set_alarms_enabled(self.enabled)
        try:
            self.config.save_config()
        except Exception as e:
            logger.warning("Could not persist alarm enabled state: %s", e)

    def stop_alarm(self) -> None:
        if self.alarm_ringing:
            self.alarm_ringing = False
            self.beeper.stop_alarm()

    def start_alarm(self) -> bool:
        if not self.alarm_ringing:
            self.alarm_ringing = True
            self.beeper.start_alarm()
            return True
        return False
