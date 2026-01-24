import cv2
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QLabel

class WebcamManager:
    def __init__(self, config, display_label: QLabel):
        self.config = config
        self.display_label = display_label
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frame)
        self.cap = None
        self.url = self.config.get_webcam_url()
        self.is_running = False

    def start(self):
        if not self.url:
            print("Webcam URL not configured")
            return

        if self.is_running:
            return

        print(f"Starting webcam stream from {self.url}")
        self.cap = cv2.VideoCapture(self.url)
        if not self.cap.isOpened():
            print("Error: Could not open video stream")
            return
        
        self.is_running = True
        self.timer.start(30)  # ~30 FPS

    def stop(self):
        if not self.is_running:
            return

        print("Stopping webcam stream")
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
        self.is_running = False
        self.display_label.clear()
        self.display_label.setText("Webcam Stopped")

    def _update_frame(self):
        if not self.cap or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if ret:
            # Convert frame to Qt format
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            
            # Scale to fit label while keeping aspect ratio
            target_h = self.display_label.height()
            target_w = self.display_label.width()
            
            # Create QImage
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # Scale and set pixmap
            scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                target_w, target_h, 
                aspectRatioMode=1  # KeepAspectRatio
            )
            self.display_label.setPixmap(scaled_pixmap)
        else:
            print("Failed to read frame")
            # Attempt to reconnect or just stop? 
            # For now, let's just log. In a robust system we might want auto-reconnect logic.
