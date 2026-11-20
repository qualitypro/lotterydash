"""Minimal Qt desktop launcher for LotteryDash."""
from pathlib import Path
from tempfile import gettempdir

from PySide6.QtWidgets import (
    QApplication, QComboBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from .models import Draw, Pick3Play, PlayType
from .preview import write_draft_preview
from .play_mapping import resolve_fields


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LotteryDash | Pick 3")
        self.resize(640, 420)
        self.plays: list[Pick3Play] = []
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addWidget(QLabel("Florida Pick 3 - Play Planner"))
        layout.addWidget(QLabel("Draft planning only. Official slip calibration is not yet enabled."))
        form = QFormLayout()
        self.digits = QLineEdit()
        self.digits.setPlaceholderText("e.g. 007")
        self.digits.setMaxLength(3)
        form.addRow("Three digits", self.digits)
        self.play_type = QComboBox()
        for item in PlayType:
            self.play_type.addItem(item.value.replace("_", " ").title(), item.value)
        form.addRow("Play type", self.play_type)
        self.amount = QComboBox()
        self.amount.addItems(["1.00", "0.50"])
        form.addRow("Wager ($)", self.amount)
        self.draw = QComboBox()
        for item in Draw:
            self.draw.addItem(item.value.title(), item.value)
        form.addRow("Draw", self.draw)
        layout.addLayout(form)
        self.summary = QLabel("0 / 5 panels")
        layout.addWidget(self.summary)
        actions = QHBoxLayout()
        for name, handler in [
            ("Add panel", self.add_panel),
            ("Clear", self.clear),
            ("Export draft PDF", self.export),
        ]:
            button = QPushButton(name)
            button.clicked.connect(handler)
            actions.addWidget(button)
        layout.addLayout(actions)
        mapper_button = QPushButton("Open Scan Mapper")
        mapper_button.clicked.connect(self.open_mapper)
        layout.addWidget(mapper_button)
        preview_button = QPushButton("Preview plays on scanned slip")
        preview_button.clicked.connect(self.preview_mapped_plays)
        layout.addWidget(preview_button)
        self.mapper_window = None
        self.setCentralWidget(root)

    def open_mapper(self):
        from .mapping_ui import MappingWindow
        if self.mapper_window is None:
            self.mapper_window = MappingWindow()
        self.mapper_window.show()
        self.mapper_window.raise_()
        self.mapper_window.activateWindow()

    def preview_mapped_plays(self):
        if not self.plays:
            QMessageBox.warning(self, "No plays", "Add at least one play in the planner first.")
            return
        root = Path(__file__).resolve().parents[2]
        scan = root / "images" / "pick3-playslip.png"
        mapping = root / "maps" / "pick3-mapping.json"
        if not scan.is_file() or not mapping.is_file():
            QMessageBox.warning(
                self, "Local assets missing",
                "Expected images/pick3-playslip.png and maps/pick3-mapping.json "
                "in the project directory."
            )
            return
        self.open_mapper()
        try:
            self.mapper_window.open_scan_path(str(scan))
            self.mapper_window.load_map_path(str(mapping))
            selected = set()
            missing = []
            for index, play in enumerate(self.plays):
                found, absent = resolve_fields(play, "ABCDE"[index], self.mapper_window.points)
                selected.update(found)
                missing.extend(absent)
            self.mapper_window.show_selections(selected, missing)
            if missing:
                QMessageBox.information(
                    self, "Incomplete mapping",
                    f"{len(missing)} required bubble fields have no saved coordinates. "
                    "The red marks show only mapped selections.\n\n"
                    + "\n".join(missing[:15])
                )
        except (OSError, ValueError, TypeError, KeyError) as exc:
            QMessageBox.critical(self, "Mapping preview failed", str(exc))

    def add_panel(self):
        from decimal import Decimal
        try:
            if len(self.plays) >= 5:
                raise ValueError("Maximum five panels per playslip")
            play = Pick3Play(
                digits=self.digits.text(),
                play_type=self.play_type.currentData(),
                amount=Decimal(self.amount.currentText()),
                draw=self.draw.currentData(),
            )
            self.plays.append(play)
            self.summary.setText(f"{len(self.plays)} / 5 panels: " + ", ".join(p.digits for p in self.plays))
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid selection", str(exc))

    def clear(self):
        self.plays.clear()
        self.summary.setText("0 / 5 panels")

    def export(self):
        if not self.plays:
            QMessageBox.warning(self, "No plays", "Add at least one play first.")
            return
        from PySide6.QtWidgets import QFileDialog
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save draft preview", str(Path(gettempdir()) / "lotterydash-preview.pdf"),
            "PDF files (*.pdf)"
        )
        if filename:
            try:
                write_draft_preview(self.plays, filename)
                QMessageBox.information(self, "Draft saved", f"Saved: {filename}")
            except (OSError, ValueError) as exc:
                QMessageBox.critical(self, "Export failed", str(exc))


def main():
    import sys
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
