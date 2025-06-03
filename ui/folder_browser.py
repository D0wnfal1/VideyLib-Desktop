import os
from PyQt5.QtCore import Qt, pyqtSignal, QDir
from PyQt5.QtWidgets import (
    QTreeView, QFileSystemModel, QVBoxLayout, QHBoxLayout,
    QPushButton, QWidget, QLineEdit, QFileDialog, QToolButton,
    QMenu, QAction, QHeaderView, QAbstractItemView, QStyle
)
from PyQt5.QtGui import QIcon

class FolderBrowser(QWidget):
    """File system browser for navigating folders"""
    
    folderSelected = pyqtSignal(str)  
    def __init__(self, parent=None):
        super().__init__(parent)
        
        main_layout = QVBoxLayout()
        nav_layout = QHBoxLayout()
        
        self.model = QFileSystemModel()
        self.model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot)
        
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.model)
        self.tree_view.setAnimated(False)
        self.tree_view.setIndentation(20)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.sortByColumn(0, Qt.AscendingOrder)
        self.tree_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        for i in range(1, self.model.columnCount()):
            self.tree_view.hideColumn(i)
            
        header = self.tree_view.header()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setStretchLastSection(False)
        
        self.back_button = QPushButton()
        self.back_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowBack))
        self.back_button.setToolTip("Go Back")
        self.back_button.setFixedSize(32, 32)
        
        self.up_button = QPushButton()
        self.up_button.setIcon(self.style().standardIcon(QStyle.SP_ArrowUp))
        self.up_button.setToolTip("Go Up One Level")
        self.up_button.setFixedSize(32, 32)
        
        self.home_button = QPushButton()
        self.home_button.setIcon(self.style().standardIcon(QStyle.SP_DirHomeIcon))
        self.home_button.setToolTip("Home Folder")
        self.home_button.setFixedSize(32, 32)
        
        self.refresh_button = QPushButton()
        self.refresh_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.refresh_button.setToolTip("Refresh")
        self.refresh_button.setFixedSize(32, 32)
        
        self.path_field = QLineEdit()
        
        self.browse_button = QPushButton()
        self.browse_button.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
        self.browse_button.setToolTip("Browse for Folder")
        self.browse_button.setFixedSize(32, 32)
        
        self.history_button = QToolButton()
        self.history_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.history_button.setToolTip("Recent Folders")
        self.history_button.setFixedSize(32, 32)
        self.history_button.setPopupMode(QToolButton.InstantPopup)
        
        self.history_menu = QMenu(self)
        self.history_button.setMenu(self.history_menu)
        
        self.tree_view.clicked.connect(self.on_folder_selected)
        self.back_button.clicked.connect(self.go_back)
        self.up_button.clicked.connect(self.go_up)
        self.home_button.clicked.connect(self.go_home)
        self.refresh_button.clicked.connect(self.refresh)
        self.browse_button.clicked.connect(self.browse_for_folder)
        self.path_field.returnPressed.connect(self.path_entered)
        
        nav_layout.addWidget(self.back_button)
        nav_layout.addWidget(self.up_button)
        nav_layout.addWidget(self.home_button)
        nav_layout.addWidget(self.refresh_button)
        nav_layout.addWidget(self.path_field)
        nav_layout.addWidget(self.browse_button)
        nav_layout.addWidget(self.history_button)
        
        main_layout.addLayout(nav_layout)
        main_layout.addWidget(self.tree_view)
        
        self.setLayout(main_layout)
        
        self.history = []
        self.current_history_index = -1
        
        self.current_path = QDir.homePath()
        self.set_root_path(self.current_path)
    
    def set_root_path(self, path):
        """Set the root path for the file system model"""
        if not path or not os.path.isdir(path):
            return False
            
        self.current_path = path
        
        self.model.setRootPath(path)
        self.tree_view.setRootIndex(self.model.index(path))
        
        self.path_field.setText(path)
        
        self.add_to_history(path)
        
        return True
    
    def refresh(self):
        """Refresh the current view"""
        current_path = self.current_path
        self.model.setRootPath("")  
        self.set_root_path(current_path)
    
    def on_folder_selected(self, index):
        """Handle folder selection in the tree view"""
        path = self.model.filePath(index)
        if os.path.isdir(path):
            self.current_path = path
            self.path_field.setText(path)
            self.folderSelected.emit(path)
    
    def go_back(self):
        """Navigate back in history"""
        if self.current_history_index > 0:
            self.current_history_index -= 1
            path = self.history[self.current_history_index]
            
            old_history = self.history.copy()
            old_index = self.current_history_index
            
            self.set_root_path(path)
            
            self.history = old_history
            self.current_history_index = old_index
    
    def go_up(self):
        """Navigate up one directory level"""
        current = self.current_path
        parent = os.path.dirname(current)
        
        if parent and parent != current:
            self.set_root_path(parent)
    
    def go_home(self):
        """Navigate to user's home directory"""
        self.set_root_path(QDir.homePath())
    
    def browse_for_folder(self):
        """Open folder selection dialog"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder",
            self.current_path,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder:
            self.set_root_path(folder)
    
    def path_entered(self):
        """Handle manual path entry"""
        path = self.path_field.text()
        if os.path.isdir(path):
            self.set_root_path(path)
        else:
            self.path_field.setText(self.current_path)
    
    def add_to_history(self, path):
        """Add a path to the navigation history"""
        if self.history and self.history[self.current_history_index] == path:
            return
            
        if self.current_history_index < len(self.history) - 1:
            self.history = self.history[:self.current_history_index + 1]
            
        self.history.append(path)
        self.current_history_index = len(self.history) - 1
        
        if len(self.history) > 20:
            self.history = self.history[-20:]
            self.current_history_index = len(self.history) - 1
    
    def get_current_path(self):
        """Get the currently selected path"""
        return self.current_path
    
    def update_recent_folders(self, folders):
        """Update the recent folders menu"""
        self.history_menu.clear()
        
        for folder in folders:
            if os.path.isdir(folder):
                action = QAction(folder, self)
                action.triggered.connect(lambda checked=False, path=folder: self.set_root_path(path))
                self.history_menu.addAction(action) 