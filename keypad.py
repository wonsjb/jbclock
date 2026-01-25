from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGridLayout, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from config import SmartClockConfig

class KeypadWidget(QWidget):
    pin_success = pyqtSignal()
    pin_cancelled = pyqtSignal()

    def __init__(self, config: SmartClockConfig):
        super().__init__()
        self.config = config
        self.current_input = ""
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Display label (masked)
        self.display_label = QLabel("Enter PIN")
        self.display_label.setAlignment(Qt.AlignCenter)
        self.display_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(self.display_label)

        # Center the grid
        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(0) # Make buttons touch each other
        
        buttons = [
            ('1', 0, 0), ('2', 0, 1), ('3', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('7', 2, 0), ('8', 2, 1), ('9', 2, 2),
            ('*', 3, 0), ('0', 3, 1), ('#', 3, 2)
        ]

        for text, row, col in buttons:
            btn = QPushButton(text)
            btn.setFixedSize(80, 80)
            btn.setStyleSheet("font-size: 24px; font-weight: bold;")
            btn.clicked.connect(lambda checked, t=text: self.on_button_click(t))
            grid_layout.addWidget(btn, row, col)

        # Center the grid container horizontally with side buttons
        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addWidget(grid_container)
        
        # Side buttons (Clear/Cancel)
        side_layout = QVBoxLayout()
        side_layout.setSpacing(10) # Some spacing between side buttons
        
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedSize(80, 60) # Slightly wider/shorter? or match width? Let's match width 80.
        clear_btn.setStyleSheet("font-size: 18px; font-weight: bold;")
        clear_btn.clicked.connect(self.clear_input)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(80, 60)
        cancel_btn.setStyleSheet("font-size: 18px; font-weight: bold;")
        cancel_btn.clicked.connect(self.cancel)
        
        side_layout.addWidget(clear_btn)
        side_layout.addWidget(cancel_btn)
        side_layout.addStretch()
        
        h_layout.addSpacing(20) # Space between grid and side buttons
        h_layout.addLayout(side_layout)
        h_layout.addStretch()
        
        layout.addLayout(h_layout)
        layout.addStretch()
        self.setLayout(layout)

    def on_button_click(self, text):
        if text.isdigit():
            self.current_input += text
            self.update_display()
            self.check_pin()
        elif text == '*':
            # Maybe backspace?
            self.current_input = self.current_input[:-1]
            self.update_display()
        elif text == '#':
            # Maybe enter? Or just ignored?
            self.check_pin()

    def update_display(self):
        self.display_label.setText("*" * len(self.current_input))

    def clear_input(self):
        self.current_input = ""
        self.display_label.setText("Enter PIN")
        self.display_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px;")

    def cancel(self):
        self.clear_input()
        self.pin_cancelled.emit()

    def check_pin(self):
        correct_pin = self.config.get_webcam_pin()
        if not correct_pin:
            # If no pin configured, allow?
            self.pin_success.emit()
            return

        if self.current_input == correct_pin:
            self.clear_input()
            self.pin_success.emit()
        elif len(self.current_input) >= len(correct_pin):
            self.display_label.setText("Incorrect PIN")
            self.display_label.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 20px; color: red;")
            self.current_input = ""

    def reset(self):
        self.clear_input()
