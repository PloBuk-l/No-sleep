import sys
import ctypes
from ctypes import wintypes
import threading
import time
from datetime import timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QFrame, QSystemTrayIcon, 
                             QMenu, QAction, QMessageBox, QCheckBox, QGroupBox, 
                             QStackedWidget, QScrollArea, QSizePolicy, QSpacerItem,
                             QGraphicsDropShadowEffect)
from PyQt5.QtCore import (Qt, QTimer, QPropertyAnimation, QEasingCurve, 
                         pyqtProperty, QRect, QSize, QPoint)
from PyQt5.QtGui import (QIcon, QPainter, QColor, QFont, QPalette, QLinearGradient, 
                        QBrush, QPixmap, QFontDatabase, QPen)

# Загрузка библиотеки kernel32 для работы с Windows API
kernel32 = ctypes.windll.kernel32

# Константы для работы с системными настройками питания
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

class FadeButton(QPushButton):
    """Класс для создания кнопки с эффектом свечения при наведении"""
    
    def __init__(self, text, parent=None, color="#6A0DAD", hover_color="#8A2BE2"):
        super().__init__(text, parent)
        self._normal_color = QColor(color)
        self._hover_color = QColor(hover_color)
        self._current_color = self._normal_color
        self._animation = QPropertyAnimation(self, b"color")
        self._animation.setDuration(300)
        self.setMinimumSize(140, 50)
        self.setCursor(Qt.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 11, QFont.Bold))
        
        # Добавляем тень
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 80))
        self.shadow.setOffset(0, 5)
        self.setGraphicsEffect(self.shadow)
        
        # Устанавливаем начальный стиль
        self.update_style()
        
    def update_style(self):
        """Обновление стиля кнопки в соответствии с текущим цветом"""
        self.setStyleSheet(f"""
            QPushButton {{
                border: none;
                border-radius: 12px;
                background-color: {self._current_color.name()};
                color: white;
                padding: 12px 25px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {self._hover_color.name()};
            }}
            QPushButton:pressed {{
                background-color: #4B0082;
                padding-top: 13px;
                padding-bottom: 11px;
            }}
        """)
        
    def enterEvent(self, event):
        """Обработчик события наведения курсора на кнопку"""
        self._animation.stop()
        self._animation.setStartValue(self._normal_color)
        self._animation.setEndValue(self._hover_color)
        self._animation.start()
        
        # Анимация тени
        self.shadow.setBlurRadius(20)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """Обработчик события выхода курсора из кнопки"""
        self._animation.stop()
        self._animation.setStartValue(self._hover_color)
        self._animation.setEndValue(self._normal_color)
        self._animation.start()
        
        # Анимация тени
        self.shadow.setBlurRadius(15)
        super().leaveEvent(event)
        
    def get_color(self):
        """Получение текущего цвета кнопки"""
        return self._current_color
        
    def set_color(self, color):
        """Установка цвета кнопки"""
        self._current_color = color
        self.update_style()
        
    color = pyqtProperty(QColor, get_color, set_color)

class ToggleSwitch(QCheckBox):
    """Класс для создания красивого переключателя"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(60, 30)
        
        # Цвета для переключателя
        self._bg_color = QColor("#E9E9E9")
        self._checked_bg_color = QColor("#6A0DAD")
        self._circle_color = QColor("#FFFFFF")
        self._circle_position = 3
        
        # Анимация движения кружка
        self._animation = QPropertyAnimation(self, b"circle_position")
        self._animation.setDuration(200)
        self._animation.setEasingCurve(QEasingCurve.OutBack)
        
        # Обработка изменения состояния
        self.stateChanged.connect(self.on_state_change)
        
    def paintEvent(self, event):
        """Отрисовка переключателя"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Рисуем фон
        bg_rect = QRect(0, 0, self.width(), self.height())
        painter.setPen(Qt.NoPen)
        
        if self.isChecked():
            painter.setBrush(self._checked_bg_color)
        else:
            painter.setBrush(self._bg_color)
            
        painter.drawRoundedRect(bg_rect, 15, 15)
        
        # Рисуем кружок
        circle_x = self._circle_position
        circle_rect = QRect(circle_x, 3, 24, 24)
        painter.setBrush(self._circle_color)
        painter.drawEllipse(circle_rect)
        
    def on_state_change(self, state):
        """Обработка изменения состояния переключателя"""
        if state == Qt.Checked:
            self._animation.setStartValue(3)
            self._animation.setEndValue(33)
        else:
            self._animation.setStartValue(33)
            self._animation.setEndValue(3)
        self._animation.start()
        
    def mousePressEvent(self, event):
        """Переопределение метода для обработки клика"""
        self.setChecked(not self.isChecked())
        
    def get_circle_position(self):
        """Получение позиции кружка"""
        return self._circle_position
        
    def set_circle_position(self, pos):
        """Установка позиции кружка"""
        self._circle_position = pos
        self.update()
        
    circle_position = pyqtProperty(int, get_circle_position, set_circle_position)

