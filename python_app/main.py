"""
Shopo Robo - AI Powered Inventory & Store Companion Desktop Application
Designed for Tier-3 Retail Shopkeepers with high contrast Lime Green & White Theme,
Bilingual Voice AI, Live Barcode Scanner, Mandi Trends, and EBITDA Financial Calculator.
"""

import sys
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QColor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QScrollArea, QGridLayout,
    QLineEdit, QComboBox, QFrame, QMessageBox, QDialog, QFormLayout,
    QSpinBox, QDoubleSpinBox, QSlider, QSizePolicy
)

from inventory_manager import InventoryManager
from ai_agent import ShopoRoboAgent
from voice_engine import VoiceEngine
from market_indices import get_market_categories, get_indices_for_category, get_all_market_trends_summary
from finance_calc import calculate_financials
from barcode_scanner import BarcodeScannerWidget
from languages import LANGUAGES, DEFAULT_LANG, get_text
from splash_screen import WelcomeSplashScreen, RoboMascotWidget

class ProductCard(QFrame):
    """Mobile-style clean product card optimized for easy readability."""
    stock_changed_signal = pyqtSignal()

    def __init__(self, item: dict, parent=None):
        super().__init__(parent)
        self.item = item
        self.inv_mgr = InventoryManager.get_instance()
        self.init_ui()

    def init_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            ProductCard {
                background-color: #FFFFFF;
                border: 2px solid #E2E8F0;
                border-radius: 14px;
                padding: 12px;
            }
            ProductCard:hover {
                border: 2px solid #84CC16;
                background-color: #F8FAFC;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Header: Name + Status Badge
        top_row = QHBoxLayout()
        name_lbl = QLabel(self.item.get("name", "Product"))
        name_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #0F172A;")
        top_row.addWidget(name_lbl)

        status = self.item.get("status", "Optimal")
        status_lbl = QLabel(status)
        if status == "Optimal":
            status_lbl.setStyleSheet("background-color: #DCFCE7; color: #166534; font-size: 11px; font-weight: 700; padding: 4px 8px; border-radius: 6px;")
        elif status == "Low Stock":
            status_lbl.setStyleSheet("background-color: #FEF3C7; color: #B45309; font-size: 11px; font-weight: 700; padding: 4px 8px; border-radius: 6px;")
        else: # Loss Making / Out of Stock
            status_lbl.setStyleSheet("background-color: #FEE2E2; color: #991B1B; font-size: 11px; font-weight: 700; padding: 4px 8px; border-radius: 6px;")
        
        top_row.addWidget(status_lbl)
        layout.addLayout(top_row)

        # Category pill
        cat_lbl = QLabel(f"📂 {self.item.get('category', 'General')}")
        cat_lbl.setStyleSheet("font-size: 12px; color: #64748B; font-weight: 600;")
        layout.addWidget(cat_lbl)

        # Stock + Expiry Row
        info_row = QHBoxLayout()
        stock_val = self.item.get("stock", 0)
        unit = self.item.get("unit", "kg")
        stock_lbl = QLabel(f"📦 <b>{stock_val} {unit}</b> in stock")
        stock_lbl.setStyleSheet("font-size: 13px; color: #334155;")
        info_row.addWidget(stock_lbl)

        exp_lbl = QLabel(f"⏳ Exp: {self.item.get('expiry', 'N/A')}")
        exp_lbl.setStyleSheet("font-size: 12px; color: #64748B;")
        info_row.addWidget(exp_lbl)
        layout.addLayout(info_row)

        # Pricing Row: Buy Price vs Sell Price
        buy_p = self.item.get("buy_price", 0)
        sell_p = self.item.get("sell_price", 0)
        price_row = QHBoxLayout()
        price_row.addWidget(QLabel(f"Buy: <b style='color:#64748B;'>₹{buy_p:.1f}</b>"))
        price_row.addWidget(QLabel(f"Sell: <b style='color:#166534;'>₹{sell_p:.1f}</b>"))
        layout.addLayout(price_row)

        # Profit Banner
        profit_unit = sell_p - buy_p
        margin_pct = (profit_unit / sell_p * 100) if sell_p > 0 else 0
        profit_card = QFrame()
        if profit_unit >= 0:
            profit_card.setStyleSheet("background-color: #ECFCCB; border-radius: 6px; padding: 6px;")
            p_text = f"💰 Profit: <b>+₹{profit_unit:.1f}/{unit}</b> (+{margin_pct:.0f}% margin)"
            p_style = "color: #365314; font-size: 12px; font-weight: 600;"
        else:
            profit_card.setStyleSheet("background-color: #FEE2E2; border-radius: 6px; padding: 6px;")
            p_text = f"⚠️ Loss: <b>-₹{abs(profit_unit):.1f}/{unit}</b> ({margin_pct:.0f}%)"
            p_style = "color: #991B1B; font-size: 12px; font-weight: 600;"
        
        p_layout = QHBoxLayout(profit_card)
        p_layout.setContentsMargins(4, 4, 4, 4)
        p_lbl = QLabel(p_text)
        p_lbl.setStyleSheet(p_style)
        p_layout.addWidget(p_lbl)
        layout.addWidget(profit_card)

        # Quick Actions: +10 / -10 Stock Buttons
        btn_row = QHBoxLayout()
        btn_minus = QPushButton(f"- 5 {unit}")
        btn_minus.setStyleSheet("background-color: #F1F5F9; color: #475569; font-weight: 700; border-radius: 6px; padding: 6px;")
        btn_minus.clicked.connect(self.decrement_stock)
        btn_row.addWidget(btn_minus)

        btn_plus = QPushButton(f"+ 10 {unit}")
        btn_plus.setStyleSheet("background-color: #84CC16; color: #FFFFFF; font-weight: 700; border-radius: 6px; padding: 6px;")
        btn_plus.clicked.connect(self.increment_stock)
        btn_row.addWidget(btn_plus)

        layout.addLayout(btn_row)

    def increment_stock(self):
        self.item["stock"] = float(self.item.get("stock", 0)) + 10
        self.inv_mgr.add_or_update_item(self.item)
        self.stock_changed_signal.emit()

    def decrement_stock(self):
        curr = float(self.item.get("stock", 0))
        self.item["stock"] = max(0, curr - 5)
        self.inv_mgr.add_or_update_item(self.item)
        self.stock_changed_signal.emit()

class AddItemDialog(QDialog):
    """Simple dialog to add a new stock item manually or after barcode scan."""
    def __init__(self, initial_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Store Item / नया सामान जोड़ें")
        self.setFixedSize(380, 440)
        self.item_data = initial_data or {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_edit = QLineEdit(self.item_data.get("name", ""))
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(["Groceries", "Spices", "Edible Oils", "Dairy", "Snacks & Instant", "Personal Care"])
        if "category" in self.item_data:
            self.cat_combo.setCurrentText(self.item_data["category"])

        self.stock_spin = QDoubleSpinBox()
        self.stock_spin.setRange(0, 10000)
        self.stock_spin.setValue(self.item_data.get("stock", 50.0))

        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["kg", "packet", "litre", "pcs", "bottle"])
        if "unit" in self.item_data:
            self.unit_combo.setCurrentText(self.item_data["unit"])

        self.buy_spin = QDoubleSpinBox()
        self.buy_spin.setRange(0, 100000)
        self.buy_spin.setValue(self.item_data.get("buy_price", 30.0))

        self.sell_spin = QDoubleSpinBox()
        self.sell_spin.setRange(0, 100000)
        self.sell_spin.setValue(self.item_data.get("sell_price", 40.0))

        self.expiry_edit = QLineEdit(self.item_data.get("expiry", "2027-06"))
        self.barcode_edit = QLineEdit(self.item_data.get("barcode", ""))

        form.addRow("Item Name:", self.name_edit)
        form.addRow("Category:", self.cat_combo)
        form.addRow("Initial Stock:", self.stock_spin)
        form.addRow("Unit:", self.unit_combo)
        form.addRow("Cost Price (Buy):", self.buy_spin)
        form.addRow("Selling Price:", self.sell_spin)
        form.addRow("Expiry Date:", self.expiry_edit)
        form.addRow("Barcode:", self.barcode_edit)

        layout.addLayout(form)

        btn_save = QPushButton("Save Item / सुरक्षित करें")
        btn_save.setStyleSheet("background-color: #84CC16; color: white; font-weight: 700; padding: 10px; border-radius: 8px;")
        btn_save.clicked.connect(self.save_and_close)
        layout.addWidget(btn_save)

    def save_and_close(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Required", "Please enter item name.")
            return
        self.item_data = {
            "name": name,
            "category": self.cat_combo.currentText(),
            "stock": self.stock_spin.value(),
            "unit": self.unit_combo.currentText(),
            "buy_price": self.buy_spin.value(),
            "sell_price": self.sell_spin.value(),
            "expiry": self.expiry_edit.text().strip(),
            "barcode": self.barcode_edit.text().strip()
        }
        self.accept()

class ShopoRoboMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shopo Robo - AI Stock & Store Knowledge Companion")
        self.resize(1180, 800)
        self.current_lang = DEFAULT_LANG
        self.inv_mgr = InventoryManager.get_instance()
        self.agent = ShopoRoboAgent.get_instance()
        self.voice = VoiceEngine.get_instance()

        self.init_ui()
        self.refresh_stats()

    def init_ui(self):
        # Master Style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F8FAFC;
            }
            QTabWidget::pane {
                border: 1px solid #E2E8F0;
                background-color: #FFFFFF;
                border-radius: 12px;
            }
            QTabBar::tab {
                background-color: #F1F5F9;
                color: #475569;
                font-weight: 700;
                font-size: 14px;
                padding: 12px 24px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected {
                background-color: #84CC16;
                color: #FFFFFF;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # 1. Top Header Bar
        header = self.create_header()
        main_layout.addLayout(header)

        # 2. Stats Bar (Cards)
        self.stats_bar = self.create_stats_bar()
        main_layout.addLayout(self.stats_bar)

        # 3. Main Tabs
        self.tabs = QTabWidget()
        self.tab_inventory = self.create_inventory_tab()
        self.tab_voice = self.create_voice_tab()
        self.tab_barcode = self.create_barcode_tab()
        self.tab_market = self.create_market_tab()
        self.tab_calc = self.create_calculator_tab()
        self.tab_settings = self.create_settings_tab()

        self.tabs.addTab(self.tab_inventory, "📦 Stock Menu")
        self.tabs.addTab(self.tab_voice, "🎙️ Jarvis Voice AI")
        self.tabs.addTab(self.tab_barcode, "📷 Barcode Scanner")
        self.tabs.addTab(self.tab_market, "📈 Mandi Trends")
        self.tabs.addTab(self.tab_calc, "🧮 Profit & EBITDA")
        self.tabs.addTab(self.tab_settings, "⚙️ Settings")

        main_layout.addWidget(self.tabs)

    def create_header(self):
        header_layout = QHBoxLayout()

        # Animated Mascot on Left
        self.header_mascot = RoboMascotWidget(size=64, parent=self)
        header_layout.addWidget(self.header_mascot)

        # Brand Title
        brand_col = QVBoxLayout()
        title = QLabel("🛒 Shopo <span style='color:#84CC16;'>Robo</span>")
        title.setTextFormat(Qt.TextFormat.RichText)
        title.setStyleSheet("font-size: 26px; font-weight: 800; color: #0F172A;")
        brand_col.addWidget(title)

        sub = QLabel("Aapki Dukaan. Hamara AI. Smarter Together.")
        sub.setStyleSheet("font-size: 13px; font-weight: 600; color: #64748B;")
        brand_col.addWidget(sub)
        header_layout.addLayout(brand_col)

        header_layout.addStretch()

        # Big Voice Mic Shortcut Button
        self.btn_header_mic = QPushButton("🎙️ Speak to Assistant")
        self.btn_header_mic.setStyleSheet("""
            QPushButton {
                background-color: #84CC16;
                color: #FFFFFF;
                font-size: 15px;
                font-weight: 700;
                padding: 10px 20px;
                border-radius: 20px;
                border: 2px solid #65A30D;
            }
            QPushButton:hover {
                background-color: #65A30D;
            }
        """)
        self.btn_header_mic.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        header_layout.addWidget(self.btn_header_mic)

        # Language Selector
        self.lang_combo = QComboBox()
        for code, ldata in LANGUAGES.items():
            self.lang_combo.addItem(ldata["name"], code)
        self.lang_combo.setStyleSheet("""
            QComboBox {
                padding: 8px 16px;
                border-radius: 8px;
                border: 1px solid #CBD5E1;
                background-color: #FFFFFF;
                font-weight: 600;
            }
        """)
        self.lang_combo.currentIndexChanged.connect(self.on_language_changed)
        header_layout.addWidget(self.lang_combo)

        return header_layout

    def create_stats_bar(self):
        layout = QHBoxLayout()
        layout.setSpacing(12)

        self.stat_items = self.create_stat_card("Total Items", "8", "#0284C7", "📦")
        self.stat_value = self.create_stat_card("Stock Valuation", "₹1,84,500", "#16A34A", "💰")
        self.stat_profit = self.create_stat_card("Monthly Profit", "₹21,560 (+24%)", "#84CC16", "📈")
        self.stat_alerts = self.create_stat_card("Stock Alerts", "1 Low Stock", "#EA580C", "⚠️")

        layout.addWidget(self.stat_items)
        layout.addWidget(self.stat_value)
        layout.addWidget(self.stat_profit)
        layout.addWidget(self.stat_alerts)
        return layout

    def create_stat_card(self, title, val, color, icon):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #FFFFFF;
                border-radius: 12px;
                border-left: 5px solid {color};
                padding: 10px;
            }}
        """)
        c_layout = QHBoxLayout(card)
        c_layout.setContentsMargins(10, 6, 10, 6)

        v_box = QVBoxLayout()
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 12px; color: #64748B; font-weight: 600;")
        val_lbl = QLabel(val)
        val_lbl.setObjectName("val_lbl")
        val_lbl.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {color};")
        v_box.addWidget(t_lbl)
        v_box.addWidget(val_lbl)
        c_layout.addLayout(v_box)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 24px;")
        c_layout.addWidget(icon_lbl)
        return card

    def refresh_stats(self):
        stats = self.inv_mgr.get_stats()
        # Update values
        self.stat_items.findChild(QLabel, "val_lbl").setText(str(stats["total_items"]))
        self.stat_value.findChild(QLabel, "val_lbl").setText(f"₹{stats['total_stock_value']:,.0f}")
        self.stat_profit.findChild(QLabel, "val_lbl").setText(f"₹{stats['potential_profit']:,.0f}")
        alert_str = f"{stats['low_stock_count']} Low Stock"
        if stats["loss_items_count"] > 0:
            alert_str += f" | {stats['loss_items_count']} Loss"
        self.stat_alerts.findChild(QLabel, "val_lbl").setText(alert_str)

    # ── TAB 1: INVENTORY MENU ────────────────────────────────────────────────
    def create_inventory_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Filter bar
        filter_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍 Search products, commodities or barcode...")
        self.search_edit.setStyleSheet("padding: 10px 14px; border: 1px solid #CBD5E1; border-radius: 8px; font-size: 14px;")
        self.search_edit.textChanged.connect(self.refresh_inventory_grid)
        filter_row.addWidget(self.search_edit)

        self.cat_filter = QComboBox()
        self.cat_filter.addItems(self.inv_mgr.get_categories())
        self.cat_filter.setStyleSheet("padding: 8px 14px; border: 1px solid #CBD5E1; border-radius: 8px; font-weight: 600;")
        self.cat_filter.currentTextChanged.connect(self.refresh_inventory_grid)
        filter_row.addWidget(self.cat_filter)

        btn_add = QPushButton("+ Add Product / सामान जोड़ें")
        btn_add.setStyleSheet("background-color: #84CC16; color: white; font-weight: 700; padding: 10px 18px; border-radius: 8px;")
        btn_add.clicked.connect(self.open_add_product_dialog)
        filter_row.addWidget(btn_add)
        layout.addLayout(filter_row)

        # Scroll area for cards
        self.inv_scroll = QScrollArea()
        self.inv_scroll.setWidgetResizable(True)
        self.inv_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self.cards_container = QWidget()
        self.cards_grid = QGridLayout(self.cards_container)
        self.cards_grid.setSpacing(12)
        self.inv_scroll.setWidget(self.cards_container)
        layout.addWidget(self.inv_scroll)

        self.refresh_inventory_grid()
        return tab

    def refresh_inventory_grid(self):
        # Clear existing cards
        while self.cards_grid.count():
            item = self.cards_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        search = self.search_edit.text()
        category = self.cat_filter.currentText()
        items = self.inv_mgr.get_items(category, search)

        col_count = 3
        for idx, itm in enumerate(items):
            card = ProductCard(itm)
            card.stock_changed_signal.connect(self.on_stock_card_updated)
            row = idx // col_count
            col = idx % col_count
            self.cards_grid.addWidget(card, row, col)

        self.refresh_stats()

    def on_stock_card_updated(self):
        self.refresh_stats()
        self.refresh_inventory_grid()

    def open_add_product_dialog(self, initial_data=None):
        dlg = AddItemDialog(initial_data, self)
        if dlg.exec():
            self.inv_mgr.add_or_update_item(dlg.item_data)
            self.refresh_inventory_grid()
            self.voice.speak(f"Added {dlg.item_data['name']} to stock catalog.")

    # ── TAB 2: JARVIS VOICE AI ───────────────────────────────────────────────
    def create_voice_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Voice Header
        v_title = QLabel("🎙️ Shopo Robo AI Assistant")
        v_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #166534;")
        layout.addWidget(v_title)

        # Chat Bubble History
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setStyleSheet("background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px;")
        
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setSpacing(8)
        self.chat_layout.addStretch()
        self.chat_scroll.setWidget(self.chat_widget)
        layout.addWidget(self.chat_scroll)

        # 1-Click Quick Voice Commands (Tier-3 shopkeeper convenience)
        quick_lbl = QLabel("⚡ Quick Voice Commands / एक-क्लिक बोलें:")
        quick_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #475569;")
        layout.addWidget(quick_lbl)

        quick_box = QHBoxLayout()
        presets = [
            ("Sugar is 100kg available", "Sugar is 100kg available in shop"),
            ("Rice stock is ending", "Rice stock is going to end"),
            ("What is monthly profit?", "What is the profit this month?"),
            ("Which item is in loss?", "Which item is in loss?"),
            ("Show Mandi Rates", "What are the market price changes?")
        ]
        for btn_txt, cmd in presets:
            btn = QPushButton(btn_txt)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ECFCCB;
                    color: #365314;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 6px 12px;
                    border-radius: 6px;
                    border: 1px solid #84CC16;
                }
                QPushButton:hover {
                    background-color: #D9F99D;
                }
            """)
            btn.clicked.connect(lambda checked, c=cmd: self.send_agent_command(c))
            quick_box.addWidget(btn)
        layout.addLayout(quick_box)

        # Command Input Field & Mic Button
        input_row = QHBoxLayout()
        self.mic_input = QLineEdit()
        self.mic_input.setPlaceholderText("Type command or click Speak (e.g., '100 kg sugar buy 34 sell 42')...")
        self.mic_input.setStyleSheet("padding: 12px; font-size: 14px; border: 1px solid #CBD5E1; border-radius: 8px;")
        self.mic_input.returnPressed.connect(self.on_mic_input_submitted)
        input_row.addWidget(self.mic_input)

        btn_send = QPushButton("Send ➔")
        btn_send.setStyleSheet("background-color: #84CC16; color: white; font-weight: 700; padding: 12px 20px; border-radius: 8px;")
        btn_send.clicked.connect(self.on_mic_input_submitted)
        input_row.addWidget(btn_send)

        self.btn_listen = QPushButton("🎙️ Speak Now")
        self.btn_listen.setStyleSheet("background-color: #166534; color: white; font-weight: 700; padding: 12px 20px; border-radius: 8px;")
        self.btn_listen.clicked.connect(self.trigger_voice_simulation)
        input_row.addWidget(self.btn_listen)

        layout.addLayout(input_row)

        # Initial Greeting
        self.add_chat_bubble("Shopo Robo", "नमस्ते! मैं आपका शोपो रोबो हूँ। आप दुकान का स्टॉक, मुनाफा या मंडी भाव मुझसे पूछ सकते हैं।", False)

        return tab

    def on_mic_input_submitted(self):
        text = self.mic_input.text().strip()
        if text:
            self.mic_input.clear()
            self.send_agent_command(text)

    def trigger_voice_simulation(self):
        # Prompts Tier-3 user with friendly quick voice selector
        dlg = QDialog(self)
        dlg.setWindowTitle("🎙️ Speak to Shopo Robo")
        dlg.setFixedSize(360, 280)
        l = QVBoxLayout(dlg)
        l.addWidget(QLabel("Select or speak command:"))
        
        cmds = [
            "Sugar is 100kg available in shop",
            "Mere paas 50 packet Maggi hai, khareed 12 bech 14",
            "Rice stock is going to end",
            "What is the profit this month and EBITDA?",
            "Which item is going in loss?",
            "Show wholesale mandi rate increases"
        ]
        for c in cmds:
            b = QPushButton(f"🗣️ \"{c}\"")
            b.setStyleSheet("text-align: left; padding: 8px; font-weight: 600; background-color: #F8FAFC;")
            b.clicked.connect(lambda checked, txt=c, d=dlg: [d.accept(), self.send_agent_command(txt)])
            l.addWidget(b)
        dlg.exec()

    def send_agent_command(self, cmd_text: str):
        self.add_chat_bubble("Shopkeeper", cmd_text, True)
        res = self.agent.process_command(cmd_text)
        reply = res.get("voice_reply", "Done.")
        self.add_chat_bubble("Shopo Robo", reply, False)
        self.voice.speak(reply)
        self.refresh_inventory_grid()

    def add_chat_bubble(self, sender: str, msg: str, is_user: bool):
        bubble = QFrame()
        bg_col = "#ECFCCB" if is_user else "#FFFFFF"
        border_col = "#84CC16" if is_user else "#E2E8F0"
        align = Qt.AlignmentFlag.AlignRight if is_user else Qt.AlignmentFlag.AlignLeft
        
        bubble.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_col};
                border: 1px solid {border_col};
                border-radius: 12px;
                padding: 10px;
                max-width: 600px;
            }}
        """)
        b_layout = QVBoxLayout(bubble)
        b_layout.setContentsMargins(8, 6, 8, 6)

        s_lbl = QLabel(f"<b>{sender}</b>")
        s_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
        m_lbl = QLabel(msg)
        m_lbl.setWordWrap(True)
        m_lbl.setStyleSheet("font-size: 13px; color: #0F172A; line-height: 1.4;")

        b_layout.addWidget(s_lbl)
        b_layout.addWidget(m_lbl)

        row = QHBoxLayout()
        if is_user:
            row.addStretch()
            row.addWidget(bubble)
        else:
            row.addWidget(bubble)
            row.addStretch()

        self.chat_layout.insertLayout(self.chat_layout.count() - 1, row)

    # ── TAB 3: BARCODE SCANNER ───────────────────────────────────────────────
    def create_barcode_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        self.scanner_widget = BarcodeScannerWidget(self)
        self.scanner_widget.product_scanned_signal.connect(self.on_barcode_scanned)
        layout.addWidget(self.scanner_widget)
        return tab

    def on_barcode_scanned(self, item_info: dict):
        self.voice.speak(f"Barcode detected: {item_info['name']}")
        # Check if already in inventory
        existing = self.inv_mgr.get_item_by_barcode(item_info["barcode"])
        if existing:
            existing["stock"] = float(existing.get("stock", 0)) + 10
            self.inv_mgr.add_or_update_item(existing)
            self.refresh_inventory_grid()
            QMessageBox.information(self, "Item Scanned", f"Updated stock for {existing['name']}. Current stock: {existing['stock']} {existing['unit']}.")
        else:
            self.open_add_product_dialog(item_info)

    # ── TAB 4: MANDI MARKET TRENDS ───────────────────────────────────────────
    def create_market_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Header
        top = QHBoxLayout()
        t_lbl = QLabel("📈 Real Wholesale Mandi & Commodity Prices")
        t_lbl.setStyleSheet("font-size: 18px; font-weight: 700; color: #166534;")
        top.addWidget(t_lbl)
        top.addStretch()

        self.mkt_cat_combo = QComboBox()
        self.mkt_cat_combo.addItems(["All Categories"] + get_market_categories())
        self.mkt_cat_combo.setStyleSheet("padding: 6px 14px; border: 1px solid #CBD5E1; border-radius: 8px; font-weight: 600;")
        self.mkt_cat_combo.currentTextChanged.connect(self.refresh_market_view)
        top.addWidget(self.mkt_cat_combo)
        layout.addLayout(top)

        # AI Alert Banner
        self.mkt_alert_banner = QFrame()
        self.mkt_alert_banner.setStyleSheet("background-color: #FEF3C7; border-left: 6px solid #D97706; border-radius: 8px; padding: 10px;")
        ab_layout = QHBoxLayout(self.mkt_alert_banner)
        self.mkt_alert_text = QLabel("💡 AI Margin Guard: Sugar wholesale rates rose 8.2% in NCDEX. Adjust retail price to protect your 18% margin.")
        self.mkt_alert_text.setStyleSheet("font-size: 13px; font-weight: 700; color: #92400E;")
        ab_layout.addWidget(self.mkt_alert_text)
        layout.addWidget(self.mkt_alert_banner)

        # Market List Scroll Area
        self.mkt_scroll = QScrollArea()
        self.mkt_scroll.setWidgetResizable(True)
        self.mkt_scroll.setStyleSheet("border: none; background: transparent;")

        self.mkt_container = QWidget()
        self.mkt_layout = QVBoxLayout(self.mkt_container)
        self.mkt_layout.setSpacing(10)
        self.mkt_scroll.setWidget(self.mkt_container)
        layout.addWidget(self.mkt_scroll)

        self.refresh_market_view()
        return tab

    def refresh_market_view(self):
        while self.mkt_layout.count():
            item = self.mkt_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        selected = self.mkt_cat_combo.currentText()
        cat = None if selected == "All Categories" else selected
        indices = get_indices_for_category(cat or "")

        for itm in indices:
            row_card = QFrame()
            row_card.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px; padding: 12px;")
            r_lay = QVBoxLayout(row_card)

            top_r = QHBoxLayout()
            name_lbl = QLabel(f"<b>{itm['name']}</b> ({itm['mandi']})")
            name_lbl.setStyleSheet("font-size: 14px; color: #0F172A;")
            top_r.addWidget(name_lbl)

            price_lbl = QLabel(f"₹{itm['current_price']:.2f} / {itm['unit']}")
            price_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #166534;")
            top_r.addWidget(price_lbl)

            pct = itm["change_pct"]
            pct_lbl = QLabel(f"{'+' if pct > 0 else ''}{pct:.1f}% {'▲' if pct > 0 else '▼'}")
            pct_lbl.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {'#16A34A' if pct > 0 else '#DC2626'};")
            top_r.addWidget(pct_lbl)
            r_lay.addLayout(top_r)

            adv_lbl = QLabel(f"⚡ AI Advice: {itm['advice']}")
            adv_lbl.setStyleSheet("font-size: 12px; color: #4B5563; font-style: italic;")
            r_lay.addWidget(adv_lbl)

            self.mkt_layout.addWidget(row_card)

        self.mkt_layout.addStretch()

    # ── TAB 5: PROFIT & EBITDA CALCULATOR ────────────────────────────────────
    def create_calculator_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("🧮 Monthly Profit, Loss & EBITDA Calculator")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #166534;")
        layout.addWidget(title)

        main_calc_row = QHBoxLayout()

        # Inputs Form
        input_frame = QFrame()
        input_frame.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 14px;")
        form = QFormLayout(input_frame)

        self.calc_sales = QDoubleSpinBox()
        self.calc_sales.setRange(0, 10000000)
        self.calc_sales.setValue(156000.0)

        self.calc_cogs = QDoubleSpinBox()
        self.calc_cogs.setRange(0, 10000000)
        self.calc_cogs.setValue(118000.0)

        self.calc_rent = QDoubleSpinBox()
        self.calc_rent.setRange(0, 1000000)
        self.calc_rent.setValue(8000.0)

        self.calc_elec = QDoubleSpinBox()
        self.calc_elec.setRange(0, 1000000)
        self.calc_elec.setValue(2500.0)

        self.calc_staff = QDoubleSpinBox()
        self.calc_staff.setRange(0, 1000000)
        self.calc_staff.setValue(6000.0)

        self.calc_spoilage = QDoubleSpinBox()
        self.calc_spoilage.setRange(0, 1000000)
        self.calc_spoilage.setValue(800.0)

        for spin in [self.calc_sales, self.calc_cogs, self.calc_rent, self.calc_elec, self.calc_staff, self.calc_spoilage]:
            spin.setPrefix("₹ ")
            spin.valueChanged.connect(self.recalc_financials)

        form.addRow("Monthly Sales (बिक्री):", self.calc_sales)
        form.addRow("Stock Cost (COGS खरीद):", self.calc_cogs)
        form.addRow("Shop Rent (दुकान किराया):", self.calc_rent)
        form.addRow("Electricity & Bills:", self.calc_elec)
        form.addRow("Staff Wages (कर्मचारी):", self.calc_staff)
        form.addRow("Wastage / Spoilage (नुकसान):", self.calc_spoilage)

        main_calc_row.addWidget(input_frame, 1)

        # Output Cards
        output_frame = QFrame()
        output_frame.setStyleSheet("background-color: #ECFCCB; border: 2px solid #84CC16; border-radius: 12px; padding: 14px;")
        o_lay = QVBoxLayout(output_frame)

        self.lbl_gross = QLabel("Gross Profit: <b>₹38,000</b> (24.4%)")
        self.lbl_gross.setStyleSheet("font-size: 16px; color: #166534;")
        self.lbl_ebitda = QLabel("EBITDA: <b>₹20,700</b> (13.3%)")
        self.lbl_ebitda.setStyleSheet("font-size: 16px; color: #15803D;")
        self.lbl_net = QLabel("Net Take-Home Profit: <b>₹17,200</b>")
        self.lbl_net.setStyleSheet("font-size: 20px; font-weight: 800; color: #14532D;")

        o_lay.addWidget(self.lbl_gross)
        o_lay.addWidget(self.lbl_ebitda)
        o_lay.addWidget(self.lbl_net)

        btn_speak_fin = QPushButton("🔊 Speak Financial Report")
        btn_speak_fin.setStyleSheet("background-color: #84CC16; color: white; font-weight: 700; padding: 10px; border-radius: 8px;")
        btn_speak_fin.clicked.connect(self.speak_financial_report)
        o_lay.addWidget(btn_speak_fin)

        main_calc_row.addWidget(output_frame, 1)
        layout.addLayout(main_calc_row)

        self.recalc_financials()
        return tab

    def recalc_financials(self):
        fin = calculate_financials(
            monthly_sales=self.calc_sales.value(),
            cogs=self.calc_cogs.value(),
            shop_rent=self.calc_rent.value(),
            electricity_bills=self.calc_elec.value(),
            staff_wages=self.calc_staff.value(),
            spoilage_wastage=self.calc_spoilage.value()
        )
        self.last_fin = fin
        self.lbl_gross.setText(f"Gross Profit: <b>₹{fin['gross_profit']:,.0f}</b> ({fin['gross_margin_pct']}%)")
        self.lbl_ebitda.setText(f"EBITDA: <b>₹{fin['ebitda']:,.0f}</b> ({fin['ebitda_margin_pct']}%)")
        self.lbl_net.setText(f"Net Take-Home Profit: <b>₹{fin['net_profit']:,.0f}</b> ({fin['net_margin_pct']}%)")

    def speak_financial_report(self):
        if hasattr(self, "last_fin"):
            self.voice.speak(self.last_fin["voice_summary"])

    # ── TAB 6: SETTINGS & 100+ VOICE PACKS ────────────────────────────────────
    def create_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        title = QLabel("⚙️ App Settings & Indian Voice Packs")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #166534;")
        layout.addWidget(title)

        s_frame = QFrame()
        s_frame.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 16px;")
        s_form = QFormLayout(s_frame)

        # Shop Type
        self.shop_type_combo = QComboBox()
        self.shop_type_combo.addItems([
            "Grocery & Kirana Store",
            "Pharmacy & Medical Store",
            "Mobile & Electronics Store",
            "Fashion & Garments Boutique",
            "Bakery & Confectionery"
        ])
        self.shop_type_combo.setCurrentText(self.inv_mgr.shop_type)
        self.shop_type_combo.currentTextChanged.connect(self.on_shop_type_changed)
        s_form.addRow("Store Category (दुकान प्रकार):", self.shop_type_combo)

        # Language Selection
        self.set_lang_combo = QComboBox()
        for c, d in LANGUAGES.items():
            self.set_lang_combo.addItem(d["name"], c)
        self.set_lang_combo.currentIndexChanged.connect(lambda idx: self.lang_combo.setCurrentIndex(idx))
        s_form.addRow("App Language (भाषा):", self.set_lang_combo)

        # Voice Volume
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(100)
        self.vol_slider.valueChanged.connect(lambda v: self.voice.set_volume(v))
        s_form.addRow("Voice Volume:", self.vol_slider)

        # Test Voice Button
        btn_test_voice = QPushButton("🔊 Test Voice Pack")
        btn_test_voice.setStyleSheet("background-color: #84CC16; color: white; font-weight: 700; padding: 8px 16px; border-radius: 8px;")
        btn_test_voice.clicked.connect(lambda: self.voice.speak("Voice pack is active. Shopo Robo ready."))
        s_form.addRow("Voice Test:", btn_test_voice)

        layout.addWidget(s_frame)
        layout.addStretch()
        return tab

    def on_shop_type_changed(self, text):
        self.inv_mgr.shop_type = text
        self.inv_mgr.save_data()
        self.voice.speak(f"Store profile updated to {text}.")

    def on_language_changed(self, idx):
        code = self.lang_combo.currentData()
        self.current_lang = code
        msg = get_text(code, "welcome_msg")
        self.voice.speak(msg)

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Set default app-wide font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    main_window = ShopoRoboMainWindow()
    main_window.show()
    main_window.raise_()
    main_window.activateWindow()

    # Bring to foreground on Windows
    try:
        import ctypes
        hwnd = int(main_window.winId())
        ctypes.windll.user32.ShowWindow(hwnd, 9) # SW_RESTORE
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass

    # Play welcome greeting immediately on launch
    VoiceEngine.get_instance().speak("Welcome! I am your Shopo Robo. Namaste! Aapki dukaan ka AI saathi.")

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
