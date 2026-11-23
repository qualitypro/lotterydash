"""Sprint 04D — interactive, non-destructive AutoMap review editor.

Launch: python -m lotterydash.automap_editor --image ... --mapping ...
The input mapping is never written. Approval creates a separately named copy.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .calibration import ScanPoint, load_mapping, save_mapping
from .global_options import GLOBAL_FIELDS, validate_global_fields
from .draft_recovery import find_latest_draft


def safe_destination(source: Path, destination: Path):
    """Prevent writes to the source mapping or existing files."""
    source = Path(source).resolve()
    destination = Path(destination).resolve()
    if source == destination:
        raise ValueError("Refusing to overwrite the source mapping")
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing file: {destination}")
    return destination


def load_review_data(mapping_path: Path):
    data = json.loads(Path(mapping_path).read_text(encoding="utf-8"))
    points = load_mapping(mapping_path)
    return points, data


def main(argv=None):
    parser = argparse.ArgumentParser(description="Interactive AutoMap review and correction")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--mapping", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("images/diagnostics/automap-editor"))
    parser.add_argument("--resume-latest", action="store_true",
                        help="Offer to reopen the latest complete 231-field draft")
    args = parser.parse_args(argv)
    from PySide6.QtCore import Qt, QPointF, QRectF
    from PySide6.QtGui import QColor, QBrush, QPen, QPixmap, QPainter, QUndoCommand, QUndoStack
    from PySide6.QtWidgets import (
        QApplication, QGraphicsEllipseItem,
        QGraphicsScene, QGraphicsView, QHBoxLayout, QVBoxLayout,
        QMainWindow, QWidget, QLabel, QPushButton, QComboBox,
        QMessageBox, QSplitter, QFormLayout, QDoubleSpinBox, QSlider
    )

    class Marker(QGraphicsEllipseItem):
        def __init__(self, name, x, y, scene_view):
            super().__init__(-5, -5, 10, 10)
            self.field = name
            self.editor = scene_view
            self.setPos(x, y)
            self.setBrush(QBrush(QColor(0, 210, 120, 130)))
            self.setPen(QPen(QColor(0, 100, 55), 1.5))
            self.setFlag(self.GraphicsItemFlag.ItemIsMovable)
            self.setFlag(self.GraphicsItemFlag.ItemIsSelectable)
            self.setFlag(self.GraphicsItemFlag.ItemSendsGeometryChanges)
            self.setZValue(10)
            self.setFlag(self.GraphicsItemFlag.ItemIgnoresTransformations, True)
            self.setToolTip(name)
            self._start = QPointF(x, y)

        def mousePressEvent(self, event):
            self._start = QPointF(self.pos())
            super().mousePressEvent(event)
            self.editor.select_field(self.field)

        def mouseReleaseEvent(self, event):
            super().mouseReleaseEvent(event)
            end = QPointF(self.pos())
            if (end - self._start).manhattanLength() > .01:
                self.editor.move_field(self.field, self._start, end)
            self.editor.update_coordinates()

    class MoveCommand(QUndoCommand):
        def __init__(self, editor, field, before, after):
            super().__init__(f"Move {field}")
            self.editor = editor
            self.field = field
            self.before = QPointF(before)
            self.after = QPointF(after)

        def undo(self):
            self.editor.apply_position(self.field, self.before)

        def redo(self):
            self.editor.apply_position(self.field, self.after)

    class Canvas(QGraphicsView):
        def __init__(self, editor):
            super().__init__()
            self.editor = editor
            self.setDragMode(self.DragMode.ScrollHandDrag)
            self.setBackgroundBrush(QColor(34, 38, 42))
            self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            self.setTransformationAnchor(self.ViewportAnchor.AnchorUnderMouse)

        def mousePressEvent(self, event):
            if self.editor.placement_field is not None and event.button() == Qt.MouseButton.LeftButton:
                point = self.mapToScene(event.position().toPoint())
                self.editor.place_global(point)
                event.accept()
                return
            super().mousePressEvent(event)

        def wheelEvent(self, event):
            factor = 1.2 if event.angleDelta().y() > 0 else 1 / 1.2
            self.scale(factor, factor)

    class Editor(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("LotteryDash — AutoMap Editor (review only)")
            self.source = args.mapping
            if args.resume_latest:
                latest = find_latest_draft(Path("images/diagnostics"))
                if latest is not None and latest.resolve() != self.source.resolve():
                    choice = QMessageBox.question(
                        self, "Resume saved AutoMap draft",
                        f"Resume the latest complete 231-field draft?\\n{latest}",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes)
                    if choice == QMessageBox.StandardButton.Yes:
                        self.source = latest
            self.points, self.source_data = load_review_data(self.source)
            self.image = QPixmap(str(args.image))
            if self.image.isNull():
                raise ValueError(f"Cannot load playslip image: {args.image}")
            self.width_px, self.height_px = self.image.width(), self.image.height()
            self.original = {k: QPointF(v.x * self.width_px, v.y * self.height_px)
                             for k, v in self.points.items()}
            self.markers = {}
            self.saved_snapshot = None
            self.active = None
            self.placement_field = None
            self.stack = QUndoStack(self)
            self.scene = QGraphicsScene(self)
            self.scene.addPixmap(self.image)
            self.view = Canvas(self)
            self.view.setScene(self.scene)
            self.scene.setSceneRect(QRectF(self.image.rect()))
            self.slip_bounds = self.calculate_slip_bounds()
            self.panel = QComboBox()
            self.panel.addItems(["All", "A", "B", "C", "D", "E", "Global"])
            self.panel.currentTextChanged.connect(self.filter_panel)
            self.field_label = QLabel("Select a marker")
            self.field_details = QLabel("Panel: — | Type: — | Value: —")
            self.field_details.setWordWrap(True)
            self.field_label.setWordWrap(True)
            self.x_spin = QDoubleSpinBox()
            self.y_spin = QDoubleSpinBox()
            for spin in (self.x_spin, self.y_spin):
                spin.setRange(0.0, 1.0)
                spin.setDecimals(7)
                spin.setSingleStep(.0001)
            self.x_spin.editingFinished.connect(self.apply_numeric)
            self.y_spin.editingFinished.connect(self.apply_numeric)
            for name, point in sorted(self.original.items()):
                marker = Marker(name, point.x(), point.y(), self)
                self.scene.addItem(marker)
                self.markers[name] = marker
            self.panel.setCurrentText("All")
            self.filter_panel("All")
            self.saved_snapshot = self.snapshot()

            side = QWidget()
            controls = QVBoxLayout(side)
            controls.addWidget(QLabel("Visible panel"))
            controls.addWidget(self.panel)
            controls.addWidget(QLabel("Global options (click-to-place)"))
            self.global_choice = QComboBox()
            self.global_choice.addItem("Choose global selection", None)
            for field in GLOBAL_FIELDS:
                self.global_choice.addItem(field, field)
            controls.addWidget(self.global_choice)
            place_button = QPushButton("Place selected global field")
            place_button.clicked.connect(self.start_global_placement)
            controls.addWidget(place_button)
            cancel_button = QPushButton("Cancel placement")
            cancel_button.clicked.connect(self.cancel_global_placement)
            controls.addWidget(cancel_button)
            self.global_status = QLabel("Global fields: 0/16 mapped")
            controls.addWidget(self.global_status)
            self.refresh_global_status()
            controls.addWidget(self.field_label)
            controls.addWidget(self.field_details)
            nav = QHBoxLayout()
            for label, callback in (("Fit Slip", self.fit_slip),
                                    ("Fit Panel", self.fit_panel),
                                    ("+", lambda: self.view.scale(1.25, 1.25)),
                                    ("−", lambda: self.view.scale(.8, .8))):
                button = QPushButton(label)
                button.clicked.connect(callback)
                nav.addWidget(button)
            controls.addLayout(nav)
            controls.addWidget(QLabel("Marker size"))
            self.marker_size = QSlider(Qt.Orientation.Horizontal)
            self.marker_size.setRange(3, 14)
            self.marker_size.setValue(5)
            self.marker_size.valueChanged.connect(self.set_marker_size)
            controls.addWidget(self.marker_size)
            form = QFormLayout()
            form.addRow("X (normalized)", self.x_spin)
            form.addRow("Y (normalized)", self.y_spin)
            controls.addLayout(form)
            for label, callback in (
                ("Undo", self.stack.undo),
                ("Redo", self.stack.redo),
                ("Reset selected field", self.reset_selected),
                ("Save draft mapping", self.save_draft),
                ("Approve as separate mapping", self.approve),
            ):
                button = QPushButton(label)
                button.clicked.connect(callback)
                controls.addWidget(button)
            controls.addStretch()
            controls.addWidget(QLabel("Original mapping is read-only.\n"
                                     "Drag markers, or edit normalized coordinates.\n"
                                     "Mouse wheel zooms; drag background to pan."))
            splitter = QSplitter()
            splitter.addWidget(self.view)
            splitter.addWidget(side)
            splitter.setStretchFactor(0, 5)
            splitter.setStretchFactor(1, 1)
            side.setMaximumWidth(340)
            self.setCentralWidget(splitter)
            self.resize(1200, 850)
            self.fit_slip()
            self.statusBar().showMessage(f"{len(self.markers)} fields loaded — review required")

        def snapshot(self):
            return {name: (marker.pos().x(), marker.pos().y())
                    for name, marker in self.markers.items()}

        def closeEvent(self, event):
            if self.snapshot() != self.saved_snapshot:
                answer = QMessageBox.question(
                    self, "Unsaved AutoMap changes",
                    "Marker changes have not been saved. Close without saving?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No)
                if answer != QMessageBox.StandardButton.Yes:
                    event.ignore()
                    return
            event.accept()

        def calculate_slip_bounds(self):
            """Derive a generous scan crop from known field centers, no image edits."""
            positions = list(self.original.values())
            if not positions:
                return QRectF(self.image.rect())
            xs = [p.x() for p in positions]
            ys = [p.y() for p in positions]
            # The printed logo/instructions extend beyond the selection fields.
            margin_x = max(100, (max(xs) - min(xs)) * .65)
            margin_y = max(300, (max(ys) - min(ys)) * .45)
            left = max(0, min(xs) - margin_x)
            top = max(0, min(ys) - margin_y)
            right = min(self.width_px, max(xs) + margin_x)
            bottom = min(self.height_px, max(ys) + margin_y)
            return QRectF(left, top, right - left, bottom - top)

        def fit_slip(self):
            self.view.fitInView(self.slip_bounds, Qt.AspectRatioMode.KeepAspectRatio)

        def fit_panel(self):
            panel = self.panel.currentText()
            if panel == "Global":
                positions = [m.pos() for name, m in self.markers.items()
                             if name.startswith("global.")]
                if not positions:
                    panel_a = [m.pos() for name, m in self.markers.items()
                               if name.startswith("a.")]
                    if panel_a:
                        low = max(p.y() for p in panel_a)
                        left = min(p.x() for p in panel_a) - 250
                        self.view.fitInView(QRectF(max(0, left), low + 20,
                            650, min(650, self.height_px - low - 20)),
                            Qt.AspectRatioMode.KeepAspectRatio)
                    return
            elif panel == "All":
                self.fit_slip()
                return
            if panel != "Global":
                positions = [m.pos() for name, m in self.markers.items()
                             if name.lower().startswith(panel.lower() + ".")]
            if positions:
                xs = [p.x() for p in positions]
                ys = [p.y() for p in positions]
                rect = QRectF(min(xs) - 55, min(ys) - 45,
                              max(xs) - min(xs) + 110,
                              max(ys) - min(ys) + 90)
                self.view.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)

        def refresh_global_status(self):
            count = sum(key in self.markers for key in GLOBAL_FIELDS)
            self.global_status.setText(f"Global fields: {count}/{len(GLOBAL_FIELDS)} mapped (manual review)")

        def start_global_placement(self):
            name = self.global_choice.currentData()
            if name not in GLOBAL_FIELDS:
                QMessageBox.warning(self, "Select a field", "Choose a global option first.")
                return
            self.placement_field = name
            self.panel.setCurrentText("All")
            self.statusBar().showMessage(f"Click the center of {name} on the scan; Esc cancels.")

        def cancel_global_placement(self):
            self.placement_field = None
            self.statusBar().showMessage("Placement cancelled")

        def keyPressEvent(self, event):
            if event.key() == Qt.Key.Key_Escape and self.placement_field:
                self.cancel_global_placement()
                return
            super().keyPressEvent(event)

        def place_global(self, point):
            name = self.placement_field
            self.placement_field = None
            if name is None:
                return
            if not (0 <= point.x() <= self.width_px and 0 <= point.y() <= self.height_px):
                QMessageBox.warning(self, "Outside scan", "Select a position inside the image.")
                return
            if name in self.markers:
                self.move_field(name, self.markers[name].pos(), point)
            else:
                marker = Marker(name, point.x(), point.y(), self)
                marker.setBrush(QBrush(QColor(255, 165, 0, 180)))
                self.scene.addItem(marker)
                self.markers[name] = marker
                self.original[name] = QPointF(point)
            self.select_field(name)
            self.refresh_global_status()
            self.statusBar().showMessage(f"Placed {name} — verify center at high zoom")

        def set_marker_size(self, size):
            for marker in self.markers.values():
                marker.setRect(-size, -size, size * 2, size * 2)

        def filter_panel(self, value):
            for name, marker in self.markers.items():
                marker.setVisible(value == "All" or name.lower().startswith(value.lower() + "."))

        def select_field(self, name):
            self.active = name
            self.field_label.setText(name)
            parts = name.split(".")
            panel = parts[0].upper() if parts else "?"
            category = parts[1] if len(parts) > 1 else "unknown"
            value = ".".join(parts[2:]) if len(parts) > 2 else "unknown"
            self.field_details.setText(
                f"Panel: {panel} | Type: {category} | Value: {value}")
            for key, marker in self.markers.items():
                selected = key == name
                marker.setPen(QPen(QColor("#ffd43b" if selected else "#006437"),
                                   3 if selected else 1.5))
                marker.setZValue(20 if selected else 10)
            self.update_coordinates()

        def update_coordinates(self):
            if self.active not in self.markers:
                return
            pos = self.markers[self.active].pos()
            self.x_spin.blockSignals(True)
            self.y_spin.blockSignals(True)
            self.x_spin.setValue(pos.x() / self.width_px)
            self.y_spin.setValue(pos.y() / self.height_px)
            self.x_spin.blockSignals(False)
            self.y_spin.blockSignals(False)

        def apply_position(self, field, pos):
            x = min(max(pos.x(), 0), self.width_px)
            y = min(max(pos.y(), 0), self.height_px)
            self.markers[field].setPos(QPointF(x, y))
            self.update_coordinates()

        def move_field(self, field, before, after):
            self.stack.push(MoveCommand(self, field, before, after))

        def apply_numeric(self):
            if self.active is None:
                return
            marker = self.markers[self.active]
            new = QPointF(self.x_spin.value() * self.width_px,
                          self.y_spin.value() * self.height_px)
            if (new - marker.pos()).manhattanLength() > .01:
                self.move_field(self.active, marker.pos(), new)

        def reset_selected(self):
            if self.active:
                self.move_field(self.active, self.markers[self.active].pos(),
                                self.original[self.active])

        def export(self, approved):
            target = args.output_dir / ("automap-approved.json" if approved else "automap-draft.json")
            try:
                target = safe_destination(self.source, target)
                meta = target.with_suffix(".review.json")
                if meta.exists():
                    raise FileExistsError(f"Refusing to overwrite review metadata: {meta}")
                if approved:
                    validate_global_fields(self.markers)
                    if len(self.markers) != 231:
                        raise ValueError(f"Expected exactly 231 fields; found {len(self.markers)}")
                output = {}
                for name, marker in self.markers.items():
                    pos = marker.pos()
                    output[name] = ScanPoint(
                        min(1, max(0, pos.x() / self.width_px)),
                        min(1, max(0, pos.y() / self.height_px)))
                save_mapping(target, output, self.width_px, self.height_px)
                # Approval is stored in a separate metadata document; the
                # mapping remains schema v1 compatible with existing tools.
                meta = target.with_suffix(".review.json")
                meta.write_text(json.dumps({
                    "approved": approved, "source": str(self.source),
                    "field_count": len(output),
                    "review_method": "manual_editor",
                }, indent=2) + "\n", encoding="utf-8")
                self.saved_snapshot = self.snapshot()
                QMessageBox.information(self, "Saved", str(target))
            except Exception as exc:
                QMessageBox.critical(self, "Save failed", str(exc))

        def save_draft(self):
            self.export(False)

        def approve(self):
            response = QMessageBox.question(
                self, "Approve mapping",
                "Have you inspected all five panels, Fireball, Quick Picks $10/$5, and Days 2–14? This creates a separate "
                "approved mapping, not a printer calibration.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if response == QMessageBox.StandardButton.Yes:
                self.export(True)

    app = QApplication.instance() or QApplication([])
    window = Editor()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
