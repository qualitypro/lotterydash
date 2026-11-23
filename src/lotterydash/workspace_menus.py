"""Compact application-owned top-level menus for the frameless workspace."""
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMenuBar, QMessageBox


def create_workspace_menus(window):
    """Use an embedded menu bar so it remains visible on Linux/Wayland."""
    bar = QMenuBar(window)
    bar.setObjectName("workspaceMenuBar")
    bar.setNativeMenuBar(False)
    bar.setToolTip("Application menus: File, Edit, View, Mapping, Print, Help")

    def action(menu, title, callback, shortcut=None):
        item = QAction(title, window)
        if shortcut:
            item.setShortcut(QKeySequence(shortcut))
            item.setShortcutContext(__import__(
                "PySide6.QtCore", fromlist=["Qt"]
            ).Qt.ShortcutContext.WindowShortcut)
        item.triggered.connect(lambda checked=False, fn=callback: fn())
        menu.addAction(item)
        return item

    def tab(name):
        for index in range(window.tabs.count()):
            if window.tabs.tabText(index) == name:
                window.tabs.setCurrentIndex(index)
                return

    file_menu = bar.addMenu("&File")
    action(file_menu, "&New Project…", window.new_project_dialog, "Ctrl+N")
    action(file_menu, "&Open Project…", window.open_project_dialog, "Ctrl+O")
    action(file_menu, "&Save Project", window.save_project_dialog, "Ctrl+S")
    action(file_menu, "Save Project &As…", lambda: window.save_project_dialog(True), "Ctrl+Shift+S")
    file_menu.addSeparator()
    action(file_menu, "Game Setup…", window.edit_game_setup)
    file_menu.addSeparator()
    action(file_menu, "E&xit", window.close, "Ctrl+Q")

    edit_menu = bar.addMenu("&Edit")
    action(edit_menu, "Edit &Plays", lambda: tab("Play"))
    action(edit_menu, "Project &Settings", lambda: tab("Settings"))
    action(edit_menu, "Clear Plays…", window.clear)

    view_menu = bar.addMenu("&View")
    for name in ("Play", "Playslip", "Mapping Studio", "Print / Proof", "Settings", "Element Guide"):
        action(view_menu, name, lambda n=name: tab(n))
    view_menu.addSeparator()
    context_action = window.context_inspector.toggleViewAction()
    context_action.setText("Context Help")
    view_menu.addAction(context_action)
    action(view_menu, "Toggle Maximize", window.app_title_bar.toggle_maximize, "F11")

    mapping_menu = bar.addMenu("&Mapping")
    action(mapping_menu, "Mapping Studio", lambda: tab("Mapping Studio"))
    action(mapping_menu, "Open Scan Mapper…", window.edit_mapping)
    action(mapping_menu, "Choose Scan…", window.choose_scan)
    action(mapping_menu, "Choose Mapping…", window.choose_mapping)
    mapping_menu.addSeparator()
    action(mapping_menu, "Publish Reviewed Mapping…", window.publish_project_mapping)

    print_menu = bar.addMenu("&Print")
    action(print_menu, "Print / Proof Workspace", lambda: tab("Print / Proof"))
    action(print_menu, "Export Draft PDF…", window.export)
    action(print_menu, "Export Mapped PDF Proof…", window.export_mapped)
    print_menu.addSeparator()
    notice = print_menu.addAction("Physical printing requires verified calibration")
    notice.setEnabled(False)

    help_menu = bar.addMenu("&Help")
    action(help_menu, "Element Guide", lambda: tab("Element Guide"), "F1")
    action(help_menu, "About LotteryDash…", lambda: QMessageBox.information(
        window, "About LotteryDash",
        "LotteryDash · Local-first playslip workspace\n"
        "Pick 3 mapping is still being calibrated.\n"
        "Proofs are not verified production prints."
    ))
    return bar
