from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Any

import requests
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from config import SmartClockConfig

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent


class _WeatherWorker(QThread):
    finished_weather = pyqtSignal(dict, dict, str)

    def __init__(self, location: str, api_key: str) -> None:
        super().__init__()
        self.location = location
        self.api_key = api_key

    def _build_query_params(self) -> dict[str, str]:
        loc = self.location.strip()
        params: dict[str, str] = {
            "appid": self.api_key,
            "units": "metric",
        }
        # If the location contains digits (e.g. a UK postcode like 'IP8 4RW'),
        # OpenWeatherMap requires the 'zip' parameter rather than 'q'.
        if any(ch.isdigit() for ch in loc):
            params["zip"] = loc if "," in loc else f"{loc},GB"
        else:
            params["q"] = loc
        return params

    def run(self) -> None:
        try:
            weather_url = "https://api.openweathermap.org/data/2.5/weather"
            params = self._build_query_params()
            resp = requests.get(weather_url, params=params, timeout=10)
            resp.raise_for_status()
            weather_data = resp.json()

            forecast_url = "https://api.openweathermap.org/data/2.5/forecast"
            f_resp = requests.get(forecast_url, params=params, timeout=10)
            f_resp.raise_for_status()
            forecast_data = f_resp.json()

            self.finished_weather.emit(weather_data, forecast_data, "")
        except Exception as e:
            logger.error("Error fetching weather: %s", e)
            self.finished_weather.emit({}, {}, str(e))


