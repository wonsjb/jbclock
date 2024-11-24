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
        response = requests.get(url)
        weather_data = json.loads(response.text)

        # Current weather
        icon_code = weather_data["weather"][0]["icon"]
        self.current_icon.setPixmap(QPixmap(f"icons/{icon_code}@2x.png"))
        self.current_temp.setText(f"{int(weather_data['main']['temp'] + 0.5)}°C")
        self.current_description.setText(weather_data["weather"][0]["description"])

        # Forecast
        forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q={self.location}&appid={self.api_key}&units=metric"
        forecast_response = requests.get(forecast_url)
        forecast_data = json.loads(forecast_response.text)
        #print(forecast_data)
        for i, forecast in enumerate(forecast_data["list"][:self.count]):
            icon_code = forecast["weather"][0]["icon"]
            self.forecast_icons[i].setPixmap(QPixmap(f"icons/{icon_code}.png"))
            time = datetime.datetime.fromtimestamp(forecast['dt']).strftime("%H:%M")
            self.forecast_temps[i].setText(f"{time}\n{int(forecast['main']['temp'] + 0.5)}°C")