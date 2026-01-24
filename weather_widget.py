import requests
import json
import datetime
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from config import SmartClockConfig

class WeatherWidget(QWidget):
    def __init__(self, config: SmartClockConfig):
        super().__init__()
        self.count = 10
        self.location = config.get_weather_location()
        self.api_key = config.get_weather_api_key()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Current weather
        current_layout = QHBoxLayout()
        self.current_icon = QLabel()
        self.current_temp = QLabel()
        self.current_description = QLabel()
        current_layout.addWidget(self.current_icon)
        current_layout.addWidget(self.current_temp)
        current_layout.addWidget(self.current_description)
        layout.addLayout(current_layout)

        # Forecast
        forecast_layout = QHBoxLayout()
        self.forecast_icons = [QLabel() for _ in range(self.count)]
        self.forecast_temps = [QLabel() for _ in range(self.count)]
        for icon, temp in zip(self.forecast_icons, self.forecast_temps):
            day_layout = QVBoxLayout()
            day_layout.addWidget(icon)
            day_layout.addWidget(temp)
            forecast_layout.addLayout(day_layout)
        layout.addLayout(forecast_layout)

        self.setLayout(layout)

    def fetch_weather(self):
        url = f"http://api.openweathermap.org/data/2.5/weather?q={self.location}&appid={self.api_key}&units=metric"
        try:
            response = requests.get(url, timeout=10)
            weather_data = json.loads(response.text)

            # Current weather
            icon_code = weather_data["weather"][0]["icon"]
            current_pixmap = self.get_icon_pixmap(icon_code)
            if not current_pixmap.isNull():
                self.current_icon.setPixmap(current_pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.current_temp.setText(f"{int(weather_data['main']['temp'] + 0.5)}°C")
            self.current_description.setText(weather_data["weather"][0]["description"])

            # Forecast
            forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q={self.location}&appid={self.api_key}&units=metric"
            forecast_response = requests.get(forecast_url, timeout=10)
            forecast_data = json.loads(forecast_response.text)
            
            for i, forecast in enumerate(forecast_data["list"][:self.count]):
                icon_code = forecast["weather"][0]["icon"]
                pixmap = self.get_icon_pixmap(icon_code)
                if not pixmap.isNull():
                    self.forecast_icons[i].setPixmap(pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                time = datetime.datetime.fromtimestamp(forecast['dt']).strftime("%H:%M")
                self.forecast_temps[i].setText(f"{time}\n{int(forecast['main']['temp'] + 0.5)}°C")
        except Exception as e:
            print(f"Error fetching weather: {e}")

    def get_icon_pixmap(self, icon_code):
        """Extract icon from day/night 3x3 sprite sheets."""
        # Parse code (e.g., '01d')
        num_part = icon_code[:2]
        char_part = icon_code[-1] # 'd' or 'n'
        
        # Load appropriate sheet
        is_day = (char_part == 'd')
        
        # Cache sheets independently
        if is_day:
            if not hasattr(self, 'sheet_day'):
                self.sheet_day = QPixmap("icons/weather_day.png")
            sheet = self.sheet_day
        else:
            if not hasattr(self, 'sheet_night'):
                self.sheet_night = QPixmap("icons/weather_night.png")
            sheet = self.sheet_night

        if sheet.isNull():
            return QPixmap()

        # Grid dimensions (3x3)
        total_w = sheet.width()
        total_h = sheet.height()
        cols = 3
        rows = 3
        icon_w = total_w // cols
        icon_h = total_h // rows

        # Mapping code to (row, col)
        # 3x3 Layout:
        # 01 02 03
        # 04 09 10
        # 11 13 50
        code_map = {
            '01': (0, 0), '02': (0, 1), '03': (0, 2),
            '04': (1, 0), '09': (1, 1), '10': (1, 2),
            '11': (2, 0), '13': (2, 1), '50': (2, 2)
        }
        
        r, c = code_map.get(num_part, (0, 0))
        
        # Crop
        x = c * icon_w
        y = r * icon_h
        return sheet.copy(x, y, icon_w, icon_h)