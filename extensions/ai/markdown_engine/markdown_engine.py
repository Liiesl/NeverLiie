# markdown_engine/main.py
# Prototype window for testing markdown rendering
# Keeped as a standalone file for easier debugging
import sys
import os
import time
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLineEdit, 
                               QScrollArea, QFrame, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from constants import THEME
from widget import ChatCanvas
from benchmark import enable_global_benchmark, get_global_benchmark

class PrototypeWindow(QWidget):
    def __init__(self):
        # disable global benchmark
        # global_bench = enable_global_benchmark()
        # global_bench.start_time = time.perf_counter()
        
        ## Clear previous benchmark file
        # if os.path.exists("bench.txt"):
        #    os.remove("bench.txt")
        
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(800, 900)
        
        # Process events to ensure window shows before heavy operations
        QApplication.processEvents()

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        
        self.container = QFrame()
        self.container.setStyleSheet(f"QFrame {{ background-color: {THEME['bg']}; border: 1px solid {THEME['border']}; border-radius: 12px; }}")
        self.layout.addWidget(self.container)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0,0,0, 100))
        self.container.setGraphicsEffect(shadow)

        self.inner_layout = QVBoxLayout(self.container)
        self.inner_layout.setContentsMargins(0, 0, 0, 0)
        self.inner_layout.setSpacing(0)

        # Header
        self.header = QFrame()
        self.header.setFixedHeight(60)
        self.header.setStyleSheet("background: transparent; border-bottom: 1px solid #45475a;")
        header_layout = QVBoxLayout(self.header)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type a message to append...")
        self.search_input.setStyleSheet(f"QLineEdit {{ color: {THEME['text']}; font-size: 16px; border: none; background: transparent; selection-background-color: {THEME['accent']}; selection-color: #232324; }}")
        self.search_input.returnPressed.connect(self.handle_input)
        header_layout.addWidget(self.search_input)
        
        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff) 
        
        self.canvas = ChatCanvas()
        self.canvas.paste_requested.connect(self.handle_canvas_paste)
        self.scroll.setWidget(self.canvas)
        
        self.inner_layout.addWidget(self.header)
        self.inner_layout.addWidget(self.scroll)

        self.old_pos = None

        self.load_markdown_file("response.md")

    def load_markdown_file(self, filename):
        bench = get_global_benchmark()
        if bench:
            timer = bench.child("File I/O")
            timer.start_time = time.perf_counter()
        
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()
                if bench:
                    timer.end_time = time.perf_counter()
                    timer.total_time = (timer.end_time - timer.start_time) * 1000
                    timer.count = 1
                    if timer.parent:
                        timer.parent.children["File I/O"].append(timer)
                self.canvas.add_message(content, is_user=False)
        else:
            if bench:
                timer.end_time = time.perf_counter()
                timer.total_time = (timer.end_time - timer.start_time) * 1000
                timer.count = 1
                if timer.parent:
                    timer.parent.children["File I/O"].append(timer)
            self.canvas.add_message(f"Error: Could not find '{filename}'", is_user=False)

    def handle_input(self):
        text = self.search_input.text()
        if not text: return
        self.search_input.clear()
        self.canvas.add_message(text, is_user=True)
        
        QScrollArea.verticalScrollBar(self.scroll).setValue(
            QScrollArea.verticalScrollBar(self.scroll).maximum() + 200
        )

    def handle_canvas_paste(self):
        self.search_input.setFocus()
        self.search_input.paste()

    def mousePressEvent(self, event):
        local_pos = event.position().toPoint()
        if self.header.geometry().contains(local_pos):
            self.old_pos = event.globalPosition().toPoint()
        else:
            self.old_pos = None

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None
    
    def closeEvent(self, event):
        # bench = get_global_benchmark()
        # if bench:
        #     bench.end_time = time.perf_counter()
        #     bench.total_time = (bench.end_time - bench.start_time) * 1000
        #     print("\n" + "=" * 60)
        #     print("PERFORMANCE BENCHMARK")
        #     print("=" * 60)
        #     bench.print_summary()
        #     print("=" * 60)
        #     print(f"Total Window Time: {bench.total_time:.2f}ms")
        #     print("=" * 60)
        #     print(f"Raw data saved to: bench.txt")
        #     print("=" * 60 + "\n")
            
        #     # Write raw data to file
        #     bench.log_raw_data("bench.txt")
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PrototypeWindow()
    window.show()
    sys.exit(app.exec())