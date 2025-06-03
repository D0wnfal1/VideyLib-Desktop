import os
import time
import datetime
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtCore import Qt, QSize, QTimer, QFileInfo, pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QAction, QMenu, QMenuBar, QToolBar, QStatusBar, QMessageBox,
    QFileDialog, QInputDialog, QDockWidget, QTabWidget, QShortcut,
    QPushButton, QLabel, QApplication, QStyle, QProgressDialog,
    QProgressBar
)
from PyQt5.QtGui import QIcon, QKeySequence

from ui.folder_browser import FolderBrowser
from ui.video_grid import VideoGrid, VideoDetailsDialog
from ui.video_player import VideoPlayer
from ui.search_filter import SearchFilterWidget
from ui.settings_dialog import SettingsDialog
from ui.review_dialog import ReviewDialog, ReviewsListDialog

from utils.video_utils import is_video_file, extract_thumbnail, extract_thumbnail_async, get_video_metadata
from utils.theme_manager import ThemeManager
from utils.settings import Settings
from db.database import Database

THREAD_POOL = ThreadPoolExecutor(max_workers=8)

class MainWindow(QMainWindow):
    """Main application window"""
    
    video_loaded_signal = pyqtSignal(str, str, object, int, float, bool, list)
    thumbnail_loaded_signal = pyqtSignal(str, object)
    load_progress_signal = pyqtSignal(int, int)  
    
    def __init__(self, settings):
        super().__init__()
        
        self.settings = settings
        self.db = Database()
        
        self._loading_thread = None
        self._loading_canceled = False
        self._current_thumbnails_loading = 0
        self._max_concurrent_thumbnails = 4
        
        self.setup_ui()
        
        self.connect_signals()
        
        theme = self.settings.get("theme", "light")
        ThemeManager.apply_theme(theme)
        
        self.setWindowTitle("Video Library")
        self.resize(1200, 800)
        
        start_folder = self.settings.get("start_folder", None)
        if start_folder and os.path.isdir(start_folder):
            self.folder_browser.set_root_path(start_folder)
            QTimer.singleShot(100, lambda: self.load_videos_in_folder(start_folder))
            
        self.update_recent_folders_menu()
        
        self.update_tag_filters()
    
    def setup_ui(self):
        """Set up the user interface"""
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        
        self.splitter = QSplitter(Qt.Horizontal)
        
        self.folder_browser = FolderBrowser()
        self.splitter.addWidget(self.folder_browser)
        
        self.video_area = QWidget()
        video_layout = QVBoxLayout()
        
        self.search_filter = SearchFilterWidget()
        video_layout.addWidget(self.search_filter)
        
        self.video_grid = VideoGrid()
        video_layout.addWidget(self.video_grid)
        
        self.video_player = VideoPlayer()
        self.video_player.hide()
        video_layout.addWidget(self.video_player)
        
        self.video_area.setLayout(video_layout)
        self.splitter.addWidget(self.video_area)
        
        self.splitter.setSizes([300, 900])
        
        main_layout.addWidget(self.splitter)
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setMaximumHeight(15)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.status_bar.addPermanentWidget(self.status_label)
        
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        self.create_menus()
        self.create_toolbars()
        
        self.create_shortcuts()
    
    def create_menus(self):
        """Create application menus"""
        file_menu = self.menuBar().addMenu("&File")
        
        open_folder_action = QAction("&Open Folder...", self)
        open_folder_action.setShortcut(QKeySequence.Open)
        open_folder_action.triggered.connect(self.browse_for_folder)
        file_menu.addAction(open_folder_action)
        
        self.recent_folders_menu = QMenu("Recent Folders", self)
        file_menu.addMenu(self.recent_folders_menu)
        
        file_menu.addSeparator()
        
        settings_action = QAction("&Settings...", self)
        settings_action.triggered.connect(self.show_settings_dialog)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        edit_menu = self.menuBar().addMenu("&Edit")
        
        rename_action = QAction("&Rename", self)
        rename_action.setShortcut(QKeySequence("F2"))
        rename_action.triggered.connect(self.rename_selected_video)
        edit_menu.addAction(rename_action)
        
        move_action = QAction("&Move to...", self)
        move_action.setShortcut(QKeySequence("Ctrl+M"))
        move_action.triggered.connect(self.move_selected_videos)
        edit_menu.addAction(move_action)
        
        delete_action = QAction("&Delete", self)
        delete_action.setShortcut(QKeySequence.Delete)
        delete_action.triggered.connect(self.delete_selected_videos)
        edit_menu.addAction(delete_action)
        
        view_menu = self.menuBar().addMenu("&View")
        
        toggle_theme_action = QAction("Toggle &Theme", self)
        toggle_theme_action.setShortcut("T")
        toggle_theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(toggle_theme_action)
        
        view_menu.addSeparator()
        
        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut(QKeySequence.Refresh)
        refresh_action.triggered.connect(self.refresh_current_folder)
        view_menu.addAction(refresh_action)
        
        tags_menu = self.menuBar().addMenu("&Tags")
        
        manage_tags_action = QAction("&Manage Tags...", self)
        manage_tags_action.triggered.connect(self.show_tag_manager)
        tags_menu.addAction(manage_tags_action)
        
        reviews_menu = self.menuBar().addMenu("&Reviews")
        
        all_reviews_action = QAction("View &All Reviews...", self)
        all_reviews_action.triggered.connect(self.show_all_reviews)
        reviews_menu.addAction(all_reviews_action)
        
        help_menu = self.menuBar().addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def create_toolbars(self):
        """Create application toolbars"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(24, 24))
        
        open_folder_action = QAction(self.style().standardIcon(QStyle.SP_DirOpenIcon), "Open Folder", self)
        open_folder_action.triggered.connect(self.browse_for_folder)
        toolbar.addAction(open_folder_action)
        
        refresh_action = QAction(self.style().standardIcon(QStyle.SP_BrowserReload), "Refresh", self)
        refresh_action.triggered.connect(self.refresh_current_folder)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        move_action = QAction(self.style().standardIcon(QStyle.SP_DirLinkIcon), "Move Files", self)
        move_action.triggered.connect(self.move_selected_videos)
        toolbar.addAction(move_action)
        
        toggle_theme_action = QAction(self.style().standardIcon(QStyle.SP_DesktopIcon), "Toggle Theme", self)
        toggle_theme_action.triggered.connect(self.toggle_theme)
        toolbar.addAction(toggle_theme_action)
        
        settings_action = QAction(self.style().standardIcon(QStyle.SP_FileDialogDetailedView), "Settings", self)
        settings_action.triggered.connect(self.show_settings_dialog)
        toolbar.addAction(settings_action)
        
        self.addToolBar(toolbar)
    
    def create_shortcuts(self):
        """Create keyboard shortcuts"""
        self.shortcut_refresh = QShortcut(QKeySequence(Qt.Key_F5), self)
        self.shortcut_refresh.activated.connect(self.refresh_current_folder)
        
        # Delete key to delete selected videos
        self.shortcut_delete = QShortcut(QKeySequence(Qt.Key_Delete), self)
        self.shortcut_delete.activated.connect(self.delete_selected_videos)
        
        # F2 to rename selected video
        self.shortcut_rename = QShortcut(QKeySequence(Qt.Key_F2), self)
        self.shortcut_rename.activated.connect(self.rename_selected_video)
        
        # Ctrl+M to move selected videos
        self.shortcut_move = QShortcut(QKeySequence("Ctrl+M"), self)
        self.shortcut_move.activated.connect(self.move_selected_videos)
    
    def connect_signals(self):
        """Connect signals to slots"""
        # Connect folder browser signals
        self.folder_browser.folderSelected.connect(self.load_videos_in_folder)
        
        # Connect video grid signals
        self.video_grid.videoDoubleClicked.connect(self.play_video)
        self.video_grid.videoSelected.connect(self.on_video_selected)
        self.video_grid.contextMenuRequested.connect(self.show_video_context_menu)
        
        # Connect video player signals
        self.video_player.videoFinished.connect(self.on_video_finished)
        self.video_player.errorOccurred.connect(self.handle_player_error)
        
        # Connect search filter signals
        self.search_filter.searchRequested.connect(self.apply_search_filter)
        
        # Подключаем наши сигналы для обновления UI из потоков
        self.video_loaded_signal.connect(self.add_video_to_grid)
        self.thumbnail_loaded_signal.connect(self.update_video_thumbnail)
        self.load_progress_signal.connect(self.update_load_progress)
    
    def update_recent_folders_menu(self):
        """Update the recent folders menu with items from settings"""
        self.recent_folders_menu.clear()
        
        recent_folders = self.settings.get("recent_folders", [])
        
        for folder in recent_folders:
            if os.path.isdir(folder):
                action = QAction(folder, self)
                action.triggered.connect(lambda checked=False, path=folder: self.open_recent_folder(path))
                self.recent_folders_menu.addAction(action)
                
        # Update the folder browser history button menu as well
        self.folder_browser.update_recent_folders(recent_folders)
    
    def update_tag_filters(self):
        """Update tag filters with all available tags"""
        # Get all tags from database
        tags = [tag["name"] for tag in self.db.get_all_tags()]
        
        # Update search filter widget
        self.search_filter.update_tags(tags)
    
    def browse_for_folder(self):
        """Open folder browser dialog"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder",
            self.folder_browser.get_current_path(),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder:
            self.folder_browser.set_root_path(folder)
            self.load_videos_in_folder(folder)
    
    def open_recent_folder(self, folder):
        """Open a folder from the recent folders list"""
        if os.path.isdir(folder):
            self.folder_browser.set_root_path(folder)
            self.load_videos_in_folder(folder)
    
    def _load_videos_async(self, folder_path, video_files):
        """Асинхронно загружает видеофайлы (для работы в отдельном потоке)"""
        try:
            total_files = len(video_files)
            
            # Отправляем начальный статус
            self.load_progress_signal.emit(0, total_files)
            
            for i, file_name in enumerate(video_files):
                # Проверяем флаг отмены
                if self._loading_canceled:
                    break
                    
                file_path = os.path.join(folder_path, file_name)
                
                # Проверяем, есть ли это видео в базе данных
                video_data = self.db.get_video_by_path(file_path)
                
                if not video_data:
                    # Извлечение метаданных
                    metadata = get_video_metadata(file_path)
                    
                    if metadata:
                        # Добавление в базу данных
                        video_id = self.db.add_video(
                            file_path,
                            file_name,
                            folder_path,
                            metadata["size"],
                            metadata["duration"],
                            metadata["date_created"],
                            metadata["date_modified"]
                        )
                        
                        # Отправляем сигнал для добавления видео в сетку (без миниатюры пока)
                        self.video_loaded_signal.emit(
                            file_path,
                            file_name,
                            None,  # thumbnail placeholder
                            metadata["size"],
                            metadata["duration"],
                            False,  # не просмотрено
                            []  # нет тегов
                        )
                        
                        # Запускаем асинхронную загрузку миниатюры
                        extract_thumbnail_async(
                            file_path, 
                            lambda path, pixmap: self.thumbnail_loaded_signal.emit(path, pixmap)
                        )
                else:
                    # Используем существующие данные из базы
                    tags = [tag["name"] for tag in self.db.get_video_tags(video_data["id"])]
                    
                    # Добавляем в сетку (также без миниатюры пока)
                    self.video_loaded_signal.emit(
                        file_path,
                        file_name,
                        None,  # thumbnail placeholder
                        video_data["size"],
                        video_data["duration"],
                        bool(video_data["watched"]),
                        tags
                    )
                    
                    # Запускаем асинхронную загрузку миниатюры
                    extract_thumbnail_async(
                        file_path, 
                        lambda path, pixmap: self.thumbnail_loaded_signal.emit(path, pixmap)
                    )
                
                # Обновляем прогресс
                self.load_progress_signal.emit(i+1, total_files)
                
            # Завершение загрузки
            if not self._loading_canceled:
                self.load_progress_signal.emit(total_files, total_files)
        
        except Exception as e:
            print(f"Error loading videos: {e}")
        finally:
            self._loading_thread = None
    
    def load_videos_in_folder(self, folder_path):
        """Load videos from the specified folder"""
        if not os.path.isdir(folder_path):
            return
            
        # Отменяем предыдущую загрузку, если она выполняется
        if self._loading_thread is not None and self._loading_thread.is_alive():
            self._loading_canceled = True
            self._loading_thread.join(1)  # Ждём 1 секунду
        
        self._loading_canceled = False
            
        # Добавление в список недавно использованных папок
        self.settings.add_recent_folder(folder_path)
        self.update_recent_folders_menu()
        
        # Очистка текущих видео
        self.video_grid.clear_videos()
        
        # Показ индикатора прогресса
        self.progress_bar.show()
        self.progress_bar.setValue(0)
        
        # Статус в строке состояния
        self.status_bar.showMessage(f"Loading videos from {folder_path}...")
        
        try:
            # Список файлов в папке
            files = os.listdir(folder_path)
        except PermissionError:
            QMessageBox.warning(
                self,
                "Permission Error",
                f"Cannot access folder: {folder_path}\nPermission denied."
            )
            self.status_bar.showMessage("Error accessing folder", 5000)
            self.progress_bar.hide()
            return
        
        # Фильтрация только видео файлов
        video_files = [f for f in files if is_video_file(os.path.join(folder_path, f))]
        
        # Если нет видео
        if not video_files:
            self.status_bar.showMessage("No video files found in this folder.", 5000)
            self.progress_bar.hide()
            return
            
        # Запускаем загрузку в отдельном потоке
        self._loading_thread = threading.Thread(
            target=self._load_videos_async,
            args=(folder_path, video_files)
        )
        self._loading_thread.daemon = True
        self._loading_thread.start()
    
    @pyqtSlot(str, str, object, int, float, bool, list)
    def add_video_to_grid(self, file_path, file_name, thumbnail, size, duration, watched, tags):
        """Добавить видео в сетку (вызывается через сигнал из другого потока)"""
        # Получаем полные данные о видео
        video_data = self.db.get_video_by_path(file_path)
        
        # Добавляем в сетку
        video_item = self.video_grid.add_video(file_path, file_name, thumbnail, size, duration, watched, tags)
        
        # Сохраняем полные данные в элементе
        if video_data:
            video_item.video_data = video_data
    
    @pyqtSlot(str, object)
    def update_video_thumbnail(self, file_path, thumbnail):
        """Обновить миниатюру видео, когда она будет загружена"""
        # Находим соответствующий элемент и обновляем миниатюру
        for i in range(self.video_grid.model.rowCount()):
            item = self.video_grid.model.item(i)
            if item and item.file_path == file_path:
                item.thumbnail = thumbnail
                item.setIcon(QIcon(thumbnail))
                break
    
    @pyqtSlot(int, int)
    def update_load_progress(self, current, total):
        """Обновляем индикатор прогресса загрузки"""
        if total == 0:
            self.progress_bar.hide()
            return
            
        percent = (current * 100) // total
        self.progress_bar.setValue(percent)
        
        # Обновляем статус
        self.status_label.setText(f"{current}/{total}")
        
        # Когда загрузка завершена
        if current >= total:
            self.status_bar.showMessage(f"Loaded {total} videos", 5000)
            QTimer.singleShot(2000, lambda: self.progress_bar.hide())
            QTimer.singleShot(2000, lambda: self.status_label.setText(""))
    
    def handle_player_error(self, error_message):
        """Обрабатывает ошибки воспроизведения"""
        self.status_bar.showMessage(f"Playback error: {error_message}", 5000)
    
    def play_video(self, file_path):
        """Play a video file"""
        # Check if file exists
        if not os.path.exists(file_path):
            QMessageBox.critical(self, "Error", f"File not found: {file_path}")
            return
            
        try:
            # Update UI to show player
            self.video_player.show()
            
            # Play the video
            success = self.video_player.open_file(file_path)
            
            if success:
                # Mark as watched in database
                video_data = self.db.get_video_by_path(file_path)
                if video_data:
                    # Update database
                    self.db.update_watched_status(
                        video_data["id"],
                        True,
                        0,  # Reset position
                        datetime.datetime.now().isoformat()
                    )
                    
                    # Update grid UI
                    self.video_grid.update_video_watched(file_path, True)
            else:
                self.status_bar.showMessage("Could not open video file", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Playback Error", f"Could not play video: {str(e)}")
    
    def on_video_finished(self):
        """Handle video playback finishing"""
        # Hide video player when playback finishes
        self.video_player.hide()
        self.status_bar.showMessage("Playback finished", 3000)
    
    def on_video_selected(self, file_path):
        """Handle video selection (not double-click)"""
        # Could implement preview or show info
        pass
    
    def show_video_context_menu(self, file_path, position):
        """Show context menu for a video file"""
        context_menu = QMenu(self)
        
        # Play action
        play_action = context_menu.addAction("Play")
        play_action.triggered.connect(lambda: self.play_video(file_path))
        
        # Play in fullscreen action
        play_fullscreen_action = context_menu.addAction("Play in Fullscreen")
        play_fullscreen_action.triggered.connect(lambda: self.play_video_fullscreen(file_path))
        
        context_menu.addSeparator()
        
        # Mark as watched/unwatched
        video_data = self.db.get_video_by_path(file_path)
        if video_data:
            is_watched = bool(video_data["watched"])
            
            if is_watched:
                mark_action = context_menu.addAction("Mark as Unwatched")
                mark_action.triggered.connect(lambda: self.mark_video_watched(file_path, False))
            else:
                mark_action = context_menu.addAction("Mark as Watched")
                mark_action.triggered.connect(lambda: self.mark_video_watched(file_path, True))
        
        context_menu.addSeparator()
        
        # File operations
        details_action = context_menu.addAction("Details & Notes")
        details_action.triggered.connect(lambda: self.show_video_details(file_path))
        
        # Review action
        review_action = context_menu.addAction("Add/Edit Review")
        review_action.triggered.connect(lambda: self.show_video_review(file_path))
        
        # Tags submenu
        tags_menu = context_menu.addMenu("Tags")
        
        # Add all available tags
        all_tags = self.db.get_all_tags()
        
        # Get current video tags
        current_tags = []
        if video_data:
            current_tags = [tag["name"] for tag in self.db.get_video_tags(video_data["id"])]
        
        for tag in all_tags:
            tag_action = tags_menu.addAction(tag["name"])
            tag_action.setCheckable(True)
            tag_action.setChecked(tag["name"] in current_tags)
            tag_action.triggered.connect(lambda checked, t=tag, v=video_data["id"]: self.toggle_video_tag(v, t, checked))
        
        # Add new tag option
        tags_menu.addSeparator()
        add_tag_action = tags_menu.addAction("Add New Tag...")
        add_tag_action.triggered.connect(lambda: self.add_new_tag_to_video(video_data["id"]))
        
        context_menu.addSeparator()
        
        rename_action = context_menu.addAction("Rename")
        rename_action.triggered.connect(lambda: self.rename_video(file_path))
        
        move_action = context_menu.addAction("Move to...")
        move_action.triggered.connect(lambda: self.move_video(file_path))
        
        delete_action = context_menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self.delete_video(file_path))
        
        context_menu.exec_(position)
    
    def play_video_fullscreen(self, file_path):
        """Play a video in fullscreen mode"""
        # Check if file exists
        if not os.path.exists(file_path):
            QMessageBox.critical(self, "Error", f"File not found: {file_path}")
            return
            
        try:
            # Используем основной видеоплеер
            self.video_player.show()
            
            # Открываем видео
            success = self.video_player.open_file(file_path)
            if not success:
                return
                
            # Переключаем в полноэкранный режим
            self.video_player.enterFullScreen()
            
            # Обновляем статус просмотра
            video_data = self.db.get_video_by_path(file_path)
            if video_data:
                self.db.update_watched_status(
                    video_data["id"],
                    True,
                    0,  # Reset position
                    datetime.datetime.now().isoformat()
                )
                self.video_grid.update_video_watched(file_path, True)
                
        except Exception as e:
            QMessageBox.critical(self, "Playback Error", f"Could not play video in fullscreen: {str(e)}")
            
    def mark_video_watched(self, file_path, watched):
        """Mark a video as watched or unwatched"""
        video_data = self.db.get_video_by_path(file_path)
        if video_data:
            self.db.update_watched_status(
                video_data["id"],
                watched,
                0,  # Reset position
                datetime.datetime.now().isoformat() if watched else None
            )
            self.video_grid.update_video_watched(file_path, watched)
    
    def show_video_details(self, file_path):
        """Show video details dialog"""
        try:
            video_data = self.db.get_video_by_path(file_path)
            if not video_data:
                return
                
            file_name = os.path.basename(file_path)
            tags = [tag["name"] for tag in self.db.get_video_tags(video_data["id"])]
            notes = self.db.get_note(video_data["id"])
            
            dialog = VideoDetailsDialog(
                file_path,
                file_name,
                video_data["size"],
                video_data["duration"],
                tags,
                notes,
                bool(video_data["watched"]),
                self
            )
            
            if dialog.exec_():
                # Update watched status
                new_watched = dialog.get_watched_status()
                if new_watched != bool(video_data["watched"]):
                    self.db.update_watched_status(
                        video_data["id"],
                        new_watched,
                        0,  # Reset position
                        datetime.datetime.now().isoformat() if new_watched else None
                    )
                    self.video_grid.update_video_watched(file_path, new_watched)
                    
                # Update notes
                self.db.save_note(video_data["id"], dialog.get_notes())
                
                # Update tags
                new_tags = dialog.get_tags()
                
                # Remove all existing tags
                current_tags = self.db.get_video_tags(video_data["id"])
                for tag in current_tags:
                    self.db.remove_video_tag(video_data["id"], tag["id"])
                    
                # Add new tags
                for tag_name in new_tags:
                    tag_id = self.db.add_tag(tag_name)
                    self.db.add_video_tag(video_data["id"], tag_id)
                
                # Update video grid
                self.video_grid.update_video_tags(file_path, new_tags)
                
                # Refresh tag filters
                self.update_tag_filters()
        except Exception as e:
            print(f"Error showing video details: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while showing video details: {str(e)}"
            )
    
    def rename_video(self, file_path):
        """Rename a video file"""
        self.rename_file(file_path)
    
    def rename_selected_video(self):
        """Rename the selected video"""
        selected = self.video_grid.get_selected_videos()
        if len(selected) == 1:
            self.rename_file(selected[0])
    
    def rename_file(self, file_path):
        """Rename a file with user input"""
        if not os.path.exists(file_path):
            return
            
        old_name = os.path.basename(file_path)
        
        new_name, ok = QInputDialog.getText(
            self,
            "Rename File",
            "Enter new filename:",
            text=old_name
        )
        
        if ok and new_name and new_name != old_name:
            directory = os.path.dirname(file_path)
            new_path = os.path.join(directory, new_name)
            
            try:
                # Rename file
                os.rename(file_path, new_path)
                
                # Update database
                video_data = self.db.get_video_by_path(file_path)
                if video_data:
                    # Remove old entry
                    # We'll reload the folder to recreate it with the new path
                    # This is simpler than trying to update the existing entry
                    
                    # Refresh the folder view
                    self.refresh_current_folder()
                
                QMessageBox.information(
                    self,
                    "Rename Successful",
                    f"File renamed to {new_name}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Could not rename file: {str(e)}"
                )
    
    def delete_video(self, file_path):
        """Delete a video file"""
        self.delete_files([file_path])
    
    def delete_selected_videos(self):
        """Delete selected video files"""
        selected = self.video_grid.get_selected_videos()
        if selected:
            self.delete_files(selected)
    
    def delete_files(self, file_paths):
        """Delete a list of files with confirmation"""
        if not file_paths:
            return
            
        # Confirm with user
        count = len(file_paths)
        message = f"Are you sure you want to delete {count} file(s)?\nThis action cannot be undone."
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
            
        # Delete files
        for file_path in file_paths:
            try:
                # Delete file
                os.remove(file_path)
                
                # Remove from database
                video_data = self.db.get_video_by_path(file_path)
                # The database cascade delete will handle removing related data
                
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Delete Error",
                    f"Could not delete {os.path.basename(file_path)}: {str(e)}"
                )
                
        # Refresh the folder view
        self.refresh_current_folder()
    
    def refresh_current_folder(self):
        """Refresh the current folder view"""
        current_path = self.folder_browser.get_current_path()
        self.load_videos_in_folder(current_path)
    
    def toggle_theme(self):
        """Toggle between light and dark theme"""
        current_theme = self.settings.get("theme", "light")
        new_theme = ThemeManager.toggle_theme(current_theme)
        self.settings.set("theme", new_theme)
    
    def show_settings_dialog(self):
        """Show the settings dialog"""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec_():
            # Apply theme if it was changed
            theme = self.settings.get("theme", "light")
            ThemeManager.apply_theme(theme)
    
    def show_about_dialog(self):
        """Show the about dialog"""
        QMessageBox.about(
            self,
            "About Video Library",
            "Video Library 1.0\n\n"
            "A desktop application for browsing and watching local video files.\n\n"
            "Created with PyQt5."
        )
        
    def apply_search_filter(self, params):
        """Apply search and filter settings"""
        # Get all videos from the current folder
        current_path = self.folder_browser.get_current_path()
        if not current_path:
            return
            
        self.status_bar.showMessage(f"Filtering videos...", 1000)
        
        # Get all videos in the current grid
        all_videos = []
        for i in range(self.video_grid.model.rowCount()):
            item = self.video_grid.model.item(i)
            if item:
                all_videos.append(item)
        
        # If no videos to filter, just return
        if not all_videos:
            return
            
        # Apply filters
        filtered_videos = []
        search_text = params.get("search_text", "").lower()
        
        for item in all_videos:
            # Skip if video doesn't exist
            if not os.path.exists(item.file_path):
                continue
                
            # Apply filename search
            if search_text and search_text not in item.file_name.lower():
                continue
                
            # Apply watched filter
            watched_filter = params.get("watched_filter", "All Videos")
            if watched_filter == "Watched Only" and not item.watched:
                continue
            elif watched_filter == "Unwatched Only" and item.watched:
                continue
                
            # Apply tag filter
            tag_filter = params.get("tag", None)
            if tag_filter and tag_filter != "All Tags":
                if not item.tags or tag_filter not in item.tags:
                    continue
                    
            # Item passed all filters, add it
            filtered_videos.append(item)
            
        # Sort videos
        sort_by = params.get("sort_by", "name")
        sort_order = params.get("sort_order", "ascending")
        
        if sort_by == "name":
            filtered_videos.sort(key=lambda x: x.file_name.lower(), 
                             reverse=(sort_order == "descending"))
        elif sort_by == "size":
            filtered_videos.sort(key=lambda x: x.size, 
                             reverse=(sort_order == "descending"))
        elif sort_by == "duration":
            filtered_videos.sort(key=lambda x: x.duration, 
                             reverse=(sort_order == "descending"))
        elif sort_by == "date_modified":
            filtered_videos.sort(key=lambda x: os.path.getmtime(x.file_path) if os.path.exists(x.file_path) else 0, 
                             reverse=(sort_order == "descending"))
        
        # Update the grid with filtered videos
        self.video_grid.model.clear()
        for item in filtered_videos:
            self.video_grid.model.appendRow(item.clone())
            
        # Show message with filter results
        self.status_bar.showMessage(
            f"Found {len(filtered_videos)} videos matching your filters", 3000)
    
    def closeEvent(self, event):
        """Действия при закрытии приложения"""
        # Отменяем текущую загрузку, если она выполняется
        if self._loading_thread is not None and self._loading_thread.is_alive():
            self._loading_canceled = True
            
        # Очистка кэшей, чтобы освободить ресурсы
        from utils.video_utils import clear_caches
        clear_caches()
        
        # Сохраняем настройки
        current_folder = self.folder_browser.get_current_path()
        self.settings.set("start_folder", current_folder)
        
        # Вызываем родительский метод
        super().closeEvent(event)
    
    def show_tag_manager(self):
        """Show tag manager dialog"""
        from PyQt5.QtWidgets import QInputDialog, QListWidget, QVBoxLayout, QPushButton, QHBoxLayout, QLabel, QDialog
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Manage Tags")
        dialog.setMinimumSize(300, 400)
        
        layout = QVBoxLayout()
        
        # Get all tags
        tags = self.db.get_all_tags()
        
        # Create tag list
        tag_list = QListWidget()
        for tag in tags:
            tag_list.addItem(tag["name"])
        
        layout.addWidget(QLabel("Tags:"))
        layout.addWidget(tag_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        add_button = QPushButton("Add")
        add_button.clicked.connect(lambda: self._add_tag_in_manager(tag_list))
        
        rename_button = QPushButton("Rename")
        rename_button.clicked.connect(lambda: self._rename_tag_in_manager(tag_list))
        
        button_layout.addWidget(add_button)
        button_layout.addWidget(rename_button)
        
        layout.addLayout(button_layout)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button)
        
        dialog.setLayout(layout)
        dialog.exec_()
        
        # Refresh tag filters after managing tags
        self.update_tag_filters()
    
    def _add_tag_in_manager(self, tag_list):
        """Add a new tag in the tag manager"""
        tag, ok = QInputDialog.getText(self, "Add Tag", "Enter tag name:")
        
        if ok and tag.strip():
            tag = tag.strip()
            # Add to database
            tag_id = self.db.add_tag(tag)
            # Add to list
            tag_list.addItem(tag)
    
    def _rename_tag_in_manager(self, tag_list):
        """Rename selected tag in the tag manager"""
        selected_items = tag_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select a tag to rename.")
            return
            
        old_name = selected_items[0].text()
        new_name, ok = QInputDialog.getText(self, "Rename Tag", "Enter new tag name:", text=old_name)
        
        if ok and new_name.strip() and new_name != old_name:
            # TODO: Implement proper tag renaming in database
            # This is a simple implementation - in a real app, you would update the tag in the database
            
            # For now, we'll add the new tag and delete the old one
            self.db.add_tag(new_name)
            
            # Update the list
            selected_items[0].setText(new_name)
    
    def toggle_video_tag(self, video_id, tag, is_checked):
        """Toggle a tag on a video"""
        if is_checked:
            # Add tag
            self.db.add_video_tag(video_id, tag["id"])
        else:
            # Remove tag
            self.db.remove_video_tag(video_id, tag["id"])
            
        # Update UI
        video_path = None
        for i in range(self.video_grid.model.rowCount()):
            item = self.video_grid.model.item(i)
            if item and item.video_data and item.video_data["id"] == video_id:
                video_path = item.file_path
                break
                
        if video_path:
            # Refresh tags for this video
            current_tags = [tag["name"] for tag in self.db.get_video_tags(video_id)]
            self.video_grid.update_video_tags(video_path, current_tags)
    
    def add_new_tag_to_video(self, video_id):
        """Add a new tag to a video"""
        tag, ok = QInputDialog.getText(self, "Add Tag", "Enter new tag name:")
        
        if ok and tag.strip():
            tag = tag.strip()
            # Add to database
            tag_id = self.db.add_tag(tag)
            # Add to video
            self.db.add_video_tag(video_id, tag_id)
            
            # Update UI
            video_path = None
            for i in range(self.video_grid.model.rowCount()):
                item = self.video_grid.model.item(i)
                if item and hasattr(item, 'video_data') and item.video_data and item.video_data["id"] == video_id:
                    video_path = item.file_path
                    break
                    
            if video_path:
                # Refresh tags for this video
                current_tags = [tag["name"] for tag in self.db.get_video_tags(video_id)]
                self.video_grid.update_video_tags(video_path, current_tags)
                
            # Update tag filters
            self.update_tag_filters()
    
    def show_video_review(self, file_path):
        """Show dialog to add or edit a review for a video"""
        video_data = self.db.get_video_by_path(file_path)
        if not video_data:
            return
            
        try:
            dialog = ReviewDialog(
                video_data["id"],
                file_path,
                video_data["file_name"],
                self
            )
            
            if dialog.exec_():
                self.status_bar.showMessage("Review saved successfully", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to show review dialog: {str(e)}")
    
    def show_all_reviews(self):
        """Show dialog with all video reviews"""
        try:
            dialog = ReviewsListDialog(self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to show reviews: {str(e)}")
    
    def move_video(self, file_path):
        """Move a video file to another folder"""
        self.move_files([file_path])
    
    def move_selected_videos(self):
        """Move selected video files to another folder"""
        selected = self.video_grid.get_selected_videos()
        if selected:
            self.move_files(selected)
    
    def move_files(self, file_paths):
        """Move a list of files to another folder"""
        if not file_paths:
            return
            
        # Ask user to select a destination folder
        dest_folder = QFileDialog.getExistingDirectory(
            self,
            "Select Destination Folder",
            os.path.dirname(file_paths[0]),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if not dest_folder:
            return  # User cancelled
            
        # Check if destination folder exists and is different from source
        if not os.path.isdir(dest_folder):
            QMessageBox.critical(self, "Error", "Invalid destination folder")
            return
            
        # Check if any of the file paths are already in the destination folder
        already_in_dest = []
        for path in file_paths:
            if os.path.dirname(path) == dest_folder:
                already_in_dest.append(os.path.basename(path))
                
        if already_in_dest:
            if len(already_in_dest) == len(file_paths):
                QMessageBox.information(
                    self, 
                    "Information", 
                    "Files are already in the destination folder"
                )
                return
            else:
                # Show warning for some files
                message = f"{len(already_in_dest)} out of {len(file_paths)} files are already in the destination folder.\n"
                message += "Do you want to continue moving the remaining files?"
                
                reply = QMessageBox.question(
                    self, 
                    "Files Already in Destination",
                    message,
                    QMessageBox.Yes | QMessageBox.No, 
                    QMessageBox.Yes
                )
                
                if reply != QMessageBox.Yes:
                    return
                
                # Filter out files that are already in the destination
                file_paths = [path for path in file_paths if os.path.dirname(path) != dest_folder]
                
        # Move files one by one
        success_count = 0
        error_count = 0
        errors = []
        
        for file_path in file_paths:
            try:
                file_name = os.path.basename(file_path)
                dest_path = os.path.join(dest_folder, file_name)
                
                # Check if a file with the same name already exists in the destination
                if os.path.exists(dest_path):
                    reply = QMessageBox.question(
                        self, 
                        "File Exists",
                        f"A file named '{file_name}' already exists in the destination folder.\n"
                        "Do you want to replace it?",
                        QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                        QMessageBox.No
                    )
                    
                    if reply == QMessageBox.Cancel:
                        # Cancel the entire move operation
                        break
                    elif reply == QMessageBox.No:
                        # Skip this file
                        continue
                
                # Move the file
                shutil.move(file_path, dest_path)
                
                # Update database record with new path
                video_data = self.db.get_video_by_path(file_path)
                if video_data:
                    self.db.update_video_path(video_data["id"], dest_path, dest_folder)
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                errors.append(f"{os.path.basename(file_path)}: {str(e)}")
                
        # Display results
        if success_count > 0:
            message = f"Successfully moved {success_count} file(s)"
            if error_count > 0:
                message += f", {error_count} file(s) could not be moved"
            
            QMessageBox.information(
                self,
                "Move Complete",
                message
            )
            
        if error_count > 0:
            error_message = "The following errors occurred:\n\n" + "\n".join(errors)
            QMessageBox.warning(
                self,
                "Move Errors",
                error_message
            )
            
        # Refresh current folder view
        self.refresh_current_folder() 