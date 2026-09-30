import sys
import os
import keyboard
from mss import mss
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, 
    QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea
)
from PyQt6.QtGui import QIcon, QPixmap
from core.ai_engine import GeminiWorker
from core.audio_listener import AudioListenerWorker

ICON_PATH = "icon.png"
SCREENSHOT_PATH = "temp_screenshot.png"

class HotkeySignaler(QObject):
    toggle_chat = pyqtSignal()
    toggle_total_hide = pyqtSignal()

class ClickableDragIcon(QPushButton):
    """Bouton personnalisé gérant Clic, Double-Clic et Drag & Drop."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_start_pos is not None:
            delta = event.globalPosition().toPoint() - self.drag_start_pos
            if delta.manhattanLength() > 5:
                self.parent_window.move(
                    self.parent_window.x() + delta.x(),
                    self.parent_window.y() + delta.y()
                )
                self.drag_start_pos = event.globalPosition().toPoint()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_start_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_window.toggle_total_visibility()
        super().mouseDoubleClickEvent(event)


class FloatingBuddy(QWidget):
    def __init__(self):
        super().__init__()
        self.old_pos = None
        self.worker = None
        self.audio_worker = None
        self.chat_history = []
        self.pending_image = None
        
        self.hotkey_signaler = HotkeySignaler()
        self.hotkey_signaler.toggle_chat.connect(self.toggle_interface_from_hotkey)
        self.hotkey_signaler.toggle_total_hide.connect(self.toggle_total_visibility)

        self.init_ui()
        self.setup_global_hotkeys()

    def init_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 1. Zone de dialogue
        self.speech_bubble = QLabel(
            "Salut ! Je suis <b>Nova</b> ✨.<br>"
            "• <b>Ctrl + Alt</b> : Afficher/Masquer le chat<br>"
            "• <b>Ctrl + Shift</b> : Masquer/Afficher TOUT<br>"
            "• Tape <i>die</i> pour fermer.", self
        )
        self.speech_bubble.setWordWrap(True)
        self.speech_bubble.setStyleSheet("""
            QLabel {
                background-color: rgba(15, 23, 42, 0.95);
                color: #f8fafc;
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 10px;
                padding: 8px 12px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
            }
        """)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidget(self.speech_bubble)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMaximumHeight(180)
        self.scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                border: none;
                background: rgba(30, 41, 59, 0.5);
                width: 4px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: rgba(56, 189, 248, 0.5);
                border-radius: 2px;
            }
        """)
        self.scroll_area.hide()
        main_layout.addWidget(self.scroll_area)

        # 2. Avatar / Icône
        self.avatar_button = ClickableDragIcon(self)
        self.avatar_button.setStyleSheet("background: transparent; border: none; padding: 0;")
        self.avatar_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.avatar_button.setToolTip("Un clic : Chat | Double-clic : Masquer tout")
        self.avatar_button.clicked.connect(self.toggle_interface)

        if os.path.exists(ICON_PATH):
            pixmap = QPixmap(ICON_PATH)
            self.avatar_button.setIcon(QIcon(pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))
            self.avatar_button.setIconSize(QSize(50, 50))
        else:
            self.avatar_button.setText("🤖")
            self.avatar_button.setStyleSheet("font-size: 36px; background: transparent;")

        main_layout.addWidget(self.avatar_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # 3. Barre d'outils compacte
        tools_layout = QHBoxLayout()
        tools_layout.setSpacing(4)
        tools_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_screenshot = QPushButton("📸 Cap", self)
        self.btn_screenshot.setToolTip("Prendre une capture d'écran")
        self.btn_screenshot.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 41, 59, 0.85);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(56, 189, 248, 0.25); }
        """)
        self.btn_screenshot.clicked.connect(self.take_screenshot)
        self.btn_screenshot.hide()

        self.btn_mic = QPushButton("🎙️ Mic", self)
        self.btn_mic.setToolTip("Parler à Nova")
        self.btn_mic.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 41, 59, 0.85);
                color: #22c55e;
                border: 1px solid rgba(34, 197, 94, 0.3);
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(34, 197, 94, 0.25); }
        """)
        self.btn_mic.clicked.connect(self.start_voice_input)
        self.btn_mic.hide()

        self.btn_clear = QPushButton("🧹 Reset", self)
        self.btn_clear.setToolTip("Effacer la mémoire")
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: rgba(30, 41, 59, 0.85);
                color: #f43f5e;
                border: 1px solid rgba(244, 63, 94, 0.3);
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(244, 63, 94, 0.25); }
        """)
        self.btn_clear.clicked.connect(self.clear_memory)
        self.btn_clear.hide()

        tools_layout.addWidget(self.btn_screenshot)
        tools_layout.addWidget(self.btn_mic)
        tools_layout.addWidget(self.btn_clear)
        main_layout.addLayout(tools_layout)

        # 4. Champ de saisie
        self.input_field = QLineEdit(self)
        self.input_field.setPlaceholderText("Pose ta question... (Entrée)")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(30, 41, 59, 0.95);
                color: #ffffff;
                border: 1px solid rgba(56, 189, 248, 0.4);
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 11px;
            }
            QLineEdit:focus { border-color: #38bdf8; }
        """)
        self.input_field.returnPressed.connect(self.handle_user_input)
        self.input_field.hide()
        
        main_layout.addWidget(self.input_field)

        self.setLayout(main_layout)
        self.setFixedWidth(280)

    def setup_global_hotkeys(self):
        try:
            keyboard.add_hotkey("ctrl+alt", lambda: self.hotkey_signaler.toggle_chat.emit(), suppress=False)
            keyboard.add_hotkey("ctrl+shift", lambda: self.hotkey_signaler.toggle_total_hide.emit(), suppress=False)
        except Exception as e:
            print(f"Erreur raccourcis : {e}")

    def toggle_total_visibility(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.scroll_area.show()
            self.input_field.show()
            self.btn_screenshot.show()
            self.btn_mic.show()
            self.btn_clear.show()
            self.input_field.setFocus()
            self.adjustSize()

    def toggle_interface_from_hotkey(self):
        if not self.isVisible():
            self.show()
            self.scroll_area.show()
            self.input_field.show()
            self.btn_screenshot.show()
            self.btn_mic.show()
            self.btn_clear.show()
            self.input_field.setFocus()
        else:
            if self.scroll_area.isVisible() or self.input_field.isVisible():
                self.input_field.hide()
                self.scroll_area.hide()
                self.btn_screenshot.hide()
                self.btn_mic.hide()
                self.btn_clear.hide()
            else:
                self.scroll_area.show()
                self.input_field.show()
                self.btn_screenshot.show()
                self.btn_mic.show()
                self.btn_clear.show()
                self.input_field.setFocus()
        self.adjustSize()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos is not None:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def toggle_interface(self):
        if self.input_field.isVisible() or self.scroll_area.isVisible():
            self.input_field.hide()
            self.scroll_area.hide()
            self.btn_screenshot.hide()
            self.btn_mic.hide()
            self.btn_clear.hide()
        else:
            self.scroll_area.show()
            self.input_field.show()
            self.btn_screenshot.show()
            self.btn_mic.show()
            self.btn_clear.show()
            self.input_field.setFocus()
        self.adjustSize()

    def take_screenshot(self):
        self.hide()
        QApplication.processEvents()

        with mss() as ssc:
            ssc.shot(output=SCREENSHOT_PATH)

        self.pending_image = SCREENSHOT_PATH
        self.show()
        self.scroll_area.show()
        self.speech_bubble.setText("📸 <b>Capture d'écran effectuée !</b> Pose ta question sur l'image.")
        self.input_field.show()
        self.input_field.setFocus()
        self.adjustSize()

    def start_voice_input(self):
        self.speech_bubble.setText("🎙️ <i>Écoute en cours... Parle maintenant !</i>")
        self.scroll_area.show()
        self.adjustSize()
        
        self.audio_worker = AudioListenerWorker()
        self.audio_worker.text_recognized.connect(self.on_voice_recognized)
        self.audio_worker.error_occurred.connect(self.on_voice_error)
        self.audio_worker.start()

    def on_voice_recognized(self, text):
        self.input_field.setText(text)
        self.adjustSize()
        self.handle_user_input()

    def on_voice_error(self, error_msg):
        self.speech_bubble.setText(f"⚠️ <span style='color: #ef4444;'>{error_msg}</span>")
        self.scroll_area.show()
        self.adjustSize()

    def clear_memory(self):
        self.chat_history.clear()
        self.speech_bubble.setText("🧹 <i>Mémoire effacée. Nouvelle conversation.</i>")
        self.input_field.setFocus()

    def handle_user_input(self):
        user_text = self.input_field.text().strip()
        if not user_text:
            return

        if user_text.lower() in ["die", "exit", "quit"]:
            QApplication.quit()
            return

        self.chat_history.append({"role": "Utilisateur", "content": user_text})

        status_msg = f"<b>Vous :</b> {user_text}<br><br>⚡ <i>Nova réfléchit...</i>"
        if self.pending_image:
            status_msg = f"🖼️ <i>[Image jointe]</i><br>" + status_msg

        self.speech_bubble.setText(status_msg)
        self.input_field.clear()
        self.adjustSize()

        image_to_send = self.pending_image
        self.pending_image = None

        self.worker = GeminiWorker(user_text, self.chat_history, image_to_send)
        self.worker.response_received.connect(self.on_ai_response)
        self.worker.error_occurred.connect(self.on_ai_error)
        self.worker.start()

    def on_ai_response(self, text):
        self.chat_history.append({"role": "Nova", "content": text})
        self.speech_bubble.setText(f"<b>Nova :</b><br>{text}")
        self.scroll_area.show()
        self.input_field.show()
        self.input_field.setFocus()
        self.adjustSize()

    def on_ai_error(self, error_msg):
        self.speech_bubble.setText(f"⚠️ <span style='color: #ef4444;'>{error_msg}</span>")
        self.scroll_area.show()
        self.input_field.show()
        self.input_field.setFocus()
        self.adjustSize()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    buddy = FloatingBuddy()
    buddy.show()
    sys.exit(app.exec())