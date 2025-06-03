from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton,
    QLabel, QComboBox, QCheckBox, QGroupBox, QFormLayout
)

class SearchFilterWidget(QWidget):
    """Widget for searching and filtering video files"""
    
    # Signals
    searchRequested = pyqtSignal(dict)  # Emits search/filter parameters
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create layouts
        main_layout = QVBoxLayout()
        search_layout = QHBoxLayout()
        filter_layout = QHBoxLayout()
        
        # Create search components
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search videos...")
        self.search_input.returnPressed.connect(self.perform_search)
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.perform_search)
        
        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_search)
        
        # Create filter components
        self.filter_group = QGroupBox("Filters")
        filter_form_layout = QFormLayout()
        
        # Sort by filter
        self.sort_by = QComboBox()
        self.sort_by.addItems(["Name", "Date Modified", "Size", "Duration"])
        filter_form_layout.addRow("Sort by:", self.sort_by)
        
        # Sort order
        self.sort_order = QComboBox()
        self.sort_order.addItems(["Ascending", "Descending"])
        filter_form_layout.addRow("Order:", self.sort_order)
        
        # Watched filter
        self.watched_filter = QComboBox()
        self.watched_filter.addItems(["All Videos", "Watched Only", "Unwatched Only"])
        filter_form_layout.addRow("Watched Status:", self.watched_filter)
        
        # Tag filter (will be populated dynamically)
        self.tag_filter = QComboBox()
        self.tag_filter.addItem("All Tags")
        filter_form_layout.addRow("Tag Filter:", self.tag_filter)
        
        # Apply filters button
        self.apply_filters_button = QPushButton("Apply Filters")
        self.apply_filters_button.clicked.connect(self.perform_search)
        
        # Set layouts
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.clear_button)
        
        self.filter_group.setLayout(filter_form_layout)
        
        filter_layout.addWidget(self.filter_group)
        filter_layout.addWidget(self.apply_filters_button)
        
        main_layout.addLayout(search_layout)
        main_layout.addLayout(filter_layout)
        
        self.setLayout(main_layout)
    
    def perform_search(self):
        """Perform search/filter based on current settings"""
        params = {
            "search_text": self.search_input.text(),
            "sort_by": self.sort_by.currentText().lower().replace(" ", "_"),
            "sort_order": self.sort_order.currentText().lower(),
            "watched_filter": self.watched_filter.currentText()
        }
        
        # Add tag filter if a specific tag is selected
        tag = self.tag_filter.currentText()
        if tag != "All Tags":
            params["tag"] = tag
            
        self.searchRequested.emit(params)
    
    def clear_search(self):
        """Clear search input and reset filters"""
        self.search_input.clear()
        self.sort_by.setCurrentIndex(0)  # Name
        self.sort_order.setCurrentIndex(0)  # Ascending
        self.watched_filter.setCurrentIndex(0)  # All Videos
        self.tag_filter.setCurrentIndex(0)  # All Tags
        
        # Perform search with cleared parameters
        self.perform_search()
    
    def update_tags(self, tags):
        """Update the tag filter dropdown with available tags"""
        # Store current selection
        current_tag = self.tag_filter.currentText()
        
        # Clear and re-populate
        self.tag_filter.clear()
        self.tag_filter.addItem("All Tags")
        
        for tag in sorted(tags):
            self.tag_filter.addItem(tag)
            
        # Try to restore previous selection
        index = self.tag_filter.findText(current_tag)
        if index >= 0:
            self.tag_filter.setCurrentIndex(index)
        else:
            self.tag_filter.setCurrentIndex(0) 