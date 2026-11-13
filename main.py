from __future__ import annotations

import logging
import sys
from datetime import datetime
from enum import IntEnum
from pathlib import Path

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QVBoxLayout

from alarm import AlarmManager
from config import SmartClockConfig
from keypad import KeypadWidget
from news import NewsManager
from radio import RadioManager
from server import start_server
from trains import TrainManager
from weather_widget import WeatherWidget
from webcam import WebcamManager

BASE_DIR = Path(__file__).resolve().parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class PageIndex(IntEnum):
    CLOCK = 0
    NEWS = 1
    RADIO = 2
    ALARM = 3
    TRAINS = 4
    WEATHER = 5
    WEBCAM = 6


APP_STYLESHEET = """
QMainWindow {
    background-color: #0f172a;
    color: #f8fafc;
}
QWidget {
    color: #f8fafc;
    font-family: "Inter", "DejaVu Sans", "Arial", sans-serif;
}
QScrollArea {
    background-color: transparent;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: transparent;
}
QListWidget {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 6px;
    font-size: 16px;
}
QListWidget::item {
    padding: 8px 12px;
    border-radius: 6px;
}
QListWidget::item:selected {
    background-color: #3b82f6;
    color: #ffffff;
    font-weight: bold;
}
QGroupBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #94a3b8;
}
QPushButton {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 14px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #334155;
}
QPushButton:pressed {
    background-color: #3b82f6;
}
QPushButton[activeNav="true"] {
    background-color: #3b82f6;
    border-color: #60a5fa;
    color: #ffffff;
}
QSlider::groove:horizontal {
    border: 1px solid #334155;
    height: 8px;
    background: #0f172a;
    border-radius: 4px;
}
QSlider::sub-page:horizontal {
    background: #3b82f6;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #f8fafc;
    border: 2px solid #3b82f6;
    width: 20px;
    margin: -7px 0;
    border-radius: 11px;
}
QCheckBox {
    font-size: 16px;
    font-weight: 600;
    spacing: 10px;
}
QCheckBox::indicator {
    width: 22px;
    height: 22px;
    border-radius: 5px;
    border: 2px solid #475569;
    background-color: #1e293b;
}
QCheckBox::indicator:checked {
    background-color: #3b82f6;
    border-color: #60a5fa;
}
QStatusBar {
    background-color: #090d16;
    color: #94a3b8;
    font-size: 13px;
    font-weight: 600;
}
"""


