"""
Shopo Robo - Real-time Webcam Barcode & QR Code Scanner Widget
Uses OpenCV's native BarcodeDetector and QRCodeDetector with a high-visibility
lime green reticle for Tier-3 shopkeeper ease of use.
"""

import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QMessageBox
)

KNOWN_FMCG_CATALOG = {
    "8901058852393": {
        "name": "Maggi 2-Minute Masala Noodles (70g)",
        "category": "Snacks & Instant",
        "buy_price": 12.0,
        "sell_price": 14.0,
        "unit": "packet",
        "expiry": "2026-12",
        "mrp": 14.0
    },
    "8901719101038": {
        "name": "Parle-G Gold Biscuits (100g)",
        "category": "Snacks & Instant",
        "buy_price": 8.5,
        "sell_price": 10.0,
        "unit": "packet",
        "expiry": "2026-10",
        "mrp": 10.0
    },
    "8904043901005": {
        "name": "Tata Salt Vacuum Evaporated (1kg)",
        "category": "Groceries",
        "buy_price": 22.0,
        "sell_price": 28.0,
        "unit": "packet",
        "expiry": "2027-10",
        "mrp": 28.0
    },
    "8901262010054": {
        "name": "Amul Butter Pasteurized (100g)",
        "category": "Dairy",
        "buy_price": 50.0,
        "sell_price": 58.0,
        "unit": "packet",
        "expiry": "2026-12",
        "mrp": 58.0
    },
    "8901396388419": {
        "name": "Dettol Original Soap (75g)",
        "category": "Personal Care",
        "buy_price": 32.0,
        "sell_price": 40.0,
        "unit": "pcs",
        "expiry": "2028-01",
        "mrp": 40.0
    },
    "8906007281023": {
        "name": "Fortune Kachi Ghani Mustard Oil (1L)",
        "category": "Edible Oils",
        "buy_price": 132.0,
        "sell_price": 150.0,
        "unit": "litre",
        "expiry": "2027-02",
        "mrp": 155.0
    }
}

class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    barcode_detected_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._run_flag = True
        self.last_scanned = ""
        self.cooldown = 0
        self.barcode_detector = cv2.barcode.BarcodeDetector()
        self.qr_detector = cv2.QRCodeDetector()

    def run(self):
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)

        while self._run_flag:
            ret, frame = cap.read()
            if ret:
                h, w, _ = frame.shape
                # Draw high-tech lime green scanning reticle in center
                box_w, box_h = int(w * 0.6), int(h * 0.45)
                x1 = (w - box_w) // 2
                y1 = (h - box_h) // 2
                x2, y2 = x1 + box_w, y1 + box_h

                # Scan barcode within frame
                detected_code = ""
                try:
                    res, decoded_type, points = self.barcode_detector.detectAndDecode(frame)
                    if res and len(res.strip()) > 3:
                        detected_code = res.strip()
                except Exception:
                    pass

                # If no barcode, check for QR code
                if not detected_code:
                    try:
                        qr_res, qr_pts, _ = self.qr_detector.detectAndDecode(frame)
                        if qr_res and len(qr_res.strip()) > 3:
                            detected_code = qr_res.strip()
                    except Exception:
                        pass

                # Handle cooldown to prevent duplicate triggers
                if self.cooldown > 0:
                    self.cooldown -= 1

                # Visual Feedback: Green box if scanning, Bright Yellow if locked
                box_color = (0, 255, 0) if not detected_code else (0, 255, 255)
                thickness = 2 if not detected_code else 4
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, thickness)
                cv2.putText(
                    frame,
                    "ALIGN BARCODE IN GREEN BOX" if not detected_code else f"SCANNED: {detected_code}",
                    (x1 + 10, y1 - 15),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    box_color,
                    2
                )

                if detected_code and self.cooldown == 0:
                    self.cooldown = 40 # ~2 seconds at 20fps
                    self.barcode_detected_signal.emit(detected_code)

                self.change_pixmap_signal.emit(frame)
            else:
                self.msleep(30)

        cap.release()

    def stop(self):
        self._run_flag = False
        self.wait()

