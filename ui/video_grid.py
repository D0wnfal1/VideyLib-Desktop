import os
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QTimer, QPoint
from PyQt5.QtWidgets import (
    QListView, QAbstractItemView, QMenu, QAction, QToolTip, 
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDialog, QFileDialog,
    QInputDialog, QMessageBox, QSizePolicy, QFormLayout, QTextEdit
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QPixmap, QIcon, QCursor, QPainter

from utils.video_utils import extract_thumbnail, format_file_size, format_duration

class VideoItem(QStandardItem):
    def __init__(self, file_path, file_name, thumbnail=None, size=0, duration=0, 
                 watched=False, tags=None):
        super().__init__()
        
        self.file_path = file_path
        self.file_name = file_name
        self.thumbnail = thumbnail
        self.size = size
        self.duration = duration
        self.watched = watched
        self.tags = tags or []
        self.video_data = None
        
        self.setData(file_path, Qt.UserRole)
        self.setData(file_name, Qt.DisplayRole)
        self.setEditable(False)
        
        if thumbnail is None:
            self.thumbnail = QPixmap(320, 180)
            self.thumbnail.fill(Qt.gray)
            self.setIcon(QIcon(self.thumbnail))
        else:
            self.setIcon(QIcon(thumbnail))

        self.setText(file_name + 
                     "\nSize: " + format_file_size(size) + 
                     " | Duration: " + format_duration(duration))
            
        self.setSizeHint(QSize(340, 220))

    def clone(self):
        return VideoItem(
            self.file_path, 
            self.file_name, 
            self.thumbnail, 
            self.size, 
            self.duration,
            self.watched,
            self.tags.copy() if self.tags else []
        )
        
    def update_watched_status(self, watched):
        self.watched = watched
        
        if watched:
            if self.thumbnail:
                overlay = QPixmap(self.thumbnail.size())
                overlay.fill(Qt.transparent)
                
                painter = QPainter(overlay)
                painter.setOpacity(0.5)
                painter.drawPixmap(0, 0, self.thumbnail)
                painter.end()
                
                self.setIcon(QIcon(overlay))
        else:
            self.setIcon(QIcon(self.thumbnail))


class VideoGrid(QListView):
    videoDoubleClicked = pyqtSignal(str)
    videoSelected = pyqtSignal(str)
    contextMenuRequested = pyqtSignal(str, QPoint)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.model = QStandardItemModel(self)
        self.setModel(self.model)
        
        self.setViewMode(QListView.IconMode)
        self.setIconSize(QSize(320, 180))
        self.setGridSize(QSize(340, 220))
        self.setResizeMode(QListView.Adjust)
        self.setUniformItemSizes(True)
        self.setSpacing(10)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        
        self.doubleClicked.connect(self._handle_double_click)
        self.clicked.connect(self._handle_click)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        self.setMouseTracking(True)
        self.hover_timer = QTimer()
        self.hover_timer.timeout.connect(self._show_video_preview)
        self.hover_item = None
        self.preview_widget = None
        self.preview_players = []
    
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        
        index = self.indexAt(event.pos())
        if index.isValid():
            if self.hover_item != index:
                self.hover_timer.stop()
                self.hover_item = index
                self.hover_timer.start(800)
        else:
            self.hover_timer.stop()
            self.hover_item = None
            if self.preview_widget:
                self._close_preview()
    
    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.hover_timer.stop()
        self.hover_item = None
        if self.preview_widget:
            self._close_preview()
    
    def _show_video_preview(self):
        try:
            if not self.hover_item:
                return
                
            item = self.model.itemFromIndex(self.hover_item)
            if not item:
                return
                
            file_path = item.file_path
            file_name = item.file_name
            
            if not os.path.exists(file_path):
                return
                
            if not self.preview_widget:
                try:
                    from utils.video_utils import extract_thumbnail
                    
                    self.preview_widget = QWidget(None, Qt.ToolTip)
                    self.preview_widget.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
                    self.preview_widget.setAttribute(Qt.WA_TranslucentBackground)
                    self.preview_widget.setStyleSheet("background-color: rgba(30, 30, 30, 230); border-radius: 8px; border: 1px solid rgba(100, 100, 100, 200);")
                    
                    main_layout = QVBoxLayout()
                    main_layout.setSpacing(8)
                    main_layout.setContentsMargins(10, 10, 10, 10)
                    
                    self.preview_title = QLabel()
                    self.preview_title.setStyleSheet("color: white; font-weight: bold;")
                    main_layout.addWidget(self.preview_title)
                    
                    self.preview_info = QLabel()
                    self.preview_info.setStyleSheet("color: white;")
                    self.preview_info.setWordWrap(True)
                    main_layout.addWidget(self.preview_info)
                    
                    thumbs_layout = QHBoxLayout()
                    thumbs_layout.setSpacing(5)
                    
                    self.preview_positions = [0.1, 0.5, 0.9]
                    self.preview_thumbnails = []
                    
                    for pos in self.preview_positions:
                        thumb_container = QWidget()
                        thumb_container.setStyleSheet("background-color: black; border-radius: 4px;")
                        container_layout = QVBoxLayout(thumb_container)
                        container_layout.setContentsMargins(0, 0, 0, 0)
                        container_layout.setSpacing(0)
                        
                        thumb_label = QLabel()
                        thumb_label.setFixedSize(160, 90)
                        thumb_label.setAlignment(Qt.AlignCenter)
                        thumb_label.setStyleSheet("background-color: black;")
                        
                        pos_label = QLabel(f"{int(pos * 100)}%")
                        pos_label.setAlignment(Qt.AlignCenter)
                        pos_label.setStyleSheet("color: white; background-color: rgba(0, 0, 0, 150); padding: 2px;")
                        
                        container_layout.addWidget(thumb_label)
                        container_layout.addWidget(pos_label)
                        
                        self.preview_thumbnails.append(thumb_label)
                        
                        thumbs_layout.addWidget(thumb_container)
                    
                    main_layout.addLayout(thumbs_layout)
                    self.preview_widget.setLayout(main_layout)
                    
                except Exception as e:
                    print(f"Error creating preview widget: {str(e)}")
                    return
            
            self.preview_title.setText(file_name)
            
            info_text = f"Size: {format_file_size(item.size)} | Duration: {format_duration(item.duration)}"
            if item.tags:
                info_text += f"<br>Tags: {', '.join(tag for tag in item.tags)}"
                
            self.preview_info.setText(info_text)
            
            from utils.video_utils import extract_thumbnail
            
            for i, pos in enumerate(self.preview_positions):
                try:
                    thumbnail = extract_thumbnail(file_path, pos, QSize(160, 90))
                    if thumbnail:
                        self.preview_thumbnails[i].setPixmap(thumbnail)
                    else:
                        placeholder = QPixmap(160, 90)
                        placeholder.fill(Qt.darkGray)
                        self.preview_thumbnails[i].setPixmap(placeholder)
                except Exception as e:
                    print(f"Error extracting thumbnail at position {pos}: {str(e)}")
                    placeholder = QPixmap(160, 90)
                    placeholder.fill(Qt.darkGray)
                    self.preview_thumbnails[i].setPixmap(placeholder)
            
            cursor_pos = QCursor.pos()
            preview_x = cursor_pos.x() + 20
            preview_y = cursor_pos.y() + 20
            
            desktop = self.screen().availableGeometry()
            if preview_x + self.preview_widget.sizeHint().width() > desktop.right():
                preview_x = desktop.right() - self.preview_widget.sizeHint().width() - 10
            if preview_y + self.preview_widget.sizeHint().height() > desktop.bottom():
                preview_y = desktop.bottom() - self.preview_widget.sizeHint().height() - 10
                
            self.preview_widget.move(preview_x, preview_y)
            self.preview_widget.show()
            
        except Exception as e:
            print(f"Error showing video preview: {str(e)}")
            self._close_preview()
    
    def _close_preview(self):
        try:
            if hasattr(self, 'preview_widget') and self.preview_widget:
                try:
                    self.preview_widget.hide()
                except Exception as e:
                    print(f"Error hiding preview widget: {str(e)}")
                    
            self.hover_item = None
            
        except Exception as e:
            print(f"Error in _close_preview: {str(e)}")
    
    def _handle_double_click(self, index):
        item = self.model.itemFromIndex(index)
        if item:
            self.videoDoubleClicked.emit(item.file_path)
    
    def _handle_click(self, index):
        item = self.model.itemFromIndex(index)
        if item:
            self.videoSelected.emit(item.file_path)
    
    def _show_context_menu(self, position):
        index = self.indexAt(position)
        if not index.isValid():
            return
            
        item = self.model.itemFromIndex(index)
        if item:
            global_pos = self.mapToGlobal(position)
            self.contextMenuRequested.emit(item.file_path, global_pos)
    
    def update_video_watched(self, file_path, watched):
        for i in range(self.model.rowCount()):
            item = self.model.item(i)
            if item and item.file_path == file_path:
                item.update_watched_status(watched)
                break
    
    def add_video(self, file_path, file_name, thumbnail=None, size=0, duration=0, 
                  watched=False, tags=None):
        video_item = VideoItem(
            file_path, 
            file_name, 
            thumbnail, 
            size, 
            duration,
            watched,
            tags
        )
        
        self.model.appendRow(video_item)
        return video_item
    
    def clear_videos(self):
        self.model.clear()
    
    def get_selected_videos(self):
        selected_indexes = self.selectedIndexes()
        video_paths = []
        
        for index in selected_indexes:
            item = self.model.itemFromIndex(index)
            if item:
                video_paths.append(item.file_path)
                
        return video_paths
        
    def update_video_tags(self, file_path, tags):
        for i in range(self.model.rowCount()):
            item = self.model.item(i)
            if item and item.file_path == file_path:
                item.tags = tags.copy() if tags else []
                item.setText(item.file_name + 
                        "\nSize: " + format_file_size(item.size) + 
                        " | Duration: " + format_duration(item.duration))
                break


class VideoDetailsDialog(QDialog):
    def __init__(self, file_path, file_name, size, duration, tags=None, notes="", watched=False, parent=None):
        super().__init__(parent)
        
        from PyQt5.QtWidgets import QPushButton, QCheckBox, QDialogButtonBox, QFormLayout
        
        self.setWindowTitle(f"Video Details - {file_name}")
        self.resize(500, 400)
        
        self.file_path = file_path
        self.file_name = file_name
        self.tags = tags or []
        self.notes = notes
        self.watched = watched
        
        layout = QVBoxLayout()
        
        info_layout = QFormLayout()
        
        thumbnail_label = QLabel()
        thumbnail = extract_thumbnail(file_path, 0.1, QSize(320, 180))
        if thumbnail:
            thumbnail_label.setPixmap(thumbnail)
        else:
            thumbnail_label.setText("No thumbnail available")
            
        info_layout.addRow("Thumbnail:", thumbnail_label)
        info_layout.addRow("File:", QLabel(file_name))
        info_layout.addRow("Path:", QLabel(file_path))
        info_layout.addRow("Size:", QLabel(format_file_size(size)))
        info_layout.addRow("Duration:", QLabel(format_duration(duration)))
        
        self.tags_label = QLabel(", ".join(self.tags) if self.tags else "No tags")
        self.tags_label.setWordWrap(True)
        
        tags_layout = QHBoxLayout()
        tags_layout.addWidget(self.tags_label)
        
        add_tag_btn = QPushButton("Add Tag")
        add_tag_btn.clicked.connect(self.add_tag)
        
        remove_tag_btn = QPushButton("Remove Tag")
        remove_tag_btn.clicked.connect(self.remove_tag)
        
        tags_layout.addWidget(add_tag_btn)
        tags_layout.addWidget(remove_tag_btn)
        
        info_layout.addRow("Tags:", tags_layout)
        
        notes_label = QLabel("Notes:")
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlainText(self.notes)
        
        self.watched_checkbox = QCheckBox("Mark as watched")
        self.watched_checkbox.setChecked(self.watched)
        
        layout.addLayout(info_layout)
        layout.addWidget(notes_label)
        layout.addWidget(self.notes_edit)
        layout.addWidget(self.watched_checkbox)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def add_tag(self):
        tag, ok = QInputDialog.getText(self, "Add Tag", "Enter tag name:")
        
        if ok and tag:
            tag = tag.strip()
            if tag and tag not in self.tags:
                self.tags.append(tag)
                self.tags_label.setText(", ".join(self.tags))
    
    def remove_tag(self):
        if not self.tags:
            return
            
        tag, ok = QInputDialog.getItem(
            self, "Remove Tag", "Select tag to remove:", 
            self.tags, 0, False
        )
        
        if ok and tag in self.tags:
            self.tags.remove(tag)
            self.tags_label.setText(", ".join(self.tags) if self.tags else "No tags")
    
    def get_notes(self):
        return self.notes_edit.toPlainText()
    
    def get_watched_status(self):
        return self.watched_checkbox.isChecked()
    
    def get_tags(self):
        return self.tags