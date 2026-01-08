# extensions/ai/__init__.py
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea, 
                               QFrame, QSizePolicy, QApplication, QLineEdit,
                               QFormLayout, QPushButton, QMessageBox)
from PySide6.QtCore import Qt, Signal, QThread, Slot

from google import genai
from google.genai import types, errors

from api.extension import Extension
# Import the custom Markdown Engine
from .markdown_engine.widget import ChatCanvas
from .markdown_engine.constants import THEME

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

# --- UI COMPONENTS ---

class ChatView(QWidget):
    def __init__(self, parent_window, extension):
        super().__init__()
        self.parent_window = parent_window
        self.extension = extension
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Setup Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 2. Setup Canvas (The Markdown Engine)
        self.canvas = ChatCanvas()
        self.canvas.paste_requested.connect(self.handle_paste_request)
        self.scroll_area.setWidget(self.canvas)
        
        self.layout.addWidget(self.scroll_area)

        self.history = [] 
        self.is_loading = False
        
        # Check configuration immediately
        if not self.extension.client:
             self.canvas.add_message("⚠️ **API Key not found.**\nPlease configure it in `Settings > AI Chat`.", is_user=False)
        elif not self.extension.has_greeted:
            self.canvas.add_message(f"Hello! I am **{self.extension.model_name}**. How can I help you today?", is_user=False)
            self.extension.has_greeted = True

    def scroll_to_bottom(self):
        """Forces the scroll area to the bottom after layout updates."""
        QApplication.processEvents()
        sb = self.scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def handle_paste_request(self):
        """Redirects paste requests from the canvas to the search input."""
        if hasattr(self.parent_window, 'search_bar'):
            self.parent_window.search_bar.search_input.setFocus()
            self.parent_window.search_bar.search_input.paste()

    def handle_enter(self):
        if self.is_loading: return
        text = self.parent_window.search_bar.search_input.text().strip()
        if not text: return

        # 1. Add User Message
        self.canvas.add_message(text, is_user=True)
        self.parent_window.search_bar.search_input.clear()
        self.scroll_to_bottom()
        
        # 2. Add Temporary "Thinking" Message
        self.canvas.add_message("_Thinking..._", is_user=False)
        self.is_loading = True
        self.scroll_to_bottom()
        
        # 3. Start Worker
        self.worker = GeminiWorker(self.extension.client, self.extension.model_name, self.history, text)
        self.worker.response_ready.connect(self.on_response)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.start()

    def _remove_last_message(self):
        """Helper to remove the 'Thinking...' message."""
        if self.canvas.messages:
            self.canvas.messages.pop()
            self.canvas.recalculate_layout()
            self.canvas.update()

    @Slot(str)
    def on_response(self, text):
        self._remove_last_message()
        self.is_loading = False
        
        self.history.append({'role': 'user', 'text': self.worker.user_input})
        self.history.append({'role': 'model', 'text': text})
        
        self.canvas.add_message(text, is_user=False)
        self.scroll_to_bottom()

    @Slot(str)
    def on_error(self, error_msg):
        self._remove_last_message()
        self.is_loading = False
        
        formatted_error = f"**Error:** {error_msg}"
        self.canvas.add_message(formatted_error, is_user=False)
        self.scroll_to_bottom()

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
        self.description = "Chat with Google Gemini (Markdown Supported)"
        self.has_greeted = False
        self.client = None
        self.model_name = "gemini-2.0-flash"

        # Initialize ID early so we can load settings
        self.id = "ai" 
        # Set Trigger Key (Tab)
        self.trigger_key = Qt.Key_Tab
        
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