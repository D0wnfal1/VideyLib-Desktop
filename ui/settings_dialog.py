from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget,
    QPushButton, QLabel, QLineEdit, QSpinBox, QComboBox, QFileDialog,
    QDialogButtonBox, QCheckBox
)
from PyQt5.QtCore import QDir

class SettingsDialog(QDialog):
    """Dialog for configuring application settings"""
    
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        
        self.settings = settings
        
        self.setWindowTitle("Settings")
        self.resize(500, 400)
        
        # Create layout
        main_layout = QVBoxLayout()
        
        # Create tabs
        tabs = QTabWidget()
        
        # General settings tab
        general_tab = QWidget()
        general_layout = QFormLayout()
        
        # Start folder selection
        start_folder_layout = QHBoxLayout()
        self.start_folder_edit = QLineEdit()
        self.start_folder_edit.setText(settings.get("start_folder", QDir.homePath()))
        
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self.browse_start_folder)
        
        start_folder_layout.addWidget(self.start_folder_edit)
        start_folder_layout.addWidget(browse_button)
        
        general_layout.addRow("Default Start Folder:", start_folder_layout)
        
        # Theme selection
        self.theme_selector = QComboBox()
        self.theme_selector.addItems(["Light", "Dark"])
        current_theme = settings.get("theme", "light").capitalize()
        self.theme_selector.setCurrentText(current_theme)
        
        general_layout.addRow("Theme on Startup:", self.theme_selector)
        
        # Default volume
        self.default_volume = QSpinBox()
        self.default_volume.setRange(0, 100)
        self.default_volume.setValue(settings.get("default_volume", 70))
        self.default_volume.setSuffix("%")
        
        general_layout.addRow("Default Volume:", self.default_volume)
        
        general_tab.setLayout(general_layout)
        
        # Video preview settings tab
        preview_tab = QWidget()
        preview_layout = QFormLayout()
        
        # Preview length
        self.preview_length = QSpinBox()
        self.preview_length.setRange(1, 10)
        self.preview_length.setValue(settings.get("preview_length_seconds", 3))
        self.preview_length.setSuffix(" seconds")
        
        preview_layout.addRow("Preview Length:", self.preview_length)
        
        # Enable video preview checkbox
        self.enable_preview = QCheckBox("Enable Video Preview on Hover")
        self.enable_preview.setChecked(settings.get("enable_preview", True))
        
        preview_layout.addRow("", self.enable_preview)
        
        preview_tab.setLayout(preview_layout)
        
        # Performance settings tab
        performance_tab = QWidget()
        performance_layout = QFormLayout()
        
        # Thumbnail cache size
        self.thumbnail_cache_size = QSpinBox()
        self.thumbnail_cache_size.setRange(10, 1000)
        self.thumbnail_cache_size.setValue(settings.get("thumbnail_cache_size_mb", 100))
        self.thumbnail_cache_size.setSuffix(" MB")
        
        performance_layout.addRow("Thumbnail Cache Size:", self.thumbnail_cache_size)
        
        # Max thumbnails to load at once
        self.max_thumbnails = QSpinBox()
        self.max_thumbnails.setRange(10, 1000)
        self.max_thumbnails.setValue(settings.get("max_thumbnails_at_once", 100))
        
        performance_layout.addRow("Max Thumbnails to Load at Once:", self.max_thumbnails)
        
        # Preload thumbnails checkbox
        self.preload_thumbnails = QCheckBox("Preload Thumbnails in Background")
        self.preload_thumbnails.setChecked(settings.get("preload_thumbnails", True))
        
        performance_layout.addRow("", self.preload_thumbnails)
        
        performance_tab.setLayout(performance_layout)
        
        # Add tabs to tab widget
        tabs.addTab(general_tab, "General")
        tabs.addTab(preview_tab, "Video Preview")
        tabs.addTab(performance_tab, "Performance")
        
        # Add tab widget to layout
        main_layout.addWidget(tabs)
        
        # Add OK/Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_settings)
        button_box.rejected.connect(self.reject)
        
        main_layout.addWidget(button_box)
        
        self.setLayout(main_layout)
    
    def browse_start_folder(self):
        """Open folder dialog to select start folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Default Start Folder",
            self.start_folder_edit.text(),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder:
            self.start_folder_edit.setText(folder)
    
    def accept_settings(self):
        """Save settings and close dialog"""
        # Update settings with new values
        self.settings.set("start_folder", self.start_folder_edit.text())
        self.settings.set("theme", self.theme_selector.currentText().lower())
        self.settings.set("default_volume", self.default_volume.value())
        self.settings.set("preview_length_seconds", self.preview_length.value())
        self.settings.set("enable_preview", self.enable_preview.isChecked())
        self.settings.set("thumbnail_cache_size_mb", self.thumbnail_cache_size.value())
        self.settings.set("max_thumbnails_at_once", self.max_thumbnails.value())
        self.settings.set("preload_thumbnails", self.preload_thumbnails.isChecked())
        
        self.accept() 