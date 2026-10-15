"""
Shopo Robo - Animated Welcome Splash Screen
Displays a friendly, animated Indian Shopo Robo mascot with voice greeting
tailored for Tier-3 retail shopkeepers.
"""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QLinearGradient, QBrush, QPen
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QProgressBar, QWidget
from voice_engine import VoiceEngine

class RoboMascotWidget(QWidget):
    """Custom animated vector rendering of the Indian Shopo Robo mascot."""

    def __init__(self, size=200, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.base_size = 200.0
        self.eye_phase = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_eyes)
        self.timer.start(120)

    def animate_eyes(self):
        self.eye_phase = (self.eye_phase + 1) % 20
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Dynamic scale based on current widget size
        scale_factor = self.width() / self.base_size
        painter.scale(scale_factor, scale_factor)

        # 1. Robot Head (Rounded White & Lime Box)
        head_gradient = QLinearGradient(40, 40, 160, 160)
        head_gradient.setColorAt(0, QColor("#FFFFFF"))
        head_gradient.setColorAt(1, QColor("#F0FDF4"))
        painter.setBrush(QBrush(head_gradient))
        painter.setPen(QPen(QColor("#84CC16"), 4))
        painter.drawRoundedRect(40, 45, 120, 110, 24, 24)

        # 2. Indian Pagdi / Turban Accent on Head
        painter.setBrush(QBrush(QColor("#65A30D")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(35, 35, 130, 22, 10, 10)
        # Gold gem in pagdi center
        painter.setBrush(QBrush(QColor("#F59E0B")))
        painter.drawEllipse(94, 38, 12, 12)

        # 3. Antenna
        painter.setPen(QPen(QColor("#84CC16"), 4))
        painter.drawLine(100, 35, 100, 15)
        # Antenna glowing orb
        glow_color = QColor("#84CC16") if self.eye_phase % 4 < 2 else QColor("#A3E635")
        painter.setBrush(QBrush(glow_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(93, 8, 14, 14)

        # 4. Digital Visor Screen
        painter.setBrush(QBrush(QColor("#0F172A")))
        painter.drawRoundedRect(55, 70, 90, 50, 12, 12)

        # 5. Animated Cyan Glowing Eyes
        eye_h = 14 if self.eye_phase != 10 else 2 # Blink effect at phase 10
        painter.setBrush(QBrush(QColor("#38BDF8")))
        # Left Eye
        painter.drawRoundedRect(68, 85 - (eye_h // 2), 18, eye_h, 4, 4)
        # Right Eye
        painter.drawRoundedRect(114, 85 - (eye_h // 2), 18, eye_h, 4, 4)

        # 6. Friendly Smile
        painter.setPen(QPen(QColor("#84CC16"), 3))
        painter.drawArc(78, 125, 44, 20, 0, -180 * 16)

        # 7. Namaste Badge
        painter.setBrush(QBrush(QColor("#84CC16")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(75, 160, 50, 20, 10, 10)
        painter.setPen(QPen(QColor("#FFFFFF")))
        font = QFont("Arial", 8, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(QRect(75, 160, 50, 20), Qt.AlignmentFlag.AlignCenter, "AI ROBO")

class WelcomeSplashScreen(QDialog):
    """Full-screen friendly welcome splash modal."""
    finished_welcome = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setFixedSize(540, 580)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #FFFFFF, stop:1 #ECFCCB);
                border: 3px solid #84CC16;
                border-radius: 24px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(30, 40, 30, 40)
        layout.setSpacing(15)

        # Mascot Widget
        self.mascot = RoboMascotWidget(self)
        layout.addWidget(self.mascot, alignment=Qt.AlignmentFlag.AlignCenter)

        # Welcome Title
        self.title = QLabel("नमस्ते! मैं हूँ आपका शोपो रोबो")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setStyleSheet("font-size: 24px; font-weight: 800; color: #166534;")
        layout.addWidget(self.title)

        # Subtitle
        self.sub = QLabel("Welcome! I am your Shopo Robo\nआपकी दुकान का स्मार्ट AI साथी")
        self.sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub.setStyleSheet("font-size: 15px; font-weight: 600; color: #4B5563; line-height: 1.4;")
        layout.addWidget(self.sub)

        # Progress Indicator
        self.prog = QProgressBar()
        self.prog.setRange(0, 100)
        self.prog.setValue(0)
        self.prog.setTextVisible(False)
        self.prog.setFixedHeight(8)
        self.prog.setStyleSheet("""
            QProgressBar {
                background-color: #E2E8F0;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #84CC16;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.prog)

        # Skip / Enter Button
        self.btn_enter = QPushButton("दुकान में प्रवेश करें / Start Shop ➔")
        self.btn_enter.setStyleSheet("""
            QPushButton {
                background-color: #84CC16;
                color: #FFFFFF;
                font-size: 16px;
                font-weight: 700;
                padding: 12px 24px;
                border-radius: 12px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #65A30D;
            }
        """)
        self.btn_enter.clicked.connect(self.close_and_finish)
        layout.addWidget(self.btn_enter)

        # Auto-timer for progress
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance_progress)
        self.progress_val = 0
        self.timer.start(40) # ~4 seconds total

        # Play welcome voice
        QTimer.singleShot(400, self.speak_greeting)

    def speak_greeting(self):
        voice = VoiceEngine.get_instance()
        voice.speak("Welcome! I am your Shopo Robo. Namaste! Welcome to your smart AI store assistant.")

    def advance_progress(self):
        self.progress_val += 1
        self.prog.setValue(self.progress_val)
        if self.progress_val >= 100:
            self.timer.stop()
            self.close_and_finish()

    def close_and_finish(self):
        self.timer.stop()
        self.finished_welcome.emit()
        self.accept()