class NoSleepApp(QMainWindow):
    """Основной класс приложения с улучшенным графическим интерфейсом"""
    
    def __init__(self):
        super().__init__()
        
        # Инициализация переменных
        self.is_active = False
        self.thread = None
        self.stop_thread = False
        self.tray_icon = None
        self.dark_mode = False
        
        # Настройка главного окна
        self.setWindowTitle("No-Sleep - Контроль сна Windows")
        self.setFixedSize(500, 700)
        self.setWindowIcon(QIcon("icon.ico"))
        
        # Установка шрифта
        self.setFont(QFont("Segoe UI", 10))
        
        # Создание центрального виджета и основного layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Создание стека для переключения между страницами
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)
        
        # Создание основной страницы и страницы инструкции
        self.main_page = QWidget()
        self.instructions_page = QWidget()
        
        # Настройка страниц
        self.setup_main_page()
        self.setup_instructions_page()
        
        # Добавление страниц в стек
        self.stacked_widget.addWidget(self.main_page)
        self.stacked_widget.addWidget(self.instructions_page)
        
        # Создание системного трея
        self.setup_tray()
        
        # Таймер для обновления времени работы
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_uptime)
        self.uptime_seconds = 0
        
        # Применение светлой темы по умолчанию
        self.apply_light_theme()
        
    def setup_main_page(self):
        """Настройка главной страницы приложения"""
        layout = QVBoxLayout(self.main_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        
        # Заголовок
        title = QLabel("No-Sleep")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont("Segoe UI", 28, QFont.Bold)
        title.setFont(title_font)
        title.setObjectName("titleLabel")
        layout.addWidget(title)
        
        # Описание
        description = QLabel("Программа предотвращает отключение экрана\nи переход в спящий режим Windows")
        description.setAlignment(Qt.AlignCenter)
        description.setObjectName("descriptionLabel")
        description.setWordWrap(True)
        layout.addWidget(description)
        
        # Группа настроек
        settings_group = QGroupBox("Настройки")
        settings_group.setObjectName("settingsGroup")
        settings_layout = QVBoxLayout(settings_group)
        settings_layout.setSpacing(15)
        
        # Настройка предотвращения сна
        sleep_layout = QHBoxLayout()
        sleep_label = QLabel("Предотвращать спящий режим")
        sleep_label.setObjectName("settingLabel")
        self.prevent_sleep_switch = ToggleSwitch()
        sleep_layout.addWidget(sleep_label)
        sleep_layout.addStretch()
        sleep_layout.addWidget(self.prevent_sleep_switch)
        self.prevent_sleep_switch.setChecked(True)
        settings_layout.addLayout(sleep_layout)
        
        # Настройка предотвращения отключения дисплея
        display_layout = QHBoxLayout()
        display_label = QLabel("Предотвращать отключение дисплея")
        display_label.setObjectName("settingLabel")
        self.prevent_display_switch = ToggleSwitch()
        display_layout.addWidget(display_label)
        display_layout.addStretch()
        display_layout.addWidget(self.prevent_display_switch)
        self.prevent_display_switch.setChecked(True)
        settings_layout.addLayout(display_layout)
        
        # Переключатель темы
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Темная тема")
        theme_label.setObjectName("settingLabel")
        self.theme_switch = ToggleSwitch()
        self.theme_switch.stateChanged.connect(self.toggle_theme)
        theme_layout.addWidget(theme_label)
        theme_layout.addStretch()
        theme_layout.addWidget(self.theme_switch)
        settings_layout.addLayout(theme_layout)
        
        layout.addWidget(settings_group)
        
        # Информационная группа
        info_group = QGroupBox("Информация")
        info_group.setObjectName("infoGroup")
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(10)
        
        # Время работы
        self.uptime_label = QLabel("Время работы: 00:00:00")
        self.uptime_label.setObjectName("infoLabel")
        info_layout.addWidget(self.uptime_label)
        
        # Статус
        self.status_label = QLabel("Статус: неактивно")
        self.status_label.setObjectName("statusLabel")
        info_layout.addWidget(self.status_label)
        
        layout.addWidget(info_group)
        
        # Кнопка управления
        self.toggle_btn = FadeButton("Запустить", color="#27AE60", hover_color="#219A73")
        self.toggle_btn.clicked.connect(self.toggle_keep_awake)
        layout.addWidget(self.toggle_btn)
        
        # Кнопка инструкции
        self.instructions_btn = FadeButton("Инструкция", color="#3498DB", hover_color="#2980B9")
        self.instructions_btn.clicked.connect(self.show_instructions)
        layout.addWidget(self.instructions_btn)
        
        # Кнопка сворачивания в трей
        self.tray_btn = FadeButton("Свернуть в трей", color="#6A0DAD", hover_color="#8A2BE2")
        self.tray_btn.clicked.connect(self.hide_to_tray)
        layout.addWidget(self.tray_btn)
        
        # Добавляем растягивающийся элемент для выравнивания
        layout.addStretch()
        
    def setup_instructions_page(self):
        """Настройка страницы с инструкцией"""
        layout = QVBoxLayout(self.instructions_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        
        # Заголовок
        title = QLabel("Инструкция по использованию")
        title.setAlignment(Qt.AlignCenter)
        title_font = QFont("Segoe UI", 20, QFont.Bold)
        title.setFont(title_font)
        title.setObjectName("instructionsTitle")
        layout.addWidget(title)
        
        # Область с прокруткой для инструкции
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setObjectName("scrollArea")
        
        # Контейнер для инструкции
        instructions_container = QWidget()
        instructions_layout = QVBoxLayout(instructions_container)
        instructions_layout.setContentsMargins(15, 15, 15, 15)
        
        # Текст инструкции
        instructions = [
            ("🎯 Назначение программы", 
             "No-Sleep предназначена для предотвращения перехода компьютера в спящий режим и отключения экрана. "
             "Это полезно при длительных загрузках, просмотре видео или других задачах, требующих непрерывной работы компьютера."),
            
            ("🚀 Как использовать", 
             "1. Выберите нужные настройки (предотвращение сна, отключения дисплея или оба варианта)\n"
             "2. Нажмите кнопку 'Запустить' для активации\n"
             "3. Для остановки нажмите кнопку 'Остановить'\n"
             "4. Вы можете свернуть программу в системный трей\n"
             "5. Для выхода из программы используйте меню в трее"),
            
            ("📌 Работа в системном трее", 
             "При сворачивании в трей программа продолжает работать в фоновом режиме. "
             "Для управления программой из трея:\n"
             "• Двойной клик по иконке - открыть программу\n"
             "• Правый клик по иконке - открыть контекстное меню\n"
             "• В контекстном меню можно управлять режимом работы и выйти из программы"),
            
            ("🖥️ Системные требования", 
             "• Windows 7/8/10/11\n"
             "• Python 3.6+\n"
             "• Библиотека PyQt5"),
            
            ("📥 Установка", 
             "1. Установите Python с официального сайта\n"
             "2. Установите необходимые зависимости: pip install pyqt5\n"
             "3. Запустите файл программы: python no_sleep.py"),
            
            ("🔒 Безопасность", 
             "Программа использует только официальные API Windows и не представляет угрозы для вашей системы. "
             "Исходный код открыт для проверки."),
            
            ("💡 Примечания", 
             "• Программа не требует административных прав для работы\n"
             "• При закрытии основного окна программа продолжает работать в трее\n"
             "• Для полного выхода из программы используйте меню в трее\n"
             "• Программа автоматически восстанавливает нормальные настройки сна при выходе")
        ]
        
        for i, (section_title, section_text) in enumerate(instructions):
            if i > 0:
                # Добавляем разделитель между секциями
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setObjectName("separator")
                instructions_layout.addWidget(separator)
                
            # Заголовок секции
            section_title_label = QLabel(section_title)
            section_title_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
            section_title_label.setObjectName("sectionTitle")
            instructions_layout.addWidget(section_title_label)
            
            # Текст секции
            section_text_label = QLabel(section_text)
            section_text_label.setWordWrap(True)
            section_text_label.setObjectName("sectionText")
            section_text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            instructions_layout.addWidget(section_text_label)
        
        # Добавляем растягивающийся элемент в конец
        instructions_layout.addStretch()
        
        # Устанавливаем контейнер в область прокрутки
        scroll_area.setWidget(instructions_container)
        layout.addWidget(scroll_area)
        
        # Кнопка возврата
        self.back_btn = FadeButton("Назад", color="#6A0DAD", hover_color="#8A2BE2")
        self.back_btn.clicked.connect(self.show_main_page)
        layout.addWidget(self.back_btn)
        
    def apply_light_theme(self):
        """Применение светлой темы"""
        self.dark_mode = False
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #E6E6FA, stop: 1 #D8BFD8);
            }
            QLabel#titleLabel {
                padding: 15px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6A0DAD, stop:1 #8A2BE2);
                border-radius: 15px;
                color: white;
                font-size: 28px;
            }
            QLabel#descriptionLabel {
                color: #4B0082;
                padding: 10px;
                font-weight: bold;
                font-size: 12px;
            }
            QGroupBox#settingsGroup, QGroupBox#infoGroup {
                font-weight: bold;
                border: 2px solid #6A0DAD;
                border-radius: 12px;
                margin-top: 10px;
                padding-top: 15px;
                background: rgba(255, 255, 255, 0.7);
                font-size: 12px;
            }
            QGroupBox#settingsGroup::title, QGroupBox#infoGroup::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #6A0DAD;
                font-size: 12px;
            }
            QLabel#settingLabel {
                color: #4B0082;
                font-weight: bold;
                font-size: 12px;
            }
            QLabel#infoLabel {
                color: #4B0082;
                padding: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QLabel#statusLabel {
                color: #E74C3C;
                font-weight: bold;
                padding: 8px;
                font-size: 12px;
            }
            QScrollArea#scrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #E6E6FA;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #6A0DAD;
                min-height: 30px;
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QLabel#instructionsTitle {
                padding: 15px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6A0DAD, stop:1 #8A2BE2);
                border-radius: 15px;
                color: white;
                font-size: 20px;
            }
            QFrame#separator {
                background-color: #D8BFD8;
                margin: 15px 0;
                max-height: 1px;
            }
            QLabel#sectionTitle {
                color: #6A0DAD;
                margin-top: 10px;
                font-size: 12px;
            }
            QLabel#sectionText {
                color: #4B0082;
                margin-bottom: 5px;
                background: transparent;
                font-size: 12px;
            }
        """)
        
    def apply_dark_theme(self):
        """Применение темной темы"""
        self.dark_mode = True
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2C3E50, stop: 1 #34495E);
            }
            QLabel#titleLabel {
                padding: 15px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6A0DAD, stop:1 #8A2BE2);
                border-radius: 15px;
                color: white;
                font-size: 28px;
            }
            QLabel#descriptionLabel {
                color: #BDC3C7;
                padding: 10px;
                font-weight: bold;
                font-size: 12px;
            }
            QGroupBox#settingsGroup, QGroupBox#infoGroup {
                font-weight: bold;
                border: 2px solid #6A0DAD;
                border-radius: 12px;
                margin-top: 10px;
                padding-top: 15px;
                background: rgba(52, 73, 94, 0.7);
                font-size: 12px;
            }
            QGroupBox#settingsGroup::title, QGroupBox#infoGroup::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #BDC3C7;
                font-size: 12px;
            }
            QLabel#settingLabel {
                color: #BDC3C7;
                font-weight: bold;
                font-size: 12px;
            }
            QLabel#infoLabel {
                color: #BDC3C7;
                padding: 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QLabel#statusLabel {
                color: #E74C3C;
                font-weight: bold;
                padding: 8px;
                font-size: 12px;
            }
            QScrollArea#scrollArea {
                border: none;
                background: rgba(52, 73, 94, 0.7);
                border-radius: 8px;
            }
            QScrollBar:vertical {
                border: none;
                background: #2C3E50;
                width: 12px;
                margin: 0px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #6A0DAD;
                min-height: 30px;
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QLabel#instructionsTitle {
                padding: 15px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6A0DAD, stop:1 #8A2BE2);
                border-radius: 15px;
                color: white;
                font-size: 20px;
            }
            QFrame#separator {
                background-color: #566573;
                margin: 15px 0;
                max-height: 1px;
            }
            QLabel#sectionTitle {
                color: #BB8FCE;
                margin-top: 10px;
                font-size: 12px;
            }
            QLabel#sectionText {
                color: #BDC3C7;
                margin-bottom: 5px;
                background: transparent;
                font-size: 12px;
            }
            QWidget {
                background: rgba(52, 73, 94, 0.7);
                border-radius: 8px;
            }
        """)
        
    def toggle_theme(self, state):
        """Переключение между светлой и темной темой"""
        if state == Qt.Checked:
            self.apply_dark_theme()
        else:
            self.apply_light_theme()
        
    def setup_tray(self):
        """Настройка системного трея"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setIcon(QIcon("icon.ico"))
            
            # Создание контекстного меню для трея
            tray_menu = QMenu()
            
            toggle_action = QAction("Запустить/Остановить", self)
            toggle_action.triggered.connect(self.toggle_keep_awake)
            tray_menu.addAction(toggle_action)
            
            theme_action = QAction("Переключить тему", self)
            theme_action.triggered.connect(lambda: self.theme_switch.setChecked(not self.theme_switch.isChecked()))
            tray_menu.addAction(theme_action)
            
            show_action = QAction("Показать", self)
            show_action.triggered.connect(self.show_from_tray)
            tray_menu.addAction(show_action)
            
            tray_menu.addSeparator()
            
            quit_action = QAction("Выход", self)
            quit_action.triggered.connect(self.quit_application)
            tray_menu.addAction(quit_action)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.tray_icon_activated)
            
            # Установка всплывающей подсказки
            self.tray_icon.setToolTip("No-Sleep - неактивно")
            self.tray_icon.show()
            
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
        self.toggle_btn._normal_color = QColor("#E74C3C")
        self.toggle_btn._hover_color = QColor("#C0392B")
        self.toggle_btn.update_style()
        self.status_label.setText("Статус: активно")
        self.status_label.setStyleSheet("color: #27AE60; font-weight: bold; padding: 8px; font-size: 12px;")
        
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
            self.show_notification("No-Sleep активирован", "Программа предотвращает сон и отключение экрана")
    
    def stop_keep_awake(self):
        """Деактивирует предотвращение сна"""
        self.is_active = False
        self.stop_thread = True
        self.toggle_btn.setText("Запустить")
        self.toggle_btn._normal_color = QColor("#27AE60")
        self.toggle_btn._hover_color = QColor("#219A73")
        self.toggle_btn.update_style()
        self.status_label.setText("Статус: неактивно")
        self.status_label.setStyleSheet("color: #E74C3C; font-weight: bold; padding: 8px; font-size: 12px;")
        
        # Восстановление нормальных настроек питания
        kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        
        # Остановка таймера
        self.timer.stop()
        
        # Обновление иконки в трее
        if self.tray_icon:
            self.tray_icon.setToolTip("No-Sleep - неактивно")
            self.show_notification("No-Sleep деактивирован", "Нормальный режим сна восстановлен")
    
    def keep_awake_worker(self):
        """Рабочая функция, которая предотвращает сон"""
        flags = ES_CONTINUOUS
        
        if self.prevent_sleep_switch.isChecked():
            flags |= ES_SYSTEM_REQUIRED
            
        if self.prevent_display_switch.isChecked():
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
    
    def show_instructions(self):
        """Показать страницу с инструкцией"""
        self.stacked_widget.setCurrentIndex(1)
    
    def show_main_page(self):
        """Показать главную страницу"""
        self.stacked_widget.setCurrentIndex(0)
    
    def hide_to_tray(self):
        """Сворачивание приложения в системный трей"""
        if self.tray_icon:
            self.hide()
            self.show_notification("No-Sleep", "Приложение свернуто в трей. Вы можете управлять им оттуда.")
    
    def show_from_tray(self):
        """Восстановление приложения из трея"""
        self.show()
        self.activateWindow()
        self.raise_()
    
    def show_notification(self, title, message):
        """Показать уведомление"""
        if self.tray_icon:
            # Для Windows 10/11
            try:
                self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 3000)
            except:
                # Fallback для старых версий Windows
                pass
    
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
            self.show_notification("No-Sleep", "Приложение продолжает работать в фоновом режиме. Для выхода используйте меню в трее.")
        else:
            self.quit_application()

if __name__ == "__main__":
    # Создание экземпляра приложения
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle('Fusion')  # Установка современного стиля
    
    # Установка иконки приложения
    app.setWindowIcon(QIcon("icon.ico"))
    
    # Инициализация и отображение главного окна
    window = NoSleepApp()
    window.show()
    
    # Запуск основного цикла приложения
    sys.exit(app.exec_())