class BarcodeScannerWidget(QWidget):
    product_scanned_signal = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.thread = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        header = QLabel("📷 Live Barcode & QR Scanner")
        header.setStyleSheet("font-size: 18px; font-weight: 700; color: #166534;")
        layout.addWidget(header)

        instruction = QLabel("Hold item's barcode in front of the camera. The app will auto-fill stock data.")
        instruction.setStyleSheet("font-size: 13px; color: #4B5563;")
        layout.addWidget(instruction)

        # Video Display Frame
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: #0F172A; border-radius: 12px; border: 3px solid #84CC16;")
        self.video_label.setMinimumSize(640, 420)
        layout.addWidget(self.video_label)

        # Scanned result card
        self.result_card = QFrame()
        self.result_card.setStyleSheet("background-color: #ECFCCB; border: 1px solid #84CC16; border-radius: 8px; padding: 10px;")
        res_layout = QHBoxLayout(self.result_card)

        self.result_text = QLabel("Awaiting barcode scan...")
        self.result_text.setStyleSheet("font-size: 14px; font-weight: 600; color: #365314;")
        res_layout.addWidget(self.result_text)

        layout.addWidget(self.result_card)

        # Controls
        ctrl_layout = QHBoxLayout()
        self.btn_toggle = QPushButton("▶️ Start Camera")
        self.btn_toggle.setStyleSheet("""
            QPushButton {
                background-color: #84CC16;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 700;
                padding: 10px 20px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #65A30D;
            }
        """)
        self.btn_toggle.clicked.connect(self.toggle_camera)
        ctrl_layout.addWidget(self.btn_toggle)

        # Manual barcode simulation button (great for quick testing!)
        self.btn_test = QPushButton("⚡ Simulate Maggi Scan")
        self.btn_test.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #334155;
                font-size: 13px;
                font-weight: 600;
                padding: 10px 16px;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
            }
        """)
        self.btn_test.clicked.connect(lambda: self.on_barcode_scanned("8901058852393"))
        ctrl_layout.addWidget(self.btn_test)

        self.btn_test2 = QPushButton("⚡ Simulate Tata Salt Scan")
        self.btn_test2.setStyleSheet("""
            QPushButton {
                background-color: #F1F5F9;
                color: #334155;
                font-size: 13px;
                font-weight: 600;
                padding: 10px 16px;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #E2E8F0;
            }
        """)
        self.btn_test2.clicked.connect(lambda: self.on_barcode_scanned("8904043901005"))
        ctrl_layout.addWidget(self.btn_test2)

        layout.addLayout(ctrl_layout)

    def toggle_camera(self):
        if self.thread and self.thread.isRunning():
            self.stop_camera()
        else:
            self.start_camera()

    def start_camera(self):
        self.thread = VideoThread()
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.barcode_detected_signal.connect(self.on_barcode_scanned)
        self.thread.start()
        self.btn_toggle.setText("⏹️ Stop Camera")
        self.btn_toggle.setStyleSheet("background-color: #EF4444; color: white; padding: 10px 20px; font-weight: 700; border-radius: 8px;")

    def stop_camera(self):
        if self.thread:
            self.thread.stop()
            self.thread = None
        self.video_label.clear()
        self.video_label.setText("Camera is Off")
        self.video_label.setStyleSheet("background-color: #0F172A; color: #94A3B8; font-size: 16px; border-radius: 12px;")
        self.btn_toggle.setText("▶️ Start Camera")
        self.btn_toggle.setStyleSheet("background-color: #84CC16; color: white; padding: 10px 20px; font-weight: 700; border-radius: 8px;")

    def update_image(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        p = convert_to_Qt_format.scaled(640, 420, Qt.AspectRatioMode.KeepAspectRatio)
        self.video_label.setPixmap(QPixmap.fromImage(p))

    def on_barcode_scanned(self, barcode: str):
        item_info = KNOWN_FMCG_CATALOG.get(barcode, {
            "name": f"Item (Barcode {barcode})",
            "category": "Groceries",
            "buy_price": 20.0,
            "sell_price": 25.0,
            "unit": "pcs",
            "expiry": "2027-01",
            "barcode": barcode
        })
        item_info["barcode"] = barcode
        self.result_text.setText(f"✅ Scanned: {item_info['name']} | Barcode: {barcode}")
        self.product_scanned_signal.emit(item_info)

    def closeEvent(self, event):
        self.stop_camera()
        event.accept()
