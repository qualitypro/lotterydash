"""Minimal Qt desktop launcher for LotteryDash."""
from pathlib import Path
from tempfile import gettempdir

from PySide6.QtWidgets import (
    QApplication, QComboBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from .models import Draw, Pick3Play, PlayType
from .preview import write_draft_preview
from .mapped_preview import write_mapped_preview
from .play_mapping import resolve_fields


class LegacyMainWindow(QMainWindow):
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
            ("Export mapped PDF proof", self.export_mapped),
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

    def export_mapped(self):
        if not self.plays:
            QMessageBox.warning(self, "No plays", "Add at least one play first.")
            return
        from PySide6.QtWidgets import QFileDialog
        root = Path(__file__).resolve().parents[2]
        scan = root / "images" / "pick3-playslip.png"
        mapping = root / "maps" / "pick3-mapping.json"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save scan-aligned PDF proof",
            str(Path(gettempdir()) / "lotterydash-mapped-proof.pdf"),
            "PDF files (*.pdf)"
        )
        if filename:
            try:
                write_mapped_preview(self.plays, filename, scan, mapping)
                QMessageBox.information(
                    self, "PDF proof saved",
                    f"Saved: {filename}\\nVisual proof only — NOT calibrated for printing."
                )
            except (OSError, ValueError, TypeError, KeyError) as exc:
                QMessageBox.critical(self, "Mapped export failed", str(exc))

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



