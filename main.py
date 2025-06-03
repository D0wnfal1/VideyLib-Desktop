#!/usr/bin/env python3
import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QDir

from ui.main_window import MainWindow
from utils.settings import Settings

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName("Video Library")
    app.setOrganizationName("VideoLibraryApp")
    
    app_data_dir = os.path.join(QDir.homePath(), ".videolibrary")
    os.makedirs(app_data_dir, exist_ok=True)
    
    settings = Settings()
    
    main_window = MainWindow(settings)
    main_window.show()
    
    sys.exit(app.exec_()) 