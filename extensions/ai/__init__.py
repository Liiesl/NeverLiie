# extensions/ai/__init__.py
import os
import markdown
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, 
                               QFrame, QSizePolicy, QApplication, QLineEdit,
                               QFormLayout, QPushButton, QMessageBox)
from PySide6.QtCore import Qt, Signal, QThread, Slot
from PySide6.QtGui import QFont

from google import genai
from google.genai import types, errors

from api.extension import Extension

# --- THEME (Reused) ---
THEME = {
    "user_bg": "#45475a",
    "ai_bg": "#313244",
    "text": "#cdd6f4",
    "accent": "#89b4fa",
    "error": "#f38ba8"
}

# --- WORKER THREAD ---
class GeminiWorker(QThread):
    response_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, client, model_name, history, user_input):
        super().__init__()
        self.client = client
        self.model_name = model_name
        self.history = history 
        self.user_input = user_input

    def run(self):
        if not self.client:
            self.error_occurred.emit("API Key not configured. Please go to Settings > AI Chat.")
            return

        try:
            contents = []
            for msg in self.history:
                role = 'model' if msg['role'] == 'model' else 'user'
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=msg['text'])]
                ))

            contents.append(types.Content(
                role='user',
                parts=[types.Part.from_text(text=self.user_input)]
            ))

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(temperature=0.7)
            )
            
            if response.text:
                self.response_ready.emit(response.text)
            else:
                self.error_occurred.emit("No text returned from API.")

        except errors.APIError as e:
            self.error_occurred.emit(f"API Error: {e.message}")
        except Exception as e:
            self.error_occurred.emit(f"System Error: {str(e)}")

# --- UI COMPONENTS (ChatBubble, ChatView) ---
class ChatBubble(QFrame):
    def __init__(self, text, is_user=False, is_error=False):
        super().__init__()
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        
        layout = QVBoxLayout(self)
        if is_user:
            layout.setContentsMargins(60, 5, 10, 5)
            align = Qt.AlignRight
            bg_color = THEME["user_bg"]
        else:
            layout.setContentsMargins(10, 5, 60, 5)
            align = Qt.AlignLeft
            bg_color = THEME["error"] if is_error else THEME["ai_bg"]

        self.bubble = QLabel()
        self.bubble.setWordWrap(True)
        self.bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.bubble.setOpenExternalLinks(True)
        
        if not is_user and not is_error:
            try:
                html = markdown.markdown(text, extensions=['fenced_code', 'nl2br'])
                style = f"""<style>p, li {{ color: {THEME['text']}; font-family: 'Segoe UI'; font-size: 14px; margin: 0; }} code {{ background: #1e1e2e; padding: 2px 4px; }} pre {{ background: #1e1e2e; padding: 10px; }} a {{ color: {THEME['accent']}; }}</style>"""
                self.bubble.setText(style + html)
                self.bubble.setTextFormat(Qt.RichText)
            except:
                self.bubble.setText(text)
        else:
            self.bubble.setText(text)
            self.bubble.setFont(QFont("Segoe UI", 11))

        self.bubble.setStyleSheet(f"QLabel {{ background-color: {bg_color}; color: {THEME['text']}; border-radius: 12px; padding: 12px 16px; }}")
        layout.addWidget(self.bubble, 0, align)

