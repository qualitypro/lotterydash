"""Application-owned title bar with native compositor move and window controls."""
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QToolButton, QStyle


class AppTitleBar(QWidget):
    def __init__(self, window):
        super().__init__(window)
        self.host = window
        self.setObjectName("appTitleBar")
        self.setFixedHeight(32)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(9, 2, 5, 2)
        layout.setSpacing(4)
        self.title = QLabel("◆  LotteryDash")
        self.title.setObjectName("appWindowTitle")
        layout.addWidget(self.title)
        layout.addStretch()
        self.minimize_button = self._button("−", "Minimize", window.showMinimized)
        self.maximize_button = self._button("□", "Maximize / Restore", self.toggle_maximize)
        self.close_button = self._button("×", "Close", window.close)
        self.close_button.setObjectName("windowCloseButton")
        self._drag_position = None

    def _button(self, symbol, tooltip, callback):
        button = QToolButton(self)
        button.setText(symbol)
        button.setToolTip(tooltip)
        button.setObjectName("windowControl")
        button.setFixedSize(32, 25)
        button.clicked.connect(callback)
        self.layout().addWidget(button)
        return button

    def toggle_maximize(self):
        if self.host.isMaximized():
            self.host.showNormal()
        else:
            self.host.showMaximized()
        self.refresh_state()

    def refresh_state(self):
        self.maximize_button.setText("❐" if self.host.isMaximized() else "□")

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.host.windowHandle()
            if handle is not None and handle.startSystemMove():
                event.accept()
                return
            self._drag_position = event.globalPosition().toPoint() - self.host.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_position is not None and event.buttons() & Qt.MouseButton.LeftButton:
            if not self.host.isMaximized():
                self.host.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_position = None
        super().mouseReleaseEvent(event)
