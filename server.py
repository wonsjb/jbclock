from __future__ import annotations

import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from flask import Flask, Response, jsonify, request

if TYPE_CHECKING:
    from main import SmartClock

BASE_DIR = Path(__file__).resolve().parent

# Suppress verbose per-second GET /api/status logs from Werkzeug
werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.setLevel(logging.WARNING)

app = Flask(__name__)
_window: SmartClock | None = None


def _get_window() -> SmartClock:
    if _window is None:
        raise RuntimeError("SmartClock window is not initialized")
    return _window


@app.route("/")
def index() -> Response:
    html_path = BASE_DIR / "server.html"
    return Response(html_path.read_text(encoding="utf-8"), mimetype="text/html")


@app.route("/api/next_station", methods=["POST"])
def next_radio_station() -> Response:
    win = _get_window()
    station = win.next_radio_station()
    return jsonify({"station": station})


@app.route("/api/play_station", methods=["POST"])
def play_station() -> Response:
    win = _get_window()
    data: dict[str, Any] = request.get_json(silent=True) or {}
    station = str(data.get("station", ""))
    if station:
        win.play_station(station)
    return jsonify({"result": "ok", "station": station})


@app.route("/api/volume", methods=["POST"])
def set_volume() -> Response:
    win = _get_window()
    data: dict[str, Any] = request.get_json(silent=True) or {}
    volume = int(data.get("volume", 50))
    win.set_remote_volume(volume)
    return jsonify({"result": "ok", "volume": volume})


@app.route("/api/set_clock", methods=["POST"])
def set_clock() -> Response:
    _get_window().set_clock()
    return jsonify({"result": "ok"})


@app.route("/api/set_news", methods=["POST"])
def set_news() -> Response:
    _get_window().set_news()
    return jsonify({"result": "ok"})


@app.route("/api/set_radio", methods=["POST"])
def set_radio() -> Response:
    _get_window().set_radio()
    return jsonify({"result": "ok"})


@app.route("/api/set_alarm", methods=["POST"])
def set_alarm() -> Response:
    _get_window().set_alarm()
    return jsonify({"result": "ok"})


@app.route("/api/set_trains", methods=["POST"])
def set_trains() -> Response:
    _get_window().set_trains()
    return jsonify({"result": "ok"})


@app.route("/api/set_weather", methods=["POST"])
def set_weather() -> Response:
    _get_window().set_weather()
    return jsonify({"result": "ok"})


@app.route("/api/set_webcam", methods=["POST"])
def set_webcam() -> Response:
    _get_window().set_webcam(bypass_pin=True)
    return jsonify({"result": "ok"})


@app.route("/api/toggle_running", methods=["POST"])
def toggle_running() -> Response:
    is_running = _get_window().play_pause()
    return jsonify({"is_running": is_running})


@app.route("/api/status", methods=["GET"])
def get_status() -> Response:
    win = _get_window()
    now = datetime.now()
    return jsonify(
        {
            "time": now.strftime("%H:%M:%S"),
            "date": now.strftime("%A, %B %d, %Y"),
            "view": win.get_current_view_name(),
            "station": win.radio_manager.played_station,
            "stations": win.radio_manager.get_stations(),
            "track": win.radio_manager.get_current_track(),
            "volume": win.radio_manager.get_volume(),
            "alarm_enabled": win.alarm_manager.enabled,
            "alarm_ringing": win.alarm_manager.alarm_ringing,
            "webcam_enabled": win.config.is_webcam_enabled(),
        }
    )


@app.route("/api/restart", methods=["POST"])
def restart() -> Response:
    _get_window().quit()
    return jsonify({"result": "restarting"})


def run_server() -> None:
    app.run(host="0.0.0.0", port=5000, use_reloader=False)


def start_server(window: SmartClock) -> None:
    global _window
    _window = window
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
