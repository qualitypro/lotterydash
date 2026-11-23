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
        from PySide6.QtCore import Qt
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        from .projects import GAMES, GAME_GROUPS
        self.setWindowTitle("LotteryDash | Project Workspace")
        self.resize(1050, 740)
        self.project = None
        self.project_path = None
        self._loading_project = False
        old_planner = self.takeCentralWidget()
        container = QWidget()
        outer = QVBoxLayout(container)
        outer.setContentsMargins(5, 3, 5, 3)
        outer.setSpacing(2)
        from .app_title_bar import AppTitleBar, WindowEdgeController
        self.app_title_bar = AppTitleBar(self)
        self.window_edge_controller = WindowEdgeController(self)
        from PySide6.QtWidgets import QFrame
        chrome = QFrame(container)
        chrome.setObjectName("applicationChrome")
        chrome_layout = QVBoxLayout(chrome)
        chrome_layout.setContentsMargins(0, 0, 0, 0)
        chrome_layout.setSpacing(0)
        chrome_layout.addWidget(self.app_title_bar)
        from .workspace_menus import create_workspace_menus
        self.workspace_menus = create_workspace_menus(self)
        chrome_layout.addWidget(self.workspace_menus)
        header = QFrame()
        header.setObjectName("workspaceHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(5, 2, 5, 2)
        header_layout.setSpacing(0)
        brand = QLabel("LOTTERYDASH  /  FLORIDA LOTTERY")
        brand.setObjectName("brandEyebrow")
        brand.hide()
        bar = QHBoxLayout()
        bar.setSpacing(5)
        game_label = QLabel("Game")
        game_label.setObjectName("sectionTitle")
        bar.addWidget(game_label)
        self.game_selector = QComboBox()
        for group, codes in GAME_GROUPS.items():
            for code in codes:
                self.game_selector.addItem(GAMES[code], code)
                self.game_selector.setItemData(self.game_selector.count() - 1, group, 3)
        self.game_selector.setMinimumWidth(145)
        self.game_selector.setToolTip("Select one of the ten Florida Lottery draw games. Pick 3 has the complete editor; other games have project setup only.")
        from PySide6.QtCore import QSettings
        self._game_settings = QSettings("LotteryDash", "LotteryDash")
        last_game = self._game_settings.value("workspace/last_game", "pick3", type=str)
        restored_index = self.game_selector.findData(last_game)
        self.game_selector.setCurrentIndex(restored_index if restored_index >= 0 else self.game_selector.findData("pick3"))
        self.game_selector.currentIndexChanged.connect(self._game_changed)
        bar.addWidget(self.game_selector)
        self.project_title = QLabel("No project selected")
        self.project_title.setObjectName("projectTitle")
        self.project_title.setMaximumWidth(220)
        bar.addWidget(self.project_title, 1)
        from PySide6.QtWidgets import QMenu, QToolButton
        project_button = QToolButton()
        project_button.setText("Project ▾")
        project_button.setObjectName("headerAction")
        project_button.setToolTip("Create, open, configure and save LotteryDash projects.")
        project_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        project_menu = QMenu(project_button)
        for label, callback in (
            ("New Project…", self.new_project_dialog),
            ("Open Project…", self.open_project_dialog),
            ("Game Setup…", self.edit_game_setup),
            ("Save Project", self.save_project_dialog),
            ("Save Project As…", lambda: self.save_project_dialog(True)),
        ):
            action = project_menu.addAction(label)
            action.triggered.connect(lambda checked=False, fn=callback: fn())
        project_button.setMenu(project_menu)
        self.project_menu_button = project_button
        bar.addWidget(project_button)
        self.context_label = QLabel("Play")
        self.context_label.setObjectName("toolbarContext")
        self.context_label.setMinimumWidth(100)
        bar.addWidget(self.context_label)
        header_layout.addLayout(bar)
        chrome_layout.addWidget(header)
        self.project_context_container = QFrame(chrome)
        self.project_context_container.setObjectName('projectContextContainer')
        self.project_context_layout = QVBoxLayout(self.project_context_container)
        self.project_context_layout.setContentsMargins(6, 2, 6, 2)
        self.project_context_layout.setSpacing(2)
        chrome_layout.addWidget(self.project_context_container)
        outer.addWidget(chrome)
        self.game_notice = QLabel()
        self.game_notice.setWordWrap(False)
        self.game_notice.setObjectName("gameNotice")
        self.game_notice.setToolTip("The selected game determines which workflows are available.")
        self.game_notice.hide()
        self.tabs = QTabWidget()
        self.tabs.setObjectName("workspaceTabs")
        self.tabs.setDocumentMode(True)
        self.tabs.currentChanged.connect(self._update_toolbar_context)
        workspace_panel = QFrame(container)
        workspace_panel.setObjectName("applicationWorkspacePanel")
        workspace_layout = QVBoxLayout(workspace_panel)
        workspace_layout.setContentsMargins(2, 2, 2, 2)
        workspace_layout.setSpacing(0)
        workspace_layout.addWidget(self.tabs)
        outer.addWidget(workspace_panel, 1)
        from .five_panel_editor import FivePanelEditor
        self.panel_editor = FivePanelEditor()
        self.tabs.addTab(self.panel_editor, "Play")
        self.tabs.setTabToolTip(0, "Edit Pick 3 numbers, play types, wagers, draw times, and Fireball for panels A–E.")
        old_planner.deleteLater()
        self.project_status = QLabel("Create or open a project to begin.")
        self.game_workflow_buttons = []
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
                self.game_workflow_buttons.append(button)
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
                    if label in ("Edit mapping", "Publish reviewed mapping"):
                        self.game_workflow_buttons.append(button)
                    column.addWidget(button)
            elif title == "Print / Proof":
                button = QPushButton("Export draft PDF")
                button.clicked.connect(self.export)
                self.game_workflow_buttons.append(button)
                column.addWidget(button)
                button = QPushButton("Export mapped PDF proof")
                button.clicked.connect(self.export_mapped)
                self.game_workflow_buttons.append(button)
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
        self.project_context_container.setVisible(self.context_inspector.isVisible())
        self.context_help_menu_action.setChecked(self.context_inspector.isVisible())
        self.context_help_menu_action.triggered.connect(
            self.project_context_container.setVisible)
        self._game_changed()
        self._update_toolbar_context()

    def changeEvent(self, event):
        super().changeEvent(event)
        if hasattr(self, "app_title_bar"):
            self.app_title_bar.refresh_state()

    def _update_toolbar_context(self, *_):
        if hasattr(self, "context_label") and hasattr(self, "tabs"):
            self.context_label.setText("Workspace: " + self.tabs.tabText(self.tabs.currentIndex()))

    def _game_changed(self, *_):
        from .projects import GAMES
        game = self.game_selector.currentData()
        supported = game == "pick3"
        self._game_settings.setValue("workspace/last_game", game)
        self.tabs.setTabEnabled(0, supported)
        self.game_notice.setText("Pick 3 · Editor ready" if supported else f"{GAMES[game]} · Project setup only")
        if not supported and self.tabs.currentIndex() == 0:
            self.tabs.setCurrentIndex(1)
        self.project_title.setText(
            (self.project["name"] if self.project else "Unsaved project") +
            " | " + GAMES[game])
        if hasattr(self, "game_workflow_buttons"):
            for button in self.game_workflow_buttons:
                button.setEnabled(supported)
                button.setToolTip(
                    "Available for Pick 3 only until this game's workflow is implemented."
                    if not supported else "")
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
        from PySide6.QtWidgets import QDialog
        from .game_setup_wizard import GameSetupWizard
        from .projects import new_project, save_project, project_filename
        if not self._confirm_discard():
            return
        wizard = GameSetupWizard(self, initial_game=self.game_selector.currentData())
        if wizard.exec() != QDialog.DialogCode.Accepted:
            return
        details = wizard.project_details()
        try:
            project = new_project(details["name"], details["game"])
            project["game_setup"] = details["game_setup"]
            project["notes"] = details["notes"]
            folder = Path.home() / "lotterydash-projects"
            target = folder / project_filename(project["name"])
            if target.exists():
                QMessageBox.warning(
                    self, "Project already exists",
                    "A project with this name already exists. Open it or choose another name.")
                return
            save_project(target, project)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Project creation failed", str(exc))
            return
        self.project = project
        self.project_path = target
        self.clear()
        self.game_selector.setCurrentIndex(self.game_selector.findData(project["game"]))
        self._game_changed()
        self.tabs.setCurrentIndex(0 if project["game"] == "pick3" else 1)
        self.statusBar().showMessage(f"Project created and saved: {target}")

    def edit_game_setup(self):
        from PySide6.QtWidgets import QDialog
        from .game_setup_wizard import GameSetupWizard
        from .projects import save_project
        if self.project is None:
            QMessageBox.information(self, "No project", "Create or open a project before editing its setup.")
            return
        wizard = GameSetupWizard(self, project=self.project)
        if wizard.exec() != QDialog.DialogCode.Accepted:
            return
        details = wizard.project_details()
        updated = dict(self.project)
        updated["name"] = details["name"]
        updated["game_setup"] = details["game_setup"]
        updated["notes"] = details["notes"]
        try:
            if self.project_path is not None:
                save_project(self.project_path, updated, overwrite=True)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Setup update failed", str(exc))
            return
        self.project = updated
        self._game_changed()
        self.statusBar().showMessage("Game setup saved.")

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
        if self.game_selector.currentData() != "pick3":
            QMessageBox.information(self, "Coming later", "PDF export is currently available for Pick 3 only.")
            return
        try:
            self._sync_panel_plays()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid panel", str(exc))
            return
        super().export()

    def export_mapped(self):
        if self.game_selector.currentData() != "pick3":
            QMessageBox.information(self, "Coming later", "Mapped proofs are currently available for Pick 3 only.")
            return
        try:
            self._sync_panel_plays()
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid panel", str(exc))
            return
        super().export_mapped()

    def preview_mapped_plays(self):
        if self.game_selector.currentData() != "pick3":
            QMessageBox.information(self, "Coming later", "Mapped previews are currently available for Pick 3 only.")
            return
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
        QMainWindow { background: #eef2f7; color: #17283d; }
        QWidget { color: #17283d; font-family: "Noto Sans", "DejaVu Sans", sans-serif; font-size: 12px; }
        QFrame#projectContextContainer { background: #f0f5fb; border-top: 1px solid #cbd8e7; }
        QWidget#projectContextHelp { background: #f0f5fb; color: #17283d; }
        QFrame#applicationChrome { background: #101f32; border: 1px solid #304968; border-radius: 7px; }
        QFrame#applicationWorkspacePanel { background: #ffffff; border: 1px solid #cbd8e7; border-radius: 7px; }
        QMenuBar#workspaceMenuBar { background: #e8eef6; color: #20344d; padding: 2px 8px; border-top: 1px solid #304968; border-bottom: 1px solid #c7d4e3; }
        QMenuBar#workspaceMenuBar::item { background: transparent; padding: 4px 12px; border-radius: 4px; }
        QMenuBar#workspaceMenuBar::item:selected { background: #cbdff5; color: #123b64; }
        QWidget#appTitleBar { background: #101f32; border-radius: 5px; }\n        QLabel#windowDragHint { color: #a6bbd2; font-size: 10px; padding-left: 10px; }\n        QLabel#appWindowTitle { color: #f3f7fd; font-weight: 700; font-size: 12px; }\n        QToolButton#windowControl, QToolButton#windowCloseButton { background: #2c4563; color: #ffffff; border: 1px solid #68819e; border-radius: 5px; font-size: 18px; font-weight: 700; }\n        QToolButton#windowControl:hover { background: #34506d; }\n        QToolButton#windowCloseButton { background: #a83240; border-color: #d66a74; }\n        QToolButton#windowCloseButton:hover { background: #dc4653; color: white; }\n        QLabel#toolbarContext { color: #bcd5f2; font-size: 11px; }\n        QToolButton#headerAction { background: #2a4565; color: #f0f6ff; border: 1px solid #54718f; border-radius: 4px; padding: 3px 8px; }\n        QToolButton#headerAction:hover { background: #365b80; }\n        QFrame#workspaceHeader { background: #172d49; border: 1px solid #284565; border-radius: 6px; }
        QFrame#workspaceHeader QLabel { color: #f4f8ff; }
        QLabel#brandEyebrow { color: #9bc8fa; font-size: 10px; font-weight: 700; }
        QLabel#projectTitle { color: #c8d8eb; font-size: 12px; }
        QFrame#workspaceHeader QLabel#sectionTitle { color: #ffffff; font-size: 12px; }
        QComboBox#primaryGameSelector { background: #ffffff; color: #17283d; border: 2px solid #79b6f1; font-weight: 700; min-height: 22px; }
        QLabel#gameNotice { background: #e2edfa; color: #284d77; border: 1px solid #c6dcf5; border-radius: 4px; padding: 3px 7px; }
        QTabWidget#workspaceTabs::pane { border: 1px solid #d7e1ed; background: #ffffff; border-radius: 0 9px 9px 9px; }
        QTabBar::tab { background: #e0e7f0; color: #4c6179; padding: 5px 10px; margin-right: 2px; border: 1px solid #d2deeb; border-bottom: none; border-radius: 7px 7px 0 0; }
        QTabBar::tab:selected { background: #ffffff; color: #1765a9; font-weight: 700; border-top: 2px solid #2685dc; padding-top: 4px; }
        QTabBar::tab:hover:!selected { background: #d4e5f7; }
        QTabBar::tab:disabled { color: #9ba8b8; background: #edf0f4; }
        QPushButton { background: #e9f0f8; color: #1b3857; border: 1px solid #c7d7e8; border-radius: 4px; padding: 3px 8px; min-height: 19px; font-weight: 500; }
        QPushButton:hover { background: #d9eafb; border-color: #8db9e3; }
        QPushButton:pressed { background: #c7dff5; }
        QPushButton:focus { border: 2px solid #2685dc; }
        QPushButton:disabled { color: #96a6b8; background: #edf1f5; }
        QPushButton#primaryButton { background: #2582d5; color: white; border-color: #459ce4; font-weight: 700; }
        QPushButton#primaryButton:hover { background: #176ab5; }
        QPushButton#headerAction { background: #2a4565; color: #f0f6ff; border-color: #54718f; }
        QPushButton#headerAction:hover { background: #365b80; }
        QPushButton#subtleButton { background: transparent; color: #52677f; border-color: transparent; }
        QPushButton#subtleButton:hover { background: #e7edf5; }
        QLineEdit, QComboBox { background: white; border: 1px solid #c5d3e3; border-radius: 4px; padding: 3px 6px; min-height: 19px; selection-background-color: #2685dc; }
        QLineEdit:focus, QComboBox:focus { border: 2px solid #2685dc; }
        QLineEdit:disabled, QComboBox:disabled { background: #edf1f5; color: #93a2b4; }
        QFrame#panelSheet { background: white; border: 1px solid #dce4ed; border-radius: 9px; }
        QWidget#panelRowEven { background: #f2f6fb; }
        QWidget#panelRowOdd { background: #ffffff; }
        QLabel#sectionTitle { font-size: 14px; font-weight: 700; }
        QLabel#columnHeader { color: #526a84; font-size: 11px; font-weight: 700; }
        QLabel#mutedLabel { color: #63778d; }
        QFrame#visualGuide { background: #eaf3fc; border: 1px solid #c9dff5; border-radius: 9px; }
        QProgressBar { border: 1px solid #d0deec; border-radius: 6px; background: #e8edf4; text-align: center; color: #172638; }
        QProgressBar::chunk { background: #2582d5; border-radius: 5px; }
        QCheckBox { spacing: 6px; }
        QDockWidget { font-weight: 700; color: #23496e; }
        QTextBrowser { background: #ffffff; border: 1px solid #d9e3ee; border-radius: 7px; }
        QStatusBar { background: #e5edf6; color: #47617d; }
        QToolTip { background: #172d49; color: #ffffff; border: 1px solid #54718f; padding: 5px; }
    """)
    from .help_tooltips import install_help
    app._lotterydash_help = install_help(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
