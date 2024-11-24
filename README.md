# JbClock
Runs on a raspberry pi (raspbian).

## Dependencies
You will need to apt-get a few dependency as pip install does not really works for some of the dependencies

```
sudo apt install python3-tomli-w python3-tomli python3-pandas python3-zeep python3-vlc python3-pyqt5 python3-pyaudio
```

(maybe others ?)


## API keys (for weather, news, train schedule services)
You will also need an api key for:
 * https://lite.realtime.nationalrail.co.uk
 * https://newsapi.org
 * https://api.openweathermap.org 

You will then need to put those API keys in the relevant places in config.toml file (see doc later)

## Icons for weather
The icons for the weather are not included (not sure about the copyright)
To get them run the `fectch_icons.sh` script in the `icons` directory

## Start at runtime
There is a `start.sh` script that can be used to make the clock start at runtime.
Edit the file called `~/.config/autostart/clock.desktop` (you might have to create the file and the directories)
and put this in it:
```toml
[Desktop Entry]
Type=Application
Name=Clock
Exec=<location of the start.sh file>
```
After this, the clock will start at runtime. Delete the file if you want to get back to being able to use the pi for some other use.

There is a `restart.sh` file if you want to restart the clock (in case you made change to the code or the config)


## Remote control
The Clock will open port 5000 with a minimal website you can connect via http. It allows to remote control the clock(change radio, restart it, choose the screen being displayed ...)


## config file
Rename `config-example.toml` to `config.toml` and make required updates. See documentation in next chapter.

# Smart Clock User Guide

## Overview
The Smart Clock is a versatile digital clock that provides multiple features to enhance your daily routine:
- Customizable alarms for weekdays and weekends
- Internet radio with multiple stations
- News headlines from various sources
- Real-time train departure information
- Weather forecast information

This guide explains how to configure your Smart Clock through the `config.toml` file.

## Configuration Guide

### Setting Up Alarms
Configure your daily wake-up times for weekdays and weekends separately.

```toml
[alarms]
weekday = ["07:00", "07:30"]  # Multiple alarms for weekdays
weekend = []                  # Empty list means no weekend alarms
enabled = true                # Master switch for all alarms
volume = 50                   # volume for the alarm, in percentage
```
- Times must be in 24-hour format (HH:MM)
- You can set multiple alarms for each day type
- Set `enabled = false` to temporarily disable all alarms without losing your settings

### Radio Settings
Configure your internet radio stations and default volume.

```toml
[radio]
default_volume = 50  # Volume level from 0-100
streams = [
    { name = "Capital FM", uri = "http://media-ice.musicradio.com/CapitalMP3" },
    { name = "Classic FM", uri = "http://media-ice.musicradio.com/ClassicFMMP3" }
]
```
- `default_volume`: Sets the starting volume (0 = mute, 100 = maximum)
- `streams`: List your preferred radio stations with their stream URLs
- The first station in the list will be the default when radio is activated
- You can find a lot of streams at https://fmstream.org

### News Configuration
Set up your news sources and update preferences.

```toml
[news]
sources = [
    # RSS Feed Example
    { 
        type = "rss", 
        name = "BBC News", 
        url = "http://feeds.bbci.co.uk/news/rss.xml" 
    },
    # API Example (for NewsAPI.org)
    { 
        type = "api",
        name = "US News",
        url = "https://newsapi.org/v2/top-headlines",
        api_key = "your-api-key",
        params = { 
            country = "us",
            pageSize = 5,
            category = "general"
        }
    }
]
update_interval = 30  # How often to refresh news (in minutes)
max_stories = 5       # Maximum number of headlines to display
```
- `update_interval`: How frequently to fetch new headlines (in minutes)
- `max_stories`: Limits the number of headlines shown at once
- Supports both RSS feeds and API-based news sources
- For API sources, you'll need to obtain and enter your own API key

### Train Information
Configure your daily commute information to see real-time departure times.

```toml
[trains]
home_station = "London Bridge"
destination_station = "Victoria"
api_key = "your-transport-api-key"
```
- Enter your regular station names exactly as they appear in the transport system
- The train schedules are refreshed every minutes
- You'll need to obtain an API key from https://lite.realtime.nationalrail.co.uk

### Weather forecast
Configure your location to get your local weather (now and every 3 h forecast)

```toml
[weather]
location="Winchmore Hill, London"
api_key="your-weather-api-key"
```
- Enter your location as https://openweathermap.org would accept it
- You'll need to obtain an API key from https://api.openweathermap.org

## Tips and Best Practices

### Alarm Settings
- Set weekday alarms 5-10 minutes earlier than you actually need to wake up
- Consider setting a backup alarm 15 minutes after your main alarm
- Leave weekend alarms empty if you prefer to sleep in

### Radio Usage
- Choose a variety of stations for different moods and times of day
- Include at least one talk radio station (like news radio) as an alternative to music

### News Configuration
- Mix both general news sources and ones specific to your interests
- Keep `update_interval` at 30 minutes or higher to avoid excessive data usage
- Limit `max_stories` to 5-7 for better readability

### Train Information
- Ensure station names match official spellings

## Troubleshooting

### Common Issues

1. **Alarms not sounding:**
   - Check if `enabled = true` in the alarms section
   - Verify time format is HH:MM (e.g., "07:00" not "7:00")

2. **Radio not playing:**
   - Verify internet connection
   - Check if stream URLs are still valid
   - Ensure volume is not set to 0

