"""Interactive scan-space mapper. Does not send anything to a printer."""
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QFileDialog, QMessageBox, QScrollArea,
)

from .calibration import ScanPoint, normalize, save_mapping, load_mapping


class ScanCanvas(QWidget):
    selected = Signal(float, float)

    def __init__(self):
        super().__init__()
        self.pixmap = QPixmap()
        self.points: dict[str, ScanPoint] = {}
        self.setMinimumSize(600, 400)

    def set_scan(self, path: str):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            raise ValueError("Could not open scan image")
        self.pixmap = pixmap
        self.setFixedSize(pixmap.size())
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.pixmap.isNull():
            painter.drawPixmap(0, 0, self.pixmap)
            painter.setPen(QPen(QColor("#0066ff"), 3))
            painter.setBrush(QColor(0, 102, 255, 90))
            for name, point in self.points.items():
                x = point.x * self.pixmap.width()
                y = point.y * self.pixmap.height()
                painter.drawEllipse(QPointF(x, y), 6, 6)
                painter.drawText(int(x + 9), int(y - 8), name)
        else:
            painter.drawText(self.rect(), Qt.AlignCenter, "Open the scanned playslip to begin mapping")

    def mousePressEvent(self, event):
        if self.pixmap.isNull() or event.button() != Qt.LeftButton:
            return
        x, y = event.position().x(), event.position().y()
        if 0 <= x <= self.pixmap.width() and 0 <= y <= self.pixmap.height():
            self.selected.emit(x, y)


class MappingWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LotteryDash | Playslip Coordinate Mapper")
        self.resize(1100, 850)
        self.canvas = ScanCanvas()
        self.scan_path = ""
        self.points: dict[str, ScanPoint] = {}

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "SCAN-SPACE ONLY — no physical DPI or printer alignment has been verified. "
            "Click a bubble center to map its position."
        ))
        controls = QHBoxLayout()
        self.name = QLineEdit()
        self.name.setPlaceholderText("Field ID, e.g. A.digit1.7 or A.straight")
        controls.addWidget(self.name)
        for title, handler in [
            ("Open scan", self.open_scan),
            ("Save map", self.save_map),
            ("Load map", self.load_map),
            ("Clear marks", self.clear_marks),
        ]:
            button = QPushButton(title)
            button.clicked.connect(handler)
            controls.addWidget(button)
        layout.addLayout(controls)
        self.status = QLabel("No scan loaded")
        layout.addWidget(self.status)
        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(False)
        layout.addWidget(scroll)
        self.canvas.selected.connect(self.mark_point)

    def open_scan(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open flatbed scan", str(Path.home()), "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if filename:
            try:
                self.canvas.set_scan(filename)
            except ValueError as exc:
                QMessageBox.warning(self, "Invalid image", str(exc))
                return
            self.scan_path = filename
            self.points.clear()
            self.canvas.points = self.points
            self.canvas.update()
            self.status.setText(
                f"Loaded {Path(filename).name}: "
                f"{self.canvas.pixmap.width()} x {self.canvas.pixmap.height()} px"
            )

    def mark_point(self, x: float, y: float):
        key = self.name.text().strip()
        if not key:
            QMessageBox.warning(self, "Field name required", "Enter a field ID before clicking.")
            return
        self.points[key] = normalize(x, y, self.canvas.pixmap.width(), self.canvas.pixmap.height())
        self.canvas.update()
        self.status.setText(f"Mapped {key}: x={x:.1f}px y={y:.1f}px ({len(self.points)} points)")

    def save_map(self):
        if self.canvas.pixmap.isNull() or not self.points:
            QMessageBox.warning(self, "Nothing to save", "Load a scan and mark at least one field.")
            return
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save mapping", str(Path.home() / "pick3-mapping.json"), "JSON (*.json)"
        )
        if filename:
            try:
                save_mapping(filename, self.points, self.canvas.pixmap.width(), self.canvas.pixmap.height())
                self.status.setText(f"Saved {len(self.points)} marks to {filename}")
            except OSError as exc:
                QMessageBox.critical(self, "Save failed", str(exc))

    def load_map(self):
        if self.canvas.pixmap.isNull():
            QMessageBox.warning(self, "Scan required", "Open the matching scan first.")
            return
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load mapping", str(Path.home()), "JSON (*.json)"
        )
        if filename:
            try:
                self.points = load_mapping(filename)
            except (OSError, ValueError, TypeError, KeyError) as exc:
                QMessageBox.critical(self, "Load failed", str(exc))
                return
            self.canvas.points = self.points
            self.canvas.update()
            self.status.setText(f"Loaded {len(self.points)} marks")

    def clear_marks(self):
        self.points.clear()
        self.canvas.update()
        self.status.setText("Marks cleared")
