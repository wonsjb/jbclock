import sys
from datetime import datetime
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtGui import QPalette, QColor
from radio import RadioManager
from trains import TrainManager
from news import NewsManager
from server import start_server
from config import SmartClockConfig
from weather_widget import WeatherWidget
from alarm import AlarmManager


class SmartClock(QtWidgets.QMainWindow):

    quit_signal = pyqtSignal()
    set_clock_signal = pyqtSignal()
    set_news_signal = pyqtSignal()
    set_radio_signal = pyqtSignal()
    set_alarm_signal = pyqtSignal()
    set_trains_signal = pyqtSignal()
    set_weather_signal = pyqtSignal()
    play_pause_signal = pyqtSignal()
    next_station_signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        # Load the UI file
        uic.loadUi('smartclock.ui', self)
        self.config = SmartClockConfig('config.toml')
        
        # Add the weather widget
        layout = QVBoxLayout()
        self.weatherWidget = WeatherWidget(self.config)
        layout.addWidget(self.weatherWidget)
        self.weatherContainer.setLayout(layout)

        # Initialize various managers
        self.radio_manager = RadioManager(self.config)
        self.alarm_manager = AlarmManager(self.config)
        self.train_manager = TrainManager(self.config, self.trainsHeaderLabel, self.trainsLayout)
        self.news_manager = NewsManager(self.config, self.newsHeaderLabel, self.newsLayout)

        # Initialize UI elements
        self._setup_ui_elements()

        # Connect signals
        self._connect_signals()
        
        # Timer for updating clock and other components
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_components)
        self.timer.start(1000)  # Update every second

    def _setup_ui_elements(self):
        """Initialize and setup UI elements"""
        # Setup radio stations
        self.radio_manager.update_radio_list(self.radioListWidget, self.volumeSlider)
        self.volumeLabel.setText(f"{self.volumeSlider.value()}%")
        
        # Setup alarm
        self.alarm_manager.update_UI(self.alarmWeekDayListWidget, self.alarmWeekEndListWidget, self.alarmCheckBox)

    def _connect_signals(self):
        """Connect all signal handlers"""
        # Previous signal connections...
        self.clockButton.clicked.connect(self._set_clock)
        self.newsButton.clicked.connect(self._set_news)
        self.radioButton.clicked.connect(self._set_radio)
        self.alarmButton.clicked.connect(self._set_alarm)
        self.trainsButton.clicked.connect(self._set_trains)
        self.weatherButton.clicked.connect(self._set_weather)


        # Radio controls
        self.playButton.clicked.connect(self._play_radio)
        self.stopButton.clicked.connect(self._stop_radio)
        self.volumeSlider.valueChanged.connect(self._set_volume)
        
        # Other connections as before...
        self.refreshNewsButton.clicked.connect(self.news_manager.update_news)
        self.nextSourceButton.clicked.connect(self.news_manager.next_source)
        self.refreshTrainsButton.clicked.connect(self.train_manager.update_train_status)
        self.refreshWeatherButton.clicked.connect(self.weatherWidget.fetch_weather)
        self.stopAlarmButton.clicked.connect(self._stop_alarm)
        self.alarmCheckBox.stateChanged.connect(self.alarm_manager.update_enabled)

        # own signals
        self.quit_signal.connect(self._quit)
        self.set_clock_signal.connect(self._set_clock)
        self.set_news_signal.connect(self._set_news)
        self.set_radio_signal.connect(self._set_radio)
        self.set_alarm_signal.connect(self._set_alarm)
        self.set_trains_signal.connect(self._set_trains)
        self.set_weather_signal.connect(self._set_weather)
        self.play_pause_signal.connect(self._play_pause)
        self.next_station_signal.connect(self._next_radio_station)

    def set_clock(self):
        self.set_clock_signal.emit()

    def set_news(self):
        self.set_news_signal.emit()

    def set_radio(self):
        self.set_radio_signal.emit()

    def set_alarm(self):
        self.set_alarm_signal.emit()

    def set_trains(self):
        self.set_trains_signal.emit()

    def set_weather(self):
        self.set_weather_signal.emit()

    def play_pause(self):
        self.play_pause_signal.emit()

    def next_radio_station(self):
        self.next_station_signal.emit()

    def _stop_alarm(self):
        if self.stopAlarmButton.text() == "Stop Alarm":
            self.alarm_manager.stop_alarm()
            self.stopAlarmButton.setText("Start Alarm")
        else:
            self.alarm_manager.start_alarm()
            self.stopAlarmButton.setText("Stop Alarm")

    def _set_clock(self):
        self.stackedWidget.setCurrentIndex(0)

    def _set_news(self):
        self.stackedWidget.setCurrentIndex(1)
        self.news_manager.update_news()

    def _set_radio(self):
        self.stackedWidget.setCurrentIndex(2)

    def _set_alarm(self):
        self.stackedWidget.setCurrentIndex(3)

    def _set_trains(self):
        self.stackedWidget.setCurrentIndex(4)
        self.train_manager.update_train_status()

    def _set_weather(self):
        self.stackedWidget.setCurrentIndex(5)
        self.weatherWidget.fetch_weather()

    def _next_radio_station(self):
        selected = self.radioListWidget.currentRow()
        selected = (selected + 1) % self.radioListWidget.count()
        self.radioListWidget.setCurrentRow(selected)

    def _play_radio(self):
        """Play selected radio station"""
        selected_items = self.radioListWidget.selectedItems()
        if selected_items:
            self.radio_manager.play_radio(selected_items[0].text())

    def _play_pause(self):
        if self.radio_manager.played_station == "":
            self._play_radio()
            return True
        else:
            self._stop_radio()
            return False

    def _stop_radio(self):
        """Stop radio playback"""
        self.radio_manager.stop_radio()

    def _set_volume(self, value):
        """Set radio volume"""
        self.radio_manager.set_volume(value)
        self.volumeLabel.setText(f"{value}%")
    
    def _update_components(self):
        """Update the clock display"""
        current_date = datetime.now()
        current_time = current_date.time()

        self.train_manager.update(current_date, self.stackedWidget.currentIndex() == 4)
        radio_status_message = self.radio_manager.get_status_message()

        # update clock screen
        self.timeLabel.setText(current_time.strftime("%H:%M:%S"))
        self.dateLabel.setText(current_date.strftime("%A, %B %d, %Y"))

        # update status bar with time and radio message
        self.statusbar.showMessage(current_time.strftime("%H:%M:%S") + "  " + radio_status_message)

        self.news_manager.update(current_date,  self.stackedWidget.currentIndex() == 1)

        if self.alarm_manager.start_if_necessary(current_date):
            # if alarm was started, change the button text to Stop Alarm, and move to alarm screen
            self.stopAlarmButton.setText("Stop Alarm")
            self._set_alarm()

    def quit(self):
        self.quit_signal.emit()

    def _quit(self):
        QtWidgets.QApplication.instance().quit()

def main():
    app = QtWidgets.QApplication(sys.argv)

    # Force the style to be the same on all OSs:
    app.setStyle("Fusion")

    # Now use a palette to switch to dark colors:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.black)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    window = SmartClock()
    start_server(window)

    window.show()
    window.showFullScreen()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