3. **News not updating:**
   - Check internet connection
   - Verify API keys are valid
   - Ensure RSS feed URLs are correct

4. **Train times not showing:**
   - Verify station names are spelled correctly
   - Check if API key is valid
   - Confirm internet connection

### Backup and Recovery
- Keep a backup copy of your working configuration file
- Note down your API keys in a secure location
- Document any custom stream URLs you've added



# Smart Clock Developer Documentation

## Overview
The Smart Clock is a PyQt5-based desktop application that functions as a multi-feature digital clock with news feeds, radio playback, train schedules, weather updates, and alarm functionality. The application follows a modular architecture with separate managers for different features.

## Architecture

### Core Components
- **Main Application (SmartClock)**: Central class that initializes and coordinates all features
- **Feature Managers**: Individual classes managing specific functionalities (news, radio, trains, etc.)
- **Config System**: TOML-based configuration for all features
- **Web Server**: Flask-based server enabling remote control

### Design Patterns
1. **Manager Pattern**: Each feature is encapsulated in its own manager class
2. **Observer Pattern**: Timer-based updates for real-time components
3. **Factory Pattern**: Used in news fetcher creation based on configuration

### Component Interaction
```
SmartClock (main.py)
    ├── Config
    ├── UI (PyQt5)
    ├── Feature Managers
    │   ├── NewsManager
    │   ├── RadioManager
    │   ├── TrainManager
    │   ├── WeatherWidget
    │   └── AlarmManager
    └── Web Server
```

## File Structure

### Core Files
1. **main.py**
   - Main application entry point
   - Initializes PyQt5 application
   - Sets up UI and managers
   - Handles main window functionality
   - Implements dark mode theme

2. **server.py**
   - Flask server implementation
   - Remote control API endpoints
   - Web interface for remote control
   - Runs in separate thread

### Feature Modules
3. **news.py**
   - News fetching functionality
   - Supports multiple news sources (API/RSS)
   - Manages news display and updates
   - Handles source switching

4. **trains.py**
   - National Rail API integration
   - Real-time train departure information
   - Train schedule display management
   - Uses SOAP/WSDL for API communication

5. **alarm.py**
   - Alarm system implementation
   - Audio generation using PyAudio
   - Supports weekday/weekend schedules
   - Volume control and timing management

### Supporting Files (Not Shown in Provided Code)
- **config.py**: Configuration management using TOML
- **radio.py**: Radio station management and playback
- **weather_widget.py**: Weather information display
- **api_news_reader.py**: API-based news fetching
- **rss_news_reader.py**: RSS feed parsing

## Adding New Features

### Step-by-Step Guide

1. **Create New Manager Class**
```python
class NewFeatureManager:
    def __init__(self, config: SmartClockConfig, *ui_elements):
        self.config = config
        # Initialize UI elements
        # Setup feature-specific functionality

    def update(self, current_time, visible):
        # Regular update logic
        pass
```

2. **Add Configuration**
   - Add new section to `config.toml`
   - Update `SmartClockConfig` class to handle new settings

3. **Update UI**
   - Add new elements to `smartclock.ui`
   - Create new tab/widget for feature
   - Add navigation button

4. **Integrate with Main Application**
```python
class SmartClock(QtWidgets.QMainWindow):
    def __init__(self):
        # Existing initialization
        self.new_feature_manager = NewFeatureManager(self.config, ui_elements)
        self._connect_new_feature_signals()

    def _connect_new_feature_signals(self):
        # Connect new feature signals
        pass

    def _update_components(self):
        # Add new feature to update cycle
        self.new_feature_manager.update(current_date, 
            self.stackedWidget.currentIndex() == new_feature_index)
```

5. **Add Remote Control Support**
   - Add new endpoints to `server.py`
   - Update web interface

### Best Practices

1. **Configuration First**
   - Always add new features behind configuration options
   - Include reasonable defaults
   - Document configuration parameters

2. **UI Integration**
   - Follow existing dark theme
   - Use consistent font sizes and styles
   - Maintain responsive layout

3. **Error Handling**
   - Implement graceful degradation
   - Log errors appropriately
   - Provide user feedback

4. **Testing**
   - Test feature in isolation
   - Verify integration with existing features
   - Check remote control functionality

## Remote Control API

Add new endpoints following this pattern:

```python
@app.route('/api/new_feature', methods=['POST'])
def new_feature_endpoint():
    result = app.window.new_feature_method()
    return jsonify({'result': result})
```

## Common Tasks

### Adding a New View
1. Add new widget to `smartclock.ui`
2. Create button in navigation panel
3. Add new index to `stackedWidget`
4. Implement view switching method
5. Connect signals and slots

### Adding New Configuration
1. Update `config.toml`:
```toml
[new_feature]
enabled = true
update_interval = 5
# feature specific settings
```

2. Add getter methods to `SmartClockConfig`
3. Use configuration in feature manager

## Dependencies
- PyQt5: UI framework
- Flask: Remote control server
- PyAudio: Sound generation
- Numpy: Audio processing
- Zeep: SOAP client for train API
- Various news/weather APIs

## Build and Development
1. Install dependencies: `pip install -r requirements.txt`
2. Configure API keys in `config.toml`
3. Run application: `python main.py`

## Troubleshooting
- Check logs for API errors
- Verify configuration file syntax
- Test network connectivity for APIs
- Confirm audio device availability