class WeatherWidget(QWidget):
    """Displays current weather conditions and 3-hour forecasts."""

    def __init__(self, config: SmartClockConfig) -> None:
        super().__init__()
        self.count = 8
        self.location = config.get_weather_location()
        self.api_key = config.get_weather_api_key()
        self._worker: _WeatherWorker | None = None
        self.sheet_day: QPixmap | None = None
        self.sheet_night: QPixmap | None = None
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        # Current weather card
        current_card = QFrame()
        current_card.setStyleSheet(
            "QFrame { background-color: #1e293b; border: 1px solid #334155; "
            "border-radius: 12px; }"
        )
        current_layout = QHBoxLayout(current_card)
        current_layout.setContentsMargins(20, 10, 20, 10)
        current_layout.setSpacing(20)

        self.current_icon = QLabel()
        self.current_icon.setAlignment(Qt.AlignCenter)
        self.current_icon.setStyleSheet("border: none; background: transparent; padding: 0;")

        info_layout = QVBoxLayout()
        info_layout.setAlignment(Qt.AlignVCenter)
        self.current_temp = QLabel("--°C")
        self.current_temp.setStyleSheet(
            "font-size: 42px; font-weight: bold; color: #f8fafc; border: none; background: transparent; padding: 0;"
        )
        self.current_description = QLabel(f"Loading {self.location}...")
        self.current_description.setStyleSheet(
            "font-size: 18px; color: #94a3b8; border: none; background: transparent; padding: 0;"
        )
        info_layout.addWidget(self.current_temp)
        info_layout.addWidget(self.current_description)

        current_layout.addStretch()
        current_layout.addWidget(self.current_icon)
        current_layout.addLayout(info_layout)
        current_layout.addStretch()
        layout.addWidget(current_card, stretch=1)

        # Forecast row
        forecast_layout = QHBoxLayout()
        forecast_layout.setSpacing(8)
        self.forecast_icons: list[QLabel] = []
        self.forecast_temps: list[QLabel] = []

        for _ in range(self.count):
            day_card = QFrame()
            day_card.setStyleSheet(
                "QFrame { background-color: #1e293b; border: 1px solid #334155; "
                "border-radius: 10px; }"
            )
            day_layout = QVBoxLayout(day_card)
            day_layout.setContentsMargins(6, 8, 6, 8)
            day_layout.setSpacing(4)

            icon = QLabel()
            icon.setAlignment(Qt.AlignCenter)
            icon.setStyleSheet("border: none; background: transparent; padding: 0;")

            temp = QLabel("--:--\n--°C")
            temp.setAlignment(Qt.AlignCenter)
            temp.setStyleSheet(
                "font-size: 13px; font-weight: 600; color: #e2e8f0; border: none; background: transparent; padding: 0;"
            )

            day_layout.addWidget(icon)
            day_layout.addWidget(temp)
            forecast_layout.addWidget(day_card)

            self.forecast_icons.append(icon)
            self.forecast_temps.append(temp)

        layout.addLayout(forecast_layout)
        self.setLayout(layout)

    def fetch_weather(self) -> None:
        """Fetch weather data in a background thread."""
        if self._worker is not None and self._worker.isRunning():
            return

        self.current_description.setText(f"Refreshing {self.location}...")
        self._worker = _WeatherWorker(self.location, self.api_key)
        self._worker.finished_weather.connect(self._on_weather_ready)
        self._worker.start()

    def _on_weather_ready(
        self,
        weather_data: dict[str, Any],
        forecast_data: dict[str, Any],
        error: str,
    ) -> None:
        if error:
            self.current_description.setText(f"Weather unavailable: {error}")
            return

        try:
            # Current weather
            weather_info = weather_data["weather"][0]
            icon_code = weather_info["icon"]
            current_pixmap = self.get_icon_pixmap(icon_code)
            if not current_pixmap.isNull():
                self.current_icon.setPixmap(
                    current_pixmap.scaled(
                        130, 130, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                )

            temp_c = round(weather_data["main"]["temp"])
            feels_c = round(weather_data["main"].get("feels_like", temp_c))
            desc = str(weather_info["description"]).capitalize()
            self.current_temp.setText(f"{temp_c}°C")
            self.current_description.setText(
                f"{desc}  •  Feels like {feels_c}°C\n{self.location}"
            )

            # Forecast
            forecasts = forecast_data.get("list", [])[: self.count]
            for i, forecast in enumerate(forecasts):
                f_icon_code = forecast["weather"][0]["icon"]
                pixmap = self.get_icon_pixmap(f_icon_code)
                if not pixmap.isNull():
                    self.forecast_icons[i].setPixmap(
                        pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    )
                time_str = datetime.datetime.fromtimestamp(forecast["dt"]).strftime("%H:%M")
                f_temp = round(forecast["main"]["temp"])
                self.forecast_temps[i].setText(f"{time_str}\n{f_temp}°C")
        except Exception as e:
            logger.error("Error parsing weather response: %s", e)
            self.current_description.setText(f"Error parsing weather: {e}")

    def get_icon_pixmap(self, icon_code: str) -> QPixmap:
        """Extract icon from day/night 3x3 sprite sheets."""
        if len(icon_code) < 3:
            return QPixmap()

        num_part = icon_code[:2]
        char_part = icon_code[-1]
        is_day = char_part == "d"

        if is_day:
            if self.sheet_day is None:
                self.sheet_day = QPixmap(str(BASE_DIR / "icons" / "weather_day.png"))
            sheet = self.sheet_day
        else:
            if self.sheet_night is None:
                self.sheet_night = QPixmap(str(BASE_DIR / "icons" / "weather_night.png"))
            sheet = self.sheet_night

        if sheet is None or sheet.isNull():
            return QPixmap()

        cols = 3
        rows = 3
        icon_w = sheet.width() // cols
        icon_h = sheet.height() // rows

        code_map = {
            "01": (0, 0),
            "02": (0, 1),
            "03": (0, 2),
            "04": (1, 0),
            "09": (1, 1),
            "10": (1, 2),
            "11": (2, 0),
            "13": (2, 1),
            "50": (2, 2),
        }

        r, c = code_map.get(num_part, (0, 0))
        return sheet.copy(c * icon_w, r * icon_h, icon_w, icon_h)
