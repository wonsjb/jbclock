import cv2
import threading
import time
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QLabel

class VideoThread(threading.Thread):
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.running = False
        self.frame = None
        self.lock = threading.Lock()
        self.daemon = True  # Daemon thread exits when main program exits

    def run(self):
        self.running = True
        cap = cv2.VideoCapture(self.url)
        # Reduce internal buffer to minimum to reduce latency
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        while self.running:
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    with self.lock:
                        self.frame = frame
                else:
                    # If read fails, wait a bit and try to reconnect
                    cap.release()
                    time.sleep(1)
                    cap = cv2.VideoCapture(self.url)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            else:
                # If not opened, wait and try to reconnect
                time.sleep(1)
                cap = cv2.VideoCapture(self.url)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
        if cap.isOpened():
            cap.release()

    def stop(self):
        self.running = False
        self.join(timeout=1.0)
    
    def get_frame(self):
        with self.lock:
            return self.frame

class WebcamManager:
    def __init__(self, config, display_label: QLabel):
        self.config = config
        self.display_label = display_label
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frame)
        self.url = self.config.get_webcam_url()
        self.is_running = False
        self.thread = None

    def start(self):
        if not self.url:
            print("Webcam URL not configured")
            return

        if self.is_running:
            return

        print(f"Starting webcam stream from {self.url}")
        self.thread = VideoThread(self.url)
        self.thread.start()
        
        self.is_running = True
        self.timer.start(30)  # ~30 FPS UI update

    def stop(self):
        if not self.is_running:
            return

        print("Stopping webcam stream")
        self.timer.stop()
        if self.thread:
            self.thread.stop()
            self.thread = None
            
        self.is_running = False
        self.display_label.clear()
        self.display_label.setPixmap(QPixmap()) # clear
        self.display_label.setText("Webcam Stopped")

    def _update_frame(self):
        if not self.thread:
            return

        frame = self.thread.get_frame()
        if frame is not None:
            # Convert frame to Qt format
            try:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                
                # Scale to fit label while keeping aspect ratio
                target_h = self.display_label.height()
                target_w = self.display_label.width()
                
                # Avoid validation errors if size is 0 (minimized)
                if target_h <= 0 or target_w <= 0:
                    return

                # Create QImage
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                
                # Scale and set pixmap
                scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
                    target_w, target_h, 
                    aspectRatioMode=1  # KeepAspectRatio
                )
                self.display_label.setPixmap(scaled_pixmap)
            except Exception as e:
                print(f"Error processing frame: {e}")
