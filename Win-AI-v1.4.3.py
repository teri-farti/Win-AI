import sys
import os
import json
import ast
import webbrowser

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QDesktopWidget,
    QTextEdit, QHBoxLayout, QMessageBox, QComboBox, QSizePolicy,
    QInputDialog, QLineEdit, QFileDialog, QDialog, QDialogButtonBox
)
from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve,
    QPoint, QEvent, QByteArray, QBuffer, QIODevice, QCoreApplication, QRect
)
from PyQt5.QtGui import QPixmap, QImage, QCursor, QFont, QTextDocument, QTextCursor, QCloseEvent, QIcon

import speech_recognition as sr
try:
    import pyaudio
except ImportError:
    pyaudio = None
    print("Внимание: PyAudio не найден. Функции работы с микрофоном могут быть недоступны.")

import google.genai as genai

GOOGLE_API_KEY = "YOUR_GOOGLE_GEMINI_API_KEY"

if GOOGLE_API_KEY == "YOUR_GOOGLE_GEMINI_API_KEY":
    try:
        env_api_key = os.environ.get("GOOGLE_API_KEY")
        if env_api_key:
            GOOGLE_API_KEY = env_api_key
            print("API ключ Win-AI загружен из переменной окружения.")
    except Exception as e:
        print(f"Ошибка при загрузке API ключа из переменной окружения: {e}")
        print("Предупреждение: API ключ Win-AI не установлен. Функции Win-AI будут отключены.")

GEMINI_API_KEY = GOOGLE_API_KEY

LANGUAGES = {
    "RU": {
        "msg": "Пожалуйста, введите ваш Google Win-AI API ключ.\nВы можете получить его здесь:",
        "placeholder": "Введите ваш API ключ здесь...",
        "lang_label": "Выберите язык интерфейса:",
        "title": "Настройка Win-AI"
    },
    "EN": {
        "msg": "Please enter your Google Win-AI API key.\nYou can get it here:",
        "placeholder": "Enter your API key here...",
        "lang_label": "Select interface language:",
        "title": "Win-AI Settings"
    }
}
UI_TEXTS = {
    "ru": {
        "chat_cleared": "Чат очищен.",
        "thinking": "Думаю...",
        "listening": "Слушаю...",
        "recording_stopped": "Запись аудио остановлена.",
        "file_sent": "Файл '{file}' отправлен в Win-AI для анализа...",
        "file_cancel": "Выбор файла отменен.",
        "model_not_init": "Ошибка: Модель Win-AI не инициализирована.",
        "audio_error_title": "Ошибка аудио",
        "api_set": "API ключ установлен. Инициализация Win-AI...",
        "api_not_set": "API ключ не установлен.",
        "mic_off": "Аудио",
        "mic_on": "Выключить микрофон",
        "you": "Вы",
        "ai": "Win-AI"
    },
    "en": {
        "chat_cleared": "Chat cleared.",
        "thinking": "Thinking...",
        "listening": "Listening...",
        "recording_stopped": "Audio recording stopped.",
        "file_sent": "File '{file}' sent to Win-AI for analysis...",
        "file_cancel": "File selection cancelled.",
        "model_not_init": "Error: Win-AI model not initialized.",
        "audio_error_title": "Audio Error",
        "api_set": "API key set. Initializing Win-AI...",
        "api_not_set": "API key not set.",
        "mic_off": "Audio",
        "mic_on": "Turn off microphone",
        "you": "You",
        "ai": "Win-AI"
    }
}