class ChatView(QWidget):
    def __init__(self, parent_window, extension):
        super().__init__()
        self.parent_window = parent_window
        self.extension = extension
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.scroll_content)
        self.content_layout.setContentsMargins(10, 10, 10, 10)
        self.content_layout.addStretch() 
        self.scroll_area.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll_area)

        self.history = [] 
        self.is_loading = False
        self.loading_bubble = None
        
        # Check configuration immediately
        if not self.extension.client:
             self.add_bubble("⚠️ API Key not found. Please configure it in Settings > AI Chat.", is_error=True)
        elif not self.extension.has_greeted:
            self.add_bubble(f"Hello! I am {self.extension.model_name}. How can I help you?", is_user=False)
            self.extension.has_greeted = True

    def add_bubble(self, text, is_user=False, is_error=False):
        bubble = ChatBubble(text, is_user, is_error)
        self.content_layout.insertWidget(self.content_layout.count() - 1, bubble)
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        QApplication.processEvents()
        sb = self.scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def handle_enter(self):
        if self.is_loading: return
        text = self.parent_window.search_bar.search_input.text().strip()
        if not text: return

        self.add_bubble(text, is_user=True)
        self.parent_window.search_bar.search_input.clear()
        
        self.add_bubble("Thinking...", is_user=False)
        self.loading_bubble = self.content_layout.itemAt(self.content_layout.count() - 2).widget()
        self.is_loading = True
        
        # Pass current client and model from extension (in case they changed)
        self.worker = GeminiWorker(self.extension.client, self.extension.model_name, self.history, text)
        self.worker.response_ready.connect(self.on_response)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()

    @Slot(str)
    def on_response(self, text):
        self._cleanup_loading()
        self.history.append({'role': 'user', 'text': self.worker.user_input})
        self.history.append({'role': 'model', 'text': text})
        self.add_bubble(text, is_user=False)

    @Slot(str)
    def on_error(self, error_msg):
        self._cleanup_loading()
        self.add_bubble(f"Error: {error_msg}", is_error=True)

    def _cleanup_loading(self):
        self.is_loading = False
        if self.loading_bubble:
            try: self.loading_bubble.deleteLater()
            except: pass
            self.loading_bubble = None

    def filter_items(self, text): pass
    def handle_key(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.handle_enter()

# --- SETTINGS WIDGET ---
class AISettingsWidget(QWidget):
    def __init__(self, extension):
        super().__init__()
        self.extension = extension
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # API Key Field
        self.api_input = QLineEdit()
        self.api_input.setEchoMode(QLineEdit.Password)
        self.api_input.setPlaceholderText("Enter Google Gemini API Key")
        self.api_input.setText(self.extension.get_setting("api_key", ""))
        
        # Model Field
        self.model_input = QLineEdit()
        self.model_input.setText(self.extension.get_setting("model_name", "gemini-2.0-flash"))
        self.model_input.setPlaceholderText("e.g. gemini-1.5-flash")
        
        lbl_api = QLabel("API Key:")
        lbl_api.setStyleSheet(f"color: {THEME['text']};")
        lbl_model = QLabel("Model Name:")
        lbl_model.setStyleSheet(f"color: {THEME['text']};")
        
        form_layout.addRow(lbl_api, self.api_input)
        form_layout.addRow(lbl_model, self.model_input)
        
        layout.addLayout(form_layout)
        
        # Save Button
        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setFixedHeight(35)
        self.btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {THEME['accent']};
                color: {THEME['ai_bg']};
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #b4befe; }}
        """)
        self.btn_save.clicked.connect(self.save_settings)
        
        layout.addWidget(self.btn_save)
        layout.addStretch()

    def save_settings(self):
        api_key = self.api_input.text().strip()
        model_name = self.model_input.text().strip()
        
        self.extension.set_setting("api_key", api_key)
        self.extension.set_setting("model_name", model_name)
        
        # Re-initialize the client in the extension
        self.extension.reload_client()
        
        # Feedback
        btn_text = self.btn_save.text()
        self.btn_save.setText("Saved!")
        QApplication.processEvents()
        QThread.msleep(500)
        self.btn_save.setText(btn_text)

# --- MAIN EXTENSION ---
class AIExtension(Extension):
    def __init__(self, core_app):
        super().__init__(core_app)
        self.name = "AI Chat"
        self.description = "Chat with Google Gemini"
        self.has_greeted = False
        self.client = None
        self.model_name = "gemini-2.0-flash"

        # Initialize ID early so we can load settings
        self.id = "ai" 
        
    def get_extension_view(self, parent_window):
        # Ensure client is loaded (in case it wasn't at startup)
        if not self.client:
            self.reload_client()
        return ChatView(parent_window, self)

    def get_settings_widget(self):
        return AISettingsWidget(self)

    def reload_client(self):
        api_key = self.get_setting("api_key")
        self.model_name = self.get_setting("model_name", "gemini-2.0-flash")
        
        if api_key:
            try:
                self.client = genai.Client(api_key=api_key)
                print("[AI Extension] Client loaded successfully.")
            except Exception as e:
                print(f"[AI Extension] Init Error: {e}")
                self.client = None
        else:
            self.client = None

    def on_input(self, text):
        return []

Extension = AIExtension