import os
import datetime
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QComboBox, QFormLayout, QDialogButtonBox, QMessageBox, QSpinBox
)
from PyQt5.QtGui import QIcon, QPixmap

from utils.video_utils import extract_thumbnail, format_file_size, format_duration
from db.database import Database

class ReviewDialog(QDialog):
    """Dialog for adding or editing a video review"""
    
    def __init__(self, video_id, file_path, file_name, parent=None):
        super().__init__(parent)
        
        self.db = Database()
        self.video_id = video_id
        self.file_path = file_path
        self.file_name = file_name
        self.existing_review = self.db.get_review(video_id)
        
        self.setWindowTitle("Video Review")
        self.resize(500, 400)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Info section
        info_layout = QFormLayout()
        
        # Extract thumbnail
        thumbnail_label = QLabel()
        thumbnail = extract_thumbnail(file_path, 0.1, QSize(320, 180))
        if thumbnail:
            thumbnail_label.setPixmap(thumbnail)
        else:
            thumbnail_label.setText("No thumbnail available")
            
        info_layout.addRow("Thumbnail:", thumbnail_label)
        info_layout.addRow("File:", QLabel(file_name))
        
        # Rating section
        rating_layout = QHBoxLayout()
        rating_label = QLabel("Rating (1-5):")
        self.rating_spinbox = QSpinBox()
        self.rating_spinbox.setRange(1, 5)
        self.rating_spinbox.setSingleStep(1)
        
        # Add star icons to represent rating
        self.star_labels = []
        for i in range(5):
            star_label = QLabel()
            star_label.setFixedSize(24, 24)
            self.star_labels.append(star_label)
            rating_layout.addWidget(star_label)
        
        # Connect rating change to update stars
        self.rating_spinbox.valueChanged.connect(self._update_stars)
        
        # Set default rating or load existing
        if self.existing_review:
            self.rating_spinbox.setValue(self.existing_review["rating"])
        else:
            self.rating_spinbox.setValue(3)  # Default to 3 stars
        
        rating_layout.insertWidget(0, rating_label)
        rating_layout.insertWidget(1, self.rating_spinbox)
        rating_layout.addStretch()
        
        # Review text section
        review_label = QLabel("Your Review:")
        self.review_edit = QTextEdit()
        
        # Load existing review if available
        if self.existing_review:
            self.review_edit.setPlainText(self.existing_review["review_text"])
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_review)
        button_box.rejected.connect(self.reject)
        
        # Add all to main layout
        layout.addLayout(info_layout)
        layout.addLayout(rating_layout)
        layout.addWidget(review_label)
        layout.addWidget(self.review_edit)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # Initialize stars
        self._update_stars(self.rating_spinbox.value())
    
    def _update_stars(self, rating):
        """Update star icons based on rating"""
        for i in range(5):
            if i < rating:
                # Filled star for ratings >= current position
                self.star_labels[i].setPixmap(self._get_star_icon(True))
            else:
                # Empty star for ratings < current position
                self.star_labels[i].setPixmap(self._get_star_icon(False))
    
    def _get_star_icon(self, filled):
        """Get star icon (filled or empty)"""
        # Use system icons if available, otherwise use text
        icon_size = QSize(20, 20)
        pixmap = QPixmap(icon_size)
        pixmap.fill(Qt.transparent)
        
        if filled:
            # Yellow filled star
            pixmap.fill(Qt.yellow)
        else:
            # Gray empty star
            pixmap.fill(Qt.lightGray)
        
        return pixmap
    
    def save_review(self):
        """Save the review"""
        rating = self.rating_spinbox.value()
        review_text = self.review_edit.toPlainText()
        
        if not review_text.strip():
            QMessageBox.warning(self, "Empty Review", "Please enter a review.")
            return
        
        try:
            if self.existing_review:
                # Update existing review
                self.db.update_review(self.existing_review["id"], rating, review_text)
            else:
                # Add new review
                self.db.add_review(
                    self.video_id,
                    rating,
                    review_text,
                    datetime.datetime.now().isoformat()
                )
            
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save review: {str(e)}")


class ReviewsListDialog(QDialog):
    """Dialog for displaying all reviews"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.db = Database()
        self.reviews = self.db.get_all_reviews()
        
        self.setWindowTitle("All Reviews")
        self.resize(700, 500)
        
        # Create layout
        layout = QVBoxLayout()
        
        # Header
        header = QLabel("<h2>Video Reviews</h2>")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Reviews container
        reviews_layout = QVBoxLayout()
        
        if not self.reviews:
            no_reviews = QLabel("No reviews found.")
            no_reviews.setAlignment(Qt.AlignCenter)
            reviews_layout.addWidget(no_reviews)
        else:
            for review in self.reviews:
                review_widget = self._create_review_widget(review)
                reviews_layout.addWidget(review_widget)
                reviews_layout.addWidget(QLabel(""))  # Spacer
        
        # Scroll area for reviews
        from PyQt5.QtWidgets import QScrollArea, QWidget
        scroll_widget = QWidget()
        scroll_widget.setLayout(reviews_layout)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_widget)
        
        layout.addWidget(scroll_area)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        
        self.setLayout(layout)
    
    def _create_review_widget(self, review):
        """Create a widget to display a review"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Header with file name and rating
        header_layout = QHBoxLayout()
        file_name = QLabel(f"<b>{review['file_name']}</b>")
        
        # Rating stars
        rating_widget = QWidget()
        rating_layout = QHBoxLayout()
        rating_layout.setContentsMargins(0, 0, 0, 0)
        
        for i in range(5):
            star = QLabel()
            star.setFixedSize(16, 16)
            
            # Filled or empty star
            if i < review['rating']:
                pixmap = QPixmap(16, 16)
                pixmap.fill(Qt.yellow)
            else:
                pixmap = QPixmap(16, 16)
                pixmap.fill(Qt.lightGray)
                
            star.setPixmap(pixmap)
            rating_layout.addWidget(star)
        
        rating_widget.setLayout(rating_layout)
        
        header_layout.addWidget(file_name)
        header_layout.addWidget(rating_widget)
        header_layout.addStretch()
        
        # Date
        date_label = QLabel(f"Review date: {review['date_added'][:10]}")
        date_label.setAlignment(Qt.AlignRight)
        header_layout.addWidget(date_label)
        
        # Review text
        review_text = QLabel(review['review_text'])
        review_text.setWordWrap(True)
        review_text.setTextFormat(Qt.PlainText)
        
        # Add to layout
        layout.addLayout(header_layout)
        layout.addWidget(review_text)
        
        widget.setLayout(layout)
        widget.setStyleSheet("background-color: rgba(200, 200, 200, 30); border-radius: 5px; padding: 10px;")
        
        return widget 