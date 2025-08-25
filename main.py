import sys
import ctypes
from ctypes import wintypes
import threading
import time
from datetime import timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QFrame, QSystemTrayIcon, 
                             QMenu, QAction, QMessageBox, QCheckBox, QGroupBox)
from PyQt5.QtCore import (Qt, QTimer, QPropertyAnimation, QEasingCurve, 
                         pyqtProperty, QRect, QSize)
from PyQt5.QtGui import (QIcon, QPainter, QColor, QFont, QPalette, QLinearGradient, 
                        QBrush, QPixmap)

# Загрузка библиотеки kernel32 для работы с Windows API
kernel32 = ctypes.windll.kernel32

# Константы для работы с системными настройками питания
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

class AnimatedButton(QPushButton):
    """Класс для создания анимированной кнопки с эффектами наведения"""
    
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self._animation = QPropertyAnimation(self, b"geometry")
        self._normal_color = QColor(46, 134, 171)  # Начальный цвет
        self._hover_color = QColor(30, 110, 150)   # Цвет при наведении
        self.setMinimumHeight(40)
        self.setCursor(Qt.PointingHandCursor)
        
        # Устанавливаем начальный стиль
        self.update_style(self._normal_color)
        
    def update_style(self, color):
        """Обновление стиля кнопки в соответствии с текущим цветом"""
        self.setStyleSheet(f"""
            QPushButton {{
                border: none;
                border-radius: 10px;
                background-color: rgb({color.red()}, {color.green()}, {color.blue()});
                color: white;
                font-weight: bold;
                padding: 10px;
            }}
        """)
        
    def enterEvent(self, event):
        """Обработчик события наведения курсора на кнопку"""
        self._animation.stop()
        self._animation.setDuration(200)
        self._animation.setStartValue(self.geometry())
        self._animation.setEndValue(QRect(self.x() - 2, self.y() - 2, 
                                         self.width() + 4, self.height() + 4))
        self._animation.setEasingCurve(QEasingCurve.OutBack)
        self._animation.start()
        
        # Меняем цвет при наведении
        self.update_style(self._hover_color)
        
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """Обработчик события выхода курсора из кнопки"""
        self._animation.stop()
        self._animation.setDuration(300)
        self._animation.setStartValue(self.geometry())
        self._animation.setEndValue(QRect(self.x() + 2, self.y() + 2, 
                                         self.width() - 4, self.height() - 4))
        self._animation.setEasingCurve(QEasingCurve.InOutBack)
        self._animation.start()
        
        # Возвращаем обычный цвет
        self.update_style(self._normal_color)
        
        super().leaveEvent(event)