class ApiKeyInputDialog(QDialog):
    def __init__(self, parent=None, current_key="", current_lang="EN"):
        super().__init__(parent)
        self.setFixedSize(500, 320)
        self.layout = QVBoxLayout(self)

        # Создаем элементы без текста (текст установит retranslate_ui)
        self.message_label = QLabel()
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setFont(QFont('Segoe UI', 12))

        self.link_label = QLabel("<a href='https://aistudio.google.com'>://aistudio.google.com</a>")
        self.link_label.setOpenExternalLinks(True)
        self.link_label.setAlignment(Qt.AlignCenter)

        self.key_input = QLineEdit(self)
        self.key_input.setText(current_key)
        self.key_input.setEchoMode(QLineEdit.Password)

        lang_layout = QHBoxLayout()
        self.lang_label = QLabel()
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["RU", "EN"])
        self.lang_combo.setCurrentText(current_lang)

        # СИГНАЛ: при смене языка в комбобоксе вызываем перевод
        self.lang_combo.currentTextChanged.connect(self.retranslate_ui)

        lang_layout.addWidget(self.lang_label)
        lang_layout.addWidget(self.lang_combo)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Help)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Добавляем на макет
        self.layout.addWidget(self.message_label)
        self.layout.addWidget(self.link_label)
        self.layout.addLayout(lang_layout)
        self.layout.addWidget(self.key_input)
        self.layout.addWidget(self.button_box)

        self.retranslate_ui(self.lang_combo.currentText())
        self.apply_styles()

    def retranslate_ui(self, lang):
        """Метод для динамической смены текста"""
        texts = LANGUAGES.get(lang, LANGUAGES["RU"])

        self.setWindowTitle(texts["title"])
        self.message_label.setText(texts["msg"])
        self.key_input.setPlaceholderText(texts["placeholder"])
        self.lang_label.setText(texts["lang_label"])

        # Обновляем текст стандартных кнопок
        ok_btn = self.button_box.button(QDialogButtonBox.Ok)
        cancel_btn = self.button_box.button(QDialogButtonBox.Cancel)
        help_btn = self.button_box.button(QDialogButtonBox.Help)

        if lang == "EN":
            if ok_btn: ok_btn.setText("OK")
            if cancel_btn: cancel_btn.setText("Cancel")
            if help_btn: help_btn.setText("Help")
        else:
            if ok_btn: ok_btn.setText("Готово")
            if cancel_btn: cancel_btn.setText("Отмена")
            if help_btn: help_btn.setText("Помощь")

    def get_data(self):
        return self.key_input.text(), self.lang_combo.currentText()

    def open_gemini_api_key_url(self):
        webbrowser.open("https://aistudio.google.com/app/apikey")

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(32, 32, 32, 0.95);
                border-radius: 15px;
                border: 1px solid rgba(70, 70, 70, 0.7);
            }
            QLabel { color: #e0e0e0; }
            QLabel a { color: #8A2BE2; text-decoration: underline; }

            QLineEdit, QComboBox {
                background-color: rgba(60, 60, 60, 0.9);
                color: #e0e0e0;
                border: 1px solid rgba(80, 80, 80, 0.7);
                border-radius: 10px;
                padding: 5px 10px;
                font-family: 'Segoe UI', sans-serif;
            }

            QComboBox {
                font-size: 14px;
                min-width: 80px;
            }

            QComboBox::drop-down {
                border: none;
                width: 30px;
            }

            QComboBox QAbstractItemView {
                background-color: #333;
                color: #e0e0e0;
                selection-background-color: #8A2BE2;
            }

            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #8A2BE2;
            }

            QPushButton {
                background-color: #8A2BE2;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #9932CC; }
            QPushButton:pressed { background-color: #7B1FA2; }
        """)


class TogglePanel(QWidget):
    show_main_panel_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.button = QPushButton("AI")
        self.button.setObjectName("toggleVisibilityButton")
        self.button.setFixedSize(75, 75)

        self.button.clicked.connect(self.show_main_panel_signal.emit)
        self.layout.addWidget(self.button, alignment=Qt.AlignTop | Qt.AlignRight)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

        self.old_pos = None

        self.set_initial_position()
        self.apply_styles()

    def set_initial_position(self):
        screen_geometry = QApplication.desktop().screenGeometry()
        x = screen_geometry.width() - 95
        y = 20
        self.move(x, y)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.old_pos = event.pos()
            event.accept()

    def mouseReleaseEvent(self, event):
        self.old_pos = None
        event.accept()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = event.pos() - self.old_pos
            self.move(self.pos() + delta)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def apply_styles(self):
        self.button.setStyleSheet("""
            QPushButton#toggleVisibilityButton {
                background-color: #8A2BE2; /* Фиолетовый фон */
                color: white;
                border: none;
                border-radius: 37px; /* Скругленные углы для создания круга */
                font-size: 30px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton#toggleVisibilityButton:hover {
                background-color: #9932CC; /* Более светлый фиолетовый при наведении */
            }
            QPushButton#toggleVisibilityButton:pressed {
                background-color: #7B1FA2; /* Более темный фиолетовый при нажатии */
            }
        """)


class OverlayPanel(QWidget):
    BORDER_WIDTH = 8
    MIN_WIDTH = 500
    MIN_HEIGHT = 350

    def __init__(self, toggle_panel, parent=None):
        super().__init__(parent)
        self.setObjectName("OverlayPanel")
        self.toggle_panel = toggle_panel
        self.settings_file = "settings.json"

        self.chat_history = []
        self.selected_microphone_index = None

        self.setMouseTracking(True)
        self.resizing = False
        self.resizing_edge = None
        self.old_pos = None
        self.old_pos_global = None
        self.current_language = "ru"

        self._setup_ui()

        self.load_settings()
        self.initialize_gemini()
        self.populate_devices()

        self.autoscroll_chat()
        self.show()
        self.toggle_panel.hide()

    def update_ui_language(self):
        if self.current_language == "ru":
            self.send_button.setText("Отправить")
            self.open_file_button.setText("Файл")
            self.toggle_audio_button.setText("Аудио")
            self.clear_chat_button.setText("Очистить чат")
            self.chat_input.setPlaceholderText("Введите сообщение...")
        else:
            self.send_button.setText("Send")
            self.open_file_button.setText("File")
            self.toggle_audio_button.setText("Audio")
            self.clear_chat_button.setText("Clear chat")
            self.chat_input.setPlaceholderText("Input message...")

    def t(self, key, **kwargs):
        text = UI_TEXTS[self.current_language].get(key, key)
        return text.format(**kwargs)

    def change_language(self):
        self.current_language = self.language_selector.currentData()
        self.settings['language'] = self.current_language
        self.save_settings()
        self.update_ui_language()
        if self.current_language == "ru":
            self.chat_display.append("<p style='color:#8A2BE2;'>Win-AI: Язык переключен на русский.</p>")
        else:
            self.chat_display.append("<p style='color:#8A2BE2;'>Win-AI: Language switched to English.</p>")

    def _setup_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        current_width = 750
        current_height = 500
        self.setGeometry(150, 150, int(current_width), int(current_height))
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.setContentsMargins(self.BORDER_WIDTH, self.BORDER_WIDTH, self.BORDER_WIDTH, self.BORDER_WIDTH)

        self.content_widget = QWidget(self)
        self.content_widget.setObjectName("ContentWidget")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        self.layout.addWidget(self.content_widget)

        self.control_panel = QWidget(self.content_widget)
        self.control_panel.setStyleSheet("background-color: rgba(60, 60, 60, 0.7); border-top-left-radius: 20px; border-top-right-radius: 20px;")
        self.control_layout = QHBoxLayout(self.control_panel)
        self.control_layout.setContentsMargins(10, 10, 10, 10)

        self.title_label = QLabel("Win-AI (v1.5.0)")
        self.title_label.setObjectName("titleLabel")
        self.control_layout.addWidget(self.title_label)

        self.language_selector = QComboBox()
        self.language_selector.addItem("Русский", "ru")
        self.language_selector.addItem("English", "en")
        self.language_selector.currentIndexChanged.connect(self.change_language)
        self.control_layout.addWidget(self.language_selector)

        self.control_layout.addStretch()

        self.clear_chat_button = QPushButton("Очистить чат")
        self.clear_chat_button.clicked.connect(self.clear_chat)
        self.control_layout.addWidget(self.clear_chat_button)

        self.hide_button = QPushButton("-")
        self.hide_button.setObjectName("toggleVisibilityButton")
        self.hide_button.setFixedSize(40, 40)
        self.hide_button.clicked.connect(self.hide_panel_animated)
        self.control_layout.addWidget(self.hide_button)

        self.close_button = QPushButton("X")
        self.close_button.setObjectName("closeButton")
        self.close_button.setFixedSize(40, 40)
        self.close_button.clicked.connect(self.close)
        self.control_layout.addWidget(self.close_button)

        self.content_layout.addWidget(self.control_panel)

        self.chat_display = QTextEdit()
        self.chat_display.setObjectName("chatDisplay")
        self.chat_display.setReadOnly(True)
        self.chat_display.setLineWrapMode(QTextEdit.WidgetWidth)
        self.content_layout.addWidget(self.chat_display, 1)

        self.input_main_layout = QHBoxLayout()
        self.input_main_layout.setContentsMargins(0, 0, 0, 0)

        self.chat_input = QTextEdit()
        self.chat_input.setObjectName("chatInput")
        self.chat_input.setPlaceholderText("Введите сообщение...")
        self.chat_input.setFixedHeight(190)
        self.chat_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input_main_layout.addWidget(self.chat_input, 1)

        self.right_buttons_container = QVBoxLayout()
        self.right_buttons_container.setContentsMargins(0, 0, 0, 0)
        self.right_buttons_container.setSpacing(5)

        self.send_button = QPushButton("Отправить")
        self.send_button.clicked.connect(self.send_message_from_input)
        self.send_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.right_buttons_container.addWidget(self.send_button)

        self.open_file_button = QPushButton("Файл") #
        self.open_file_button.clicked.connect(self.select_file_for_analysis)
        self.open_file_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.right_buttons_container.addWidget(self.open_file_button)

        self.toggle_audio_button = QPushButton("Аудио")
        self.toggle_audio_button.setObjectName("toggleAudioButton")
        self.toggle_audio_button.clicked.connect(self.toggle_audio_recording)
        self.toggle_audio_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.right_buttons_container.addWidget(self.toggle_audio_button)

        self.right_buttons_container.addStretch(1)

        self.input_main_layout.addLayout(self.right_buttons_container)
        self.content_layout.addLayout(self.input_main_layout)

        self.gemini_model = None
        self.audio_thread = None
        self.recording_in_progress = False

        self.apply_styles()
        self.chat_input.installEventFilter(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            rect = self.rect()
            pos = event.pos()

            on_left_edge = abs(pos.x() - rect.left()) < self.BORDER_WIDTH
            on_right_edge = abs(pos.x() - rect.right()) < self.BORDER_WIDTH
            on_top_edge = abs(pos.y() - rect.top()) < self.BORDER_WIDTH
            on_bottom_edge = abs(pos.y() - rect.bottom()) < self.BORDER_WIDTH

            if on_left_edge and on_top_edge:
                self.resizing = True
                self.resizing_edge = "top_left"
            elif on_right_edge and on_top_edge:
                self.resizing = True
                self.resizing_edge = "top_right"
            elif on_left_edge and on_bottom_edge:
                self.resizing = True
                self.resizing_edge = "bottom_left"
            elif on_right_edge and on_bottom_edge:
                self.resizing = True
                self.resizing_edge = "bottom_right"
            elif on_left_edge:
                self.resizing = True
                self.resizing_edge = "left"
            elif on_right_edge:
                self.resizing = True
                self.resizing_edge = "right"
            elif on_top_edge:
                self.resizing = True
                self.resizing_edge = "top"
            elif on_bottom_edge:
                self.resizing = True
                self.resizing_edge = "bottom"
            else:
                self.old_pos = event.pos()

            self.old_pos_global = event.globalPos()
            event.accept()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.old_pos = None
        self.resizing = False
        self.resizing_edge = None
        self.old_pos_global = None
        self.save_settings()
        event.accept()
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self.resizing:
            current_pos = event.globalPos()
            diff = current_pos - self.old_pos_global
            self.old_pos_global = current_pos

            new_x, new_y, new_width, new_height = self.geometry().x(), self.geometry().y(), self.width(), self.height()

            if self.resizing_edge == "right":
                new_width = max(self.MIN_WIDTH, self.width() + diff.x())
            elif self.resizing_edge == "left":
                new_x = self.x() + diff.x()
                new_width = max(self.MIN_WIDTH, self.width() - diff.x())
            elif self.resizing_edge == "bottom":
                new_height = max(self.MIN_HEIGHT, self.height() + diff.y())
            elif self.resizing_edge == "top":
                new_y = self.y() + diff.y()
                new_height = max(self.MIN_HEIGHT, self.height() - diff.y())
            elif self.resizing_edge == "top_left":
                new_x = self.x() + diff.x()
                new_y = self.y() + diff.y()
                new_width = max(self.MIN_WIDTH, self.width() - diff.x())
                new_height = max(self.MIN_HEIGHT, self.height() - diff.y())
            elif self.resizing_edge == "top_right":
                new_y = self.y() + diff.y()
                new_width = max(self.MIN_WIDTH, self.width() + diff.x())
                new_height = max(self.MIN_HEIGHT, self.height() - diff.y())
            elif self.resizing_edge == "bottom_left":
                new_x = self.x() + diff.x()
                new_width = max(self.MIN_WIDTH, self.width() - diff.x())
                new_height = max(self.MIN_HEIGHT, self.height() + diff.y())
            elif self.resizing_edge == "bottom_right":
                new_width = max(self.MIN_WIDTH, self.width() + diff.x())
                new_height = max(self.MIN_HEIGHT, self.height() + diff.y())

            self.setGeometry(new_x, new_y, new_width, new_height)
            event.accept()
        elif self.old_pos is not None:
            delta = event.pos() - self.old_pos
            self.move(self.pos() + delta)
            event.accept()
        else:
            self.set_cursor_shape(event.pos())
            super().mouseMoveEvent(event)

    def set_cursor_shape(self, pos):
        rect = self.rect()
        on_left_edge = abs(pos.x() - rect.left()) < self.BORDER_WIDTH
        on_right_edge = abs(pos.x() - rect.right()) < self.BORDER_WIDTH
        on_top_edge = abs(pos.y() - rect.top()) < self.BORDER_WIDTH
        on_bottom_edge = abs(pos.y() - rect.bottom()) < self.BORDER_WIDTH

        if on_right_edge and on_bottom_edge:
            self.setCursor(Qt.SizeFDiagCursor)
        elif on_left_edge and on_bottom_edge:
            self.setCursor(Qt.SizeBDiagCursor)
        elif on_left_edge and on_top_edge:
            self.setCursor(Qt.SizeFDiagCursor)
        elif on_right_edge and on_top_edge:
            self.setCursor(Qt.SizeBDiagCursor)
        elif on_right_edge or on_left_edge:
            self.setCursor(Qt.SizeHorCursor)
        elif on_top_edge or on_bottom_edge:
            self.setCursor(Qt.SizeVerCursor)
        else:
            if pos.y() <= self.control_panel.height() + self.BORDER_WIDTH and \
               pos.x() > self.BORDER_WIDTH and \
               pos.x() < self.width() - self.BORDER_WIDTH:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

    def leaveEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

    def eventFilter(self, obj, event):
        if obj is self.chat_input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                if event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier):
                    self.chat_input.insertPlainText("\n")
                    return True
                else:
                    self.send_message_from_input()
                    return True
        return super().eventFilter(obj, event)

    def event(self, event):
        if event.type() == QEvent.MouseMove and event.buttons() == Qt.NoButton:
            self.set_cursor_shape(event.pos())
        return super().event(event)

    def apply_styles(self):
        self.setStyleSheet(f"""
            OverlayPanel {{
                background-color: rgba(32, 32, 32, 0.95); /* Полупрозрачный темный фон */
                border-radius: 25px; /* Скругленные углы */
                border: {self.BORDER_WIDTH}px solid rgba(70, 70, 70, 0.7); /* Рамка */
                box-shadow: 0 10px 20px rgba(0, 0, 0, 0.3); /* Тень */
            }}

            QWidget#ContentWidget {{
                background-color: transparent; /* Прозрачный фон для виджета содержимого */
                border-radius: 20px;
            }}

            QLabel#titleLabel {{
                background-color: rgba(60, 60, 60, 0.7);
                color: #FFFFFF;
                font-size: 22px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
                border-radius: 12px;
                padding: 5px 15px;
                margin-left: 0px;
                margin-right: 0px;
            }}

            QLabel#deviceLabel {{ /* Для будущих элементов, если будут */
                background-color: rgba(60, 60, 60, 0.7);
                color: #FFFFFF;
                font-size: 18px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
                border-radius: 10px;
                padding: 5px 12px;
                margin-left: 0px;
                margin-right: 0px;
            }}

            QPushButton#toggleVisibilityButton {{
                background-color: #555555;
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 20px;
                font-weight: bold;
                padding: 0;
            }}
            QPushButton#toggleVisibilityButton:hover {{
                background-color: #777777;
            }}
            QPushButton#toggleVisibilityButton:pressed {{
                background-color: #333333;
            }}

            QPushButton#closeButton {{
                background-color: #E81123 !important; /* Красный цвет для кнопки закрытия */
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 20px;
                font-weight: bold;
                padding: 0;
            }}
            QPushButton#closeButton:hover {{
                background-color: #F1707A !important;
            }}
            QPushButton#closeButton:pressed {{
                background-color: #B20000 !important;
            }}

            QPushButton {{ /* Общие стили для всех QPushButton */
                background-color: #8A2BE2; /* Фиолетовый фон */
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 10px;
                font-size: 18px;
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
                min-height: 40px; /* Минимальная высота */
            }}
            QPushButton:hover {{
                background-color: #9932CC;
            }}
            QPushButton:pressed {{
                background-color: #7B1FA2;
            }}
            QPushButton:disabled {{
                background-color: #3e3e3e; /* Серый фон для отключенных кнопок */
                color: #888888;
            }}

            /* Стили для кнопок справа, чтобы они были одного размера с "Отправить" */
            QPushButton[text="Отправить"],
            QPushButton[text="Файл"],
            QPushButton#toggleAudioButton {{
                min-width: 100px; /* Фиксированная минимальная ширина */
                max-width: 150px; /* Ограничиваем максимальную ширину */
                padding: 10px 15px;
            }}

            QPushButton#toggleAudioButton.active {{ /* Стиль для активной кнопки аудиозаписи */
                background-color: #dc3545; /* Красный цвет */
                color: white;
            }}
            QPushButton#toggleAudioButton.active:hover {{
                background-color: #e35d6a;
            }}
            QPushButton#toggleAudioButton.active:pressed {{
                background-color: #c82333;
            }}

            QComboBox {{ /* Стили для выпадающих списков (если будут) */
                background-color: #404040;
                color: white;
                border: 1px solid #606060;
                border-radius: 10px;
                padding: 5px 12px;
                font-size: 18px;
                min-height: 40px;
            }}
            QComboBox::drop-down {{
                border: 0px;
                width: 30px;
            }}
            QComboBox::down-arrow {{
                /* Иконка стрелки вниз (базовый base64) */
                image: url(data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA0AAAAHCAYAAADgSxdxAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAAXNSR0IArs4c6QAAAARnQUBUBAACxjwv8YQUAAABJSURBVHjaY/z//z8D/y9wDAxM+FwM/F0w/N+f+Pw/A1wMDAT+z///PwMABbQxMDBM/f8fBmAASxADWBoB4zE0gA2GzQAAg8Y8B9B+9CMAAAAASUVORK5CYII=);
                width: 15px;
                height: 8px;
                padding-right: 5px;
            }}
            QComboBox:hover {{
                background-color: #505050;
            }}
            QComboBox::item {{
                padding: 5px 12px;
                color: white;
            }}
            QComboBox::item:selected {{
                background-color: #8A2BE2;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid #606060;
                border-radius: 10px;
                background-color: #404040;
                selection-background-color: #8A2BE2;
                outline: 0;
            }}
            QComboBox QAbstractItemView::verticalScrollBar {{
                border: none;
                background: rgba(50, 50, 50, 0.5);
                width: 12px;
                margin: 5px 0px 5px 0px;
                border-radius: 6px;
            }}
            QComboBox QAbstractItemView::verticalScrollBar::handle:vertical {{
                background: rgba(120, 120, 120, 0.7);
                border-radius: 6px;
                min-height: 35px;
            }}
            QComboBox QAbstractItemView::verticalScrollBar::handle:vertical:hover {{
                background: rgba(150, 150, 150, 0.8);
            }}
            QComboBox QAbstractItemView::verticalScrollBar::add-line:vertical,
            QComboBox QAbstractItemView::verticalScrollBar::sub-line:vertical {{
                background: none;
            }}
            QComboBox QAbstractItemView::verticalScrollBar::add-page:vertical,
            QComboBox QAbstractItemView::verticalScrollBar::sub-page:vertical {{
                background: none;
            }}

            QTextEdit#chatDisplay {{
                background-color: rgba(45, 45, 45, 0.9);
                color: #e0e0e0;
                border: 1px solid rgba(70, 70, 70, 0.7);
                border-radius: 18px;
                padding: 18px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 18px;
                font-weight: 500;
            }}
            QTextEdit#chatInput {{
                background-color: rgba(60, 60, 60, 0.9);
                color: #e0e0e0;
                border: 1px solid rgba(80, 80, 80, 0.7);
                border-radius: 15px;
                padding: 15px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 18px;
                font-weight: 500;
            }}
            QTextEdit#chatInput:focus {{
                border: 1px solid #8A2BE2; /* Фиолетовая рамка при фокусе */
            }}

            QScrollBar:vertical {{
                border: none;
                background: rgba(50, 50, 50, 0.5);
                width: 12px;
                margin: 5px 0px 5px 0px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(120, 120, 120, 0.7);
                border-radius: 6px;
                min-height: 35px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(150, 150, 150, 0.8);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                background: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

    def clear_chat(self):
        self.chat_display.clear()
        self.chat_history = []
        self.chat_display.append(f"<p style='color:#8A2BE2;'>{self.t('ai')}: {self.t('chat_cleared')}</p>")
        self.save_settings() #

    def load_settings(self):
        if os.path.exists(self.settings_file):
            with open(self.settings_file, 'r') as f:
                self.settings = json.load(f)
        else:
            self.settings = {}

        self.current_language = self.settings.get('language', 'ru')

        index = 0 if self.current_language == "ru" else 1
        self.language_selector.setCurrentIndex(index)

        current_width = self.settings.get('width', 750)
        current_height = self.settings.get('height', 500)
        self.setGeometry(self.settings.get('pos_x', 150), self.settings.get('pos_y', 150),
                         int(current_width), int(current_height))
        self.setMinimumSize(self.MIN_WIDTH, self.MIN_HEIGHT)

        global GEMINI_API_KEY
        if 'api_key' in self.settings and self.settings['api_key'] and self.settings['api_key'] != "YOUR_GOOGLE_GEMINI_API_KEY":
            GEMINI_API_KEY = self.settings['api_key']
        else:
            self.prompt_for_api_key()

        if 'chat_history' in self.settings:
            try:
                self.chat_display.setFont(QFont('Segoe UI', 18, QFont.Medium))
                raw_history = self.settings['chat_history']
                if raw_history.startswith('[') and raw_history.endswith(']'):
                    parsed_history = ast.literal_eval(raw_history)
                    for i, msg in enumerate(parsed_history):
                        if "<p style='color:#ADD8E6;'>" in msg or "<p style='color:green;'>" in msg:
                            parsed_history[i] = msg.replace("<p style='color:#ADD8E6;'>", "<p style='color:#8A2BE2;'>")
                            parsed_history[i] = parsed_history[i].replace("<p style='color:green;'>", "<p style='color:#8A2BE2;'>")
                    self.chat_history = parsed_history
                else:
                    if "<p style='color:#ADD8E6;'>" in raw_history or "<p style='color:green;'>" in raw_history:
                        raw_history = raw_history.replace("<p style='color:#ADD8E6;'>", "<p style='color:#8A2BE2;'>")
                        raw_history = raw_history.replace("<p style='color:green;'>", "<p style='color:#8A2BE2;'>")
                    self.chat_history = [raw_history]

                for message in self.chat_history:
                    self.chat_display.append(message)
            except (ValueError, SyntaxError) as e:
                print(f"Ошибка при загрузке истории чата: {e}. История будет очищена.")
                self.chat_history = []
        else:
            self.chat_display.setFont(QFont('Segoe UI', 18, QFont.Medium))

        self.selected_microphone_index = self.settings.get('selected_microphone_index', None)

    def save_settings(self):
        self.settings['pos_x'] = self.pos().x()
        self.settings['pos_y'] = self.pos().y()
        self.settings['width'] = self.width()
        self.settings['height'] = self.height()
        self.settings['api_key'] = GEMINI_API_KEY
        self.settings['chat_history'] = str(self.chat_history)
        self.settings['selected_microphone_index'] = self.selected_microphone_index

        with open(self.settings_file, 'w') as f:
            json.dump(self.settings, f, indent=4)

    def prompt_for_api_key(self):
        global GEMINI_API_KEY
        dialog = ApiKeyInputDialog(self, current_key=GEMINI_API_KEY if GEMINI_API_KEY != "YOUR_GOOGLE_GEMINI_API_KEY" else "")
        if dialog.exec_() == QDialog.Accepted:
            key = dialog.get_api_key()
            if key:
                GEMINI_API_KEY = key
                self.settings['api_key'] = key
                self.save_settings()
                self.chat_display.append("<p style='color:#8A2BE2;'>The API key has been installed. Initializing Win-AI...</p>")
                self.initialize_gemini()
            else:
                QMessageBox.warning(self, "Error", "API key cannot be empty. Win-AI features will be disabled.")
                self.chat_display.append("<p style='color:red;'>API ключ не установлен.</p>")
                self.send_button.setEnabled(False)
                self.open_file_button.setEnabled(False)
                self.toggle_audio_button.setEnabled(False)
        else:
            self.chat_display.append("<p style='color:red;'>The API key is not installed. Win-AI features will be disabled.</p>")
            self.send_button.setEnabled(False)
            self.open_file_button.setEnabled(False)
            self.toggle_audio_button.setEnabled(False)

    def initialize_gemini(self):
        global GEMINI_API_KEY
        if GEMINI_API_KEY and GEMINI_API_KEY != "YOUR_GOOGLE_GEMINI_API_KEY":
            try:
                genai.configure(api_key=GEMINI_API_KEY)
                self.gemini_model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
                _ = genai.get_model('gemini-2.5-flash-preview-05-20')

                self.send_button.setEnabled(True)
                self.open_file_button.setEnabled(True)
                self.toggle_audio_button.setEnabled(True)

            except Exception as e:
                self.send_button.setEnabled(False)
                self.open_file_button.setEnabled(False)
                self.toggle_audio_button.setEnabled(False)
                self.chat_display.append(
                    f"<p style='color:red;'>Error: The Win-AI model is not initialized. Check your API key and internet connection: {e}</p>")
        else:
            self.send_button.setEnabled(False)
            self.open_file_button.setEnabled(False)
            self.toggle_audio_button.setEnabled(False)
            self.chat_display.append(
                "<p style='color:red;'>Error: The Google Win-AI API key is not installed. Win-AI and related features will be disabled.</p>")

    def autoscroll_chat(self):
        self.chat_display.verticalScrollBar().setValue(self.chat_display.verticalScrollBar().maximum())

    def hide_panel_animated(self):
        self.save_settings()
        screen_geometry = QApplication.desktop().screenGeometry()
        start_pos = self.pos()
        toggle_button_width = 75
        toggle_button_height = 75
        end_pos = QPoint(screen_geometry.width() - toggle_button_width - 20, 20)
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(300)
        self.animation.setStartValue(start_pos)
        self.animation.setEndValue(end_pos)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.finished.connect(self.hide)
        self.animation.finished.connect(self.toggle_panel.show) #
        self.animation.start()

    def show_panel_animated(self):
        self.show()
        self.toggle_panel.hide()
        screen_geometry = QApplication.desktop().screenGeometry()
        toggle_button_width = 75
        toggle_button_height = 75
        start_pos = QPoint(screen_geometry.width() - toggle_button_width - 20, 20)
        end_pos = QPoint(self.settings.get('pos_x', 150), self.settings.get('pos_y', 150))

        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(300)
        self.animation.setStartValue(start_pos)
        self.animation.setEndValue(end_pos)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.start()

    def closeEvent(self, event: QCloseEvent):
        if self.audio_thread and self.audio_thread.isRunning():
            self.audio_thread.stop()
            self.audio_thread.wait(2000)

        self.save_settings()
        event.accept()
        QCoreApplication.instance().quit()

    def select_file_for_analysis(self):
        if not self.gemini_model:
            self.chat_display.append("<p style='color:red;'>Error: Win-AI model not initialized. Unable to parse files.</p>")
            return

        options = QFileDialog.Options()
        file_filters = (
            "Все поддерживаемые файлы ("
            "*.txt *.py *.json *.xml *.html *.css *.js *.md *.csv *.tsv *.log *.ini *.cfg *.conf "
            "*.pdf *.docx *.xlsx *.pptx "
            "*.jpg *.jpeg *.png *.gif *.bmp *.tiff *.webp "
            "*.mp3 *.wav *.flac *.ogg *.aac "
            "*.mp4 *.avi *.mov *.wmv *.flv *.webm "
            "*.zip *.rar *.7z"
            ");;"
            "Текстовые и программные файлы ("
            "*.txt *.py *.json *.xml *.html *.css *.js *.md *.csv *.tsv *.log *.ini *.cfg *.conf"
            ");;"
            "Документы ("
            "*.pdf *.docx *.xlsx *.pptx"
            ");;"
            "Изображения ("
            "*.jpg *.jpeg *.png *.gif *.bmp *.tiff *.webp"
            ");;"
            "Аудио файлы ("
            "*.mp3 *.wav *.flac *.ogg *.aac"
            ");;"
            "Видео файлы ("
            "*.mp4 *.avi *.mov *.wmv *.flv *.webm"
            ");;"
            "Архивы (*.zip *.rar *.7z);;"
            "Все файлы (*.*)"
        )

        file_path, _ = QFileDialog.getOpenFileName(self, "Выбрать файл для анализа", "", file_filters, options=options)
        if file_path:
            try:
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                file_name = os.path.basename(file_path)
                file_extension = os.path.splitext(file_name)[1].lower()

                mime_type = "application/octet-stream"


                if file_extension in (".txt", ".py", ".json", ".xml", ".html", ".css", ".js", ".md", ".csv", ".tsv", ".log", ".ini", ".cfg", ".conf"):
                    mime_type = "text/plain"
                elif file_extension == ".pdf":
                    mime_type = "application/pdf"
                elif file_extension == ".docx":
                    mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                elif file_extension == ".xlsx":
                    mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif file_extension == ".pptx":
                    mime_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                elif file_extension in (".jpg", ".jpeg"):
                    mime_type = "image/jpeg"
                elif file_extension == ".png":
                    mime_type = "image/png"
                elif file_extension == ".gif":
                    mime_type = "image/gif"
                elif file_extension == ".bmp":
                    mime_type = "image/bmp"
                elif file_extension == ".tiff":
                    mime_type = "image/tiff"
                elif file_extension == ".webp":
                    mime_type = "image/webp"
                elif file_extension == ".mp4":
                    mime_type = "video/mp4"
                elif file_extension == ".avi":
                    mime_type = "video/x-msvideo"
                elif file_extension == ".mov":
                    mime_type = "video/quicktime"
                elif file_extension == ".wmv":
                    mime_type = "video/x-ms-wmv"
                elif file_extension == ".flv":
                    mime_type = "video/x-flv"
                elif file_extension == ".webm":
                    mime_type = "video/webm"
                elif file_extension == ".mp3":
                    mime_type = "audio/mpeg"
                elif file_extension == ".wav":
                    mime_type = "audio/wav"
                elif file_extension == ".flac":
                    mime_type = "audio/flac"
                elif file_extension == ".ogg":
                    mime_type = "audio/ogg"
                elif file_extension == ".aac":
                    mime_type = "audio/aac"

                self.send_message(f"Проанализируй содержимое этого файла: {file_name}", file_data=file_data, file_name=file_name, file_mime_type=mime_type)
                self.chat_display.append(
                    f"<p style='color:#8A2BE2;'>{self.t('ai')}: {self.t('file_sent', file=file_name)}</p>"
                )


            except Exception as e:
                self.chat_display.append(
                    f"<p style='color:red;'>{self.t('ai')}: {self.t('file_cancel')}</p>"
                )

        else:
            self.chat_display.append(
                f"<p style='color:red;'>{self.t('ai')}: {self.t('file_cancel')}</p>"
            )

    def send_message_from_input(self):
        message_text = self.chat_input.toPlainText().strip()
        if message_text:
            self.send_message(message_text)
        self.chat_input.clear()

    def send_message(self, text, image_data=None, file_data=None, file_name=None, file_mime_type=None):
        if not self.gemini_model:
            self.chat_display.append("<p style='color:red;'>Error: Win-AI model not initialized.</p>")
            return

        self.send_button.setEnabled(False)

        user_message_html = f"<p style='color:#FFFFFF;'>{self.t('you')}: {text}</p>"
        self.chat_display.append(user_message_html)
        self.chat_history.append(user_message_html)

        self.chat_display.append(f"<p style='color:#8A2BE2;'>{self.t('ai')}: {self.t('thinking')}</p>")

        prompt_parts = []

        if self.current_language == "ru":
            language_instruction = "Ответь на русском языке."
        else:
            language_instruction = "Answer in English."
        if file_data and file_name and file_mime_type:
            prompt_parts.append({"mime_type": file_mime_type, "data": file_data})
            prompt_parts.append(f"{language_instruction}\nAnalyze file {file_name}: {text}")

        else:
            prompt_parts.append(f"{language_instruction}\n{text}")

        self.worker_thread = WorkerThread(self.gemini_model, prompt_parts)
        self.worker_thread.response_received.connect(self.handle_gemini_response)
        self.worker_thread.error_occurred.connect(self.handle_gemini_error)
        self.worker_thread.start()

        self.chat_input.clear()
        self.autoscroll_chat()

    def handle_gemini_response(self, response_text):
        html_content = self.chat_display.toHtml()
        think_html = "<p style=\"color:#8A2BE2;\">Win-AI: Думаю...</p>"
        if html_content.strip().endswith(think_html.strip()):
            last_think_index = html_content.rfind(think_html)
            if last_think_index != -1:
                html_content = html_content[:last_think_index]
                self.chat_display.setHtml(html_content)
        self.chat_display.append(f"<p style='color:#8A2BE2;'>Win-AI: {response_text}</p>")

        if self.chat_history and self.chat_history[-1].strip() == think_html.strip():
            self.chat_history.pop()
        self.chat_history.append(f"<p style='color:#8A2BE2;'>Win-AI: {response_text}</p>")

        self.send_button.setEnabled(True)
        self.autoscroll_chat()
        self.save_settings()

    def handle_gemini_error(self, error_message):
        html_content = self.chat_display.toHtml()
        think_html = "<p style=\"color:#8A2BE2;\">Win-AI: Думаю...</p>"
        if html_content.strip().endswith(think_html.strip()):
            last_think_index = html_content.rfind(think_html)
            if last_think_index != -1:
                html_content = html_content[:last_think_index]
                self.chat_display.setHtml(html_content)
        self.chat_display.append(f"<p style='color:#8A2BE2;'>{self.t('ai')}: {error_message}</p>")

        if self.chat_history and self.chat_history[-1].strip() == think_html.strip():
            self.chat_history.pop()
        self.chat_display.append(f"<p style='color:#8A2BE2;'>{self.t('ai')}: {error_message}</p>")

        self.send_button.setEnabled(True)
        self.autoscroll_chat()
        self.save_settings()

    def populate_devices(self):
        pass #

    def toggle_audio_recording(self):
        if self.recording_in_progress:
            self.stop_audio_recording()
        else:
            self.start_audio_recording()

    def start_audio_recording(self):
        if self.recording_in_progress:
            return
        if not pyaudio:
            self.chat_display.append("<p style='color:red;'>Не могу начать запись аудио: PyAudio не установлен.</p>")
            return

        self.audio_thread = AudioWorkerThread(self)
        self.audio_thread.transcribed_text.connect(self.handle_transcribed_text)
        self.audio_thread.error_occurred.connect(self.handle_audio_error)
        self.audio_thread.start()
        self.recording_in_progress = True
        self.toggle_audio_button.setText(self.t("mic_on"))
        self.toggle_audio_button.setStyleSheet("QPushButton#toggleAudioButton.active { background-color: #dc3545; color: white; }")
        self.toggle_audio_button.setProperty("class", "active")
        self.toggle_audio_button.style().polish(self.toggle_audio_button)
        self.chat_display.append(f"<p style='color:#8A2BE2;'>{self.t('ai')}: {self.t('listening')}</p>")

    def stop_audio_recording(self):
        if self.audio_thread and self.audio_thread.isRunning():
            self.audio_thread.stop()
            self.recording_in_progress = False
            self.toggle_audio_button.setProperty("class", "")
            self.toggle_audio_button.style().polish(self.toggle_audio_button)
            self.toggle_audio_button.setText(self.t("mic_off"))

            self.chat_display.append(
                f"<p style='color:#8A2BE2;'>{self.t('ai')}: {self.t('recording_stopped')}</p>"
            )

    def handle_transcribed_text(self, text):
        self.chat_input.setText(text)
        self.send_message_from_input()

    def handle_audio_error(self, error_message):
        QMessageBox.critical(self, self.t("audio_error_title"), error_message)
        self.chat_display.append(f"<p style='color:red;'>Audio Error: {error_message}</p>")
        self.stop_audio_recording()



class AudioWorkerThread(QThread):
    transcribed_text = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
        self.recognizer = sr.Recognizer()

    def run(self):
        self.running = True
        if not pyaudio:
            self.error_occurred.emit("PyAudio не доступен. Невозможно использовать микрофон.")
            self.running = False
            return

        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source)
                self.recognizer.dynamic_energy_threshold = False

                while self.running:
                    try:
                        audio = self.recognizer.listen(source, timeout=10, phrase_time_limit=15)
                        lang = "ru-RU" if self.parent().current_language == "ru" else "en-US"
                        text = self.recognizer.recognize_google(audio, language=lang)
                        if text:
                            self.transcribed_text.emit(text)
                    except sr.UnknownValueError:
                        pass
                    except sr.WaitTimeoutError:
                        pass
                    except sr.RequestError as e:
                        self.error_occurred.emit(f"Не удалось получить результаты от сервиса Google Speech Recognition; проверьте подключение к интернету: {e}")
                        self.running = False
                    except Exception as e:
                        self.error_occurred.emit(f"Общая ошибка аудио во время обработки: {e}")
                        self.running = False
                    self.msleep(100)

        except Exception as e:
            self.error_occurred.emit(f"Ошибка инициализации микрофона: {e}. Убедитесь, что драйверы аудио корректны и микрофон доступен.")
            self.running = False

    def stop(self):
        self.running = False
        self.wait()



class WorkerThread(QThread):
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, model, prompt_parts):
        super().__init__()
        self.model = model
        self.prompt_parts = prompt_parts

    def run(self):
        try:
            response = self.model.generate_content(self.prompt_parts, stream=False)
            response.resolve()
            self.response_received.emit(response.text)
        except Exception as e:
            self.error_occurred.emit(str(e))


if __name__ == '__main__':
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)

    toggle_panel = TogglePanel()
    main_panel = OverlayPanel(toggle_panel) #


    toggle_panel.show_main_panel_signal.connect(main_panel.show_panel_animated)

    sys.exit(app.exec_())