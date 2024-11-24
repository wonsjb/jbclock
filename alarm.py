import numpy as np
import pyaudio
from config import SmartClockConfig
from datetime import datetime, time


class Beeper():
    def __init__(self, volume: int):
        # Audio parameters
        self.sample_rate = 44100
        self.frequency = 440  # Hz (A4 note)
        self.volume = volume / 100.0
        self.alarm_running = False
        self.p = pyaudio.PyAudio()
        self.current_time = 0


    def generate_samples(self, duration):
        """Generate audio samples for a given duration"""
        samples_per_period = int(self.sample_rate / self.frequency)
        num_samples = int(self.sample_rate * duration)
        
        t = np.linspace(self.current_time, self.current_time + duration, num_samples)
        samples = np.sin(2 * np.pi * self.frequency * t)
        samples *= np.sin(2 * np.pi * 2 * t)

        samples = samples * self.volume
        self.current_time += duration
        
        # Convert to 32-bit float
        return samples.astype(np.float32)
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        """Callback for PyAudio stream"""
        samples = self.generate_samples(frame_count / self.sample_rate)
        return (samples, pyaudio.paContinue)

    def start_alarm(self):
        self.alarm_running = True
        
        # Open PyAudio stream
        self.stream = self.p.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=self.sample_rate,
            output=True,
            stream_callback=self.audio_callback,
            frames_per_buffer=1024
        )
        
        self.stream.start_stream()
    
    def stop_alarm(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        self.alarm_running = False

class AlarmManager():

    def __init__(self, config: SmartClockConfig):
        self.enabled = config.get_alarms_enabled()
        self.week_day_alarms = []
        for time in config.get_weekday_alarms():
            self.week_day_alarms.append(datetime.strptime(time, "%H:%M").time())
        self.week_end_alarms = []
        for time in config.get_weekend_alarms():
            self.week_end_alarms.append(datetime.strptime(time, "%H:%M").time())
        self.alarm_ringing = False
        self.beeper = Beeper(config.get_alarms_volume())
        self.last_alarm_check = datetime.now().time() 

    def update_UI(self, weekday_widget, weekend_widget, enabled_widget):
        for time in self.week_day_alarms:
            weekday_widget.addItem(f"Alarm: {time.strftime('%H:%M')}")
        for time in self.week_end_alarms:
            weekend_widget.addItem(f"Alarm: {time.strftime('%H:%M')}")
        enabled_widget.setChecked(self.enabled)

    def start_if_necessary(self, current_datetime) -> bool:
        current_time = current_datetime.time()
        # did we pass midnight ?
        if self.last_alarm_check > current_time:
            self.last_alarm_check = time(0, 0, 0)
        
        current_day = current_datetime.date()
        started = False
        if current_day.weekday() < 5:
            list_to_check = self.week_day_alarms
        else:
            list_to_check = self.week_end_alarms
        for alarm_time in list_to_check:
            if self.last_alarm_check < alarm_time <= current_time:
                started = self.start_alarm()
                break
        
        self.last_alarm_check = current_time
        return started

    def update_enabled(self, enabled):
        self.enabled = enabled

    def stop_alarm(self):
        if self.alarm_ringing:
            self.alarm_ringing = False
            self.beeper.stop_alarm()

    def start_alarm(self):
        if not self.alarm_ringing and self.enabled:
            self.alarm_ringing = True
            self.beeper.start_alarm()
            return True
        return False

        

