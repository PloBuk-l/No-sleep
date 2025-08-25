import tkinter as tk
from tkinter import ttk
import ctypes
from ctypes import wintypes
import threading
import time

# Загрузка библиотеки kernel32 для работы с Windows API
kernel32 = ctypes.windll.kernel32

# Константы для работы с системными настройками питания
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

class KeepAwakeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("KeepAwake - Контроль сна Windows")
        self.root.geometry("400x200")
        self.root.resizable(False, False)
        
        # Переменная для отслеживания состояния
        self.is_active = False
        self.thread = None
        self.stop_thread = False
        
        # Создание интерфейса
        self.create_widgets()
        
        # Обработка закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def create_widgets(self):
        # Основной фрейм
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Заголовок
        title_label = ttk.Label(main_frame, 
                               text="KeepAwake", 
                               font=("Arial", 16, "bold"),
                               foreground="#2E86AB")
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Описание
        desc_label = ttk.Label(main_frame,
                              text="Программа предотвращает отключение экрана\nи переход в спящий режим",
                              justify=tk.CENTER)
        desc_label.grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
        # Кнопка запуска/остановки
        self.toggle_btn = ttk.Button(main_frame, 
                                    text="Запустить", 
                                    command=self.toggle_keep_awake,
                                    style="Accent.TButton")
        self.toggle_btn.grid(row=2, column=0, columnspan=2, pady=(0, 10))
        
        # Статус
        self.status_label = ttk.Label(main_frame, 
                                     text="Статус: неактивно", 
                                     foreground="gray")
        self.status_label.grid(row=3, column=0, columnspan=2)
        
        # Настройка стилей для красивого интерфейса
        style = ttk.Style()
        style.configure("Accent.TButton", foreground="white", background="#2E86AB")
        
    def toggle_keep_awake(self):
        if not self.is_active:
            self.start_keep_awake()
        else:
            self.stop_keep_awake()
    
    def start_keep_awake(self):
        """Активирует предотвращение сна"""
        self.is_active = True
        self.stop_thread = False
        self.toggle_btn.config(text="Остановить")
        self.status_label.config(text="Статус: активно", foreground="green")
        
        # Запуск в отдельном потоке для избежания блокировки GUI
        self.thread = threading.Thread(target=self.keep_awake_worker)
        self.thread.daemon = True
        self.thread.start()
    
    def stop_keep_awake(self):
        """Деактивирует предотвращение сна"""
        self.is_active = False
        self.stop_thread = True
        self.toggle_btn.config(text="Запустить")
        self.status_label.config(text="Статус: неактивно", foreground="gray")
        
        # Восстановление нормальных настроек питания
        kernel32.SetThreadExecutionState(ES_CONTINUOUS)
    
    def keep_awake_worker(self):
        """Рабочая функция, которая предотвращает сон"""
        while not self.stop_thread:
            # Устанавливаем флаги для предотвращения сна и отключения дисплея
            kernel32.SetThreadExecutionState(ES_CONTINUOUS | 
                                            ES_SYSTEM_REQUIRED | 
                                            ES_DISPLAY_REQUIRED)
            time.sleep(60)  # Обновляем состояние каждую минуту
    
    def on_closing(self):
        """Обработчик закрытия окна"""
        if self.is_active:
            self.stop_keep_awake()
        self.root.destroy()

if __name__ == "__main__":
    # Создание главного окна
    root = tk.Tk()
    
    # Инициализация приложения
    app = KeepAwakeApp(root)
    
    # Запуск главного цикла
    root.mainloop()
