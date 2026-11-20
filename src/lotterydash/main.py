"""Minimal Qt desktop launcher for LotteryDash."""
from pathlib import Path
from tempfile import gettempdir

from PySide6.QtWidgets import (
    QApplication, QComboBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from .models import Draw, Pick3Play, PlayType
from .preview import write_draft_preview


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
            self.play_type.addItem(item.value.replace("_", " ").title(), item)
        form.addRow("Play type", self.play_type)
        self.amount = QComboBox()
        self.amount.addItems(["1.00", "0.50"])
        form.addRow("Wager ($)", self.amount)
        self.draw = QComboBox()
        for item in Draw:
            self.draw.addItem(item.value.title(), item)
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
        self.setCentralWidget(root)

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
