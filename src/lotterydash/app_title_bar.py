"""Application-owned title bar and compositor-native edge resizing."""
from PySide6.QtCore import Qt, QObject, QEvent
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QToolButton, QApplication


class WindowEdgeController(QObject):
    """Start native resize on all eight edges/corners, including Wayland."""

    MARGIN = 9

    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self._cursor_widget = None
        QApplication.instance().installEventFilter(self)

    def _edges(self, point):
        rect = self.host.rect()
        m = self.MARGIN
        edges = Qt.Edge(0)
        if point.x() < m:
            edges |= Qt.Edge.LeftEdge
        elif point.x() >= rect.width() - m:
            edges |= Qt.Edge.RightEdge
        if point.y() < m:
            edges |= Qt.Edge.TopEdge
        elif point.y() >= rect.height() - m:
            edges |= Qt.Edge.BottomEdge
        return edges

    @staticmethod
    def _shape(edges):
        horizontal = bool(edges & (Qt.Edge.LeftEdge | Qt.Edge.RightEdge))
        vertical = bool(edges & (Qt.Edge.TopEdge | Qt.Edge.BottomEdge))
        if horizontal and vertical:
            same = bool(edges & Qt.Edge.LeftEdge) == bool(edges & Qt.Edge.TopEdge)
            return Qt.CursorShape.SizeFDiagCursor if same else Qt.CursorShape.SizeBDiagCursor
        if horizontal:
            return Qt.CursorShape.SizeHorCursor
        if vertical:
            return Qt.CursorShape.SizeVerCursor
        return None

    def _clear_cursor(self):
        if self._cursor_widget is not None:
            self._cursor_widget.unsetCursor()
            self._cursor_widget = None

    def eventFilter(self, watched, event):
        if not isinstance(watched, QWidget) or watched.window() is not self.host:
            return False
        if self.host.isMaximized() or self.host.isFullScreen():
            self._clear_cursor()
            return False
        if event.type() not in (QEvent.Type.MouseMove, QEvent.Type.MouseButtonPress):
            return False
        point = self.host.mapFromGlobal(event.globalPosition().toPoint())
        edges = self._edges(point)
        if event.type() == QEvent.Type.MouseMove:
            if self._cursor_widget is not watched:
                self._clear_cursor()
            shape = self._shape(edges)
            if shape is not None:
                watched.setCursor(shape)
                self._cursor_widget = watched
            elif self._cursor_widget is watched:
                self._clear_cursor()
        elif edges and event.button() == Qt.MouseButton.LeftButton:
            handle = self.host.windowHandle()
            if handle is not None and handle.startSystemResize(edges):
                return True
        return False


class AppTitleBar(QWidget):
    def __init__(self, window):
        super().__init__(window)
        self.host = window
        self.setObjectName("appTitleBar")
        self.setFixedHeight(39)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 3, 7, 3)
        layout.setSpacing(5)
        self.title = QLabel("◆  LotteryDash")
        self.title.setObjectName("appWindowTitle")
        self.title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.title)
        self.drag_hint = QLabel("Drag to move  ·  Edges to resize")
        self.drag_hint.setObjectName("windowDragHint")
        self.drag_hint.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.drag_hint)
        layout.addStretch()
        self.minimize_button = self._button("−", "Minimize window", window.showMinimized)
        self.maximize_button = self._button("□", "Maximize or restore window", self.toggle_maximize)
        self.close_button = self._button("×", "Close LotteryDash", window.close)
        self.close_button.setObjectName("windowCloseButton")
        self._drag_position = None

    def _button(self, symbol, tooltip, callback):
        button = QToolButton(self)
        button.setText(symbol)
        button.setToolTip(tooltip)
        button.setObjectName("windowControl")
        button.setFixedSize(43, 31)
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
        self.maximize_button.setToolTip("Restore window" if self.host.isMaximized() else "Maximize window")

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