class MainWindow(LegacyMainWindow):
    """Project-aware tabbed workspace; preserves the existing Pick 3 planner."""

    def __init__(self):
        from PySide6.QtWidgets import QTabWidget, QGroupBox
        super().__init__()
        from .projects import GAMES
        self.setWindowTitle("LotteryDash | Project Workspace")
        self.resize(1050, 740)
        self.project = None
        self.project_path = None
        self._loading_project = False
        old_planner = self.takeCentralWidget()
        container = QWidget()
        outer = QVBoxLayout(container)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Game"))
        self.game_selector = QComboBox()
        for code, title in GAMES.items():
            self.game_selector.addItem(title, code)
        self.game_selector.currentIndexChanged.connect(self._game_changed)
        bar.addWidget(self.game_selector)
        self.project_title = QLabel("No project selected")
        bar.addWidget(self.project_title, 1)
        for label, callback in (
            ("New", self.new_project_dialog),
            ("Open", self.open_project_dialog),
            ("Save", self.save_project_dialog),
            ("Save As", lambda: self.save_project_dialog(True)),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            bar.addWidget(button)
        outer.addLayout(bar)
        self.tabs = QTabWidget()
        outer.addWidget(self.tabs)
        from .five_panel_editor import FivePanelEditor
        self.panel_editor = FivePanelEditor()
        self.tabs.addTab(self.panel_editor, "Play")
        self.tabs.setTabToolTip(0, "Edit Pick 3 numbers, play types, wagers, draw times, and Fireball for panels A–E.")
        old_planner.deleteLater()
        self.project_status = QLabel("Create or open a project to begin.")
        for title, description in (
            ("Playslip", "Preview current play selections against this project's scanned slip."),
            ("Mapping Studio", "Edit a draft, review the 231 fields, and publish a versioned mapping."),
            ("Print / Proof", "Export proofs. Production mapping does not imply printer calibration."),
            ("Settings", "Project metadata and current file references."),
        ):
            page = QWidget()
            column = QVBoxLayout(page)
            column.addWidget(QLabel(description))
            if title == "Playslip":
                button = QPushButton("Preview mapped selections")
                button.clicked.connect(self.preview_mapped_plays)
                column.addWidget(button)
            elif title == "Mapping Studio":
                self.mapping_status = QLabel("No mapping selected")
                column.addWidget(self.mapping_status)
                for label, callback in (
                    ("Choose scan", self.choose_scan),
                    ("Choose mapping draft", self.choose_mapping),
                    ("Edit mapping", self.edit_mapping),
                    ("Publish reviewed mapping", self.publish_project_mapping),
                ):
                    button = QPushButton(label)
                    button.clicked.connect(callback)
                    column.addWidget(button)
            elif title == "Print / Proof":
                button = QPushButton("Export draft PDF")
                button.clicked.connect(self.export)
                column.addWidget(button)
                button = QPushButton("Export mapped PDF proof")
                button.clicked.connect(self.export_mapped)
                column.addWidget(button)
            elif title == "Settings":
                column.addWidget(self.project_status)
            column.addStretch()
            index = self.tabs.addTab(page, title)
            from .help_tooltips import HELP
            self.tabs.setTabToolTip(index, HELP.get(title, title))
        from .element_guide import ElementGuide
        self.element_guide = ElementGuide()
        guide_index = self.tabs.addTab(self.element_guide, "Element Guide")
        self.tabs.setTabToolTip(
            guide_index, "Search the meanings of game terms, playslip controls, mapping, projects and printing.")
        self.setCentralWidget(container)
        from .context_inspector import install_context_inspector
        install_context_inspector(self)
        self._game_changed()

    def _game_changed(self, *_):
        from .projects import GAMES
        game = self.game_selector.currentData()
        self.tabs.setTabEnabled(0, game == "pick3")
        if game != "pick3" and self.tabs.currentIndex() == 0:
            self.tabs.setCurrentIndex(1)
        self.project_title.setText(
            (self.project["name"] if self.project else "Unsaved project") +
            " | " + GAMES[game])
        self._refresh_project_status()

    def _refresh_project_status(self):
        if not hasattr(self, "project_status"):
            return
        if self.project is None:
            status = "No project selected"
        else:
            status = (
                f"Project: {self.project['name']}\n"
                f"Scan: {self.project.get('scan') or 'Not selected'}\n"
                f"Mapping draft: {self.project.get('mapping') or 'Not selected'}\n"
                f"Production: {self.project.get('production_version') or 'Not published'}"
            )
        self.project_status.setText(status)
        if hasattr(self, "mapping_status"):
            self.mapping_status.setText(status)

    def _confirm_discard(self):
        if not self.plays and self.project is None:
            return True
        return QMessageBox.question(
            self, "Switch project",
            "Save your current project before switching. Continue without saving?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def new_project_dialog(self):
        from PySide6.QtWidgets import QInputDialog
        from .projects import new_project
        if not self._confirm_discard():
            return
        name, ok = QInputDialog.getText(self, "New project", "Project name")
        if not ok or not name.strip():
            return
        try:
            project = new_project(name, self.game_selector.currentData())
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid name", str(exc))
            return
        from .projects import save_project, project_filename
        folder = Path.home() / "lotterydash-projects"
        target = folder / project_filename(project["name"])
        if target.exists():
            QMessageBox.warning(
                self, "Project already exists",
                "A project with this name already exists. Open it or choose another name.")
            return
        try:
            save_project(target, project)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Project creation failed", str(exc))
            return
        self.project = project
        self.project_path = target
        self.clear()
        self._game_changed()
        self.tabs.setCurrentIndex(0 if project["game"] == "pick3" else 1)
        self.statusBar().showMessage(f"Project created and saved: {target}")

    def _sync_panel_plays(self):
        if self.game_selector.currentData() != "pick3":
            return
        self.plays = self.panel_editor.collect_plays()

    def _restore_plays(self, data):
        from decimal import Decimal
        restored = [
            Pick3Play(digits=p["digits"], play_type=p["play_type"],
                      amount=Decimal(p["amount"]), draw=p["draw"],
                      fireball=p.get("fireball", False))
            for p in data
        ]
        self.panel_editor.set_plays(restored)
        self.plays = restored

    def clear(self):
        if hasattr(self, "panel_editor"):
            self.panel_editor.clear_all()
        self.plays = []

    def export(self):
        try:
            self._sync_panel_plays()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid panel", str(exc))
            return
        super().export()

    def export_mapped(self):
        try:
            self._sync_panel_plays()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid panel", str(exc))
            return
        super().export_mapped()

    def preview_mapped_plays(self):
        try:
            self._sync_panel_plays()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid panel", str(exc))
            return
        super().preview_mapped_plays()

    def _serialize_plays(self):
        return [
            {"digits": p.digits, "play_type": p.play_type.value,
             "amount": str(p.amount), "draw": p.draw.value,
             "fireball": p.fireball}
            for p in self.plays
        ]

    def open_project_dialog(self):
        from PySide6.QtWidgets import QFileDialog
        from .projects import load_project
        if not self._confirm_discard():
            return
        from PySide6.QtWidgets import QInputDialog
        folder = Path.home() / "lotterydash-projects"
        available = sorted(folder.glob("*.lottery.json"))
        if not available:
            QMessageBox.information(
                self, "No saved projects",
                "No projects have been saved yet. Use New to create one.")
            return
        names = [path.name for path in available]
        choice, ok = QInputDialog.getItem(
            self, "Open project", "Saved projects", names, 0, False)
        if not ok:
            return
        filename = str(available[names.index(choice)])
        try:
            project = load_project(Path(filename))
            if project["game"] != "pick3" and project["plays"]:
                raise ValueError("Play restoration is not available for this game")
            if project["game"] == "pick3":
                from decimal import Decimal
                for p in project["plays"]:
                    Pick3Play(digits=p["digits"], play_type=p["play_type"],
                              amount=Decimal(p["amount"]), draw=p["draw"],
                              fireball=p.get("fireball", False))
            self.project = project
            self.project_path = Path(filename)
            self.game_selector.setCurrentIndex(
                self.game_selector.findData(project["game"]))
            self._restore_plays(project["plays"] if project["game"] == "pick3" else [])
            self._game_changed()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            QMessageBox.warning(self, "Open failed", str(exc))

    def save_project_dialog(self, save_as=False):
        from PySide6.QtWidgets import QFileDialog
        from .projects import save_project, project_filename
        if self.project is None:
            QMessageBox.warning(self, "No project", "Create a project first.")
            return
        if self.project["game"] != self.game_selector.currentData():
            QMessageBox.warning(self, "Game mismatch",
                                "Choose the project's game before saving.")
            return
        target = None if save_as else self.project_path
        if target is None:
            folder = Path.home() / "lotterydash-projects"
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save project",
                str(folder / project_filename(self.project["name"])),
                "LotteryDash projects (*.lottery.json)")
            if not filename:
                return
            target = Path(filename)
        try:
            self._sync_panel_plays()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid panel", str(exc))
            return
        payload = dict(self.project)
        payload["plays"] = self._serialize_plays() if payload["game"] == "pick3" else []
        try:
            save_project(target, payload, overwrite=target == self.project_path)
            self.project = payload
            self.project_path = target
            self.statusBar().showMessage(f"Saved project: {target}")
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Save failed", str(exc))

    def _select_project_asset(self, key, title, pattern):
        from PySide6.QtWidgets import QFileDialog
        if self.project is None:
            QMessageBox.warning(self, "No project", "Create a project first.")
            return
        filename, _ = QFileDialog.getOpenFileName(
            self, title, str(Path.home()), pattern)
        if filename:
            self.project[key] = str(Path(filename).resolve())
            if key == "mapping":
                self.project["mapping_approved"] = False
            self._refresh_project_status()

    def choose_scan(self):
        self._select_project_asset("scan", "Select scanned playslip",
                                   "Images (*.png *.jpg *.jpeg *.tif *.tiff)")

    def choose_mapping(self):
        self._select_project_asset("mapping", "Select mapping draft",
                                   "JSON mappings (*.json)")

    def edit_mapping(self):
        import subprocess
        import sys
        from datetime import datetime
        if self.project is None or not self.project.get("scan") or not self.project.get("mapping"):
            QMessageBox.warning(self, "Missing assets",
                                "Choose a scan and mapping draft first.")
            return
        if self.project["game"] != "pick3":
            QMessageBox.warning(self, "Editor unavailable",
                                "This game's mapping schema and editor are not implemented yet.")
            return
        folder = Path.home() / "lotterydash-projects" / "reviews" / (
            "editor-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
        args = [
            sys.executable, "-m", "lotterydash.automap_editor",
            "--image", self.project["scan"],
            "--mapping", self.project["mapping"],
            "--output-dir", str(folder),
        ]
        try:
            self._editor_process = subprocess.Popen(args)
            self.statusBar().showMessage("AutoMap editor launched; import its saved draft when done")
        except OSError as exc:
            QMessageBox.warning(self, "Editor failed", str(exc))

    def publish_project_mapping(self):
        from uuid import uuid4
        from .production_mapping import publish_mapping
        if self.project is None or not self.project.get("mapping"):
            QMessageBox.warning(self, "Missing mapping", "Choose a mapping draft first.")
            return
        response = QMessageBox.question(
            self, "Publish mapping",
            "Have you visually reviewed all fields? Publication creates a separate "
            "versioned snapshot, NOT a printer calibration.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if response != QMessageBox.StandardButton.Yes:
            return
        if not self.project.get("project_id"):
            self.project["project_id"] = uuid4().hex
        try:
            record = publish_mapping(
                self.project, Path(self.project["mapping"]),
                Path.home() / "lotterydash-projects" / "mapping-versions",
                reviewed=True)
            self.project["production_version"] = record["version"]
            self.project["mapping_approved"] = True
            self._refresh_project_status()
            QMessageBox.information(
                self, "Mapping published",
                f"Version: {record['version']}\nSave the project to retain this reference.")
        except (OSError, ValueError, KeyError) as exc:
            QMessageBox.warning(self, "Publication failed", str(exc))


def main():
    import sys
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow, QWidget { background: #f5f7fb; color: #172638;
            font-family: "Noto Sans", "DejaVu Sans", sans-serif; font-size: 12px; }
        QTabWidget::pane { border: 1px solid #dbe3ed; background: #ffffff; }
        QTabBar::tab { background: #e9eef5; padding: 9px 17px;
            margin-right: 3px; border-radius: 5px 5px 0 0; }
        QTabBar::tab:selected { background: #ffffff; color: #1762a3;
            font-weight: 600; }
        QPushButton { background: #e7edf5; border: 1px solid #cbd6e3;
            border-radius: 5px; padding: 6px 12px; min-height: 20px; }
        QPushButton:hover { background: #d9e9f8; border-color: #8db9e3; }
        QPushButton:pressed { background: #c7dff5; }
        QPushButton#subtleButton { background: transparent; color: #52677f;
            border-color: transparent; }
        QPushButton#subtleButton:hover { background: #e7edf5; }
        QLineEdit, QComboBox { background: white; border: 1px solid #cbd6e3;
            border-radius: 5px; padding: 5px 7px; min-height: 22px; }
        QLineEdit:focus, QComboBox:focus { border-color: #2683d6; }
        QFrame#panelSheet { background: white; border: 1px solid #dce4ed;
            border-radius: 8px; }
        QWidget#panelRowEven { background: #f7f9fc; }
        QWidget#panelRowOdd { background: #ffffff; }
        QLabel#sectionTitle { font-size: 18px; font-weight: 700; }
        QLabel#columnHeader { color: #61758c; font-size: 11px; font-weight: 600; }
        QLabel#mutedLabel { color: #63778d; }
        QFrame#visualGuide { background: #edf4fb; border: 1px solid #d0e2f4;
            border-radius: 7px; }
        QProgressBar { border: 1px solid #d0deec; border-radius: 6px;
            background: #e8edf4; text-align: center; color: #172638; }
        QProgressBar::chunk { background: #69a5da; border-radius: 5px; }
        QCheckBox { spacing: 5px; }
    """)
    from .help_tooltips import install_help
    app._lotterydash_help = install_help(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
