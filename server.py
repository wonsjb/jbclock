from flask import Flask, jsonify
import threading
from datetime import datetime

# Flask server to handle remote control
app = Flask(__name__)

# HTML interface
@app.route('/')
def index():
    with open('server.html', 'r') as file:
        return file.read()

@app.route('/api/next_station', methods=['POST'])
def next_radio_station():
    station = app.window.next_radio_station()
    return jsonify({'station': station})

@app.route('/api/set_clock', methods=['POST'])
def set_clock():
    app.window.set_clock()
    return jsonify({'result': 'ok'})

@app.route('/api/set_news', methods=['POST'])
def set_news():
    app.window.set_news()
    return jsonify({'result': 'ok'})

@app.route('/api/set_radio', methods=['POST'])
def set_radio():
    app.window.set_radio()
    return jsonify({'result': 'ok'})

@app.route('/api/set_alarm', methods=['POST'])
def set_alarm():
    app.window.set_alarm()
    return jsonify({'result': 'ok'})

@app.route('/api/set_trains', methods=['POST'])
def set_trains():
    app.window.set_trains()
    return jsonify({'result': 'ok'})

@app.route('/api/set_weather', methods=['POST'])
def set_weather():
    app.window.set_weather()
    return jsonify({'result': 'ok'})

@app.route('/api/toggle_running', methods=['POST'])
def toggle_running():
    is_running = app.window.play_pause()
    return jsonify({'is_running': is_running})

@app.route('/api/status', methods=['GET'])
def get_status():
    pass
    return jsonify({
        'time': datetime.now().time().strftime("%H:%M:%S"),
        'station': app.window.radio_manager.played_station,
        'track': app.window.radio_manager.get_current_track()
    })

@app.route('/api/restart', methods=['POST'])
def restart():
    is_running = app.window.quit()
    return jsonify({})

# Flask server thread
def run_server():
    app.run(host='0.0.0.0', port=5000)


def start_server(window):
    # Start Flask server in a separate thread
    app.window = window
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()