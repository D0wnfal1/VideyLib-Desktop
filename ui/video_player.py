import os
import sys
import time
import vlc
from PyQt5.QtCore import Qt, QUrl, pyqtSignal, QTimer, QSize, QPoint, QEvent, QRect
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider, QLabel, 
    QStyle, QSizePolicy, QDialog, QShortcut, QMessageBox, QFrame, QApplication,
    QToolTip
)
from PyQt5.QtGui import QIcon, QKeySequence, QPixmap, QPainter, QColor, QPen, QFont

class CustomSlider(QSlider):
    """Custom slider that supports clicking on the track"""
    
    sliderClicked = pyqtSignal(int)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Get the position clicked as a value
            value = QStyle.sliderValueFromPosition(
                self.minimum(), self.maximum(), 
                event.x(), self.width()
            )
            self.setValue(value)
            self.sliderClicked.emit(value)
        super().mousePressEvent(event)

class VideoPlayer(QWidget):
    """Video player component using VLC"""
    
    # Signals
    videoFinished = pyqtSignal()
    positionChanged = pyqtSignal(int)  # Position in milliseconds
    errorOccurred = pyqtSignal(str)    # Сигнал об ошибке
    nextVideoRequested = pyqtSignal()  # Signal to request next video
    previousVideoRequested = pyqtSignal()  # Signal to request previous video
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Инициализируем VLC
        try:
            if hasattr(sys, '_MEIPASS'):  # Проверяем, запущено ли из PyInstaller
                vlc_path = os.path.join(sys._MEIPASS, 'vlc')
                self.instance = vlc.Instance("--no-video-title-show", "--quiet", f"--plugin-path={vlc_path}")
                self.is_vlc_available = True
            else:
                self.instance = vlc.Instance("--no-video-title-show", "--quiet")
                self.is_vlc_available = True
        except Exception as e:
            print(f"Ошибка инициализации VLC: {e}")
            self.is_vlc_available = False
            self.instance = None
            
        if self.is_vlc_available:
            # Создаем VLC медиаплеер
            self.media_player = self.instance.media_player_new()
            
            # VLC события
            self.event_manager = self.media_player.event_manager()
            self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)
            self.event_manager.event_attach(vlc.EventType.MediaPlayerTimeChanged, self._on_time_changed)
            self.event_manager.event_attach(vlc.EventType.MediaPlayerPositionChanged, self._on_position_changed)
            self.event_manager.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._on_error)
        
        # Настройка UI
        self.setup_ui()
        
        # Подключаем сигналы к слотам
        self.playButton.clicked.connect(self.play)
        self.stopButton.clicked.connect(self.stop)
        self.positionSlider.sliderPressed.connect(self._on_slider_pressed)
        self.positionSlider.sliderReleased.connect(self._on_slider_released)
        self.positionSlider.sliderMoved.connect(self.setPosition)
        self.positionSlider.sliderClicked.connect(self.setPosition)  # Add click handler
        self.volumeSlider.valueChanged.connect(self.setVolume)
        self.fullScreenButton.clicked.connect(self.toggleFullScreen)
        self.nextButton.clicked.connect(self.requestNextVideo)
        self.previousButton.clicked.connect(self.requestPreviousVideo)
        
        # Double click on video frame to toggle fullscreen
        self.video_frame.mouseDoubleClickEvent = self.on_video_double_click
        
        # Настройка клавиатурных сокращений
        self.setup_shortcuts()
        
        # Установка начального уровня громкости
        self.volumeSlider.setValue(70)
        if self.is_vlc_available:
            self.media_player.audio_set_volume(70)
            
        # Таймер для обновления позиции
        self.update_timer = QTimer(self)
        self.update_timer.setInterval(200)  # 200 мс
        self.update_timer.timeout.connect(self.update_ui)
        
        # Контроль питания экрана
        self.keepScreenOn = True
        
        # Для отслеживания состояния слайдера
        self.is_slider_being_dragged = False
        self.is_playing = False
        
        # Save original window state
        self.was_maximized = False
        self.original_geometry = None
        self.original_parent = None
    
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        # Создаем макеты
        layout = QVBoxLayout()
        controlsLayout = QHBoxLayout()
        
        # Виджет для видео
        self.video_frame = QFrame()
        self.video_frame.setFrameShape(QFrame.StyledPanel)
        self.video_frame.setFrameShadow(QFrame.Raised)
        self.video_frame.setAutoFillBackground(True)
        self.video_frame.setStyleSheet("background-color: black;")
        self.video_frame.setMinimumSize(QSize(640, 360))
        
        # Добавляем виджет видео
        layout.addWidget(self.video_frame)
        
        # Создаем кнопки управления с иконками и подсказками
        self.previousButton = QPushButton()
        self.previousButton.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipBackward))
        self.previousButton.setToolTip("Previous Video (PageUp)")
        self.previousButton.setFixedSize(40, 40)
        
        self.playButton = QPushButton()
        self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playButton.setToolTip("Play/Pause (Space)")
        self.playButton.setFixedSize(40, 40)
        
        self.stopButton = QPushButton()
        self.stopButton.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stopButton.setToolTip("Stop (S)")
        self.stopButton.setFixedSize(40, 40)
        
        self.nextButton = QPushButton()
        self.nextButton.setIcon(self.style().standardIcon(QStyle.SP_MediaSkipForward))
        self.nextButton.setToolTip("Next Video (PageDown)")
        self.nextButton.setFixedSize(40, 40)
        
        self.fullScreenButton = QPushButton()
        self.fullScreenButton.setIcon(self.style().standardIcon(QStyle.SP_TitleBarMaxButton))
        self.fullScreenButton.setToolTip("Toggle Fullscreen (F)")
        self.fullScreenButton.setFixedSize(40, 40)
        
        # Close button
        self.closeButton = QPushButton()
        self.closeButton.setIcon(self.style().standardIcon(QStyle.SP_DialogCloseButton))
        self.closeButton.setToolTip("Close Video (Esc)")
        self.closeButton.setFixedSize(40, 40)
        self.closeButton.clicked.connect(self.close_video)
        
        # Слайдер позиции (используем наш кастомный слайдер)
        self.positionSlider = CustomSlider(Qt.Horizontal)
        self.positionSlider.setRange(0, 1000)  # VLC использует от 0 до 1, умножаем на 1000 для точности
        self.positionSlider.setToolTip("Seek")
        
        # Слайдер громкости
        self.volumeLabel = QLabel()
        self.volumeLabel.setPixmap(self.style().standardPixmap(QStyle.SP_MediaVolume))
        self.volumeLabel.setToolTip("Volume")
        
        self.volumeSlider = QSlider(Qt.Horizontal)
        self.volumeSlider.setRange(0, 100)  # VLC использует диапазон от 0 до 100
        self.volumeSlider.setFixedWidth(100)
        self.volumeSlider.setToolTip("Adjust Volume")
        
        # Метки времени
        self.currentTimeLabel = QLabel("00:00")
        self.totalTimeLabel = QLabel("00:00")
        
        # Добавляем виджеты в макет элементов управления
        controlsLayout.addWidget(self.previousButton)
        controlsLayout.addWidget(self.playButton)
        controlsLayout.addWidget(self.stopButton)
        controlsLayout.addWidget(self.nextButton)
        controlsLayout.addWidget(self.currentTimeLabel)
        controlsLayout.addWidget(self.positionSlider)
        controlsLayout.addWidget(self.totalTimeLabel)
        controlsLayout.addWidget(self.volumeLabel)
        controlsLayout.addWidget(self.volumeSlider)
        controlsLayout.addWidget(self.fullScreenButton)
        controlsLayout.addWidget(self.closeButton)
        
        # Добавляем элементы управления в главный макет
        layout.addLayout(controlsLayout)
        
        # Устанавливаем макет
        self.setLayout(layout)
        
        # Устанавливаем фокус
        self.setFocusPolicy(Qt.StrongFocus)
    
    def setup_shortcuts(self):
        """Настройка клавиатурных сокращений"""
        # Play/Pause - Space
        self.shortcutPlayPause = QShortcut(QKeySequence(Qt.Key_Space), self)
        self.shortcutPlayPause.activated.connect(self.play)
        
        # Stop - S
        self.shortcutStop = QShortcut(QKeySequence("S"), self)
        self.shortcutStop.activated.connect(self.stop)
        
        # Fullscreen - F
        self.shortcutFullscreen = QShortcut(QKeySequence("F"), self)
        self.shortcutFullscreen.activated.connect(self.toggleFullScreen)
        
        # Close video - Esc
        self.shortcutClose = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.shortcutClose.activated.connect(self.close_video)
        
        # Увеличение громкости - стрелка вверх
        self.shortcutVolumeUp = QShortcut(QKeySequence(Qt.Key_Up), self)
        self.shortcutVolumeUp.activated.connect(self.increaseVolume)
        
        # Уменьшение громкости - стрелка вниз
        self.shortcutVolumeDown = QShortcut(QKeySequence(Qt.Key_Down), self)
        self.shortcutVolumeDown.activated.connect(self.decreaseVolume)
        
        # Перемотка вперед - стрелка вправо
        self.shortcutSeekForward = QShortcut(QKeySequence(Qt.Key_Right), self)
        self.shortcutSeekForward.activated.connect(self.seekForward)
        
        # Перемотка назад - стрелка влево
        self.shortcutSeekBackward = QShortcut(QKeySequence(Qt.Key_Left), self)
        self.shortcutSeekBackward.activated.connect(self.seekBackward)
        
        # Mute - M
        self.shortcutMute = QShortcut(QKeySequence("M"), self)
        self.shortcutMute.activated.connect(self.toggleMute)
        
        # Next video - Page Down
        self.shortcutNextVideo = QShortcut(QKeySequence(Qt.Key_PageDown), self)
        self.shortcutNextVideo.activated.connect(self.requestNextVideo)
        
        # Previous video - Page Up
        self.shortcutPrevVideo = QShortcut(QKeySequence(Qt.Key_PageUp), self)
        self.shortcutPrevVideo.activated.connect(self.requestPreviousVideo)
    
    def open_file(self, file_path):
        """Открыть и воспроизвести видеофайл"""
        if not file_path or not self.is_vlc_available:
            if not self.is_vlc_available:
                self.errorOccurred.emit("VLC не доступен. Установите VLC Media Player.")
                QMessageBox.critical(self, "Ошибка", "VLC не доступен. Пожалуйста, установите VLC Media Player.")
            return False
            
        try:
            # Останавливаем текущее воспроизведение
            self.stop()
            
            # Создаем медиа из файла
            media = self.instance.media_new(file_path)
            
            # Устанавливаем медиа в плеер
            self.media_player.set_media(media)
            
            # Устанавливаем видеофрейм как вывод
            if sys.platform.startswith('linux'):  # для Linux
                self.media_player.set_xwindow(int(self.video_frame.winId()))
            elif sys.platform == "win32":  # для Windows
                self.media_player.set_hwnd(int(self.video_frame.winId()))
            elif sys.platform == "darwin":  # для macOS
                self.media_player.set_nsobject(int(self.video_frame.winId()))
                
            # Автоматически запускаем воспроизведение
            self.media_player.play()
            self.is_playing = True
            self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            
            # Обновляем длительность после загрузки
            self.update_timer.start()
            
            # Ожидаем, пока медиа будет полностью загружено
            QTimer.singleShot(500, self._update_duration)
            
            # Включаем экран при воспроизведении
            if self.keepScreenOn:
                self._prevent_screen_saver(True)
                
            return True
            
        except Exception as e:
            error_message = f"Не удалось открыть видеофайл: {str(e)}"
            print(error_message)
            self.errorOccurred.emit(error_message)
            QMessageBox.critical(self, "Ошибка", error_message)
            return False
    
    def _update_duration(self):
        """Обновить информацию о длительности после полной загрузки видео"""
        if not self.is_vlc_available or not self.media_player.get_media():
            return
            
        # Длительность в миллисекундах
        duration = self.media_player.get_length()
        
        if duration > 0:
            self.totalTimeLabel.setText(self._format_time(duration))
    
    def play(self):
        """Переключение воспроизведение/пауза"""
        if not self.is_vlc_available:
            return
            
        if self.is_playing:
            self.media_player.pause()
            self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            self.is_playing = False
            
            # Разрешаем выключение экрана при паузе
            if self.keepScreenOn:
                self._prevent_screen_saver(False)
        else:
            self.media_player.play()
            self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
            self.is_playing = True
            
            # Запрещаем выключение экрана при воспроизведении
            if self.keepScreenOn:
                self._prevent_screen_saver(True)
    
    def stop(self):
        """Остановить воспроизведение"""
        if not self.is_vlc_available:
            return
            
        self.media_player.stop()
        self.is_playing = False
        self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        
        # Разрешаем выключение экрана при остановке
        if self.keepScreenOn:
            self._prevent_screen_saver(False)
            
        # Сброс позиции
        self.positionSlider.setValue(0)
        self.currentTimeLabel.setText("00:00")
    
    def close_video(self):
        """Закрыть видео и вернуться к основному экрану"""
        self.stop()
        
        # Если мы в полноэкранном режиме, выходим из него
        if self.isFullScreen():
            self.exitFullScreen()
            
        # Скрываем видеоплеер
        self.hide()
            
        # Отправляем сигнал родительскому виджету о закрытии видео
        if self.parent() and hasattr(self.parent(), 'on_video_closed'):
            self.parent().on_video_closed()
        elif isinstance(self.parent(), QDialog):
            self.parent().close()
    
    def _on_end_reached(self, event):
        """Обработка события окончания воспроизведения"""
        # В VLC событие приходит в другом потоке, поэтому используем таймер
        QTimer.singleShot(100, self._emit_finished)
    
    def _emit_finished(self):
        """Эмитировать сигнал окончания воспроизведения из основного потока"""
        self.is_playing = False
        self.playButton.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        
        # Разрешаем выключение экрана
        if self.keepScreenOn:
            self._prevent_screen_saver(False)
            
        # Эмитируем сигнал для внешних обработчиков
        self.videoFinished.emit()
    
    def _on_time_changed(self, event):
        """Обработка события изменения времени воспроизведения"""
        # Не обновляем, если пользователь перетаскивает слайдер
        if self.is_slider_being_dragged:
            return
            
        # Текущее время в миллисекундах
        time = self.media_player.get_time()
        
        # Обновляем метку времени
        if time >= 0:
            self.currentTimeLabel.setText(self._format_time(time))
            
            # Эмитируем сигнал для внешних обработчиков
            self.positionChanged.emit(time)
    
    def _on_position_changed(self, event):
        """Обработка события изменения позиции воспроизведения"""
        # Не обновляем, если пользователь перетаскивает слайдер
        if self.is_slider_being_dragged:
            return
            
        # Позиция от 0 до 1, умножаем на 1000 для слайдера
        position = int(self.media_player.get_position() * 1000)
        
        # Обновляем слайдер
        if position >= 0:
            self.positionSlider.setValue(position)
    
    def _on_error(self, event):
        """Обработка ошибок воспроизведения"""
        error_message = "Ошибка воспроизведения видео"
        print(error_message)
        self.errorOccurred.emit(error_message)
    
    def _on_slider_pressed(self):
        """Обработка нажатия на слайдер"""
        self.is_slider_being_dragged = True
        
    def _on_slider_released(self):
        """Обработка отпускания слайдера"""
        position = self.positionSlider.value() / 1000.0  # Позиция от 0 до 1
        self.media_player.set_position(position)
        self.is_slider_being_dragged = False
    
    def setPosition(self, position):
        """Установить позицию воспроизведения по слайдеру"""
        if not self.is_vlc_available:
            return
            
        # Позиция от 0 до 1000 в слайдере, нормализуем до 0-1
        normalized_pos = position / 1000.0
        self.media_player.set_position(normalized_pos)
    
    def setVolume(self, volume):
        """Установить громкость"""
        if not self.is_vlc_available:
            return
            
        self.media_player.audio_set_volume(volume)
    
    def increaseVolume(self):
        """Увеличить громкость на 5%"""
        current_volume = self.volumeSlider.value()
        new_volume = min(current_volume + 5, 100)
        self.volumeSlider.setValue(new_volume)
    
    def decreaseVolume(self):
        """Уменьшить громкость на 5%"""
        current_volume = self.volumeSlider.value()
        new_volume = max(current_volume - 5, 0)
        self.volumeSlider.setValue(new_volume)
    
    def toggleMute(self):
        """Включить/выключить звук"""
        if not self.is_vlc_available:
            return
            
        self.media_player.audio_toggle_mute()
    
    def seekForward(self):
        """Перемотка вперед на 5 секунд"""
        if not self.is_vlc_available:
            return
            
        time = self.media_player.get_time()
        if time >= 0:
            self.media_player.set_time(time + 5000)  # +5 секунд (миллисекунды)
    
    def seekBackward(self):
        """Перемотка назад на 5 секунд"""
        if not self.is_vlc_available:
            return
            
        time = self.media_player.get_time()
        if time >= 0:
            self.media_player.set_time(max(time - 5000, 0))  # -5 секунд (не менее 0)
    
    def on_video_double_click(self, event):
        """Обработка двойного клика по видео для переключения полноэкранного режима"""
        self.toggleFullScreen()
        
    def toggleFullScreen(self):
        """Переключение полноэкранного режима"""
        if self.isFullScreen():
            self.exitFullScreen()
        else:
            self.enterFullScreen()
    
    def enterFullScreen(self):
        """Вход в полноэкранный режим"""
        if self.isFullScreen():
            return
            
        # Сохраняем текущее состояние
        self.was_maximized = self.isMaximized()
        self.original_geometry = self.geometry()
        self.original_parent = self.parent()
        
        # Отсоединяем от родителя, если он есть
        if self.parent():
            self.setParent(None)
        
        # Скрываем декорации окна и делаем окно независимым
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        
        # Получаем размер основного экрана
        desktop = QApplication.desktop()
        screen_rect = desktop.screenGeometry(desktop.screenNumber(self))
        
        # Показываем окно и затем устанавливаем полноэкранный режим
        self.show()
        self.setGeometry(screen_rect)
        self.showFullScreen()
        
        # Поднимаем окно поверх других окон
        self.raise_()
        self.activateWindow()
    
    def exitFullScreen(self):
        """Выход из полноэкранного режима"""
        if not self.isFullScreen():
            return
            
        # Восстанавливаем исходные флаги окна
        self.setWindowFlags(Qt.Widget)
        
        # Восстанавливаем родителя, если он был
        if self.original_parent:
            self.setParent(self.original_parent)
            self.original_parent.layout().addWidget(self)
        
        # Восстанавливаем предыдущее состояние
        self.showNormal()
        
        if self.was_maximized:
            self.showMaximized()
        elif self.original_geometry:
            self.setGeometry(self.original_geometry)
            
        # Показываем окно после всех изменений
        self.show()
        
        # Сбрасываем сохраненные значения
        self.original_parent = None
        self.original_geometry = None
    
    def update_ui(self):
        """Периодическое обновление UI"""
        if not self.is_vlc_available or not self.media_player.get_media():
            return
            
        # Обновление слайдера, если не перетаскивается
        if not self.is_slider_being_dragged:
            position = self.media_player.get_position()
            self.positionSlider.setValue(int(position * 1000))
        
        # Обновляем длительность, если она еще не установлена
        if self.totalTimeLabel.text() == "00:00":
            self._update_duration()
    
    def _format_time(self, ms):
        """Форматирование времени в миллисекундах в формат MM:SS"""
        seconds = int(ms / 1000)
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def get_current_position(self):
        """Получить текущую позицию воспроизведения в миллисекундах"""
        if not self.is_vlc_available:
            return 0
        return self.media_player.get_time()
    
    def get_duration(self):
        """Получить длительность видео в миллисекундах"""
        if not self.is_vlc_available:
            return 0
        return self.media_player.get_length()
    
    def _prevent_screen_saver(self, prevent):
        """Предотвратить выключение экрана"""
        if not sys.platform.startswith('win'):
            return
            
        try:
            import ctypes
            if prevent:
                # ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001 | 0x00000002)
            else:
                # ES_CONTINUOUS
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        except Exception as e:
            print(f"Ошибка управления состоянием энергосбережения: {e}")
            
    def set_keep_screen_on(self, enabled):
        """Установить режим предотвращения выключения экрана"""
        self.keepScreenOn = enabled
        
        # Применить текущую настройку
        if self.is_playing and enabled:
            self._prevent_screen_saver(True)
        else:
            self._prevent_screen_saver(False)
            
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        # Останавливаем воспроизведение
        if self.is_vlc_available:
            self.stop()
            self.update_timer.stop()
            
        # Разрешаем выключение экрана
        if self.keepScreenOn:
            self._prevent_screen_saver(False)
            
        # Вызываем родительский метод
        super().closeEvent(event)
    
    def requestNextVideo(self):
        """Emit signal to request the next video"""
        self.nextVideoRequested.emit()
    
    def requestPreviousVideo(self):
        """Emit signal to request the previous video"""
        self.previousVideoRequested.emit() 