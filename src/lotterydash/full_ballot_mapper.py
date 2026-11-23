"""Guided, non-destructive Pick 3 full-ballot mapping workflow.

Replicates the 43 verified Panel A scan-space offsets to target panels only
after the operator selects a corresponding anchor on the actual scan.
All generated coordinates are drafts requiring visual review.
"""
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QFileDialog, QMessageBox, QProgressBar, QDoubleSpinBox, QGroupBox,
)
from .calibration import ScanPoint, load_mapping, save_mapping
from .global_options import GLOBAL_FIELDS, mapping_summary
from .mapping_ui import ScanCanvas

PANEL_LETTERS = "abcde"


def replicate_panel(points, target, source_anchor, target_anchor):
    """Translate Panel A scan points using two corresponding bubble centers."""
    target = target.lower()
    if target not in "bcde":
        raise ValueError("Target must be B, C, D or E")
    source = {k: v for k, v in points.items() if k.startswith("a.")}
    if len(source) != 43:
        raise ValueError("Panel A must contain exactly 43 mapped fields")
    if source_anchor not in source:
        raise ValueError("Choose an existing Panel A anchor")
    if not (0 <= target_anchor.x <= 1 and 0 <= target_anchor.y <= 1):
        raise ValueError("Target anchor outside scan")
    dx = target_anchor.x - source[source_anchor].x
    dy = target_anchor.y - source[source_anchor].y
    draft = {}
    for key, point in source.items():
        x, y = point.x + dx, point.y + dy
        if not (0 <= x <= 1 and 0 <= y <= 1):
            raise ValueError("Panel translation moves fields outside the scan")
        draft[target + key[1:]] = ScanPoint(x, y)
    return draft


class FullBallotMapper(QWidget):
    """Map all panels and global selections without modifying source JSON."""
    def __init__(self, scan_path, mapping_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LotteryDash | Full Ballot Mapping")
        self.resize(1080, 790)
        self.scan_path = Path(scan_path)
        self.mapping_path = Path(mapping_path)
        self.points = load_mapping(self.mapping_path)
        self.original = dict(self.points)
        self.reviewed_panels = set()
        self.canvas = ScanCanvas()
        self.canvas.set_scan(str(self.scan_path))
        self.canvas.points = self.points
        self.canvas.selected.connect(self.place)
        root = QVBoxLayout(self)
        root.addWidget(QLabel(
            "FULL BALLOT MAPPING · Click corresponding anchors for B–E, then place "
            "each global field. Draft coordinates require visual inspection. "
            "The original mapping is never overwritten."
        ))
        self.progress = QProgressBar()
        self.progress.setRange(0, 231)
        root.addWidget(self.progress)
        self.status = QLabel()
        root.addWidget(self.status)

        panel_box = QGroupBox("1 · Replicate Panel A (43 fields per panel)")
        panel_row = QHBoxLayout(panel_box)
        self.panel = QComboBox()
        for name in "BCDE":
            self.panel.addItem("Panel " + name, name.lower())
        panel_row.addWidget(self.panel)
        self.anchor = QComboBox()
        for key in sorted(k for k in self.points if k.startswith("a.")):
            self.anchor.addItem(key)
        panel_row.addWidget(self.anchor, 2)
        self.panel_button = QPushButton("Click matching bubble on target panel")
        self.panel_button.clicked.connect(self.arm_panel)
        panel_row.addWidget(self.panel_button, 2)
        root.addWidget(panel_box)

        global_box = QGroupBox("2 · Map global selections (16 fields)")
        global_row = QHBoxLayout(global_box)
        self.global_field = QComboBox()
        self.global_field.addItems(GLOBAL_FIELDS)
        global_row.addWidget(self.global_field, 2)
        self.global_button = QPushButton("Click selected global bubble")
        self.global_button.clicked.connect(self.arm_global)
        global_row.addWidget(self.global_button, 2)
        root.addWidget(global_box)

        actions = QHBoxLayout()
        self.mode = None
        self.save_button = QPushButton("Save draft mapping as…")
        self.save_button.clicked.connect(self.save_draft)
        actions.addWidget(self.save_button)
        self.reset_button = QPushButton("Discard draft changes")
        self.reset_button.clicked.connect(self.reset)
        actions.addWidget(self.reset_button)
        root.addLayout(actions)

        from PySide6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidget(self.canvas)
        scroll.setWidgetResizable(False)
        root.addWidget(scroll)
        self.refresh()

    def refresh(self):
        summary = mapping_summary(self.points)
        self.progress.setValue(min(231, len(self.points)))
        self.status.setText(
            f"{len(self.points)}/231 mapped · " +
            " · ".join(f"{p.upper()}: {summary['panel_counts'][p]}/43" for p in PANEL_LETTERS) +
            f" · Global: {16-len(summary['global_missing'])}/16 · "
            "DRAFT / physical alignment unverified"
        )
        self.canvas.points = self.points
        self.canvas.update()

    def arm_panel(self):
        self.mode = ("panel", self.panel.currentData(), self.anchor.currentText())
        self.status.setText(
            f"Click the center of {self.anchor.currentText()[2:]} "
            f"in Panel {self.panel.currentData().upper()}."
        )

    def arm_global(self):
        self.mode = ("global", self.global_field.currentText())
        self.status.setText("Click center of " + self.global_field.currentText())

    def place(self, x, y):
        if self.mode is None:
            return
        point = ScanPoint(x / self.canvas.pixmap.width(),
                          y / self.canvas.pixmap.height())
        mode = self.mode
        self.mode = None
        try:
            if mode[0] == "panel":
                _, panel, anchor = mode
                draft = replicate_panel(self.points, panel, anchor, point)
                existing = [k for k in draft if k in self.original]
                if existing:
                    raise ValueError("Target has original coordinates; refusing overwrite")
                self.points.update(draft)
                self.reviewed_panels.discard(panel)
                QMessageBox.information(
                    self, "Panel draft created",
                    f"43 Panel {panel.upper()} points generated. "
                    "Inspect each mark against the scan before approving. "
                    "You can reselect an anchor to reposition this panel."
                )
            else:
                field = mode[1]
                if field in self.original:
                    raise ValueError("Original coordinate protected")
                self.points[field] = point
                remaining = [k for k in GLOBAL_FIELDS if k not in self.points]
                if remaining:
                    self.global_field.setCurrentText(remaining[0])
        except ValueError as exc:
            QMessageBox.warning(self, "Mapping not changed", str(exc))
        self.refresh()

    def reset(self):
        self.points = dict(self.original)
        self.mode = None
        self.refresh()

    def save_draft(self):
        initial = self.mapping_path.with_name("pick3-mapping-draft.json")
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save draft without overwriting original", str(initial),
            "JSON files (*.json)"
        )
        if not filename:
            return
        dest = Path(filename)
        if dest.resolve() == self.mapping_path.resolve():
            QMessageBox.warning(self, "Protected", "Original mapping cannot be overwritten")
            return
        if dest.exists():
            QMessageBox.warning(self, "Protected", "Choose a new filename; existing files are protected")
            return
        try:
            save_mapping(dest, self.points,
                         self.canvas.pixmap.width(), self.canvas.pixmap.height())
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
            return
        QMessageBox.information(
            self, "Draft saved",
            f"Saved {len(self.points)}/231 fields to {dest}. "
            "Physical printer calibration and manual field review are still required."
        )