class KeepAwakeApp(QMainWindow):
    """Основной класс приложения с графическим интерфейсом"""
    
    def __init__(self):
        super().__init__()
        
        # Инициализация переменных
        self.is_active = False
        self.thread = None
        self.stop_thread = False
        self.tray_icon = None
        
        # Настройка главного окна
        self.setWindowTitle("No-Sleep - Контроль сна Windows")
        self.setFixedSize(450, 500)
        self.setWindowIcon(QIcon(self.create_icon()))
        
        # Создание центрального виджета и основного layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Создание и настройка элементов интерфейса
        self.setup_ui(layout)
        
        # Создание системного трея
        self.setup_tray()
        
        # Таймер для обновления времени работы
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_uptime)
        self.uptime_seconds = 0
        
    def setup_ui(self, layout):
        """Настройка пользовательского интерфейса"""
        
        # Заголовок
        title = QLabel("No-Sleep")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #2E86AB; padding: 10px;")
        layout.addWidget(title)
        
        # Описание
        description = QLabel("Программа предотвращает отключение экрана\nи переход в спящий режим Windows")
        description.setAlignment(Qt.AlignCenter)
        description.setStyleSheet("color: #555; padding: 5px;")
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Группа настроек
        settings_group = QGroupBox("Настройки")
        settings_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2E86AB;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #2E86AB;
            }
        """)
        settings_layout = QVBoxLayout(settings_group)
        
        # Чекбокс для предотвращения сна
        self.prevent_sleep_cb = QCheckBox("Предотвращать спящий режим")
        self.prevent_sleep_cb.setChecked(True)
        self.prevent_sleep_cb.setStyleSheet("color: #333; padding: 5px;")
        settings_layout.addWidget(self.prevent_sleep_cb)
        
        # Чекбокс для предотвращения отключения дисплея
        self.prevent_display_off_cb = QCheckBox("Предотвращать отключение дисплея")
        self.prevent_display_off_cb.setChecked(True)
        self.prevent_display_off_cb.setStyleSheet("color: #333; padding: 5px;")
        settings_layout.addWidget(self.prevent_display_off_cb)
        
        layout.addWidget(settings_group)
        
        # Информационная группа
        info_group = QGroupBox("Информация")
        info_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #2E86AB;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #2E86AB;
            }
        """)
        info_layout = QVBoxLayout(info_group)
        
        # Время работы
        self.uptime_label = QLabel("Время работы: 00:00:00")
        self.uptime_label.setStyleSheet("color: #333; padding: 5px;")
        info_layout.addWidget(self.uptime_label)
        
        # Статус
        self.status_label = QLabel("Статус: неактивно")
        self.status_label.setStyleSheet("color: #E74C3C; font-weight: bold; padding: 5px;")
        info_layout.addWidget(self.status_label)
        
        layout.addWidget(info_group)
        
        # Кнопка управления
        self.toggle_btn = AnimatedButton("Запустить")
        self.toggle_btn.clicked.connect(self.toggle_keep_awake)
        layout.addWidget(self.toggle_btn)
        
        # Кнопка сворачивания в трей
        self.tray_btn = AnimatedButton("Свернуть в трей")
        self.tray_btn._normal_color = QColor(52, 152, 219)
        self.tray_btn._hover_color = QColor(41, 128, 185)
        self.tray_btn.update_style(self.tray_btn._normal_color)
        self.tray_btn.clicked.connect(self.hide_to_tray)
        layout.addWidget(self.tray_btn)
        
        # Установка градиентного фона
        self.setAutoFillBackground(True)
        palette = self.palette()
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor(240, 248, 255))
        gradient.setColorAt(1, QColor(230, 244, 254))
        palette.setBrush(QPalette.Window, QBrush(gradient))
        self.setPalette(palette)
        
    def setup_tray(self):
        """Настройка системного трея"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setIcon(QIcon(self.create_icon()))
            
            # Создание контекстного меню для трея
            tray_menu = QMenu()
            
            toggle_action = QAction("Запустить/Остановить", self)
            toggle_action.triggered.connect(self.toggle_keep_awake)
            tray_menu.addAction(toggle_action)
            
            show_action = QAction("Показать", self)
            show_action.triggered.connect(self.show_from_tray)
            tray_menu.addAction(show_action)
            
            quit_action = QAction("Выход", self)
            quit_action.triggered.connect(self.quit_application)
            tray_menu.addAction(quit_action)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.tray_icon_activated)
            self.tray_icon.show()
            
    def create_icon(self):
        """Создание иконки для приложения"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(46, 134, 171))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 16, 16)
        painter.setBrush(Qt.white)
        painter.drawEllipse(4, 6, 2, 2)
        painter.drawEllipse(10, 6, 2, 2)
        painter.drawArc(4, 8, 8, 4, 0, 180 * 16)
        painter.end()
        return pixmap
        
    def toggle_keep_awake(self):
        """Переключение режима предотвращения сна"""
        if not self.is_active:
            self.start_keep_awake()
        else:
            self.stop_keep_awake()
    
    def start_keep_awake(self):
        """Активирует предотвращение сна"""
        self.is_active = True
        self.stop_thread = False
        self.toggle_btn.setText("Остановить")
        self.status_label.setText("Статус: активно")
        self.status_label.setStyleSheet("color: #27AE60; font-weight: bold; padding: 5px;")
        
        # Запуск в отдельном потоке для избежания блокировки GUI
        self.thread = threading.Thread(target=self.keep_awake_worker)
        self.thread.daemon = True
        self.thread.start()
        
        # Запуск таймера для отсчета времени
        self.uptime_seconds = 0
        self.timer.start(1000)  # Обновление каждую секунду
        self.update_uptime()
        
        # Обновление иконки в трее
        if self.tray_icon:
            self.tray_icon.setToolTip("No-Sleep - активно")
    
    def stop_keep_awake(self):
        """Деактивирует предотвращение сна"""
        self.is_active = False
        self.stop_thread = True
        self.toggle_btn.setText("Запустить")
        self.status_label.setText("Статус: неактивно")
        self.status_label.setStyleSheet("color: #E74C3C; font-weight: bold; padding: 5px;")
        
        # Восстановление нормальных настроек питания
        kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        
        # Остановка таймера
        self.timer.stop()
        
        # Обновление иконки в трее
        if self.tray_icon:
            self.tray_icon.setToolTip("No-Sleep - неактивно")
    
    def keep_awake_worker(self):
        """Рабочая функция, которая предотвращает сон"""
        flags = ES_CONTINUOUS
        
        if self.prevent_sleep_cb.isChecked():
            flags |= ES_SYSTEM_REQUIRED
            
        if self.prevent_display_off_cb.isChecked():
            flags |= ES_DISPLAY_REQUIRED
        
        while not self.stop_thread:
            # Устанавливаем флаги для предотвращения сна и отключения дисплея
            kernel32.SetThreadExecutionState(flags)
            time.sleep(30)  # Обновляем состояние каждые 30 секунд
    
    def update_uptime(self):
        """Обновление времени работы"""
        self.uptime_seconds += 1
        hours = self.uptime_seconds // 3600
        minutes = (self.uptime_seconds % 3600) // 60
        seconds = self.uptime_seconds % 60
        self.uptime_label.setText(f"Время работы: {hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def hide_to_tray(self):
        """Сворачивание приложения в системный трей"""
        if self.tray_icon:
            self.hide()
            self.tray_icon.showMessage(
                "No-Sleep", 
                "Приложение свернуто в трей. Вы можете управлять им оттуда.",
                QSystemTrayIcon.Information, 
                2000
            )
    
    def show_from_tray(self):
        """Восстановление приложения из трея"""
        self.show()
        self.activateWindow()
        self.raise_()
    
    def tray_icon_activated(self, reason):
        """Обработка активации иконки в трее"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_from_tray()
    
    def quit_application(self):
        """Корректный выход из приложения"""
        if self.is_active:
            self.stop_keep_awake()
        QApplication.quit()
    
    def closeEvent(self, event):
        """Обработка события закрытия окна"""
        if self.tray_icon and self.tray_icon.isVisible():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "No-Sleep", 
                "Приложение продолжает работать в фоновом режиме. Для выхода используйте меню в трее.",
                QSystemTrayIcon.Information, 
                2000
            )
        else:
            self.quit_application()

if __name__ == "__main__":
    # Создание экземпляра приложения
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Инициализация и отображение главного окна
    window = KeepAwakeApp()
    window.show()
    
    # Запуск основного цикла приложения
    sys.exit(app.exec_())
