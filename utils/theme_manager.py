from PyQt5.QtWidgets import QApplication
import qdarkstyle

LIGHT_STYLESHEET = """
QWidget {
    background-color: #f5f5f5;
    color: #333333;
}

QPushButton {
    background-color: #e0e0e0;
    border: 1px solid #bbbbbb;
    border-radius: 4px;
    padding: 5px 10px;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #d0d0d0;
}

QPushButton:pressed {
    background-color: #c0c0c0;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: white;
    border: 1px solid #bbbbbb;
    border-radius: 4px;
    padding: 2px;
}

QListView, QTreeView, QTableView {
    background-color: white;
    alternate-background-color: #f0f0f0;
    border: 1px solid #bbbbbb;
}

QListView::item:selected, QTreeView::item:selected, QTableView::item:selected {
    background-color: #0078d7;
    color: white;
}

QMenu {
    background-color: white;
    border: 1px solid #bbbbbb;
}

QMenu::item:selected {
    background-color: #0078d7;
    color: white;
}

QScrollBar:vertical {
    border: none;
    background-color: #f0f0f0;
    width: 10px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #c0c0c0;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #a0a0a0;
}

QSlider::groove:horizontal {
    border: 1px solid #bbbbbb;
    height: 8px;
    background: #f0f0f0;
    margin: 2px 0;
    border-radius: 4px;
}

QSlider::handle:horizontal {
    background: #0078d7;
    border: 1px solid #0078d7;
    width: 18px;
    height: 18px;
    margin: -5px 0;
    border-radius: 9px;
}

QGroupBox {
    border: 1px solid #bbbbbb;
    border-radius: 4px;
    margin-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 5px;
}

QTabWidget::pane {
    border: 1px solid #bbbbbb;
    background-color: white;
}

QTabBar::tab {
    background-color: #e0e0e0;
    border: 1px solid #bbbbbb;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 5px 10px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: white;
}

QComboBox {
    border: 1px solid #bbbbbb;
    border-radius: 4px;
    padding: 1px 18px 1px 3px;
    min-width: 6em;
    background-color: white;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 15px;
    border-left: 1px solid #bbbbbb;
}

QMainWindow::separator {
    width: 1px;
    height: 1px;
    background-color: #bbbbbb;
}

QToolTip {
    background-color: #f5f5f5;
    border: 1px solid #bbbbbb;
    color: #333333;
    padding: 2px;
}

QStatusBar {
    background-color: #e0e0e0;
    color: #333333;
}

QProgressBar {
    border: 1px solid #bbbbbb;
    border-radius: 4px;
    text-align: center;
    background-color: white;
}

QProgressBar::chunk {
    background-color: #0078d7;
    width: 1px;
}
"""

class ThemeManager:
    @staticmethod
    def apply_theme(theme_name, app=None):
        if app is None:
            app = QApplication.instance()
            
        if app is None:
            return
            
        if theme_name.lower() == "dark":
            app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        else:
            app.setStyleSheet(LIGHT_STYLESHEET)
            
    @staticmethod
    def toggle_theme(current_theme, app=None):
        new_theme = "light" if current_theme.lower() == "dark" else "dark"
        ThemeManager.apply_theme(new_theme, app)
        return new_theme