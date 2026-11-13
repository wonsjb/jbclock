from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import SmartClockConfig


class KeypadWidget(QWidget):
    """Touch-friendly numeric PIN entry pad for unlocking protected views."""

    pin_success = pyqtSignal()
    pin_cancelled = pyqtSignal()

    def __init__(self, config: SmartClockConfig) -> None:
        super().__init__()
        self.config = config
        self.current_input = ""
        self.setup_ui()

    def setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        self.display_label = QLabel("Enter PIN")
        self.display_label.setAlignment(Qt.AlignCenter)
        self._set_default_label_style()
        layout.addWidget(self.display_label)

        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setContentsMargins(0, 0, 0, 0)
        grid_layout.setSpacing(8)

        buttons = [
            ("1", 0, 0), ("2", 0, 1), ("3", 0, 2),
            ("4", 1, 0), ("5", 1, 1), ("6", 1, 2),
            ("7", 2, 0), ("8", 2, 1), ("9", 2, 2),
            ("⌫", 3, 0), ("0", 3, 1), ("✓", 3, 2),
        ]

        for text, row, col in buttons:
            btn = QPushButton(text)
            btn.setFixedSize(78, 66)
            btn.setStyleSheet(
                "QPushButton { background-color: #1e293b; color: #f8fafc; "
                "border: 1px solid #334155; border-radius: 10px; "
                "font-size: 22px; font-weight: bold; } "
                "QPushButton:pressed { background-color: #3b82f6; }"
            )
            btn.clicked.connect(lambda _checked=False, t=text: self.on_button_click(t))
            grid_layout.addWidget(btn, row, col)

        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addWidget(grid_container)

        side_layout = QVBoxLayout()
        side_layout.setSpacing(10)

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedSize(96, 66)
        clear_btn.setStyleSheet(
            "QPushButton { background-color: #334155; color: #f8fafc; "
            "border-radius: 10px; font-size: 16px; font-weight: bold; } "
            "QPushButton:pressed { background-color: #475569; }"
        )
        clear_btn.clicked.connect(self.clear_input)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedSize(96, 66)
        cancel_btn.setStyleSheet(
            "QPushButton { background-color: #7f1d1d; color: #fecaca; "
            "border-radius: 10px; font-size: 16px; font-weight: bold; } "
            "QPushButton:pressed { background-color: #991b1b; }"
        )
        cancel_btn.clicked.connect(self.cancel)

        side_layout.addWidget(clear_btn)
        side_layout.addWidget(cancel_btn)
        side_layout.addStretch()

        h_layout.addSpacing(20)
        h_layout.addLayout(side_layout)
        h_layout.addStretch()

        layout.addLayout(h_layout)
        layout.addStretch()
        self.setLayout(layout)

    def _set_default_label_style(self) -> None:
        self.display_label.setStyleSheet(
            "font-size: 24px; font-weight: bold; color: #f8fafc; margin-bottom: 8px;"
        )

    def on_button_click(self, text: str) -> None:
        if text.isdigit():
            self.current_input += text
            self.update_display()
            self.check_pin()
        elif text in ("*", "⌫"):
            self.current_input = self.current_input[:-1]
            self.update_display()
        elif text in ("#", "✓"):
            self.check_pin()

    def update_display(self) -> None:
        if self.current_input:
            self.display_label.setText("● " * len(self.current_input))
            self._set_default_label_style()
        else:
            self.display_label.setText("Enter PIN")
            self._set_default_label_style()

    def clear_input(self) -> None:
        self.current_input = ""
        self.display_label.setText("Enter PIN")
        self._set_default_label_style()

    def cancel(self) -> None:
        self.clear_input()
        self.pin_cancelled.emit()

    def check_pin(self) -> None:
        correct_pin = self.config.get_webcam_pin()
        if not correct_pin:
            self.pin_success.emit()
            return

        if self.current_input == correct_pin:
            self.clear_input()
            self.pin_success.emit()
        elif len(self.current_input) >= len(correct_pin):
            self.display_label.setText("Incorrect PIN")
            self.display_label.setStyleSheet(
                "font-size: 24px; font-weight: bold; color: #f87171; margin-bottom: 8px;"
            )
            self.current_input = ""

    def reset(self) -> None:
        self.clear_input()
