#!/usr/bin/env python3
import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon

from ui.main_window import MainWindow
from utils.settings import Settings

def main():
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("Video Library")
    app.setOrganizationName("VideoLibraryApp")
    
    icon_path = os.path.join(os.path.dirname(__file__), "resources", "icons", "app_icon.svg")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    settings = Settings()
    
    main_window = MainWindow(settings)
    main_window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 