from __future__ import annotations

import ipaddress
import logging
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import urlparse, urlunparse

import cv2
import numpy as np
import requests
import urllib3
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QLabel

from config import SmartClockConfig

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)


def _check_tcp_port(host: str, port: int = 554, timeout: float = 0.4) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _verify_reolink_camera_name(
    host: str, username: str, password: str, target_name: str, timeout: float = 1.5
) -> bool:
    """Verify if the host at `host` is a Reolink camera matching `target_name`."""
    try:
        resp = requests.post(
            "https://%s/cgi-bin/api.cgi" % host,
            params={"cmd": "GetDevName", "user": username, "password": password},
            json=[{"cmd": "GetDevName", "action": 0, "param": {}}],
            verify=False,
            timeout=timeout,
        )
        if resp.ok:
            data = resp.json()
            if isinstance(data, list) and data:
                dev_name = (
                    data[0].get("value", {}).get("DevName", {}).get("name", "")
                )
                return str(dev_name).strip().lower() == target_name.strip().lower()
    except Exception:
        pass
    return False


def _get_local_subnet_hosts() -> list[str]:
    """Determine the local /24 subnet IP addresses to scan."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        net = ipaddress.ip_network(f"{local_ip}/24", strict=False)
        return [str(ip) for ip in net.hosts() if str(ip) != local_ip]
    except Exception as e:
        logger.warning("Could not determine local subnet for camera scan: %s", e)
        return []


def discover_camera_ip(
    camera_name: str,
    current_host: str = "",
    rtsp_port: int = 554,
    username: str = "",
    password: str = "",
) -> str | None:
    """
    Discover the IP address of `camera_name` (e.g., 'Victor') on the local network.

    Order of discovery:
    1. DNS / mDNS lookup for `<camera_name>`, `<camera_name>.lan`, `<camera_name>.local`.
    2. Current configured host if reachable.
    3. Fast parallel TCP scan of port 554 on the local /24 subnet + Reolink API verification.
    """
    candidates: list[str] = []
    if camera_name:
        base = camera_name.strip()
        for suffix in ("", ".lan", ".local"):
            candidates.append(f"{base}{suffix}")
            candidates.append(f"{base.lower()}{suffix}")

    seen_ips: set[str] = set()
    for hostname in candidates:
        try:
            ip = socket.gethostbyname(hostname)
            if ip and ip not in seen_ips:
                seen_ips.add(ip)
                if _check_tcp_port(ip, rtsp_port, timeout=1.0):
                    logger.info(
                        "Discovered camera %r via hostname %s at %s",
                        camera_name,
                        hostname,
                        ip,
                    )
                    return ip
        except OSError:
            continue

    if current_host and _check_tcp_port(current_host, rtsp_port, timeout=0.8):
        return current_host

    # Fallback: scan local /24 subnet for open RTSP port 554
    logger.info("Scanning local subnet for camera %r...", camera_name)
    subnet_ips = _get_local_subnet_hosts()
    if not subnet_ips:
        return None

    open_rtsp_ips: list[str] = []
    with ThreadPoolExecutor(max_workers=48) as executor:
        future_to_ip = {
            executor.submit(_check_tcp_port, ip, rtsp_port, 0.35): ip
            for ip in subnet_ips
        }
        for future in as_completed(future_to_ip):
            ip = future_to_ip[future]
            if future.result():
                open_rtsp_ips.append(ip)

    for ip in open_rtsp_ips:
        if username and password and camera_name:
            if _verify_reolink_camera_name(ip, username, password, camera_name):
                logger.info("Discovered camera %r via subnet scan at %s", camera_name, ip)
                return ip

    if len(open_rtsp_ips) == 1:
        logger.info("Using single RTSP host found on subnet: %s", open_rtsp_ips[0])
        return open_rtsp_ips[0]

    return None


def _replace_url_host(rtsp_url: str, new_host: str) -> str:
    parsed = urlparse(rtsp_url)
    userinfo = ""
    if parsed.username is not None:
        userinfo = parsed.username
        if parsed.password is not None:
            userinfo += f":{parsed.password}"
        userinfo += "@"
    port_part = f":{parsed.port}" if parsed.port else ""
    new_netloc = f"{userinfo}{new_host}{port_part}"
    return urlunparse(parsed._replace(netloc=new_netloc))


class VideoThread(threading.Thread):
    """Background daemon thread that discovers the camera and captures RTSP frames."""

    def __init__(self, config: SmartClockConfig) -> None:
        super().__init__(daemon=True)
        self.config = config
        self.running = False
        self.frame: np.ndarray[Any, Any] | None = None
        self.status_text: str = "Connecting to Webcam..."
        self.lock = threading.Lock()

    def _set_status(self, text: str) -> None:
        with self.lock:
            self.status_text = text

    def _resolve_rtsp_url(self) -> str:
        raw_url = self.config.get_webcam_url()
        if not raw_url:
            return ""

        parsed = urlparse(raw_url)
        current_host = parsed.hostname or ""
        port = parsed.port or 554
        username = parsed.username or ""
        password = parsed.password or ""
        camera_name = self.config.get_webcam_camera_name()

        self._set_status(f"Discovering camera '{camera_name}'...")
        discovered_ip = discover_camera_ip(
            camera_name=camera_name,
            current_host=current_host,
            rtsp_port=port,
            username=username,
            password=password,
        )

        if discovered_ip and discovered_ip != current_host:
            new_url = _replace_url_host(raw_url, discovered_ip)
            logger.info("Updated webcam RTSP host: %s -> %s", current_host, discovered_ip)
            self.config.set_webcam_url(new_url)
            try:
                self.config.save_config()
            except Exception as e:
                logger.warning("Failed to save discovered webcam IP to config: %s", e)
            return new_url

        return raw_url

    def run(self) -> None:
        self.running = True
        rtsp_url = self._resolve_rtsp_url()
        if not rtsp_url or not self.running:
            self._set_status("Webcam URL not configured")
            return

        self._set_status("Opening video stream...")
        cap = cv2.VideoCapture(rtsp_url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        while self.running:
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    with self.lock:
                        self.frame = frame
                        self.status_text = ""
                else:
                    cap.release()
                    self._set_status("Reconnecting to camera...")
                    time.sleep(1.0)
                    if not self.running:
                        break
                    rtsp_url = self._resolve_rtsp_url()
                    cap = cv2.VideoCapture(rtsp_url)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            else:
                self._set_status("Searching for camera...")
                time.sleep(1.0)
                if not self.running:
                    break
                rtsp_url = self._resolve_rtsp_url()
                cap = cv2.VideoCapture(rtsp_url)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if cap.isOpened():
            cap.release()

    def stop(self) -> None:
        self.running = False
        self.join(timeout=1.5)

    def get_state(self) -> tuple[np.ndarray[Any, Any] | None, str]:
        with self.lock:
            return self.frame, self.status_text


class WebcamManager:
    """Manages starting/stopping the RTSP stream and rendering frames onto a QLabel."""

    def __init__(self, config: SmartClockConfig, display_label: QLabel) -> None:
        self.config = config
        self.display_label = display_label
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frame)
        self.is_running = False
        self.thread: VideoThread | None = None

    def start(self) -> None:
        if not self.config.get_webcam_url():
            logger.warning("Webcam URL not configured")
            self.display_label.setText("Webcam URL not configured")
            return

        if self.is_running:
            return

        logger.info("Starting webcam stream")
        self.display_label.setText(
            f"Discovering camera '{self.config.get_webcam_camera_name()}'..."
        )
        self.thread = VideoThread(self.config)
        self.thread.start()

        self.is_running = True
        self.timer.start(33)  # ~30 FPS UI update

    def stop(self) -> None:
        if not self.is_running:
            return

        logger.info("Stopping webcam stream")
        self.timer.stop()
        if self.thread is not None:
            self.thread.stop()
            self.thread = None

        self.is_running = False
        self.display_label.clear()
        self.display_label.setPixmap(QPixmap())
        self.display_label.setText("Webcam Stopped")

    def _update_frame(self) -> None:
        if self.thread is None:
            return

        frame, status_text = self.thread.get_state()
        if frame is not None:
            try:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w

                target_h = self.display_label.height()
                target_w = self.display_label.width()

                if target_h <= 0 or target_w <= 0:
                    return

                qt_image = QImage(
                    rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888
                )
                scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                    target_w,
                    target_h,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.display_label.setPixmap(scaled_pixmap)
            except Exception as e:
                logger.error("Error processing webcam frame: %s", e)
        elif status_text:
            self.display_label.setText(status_text)