class SmartClock(QtWidgets.QMainWindow):
    """Main application window coordinating all smart clock views and managers."""

    quit_signal = pyqtSignal()
    set_clock_signal = pyqtSignal()
    set_news_signal = pyqtSignal()
    set_radio_signal = pyqtSignal()
    set_alarm_signal = pyqtSignal()
    set_trains_signal = pyqtSignal()
    set_weather_signal = pyqtSignal()
    set_webcam_signal = pyqtSignal(bool)
    play_pause_signal = pyqtSignal()
    next_station_signal = pyqtSignal()
    play_station_signal = pyqtSignal(str)
    set_volume_signal = pyqtSignal(int)

    def __init__(self) -> None:
        super().__init__()

        uic.loadUi(str(BASE_DIR / "smartclock.ui"), self)
        self.config = SmartClockConfig(BASE_DIR / "config.toml")

        # Add the weather widget
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.weatherWidget = WeatherWidget(self.config)
        layout.addWidget(self.weatherWidget)
        self.weatherContainer.setLayout(layout)

        # Initialize various managers
        self.radio_manager = RadioManager(self.config)
        self.alarm_manager = AlarmManager(self.config)
        self.train_manager = TrainManager(
            self.config, self.trainsHeaderLabel, self.trainsLayout
        )
        self.news_manager = NewsManager(
            self.config, self.newsHeaderLabel, self.newsLayout
        )
        self.webcam_manager = WebcamManager(self.config, self.webcamDisplay)
        self.keypad_manager = KeypadWidget(self.config)
        self.stackedWidget.addWidget(self.keypad_manager)

        self._nav_buttons: dict[int, QtWidgets.QPushButton] = {
            PageIndex.CLOCK: self.clockButton,
            PageIndex.NEWS: self.newsButton,
            PageIndex.RADIO: self.radioButton,
            PageIndex.ALARM: self.alarmButton,
            PageIndex.TRAINS: self.trainsButton,
            PageIndex.WEATHER: self.weatherButton,
            PageIndex.WEBCAM: self.webcamButton,
        }

        self._setup_ui_elements()
        self._connect_signals()
        self._update_nav_highlight(PageIndex.CLOCK)

        # Timer for updating clock and other components
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_components)
        self.timer.start(1000)
        self._update_components()

    def _setup_ui_elements(self) -> None:
        """Initialize and setup UI elements."""
        self.timeLabel.setStyleSheet(
            "font-size: 92px; font-weight: bold; color: #f8fafc; letter-spacing: 2px;"
        )
        self.dateLabel.setStyleSheet(
            "font-size: 26px; font-weight: 500; color: #94a3b8;"
        )

        self.radio_manager.update_radio_list(self.radioListWidget, self.volumeSlider)
        self.volumeLabel.setText(f"{self.volumeSlider.value()}%")

        self.alarm_manager.update_UI(
            self.alarmWeekDayListWidget,
            self.alarmWeekEndListWidget,
            self.alarmCheckBox,
        )

        if not self.config.is_webcam_enabled():
            self.webcamButton.setVisible(False)

    def _connect_signals(self) -> None:
        """Connect all signal handlers."""
        self.clockButton.clicked.connect(self._set_clock)
        self.newsButton.clicked.connect(self._set_news)
        self.radioButton.clicked.connect(self._set_radio)
        self.alarmButton.clicked.connect(self._set_alarm)
        self.trainsButton.clicked.connect(self._set_trains)
        self.weatherButton.clicked.connect(self._set_weather)
        self.webcamButton.clicked.connect(lambda: self._set_webcam(False))

        # Radio controls
        self.playButton.clicked.connect(self._play_radio)
        self.stopButton.clicked.connect(self._stop_radio)
        self.radioListWidget.itemDoubleClicked.connect(lambda _: self._play_radio())
        self.volumeSlider.valueChanged.connect(self._set_volume)

        # Feature controls
        self.refreshNewsButton.clicked.connect(self.news_manager.update_news)
        self.nextSourceButton.clicked.connect(self.news_manager.next_source)
        self.refreshTrainsButton.clicked.connect(self.train_manager.update_train_status)
        self.refreshWeatherButton.clicked.connect(self.weatherWidget.fetch_weather)
        self.stopAlarmButton.clicked.connect(self._stop_alarm)
        self.alarmCheckBox.stateChanged.connect(self.alarm_manager.update_enabled)

        # Thread-safe remote signals
        self.quit_signal.connect(self._quit)
        self.set_clock_signal.connect(self._set_clock)
        self.set_news_signal.connect(self._set_news)
        self.set_radio_signal.connect(self._set_radio)
        self.set_alarm_signal.connect(self._set_alarm)
        self.set_trains_signal.connect(self._set_trains)
        self.set_weather_signal.connect(self._set_weather)
        self.set_webcam_signal.connect(self._set_webcam)
        self.play_pause_signal.connect(self._play_pause)
        self.next_station_signal.connect(self._next_radio_station)
        self.play_station_signal.connect(self._play_specific_station)
        self.set_volume_signal.connect(self._set_volume_from_remote)

        # Keypad signals
        self.keypad_manager.pin_success.connect(self._on_pin_success)
        self.keypad_manager.pin_cancelled.connect(self._set_clock)

    def _update_nav_highlight(self, active_index: int) -> None:
        for idx, btn in self._nav_buttons.items():
            btn.setProperty("activeNav", "true" if idx == active_index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    # Public thread-safe API (called by Flask web server)
    def set_clock(self) -> None:
        self.set_clock_signal.emit()

    def set_news(self) -> None:
        self.set_news_signal.emit()

    def set_radio(self) -> None:
        self.set_radio_signal.emit()

    def set_alarm(self) -> None:
        self.set_alarm_signal.emit()

    def set_trains(self) -> None:
        self.set_trains_signal.emit()

    def set_weather(self) -> None:
        self.set_weather_signal.emit()

    def set_webcam(self, bypass_pin: bool = False) -> None:
        self.set_webcam_signal.emit(bypass_pin)

    def play_pause(self) -> bool:
        will_play = self.radio_manager.played_station == ""
        self.play_pause_signal.emit()
        return will_play

    def next_radio_station(self) -> str:
        stations = self.radio_manager.get_stations()
        if not stations:
            return ""
        self.next_station_signal.emit()
        return self.radio_manager.played_station

    def play_station(self, station_name: str) -> None:
        self.play_station_signal.emit(station_name)

    def set_remote_volume(self, volume: int) -> None:
        self.set_volume_signal.emit(int(volume))

    def get_current_view_name(self) -> str:
        idx = self.stackedWidget.currentIndex()
        try:
            return PageIndex(idx).name.lower()
        except ValueError:
            return "keypad"

    # Internal UI slot handlers
    def _stop_alarm(self) -> None:
        if self.stopAlarmButton.text() == "Stop Alarm":
            self.alarm_manager.stop_alarm()
            self.stopAlarmButton.setText("Start Alarm")
        else:
            self.alarm_manager.start_alarm()
            self.stopAlarmButton.setText("Stop Alarm")

    def _switch_to_page(self, page: PageIndex) -> None:
        if page != PageIndex.WEBCAM:
            self.webcam_manager.stop()
        self.stackedWidget.setCurrentIndex(int(page))
        self._update_nav_highlight(int(page))

    def _set_clock(self) -> None:
        self._switch_to_page(PageIndex.CLOCK)

    def _set_news(self) -> None:
        self._switch_to_page(PageIndex.NEWS)
        self.news_manager.update_news()

    def _set_radio(self) -> None:
        self._switch_to_page(PageIndex.RADIO)

    def _set_alarm(self) -> None:
        self._switch_to_page(PageIndex.ALARM)

    def _set_trains(self) -> None:
        self._switch_to_page(PageIndex.TRAINS)
        self.train_manager.update_train_status()

    def _set_weather(self) -> None:
        self._switch_to_page(PageIndex.WEATHER)
        self.weatherWidget.fetch_weather()

    def _set_webcam(self, bypass_pin: bool = False) -> None:
        pin = self.config.get_webcam_pin()
        if bypass_pin or not pin:
            self._show_webcam_view()
        else:
            self.webcam_manager.stop()
            self.stackedWidget.setCurrentWidget(self.keypad_manager)
            self._update_nav_highlight(PageIndex.WEBCAM)
            self.keypad_manager.reset()

    def _show_webcam_view(self) -> None:
        self._switch_to_page(PageIndex.WEBCAM)
        self.webcam_manager.start()

    def _on_pin_success(self) -> None:
        self._show_webcam_view()

    def _next_radio_station(self) -> None:
        count = self.radioListWidget.count()
        if count == 0:
            return
        selected = (self.radioListWidget.currentRow() + 1) % count
        self.radioListWidget.setCurrentRow(selected)
        if self.radio_manager.played_station:
            self._play_radio()

    def _play_specific_station(self, station_name: str) -> None:
        items = self.radioListWidget.findItems(station_name, Qt.MatchExactly)
        if items:
            self.radioListWidget.setCurrentItem(items[0])
        self.radio_manager.play_radio(station_name)

    def _play_radio(self) -> None:
        """Play selected radio station."""
        selected_items = self.radioListWidget.selectedItems()
        if not selected_items and self.radioListWidget.count() > 0:
            self.radioListWidget.setCurrentRow(0)
            selected_items = self.radioListWidget.selectedItems()
        if selected_items:
            self.radio_manager.play_radio(selected_items[0].text())

    def _play_pause(self) -> bool:
        if self.radio_manager.played_station == "":
            self._play_radio()
            return True
        self._stop_radio()
        return False

    def _stop_radio(self) -> None:
        """Stop radio playback."""
        self.radio_manager.stop_radio()

    def _set_volume(self, value: int) -> None:
        """Set radio volume."""
        self.radio_manager.set_volume(value)
        self.volumeLabel.setText(f"{value}%")

    def _set_volume_from_remote(self, value: int) -> None:
        self.volumeSlider.setValue(max(0, min(100, value)))

    def _update_components(self) -> None:
        """Update the clock display and periodic background checks."""
        current_date = datetime.now()
        current_time = current_date.time()

        self.train_manager.update(
            current_date, self.stackedWidget.currentIndex() == PageIndex.TRAINS
        )
        radio_status_message = self.radio_manager.get_status_message()

        # Update clock screen
        self.timeLabel.setText(current_time.strftime("%H:%M:%S"))
        self.dateLabel.setText(current_date.strftime("%A, %B %d, %Y"))

        # Update status bar with time and radio message
        status_text = current_time.strftime("%H:%M:%S")
        if radio_status_message:
            status_text = f"{status_text}    |    {radio_status_message}"
        self.statusbar.showMessage(status_text)

        self.news_manager.update(
            current_date, self.stackedWidget.currentIndex() == PageIndex.NEWS
        )

        if self.alarm_manager.start_if_necessary(current_date):
            self.stopAlarmButton.setText("Stop Alarm")
            self._set_alarm()

    def quit(self) -> None:
        self.webcam_manager.stop()
        self.alarm_manager.beeper.close()
        self.quit_signal.emit()

    def _quit(self) -> None:
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.quit()


def _apply_dark_palette(app: QtWidgets.QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(15, 23, 42))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(30, 41, 59))
    palette.setColor(QPalette.AlternateBase, QColor(15, 23, 42))
    palette.setColor(QPalette.ToolTipBase, Qt.black)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(30, 41, 59))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(59, 130, 246))
    palette.setColor(QPalette.Highlight, QColor(59, 130, 246))
    palette.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(palette)
    app.setStyleSheet(APP_STYLESHEET)


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    _apply_dark_palette(app)

    window = SmartClock()
    start_server(window)

    window.show()
    window.showFullScreen()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
