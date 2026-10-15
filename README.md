# 🛒 Shopo Robo - AI-Powered Inventory Store

> **"Your Shop. Our AI. Smarter Together."**  
> A voice-first, AI-driven stock knowledge and store intelligence web application designed specifically for shopkeepers to manage inventory, track profits, identify loss-making items, monitor wholesale mandi price trends, and automatically generate custom store types with **Jarvis AI**.

---

## 🌟 Highlights & Features

### 🎙️ 1. Hands-Free Jarvis AI Voice Assistant
- **Speech-to-Text & Text-to-Speech**: Full integration with the browser's Web Speech Recognition & Web Speech Synthesis API.
- **Audio Waveform Canvas**: Real-time visual sound wave pulsations on both sides of the microphone when listening or speaking.
- **Procedural Chimes**: Web Audio API generated futuristic start/reply sound effects.
- **Natural Language & Bilingual Understanding**: Recognizes both English and Hinglish commands naturally.

### 📦 2. Stock Management & Knowledge
- **Voice-Operated Stocking**: e.g., *"Sugar is 100kg available in shop"*, *"Add 50 kg rice"*, *"Update sugar stock to 120 kg"*.
- **Low Stock Early Warning**: e.g., *"Rice stock is going to end soon! Only 5 kg left."* Jarvis automatically flags it and updates AI Alerts.
- **Interactive Stock Levels**: Real-time badges for `Sufficient`, `Low Stock`, and `Out of Stock` with instant Stock In / Stock Out dialogs.

### 💰 3. Profit & Loss Intelligence
- **Monthly P&L Audit**: Track Total Sales (₹ 1,56,000), Total Expenses (₹ 1,34,440), and Net Profit (₹ 21,560, +24%).
- **Interactive Visual Bar Chart**: Exact 3-bar breakdown (Sales, Expenses, Profit) matching the design.
- **Loss-Making Items Hunter**: Spot items sold below wholesale cost (e.g. *Maggi selling at ₹14 with cost of ₹14.50*) and receive AI pricing advice to restore margins.
- **Best Selling vs. Loss Making**: One-click pill tab toggle.

### 📈 4. Wholesale Mandi Market Price Trends
- **Live Commodity Price Tracker**: Tracks wholesale rate fluctuations (Sugar +8% ▲, Rice -5% ▼, Wheat Flour +3% ▲, Cooking Oil -2% ▼, Milk +5% ▲).
- **AI Margin Guard**: Advises the shopkeeper when wholesale costs increase so they can adjust selling prices before suffering losses.

### 🏪 5. Automated AI Shop Type Generator
- **Automatic Setup by Owner Data**: Shopkeeper can say *"Create a new shop type"* or choose from presets:
  - 🛒 **Grocery & Kirana Store** (Staples, Rice, Sugar, Grains, Edible Oils, Spices)
  - 💊 **Pharmacy & Medical Store** (Tablets, Syrups, First Aid, Surgical, Baby Care)
  - 📱 **Mobile & Electronics Store** (Smartphones, USB Cables, Earbuds, Tempered Glass)
  - 👗 **Fashion & Garments Boutique** (T-shirts, Jeans, Kurtis, Formal Wear)
  - 🥐 **Bakery & Confectionery** (Breads, Pastries, Cookies, Patties)
- Jarvis dynamically creates catalog items, categories, standard units (`kg`, `L`, `pcs`, `strips`, `bottles`), and financial baselines.

### ☁️ 6. Supabase Cloud Database Integration
- Pre-configured `supabase-schema.sql` script ready to run in Supabase SQL editor.
- Connect via URL & Anon Public API Key in Settings.
- Seamless **Offline-First Fallback** to browser LocalStorage so the app works immediately out of the box without any setup needed.

---

## 🎨 Theme & Design
- **Theme**: Crisp White & Vibrant Lime Green (`#84CC16`, `#65A30D`, `#ECFCCB`).
- **Typography**: Plus Jakarta Sans.
- **Icons**: FontAwesome 6 Crisp Vector Icons.

---

## 🗣️ Voice Commands Guide (Jarvis)

| Voice Command | Action Taken by Jarvis |
| :--- | :--- |
| **"Show me current stock"** | Reads out current inventory valuation, total items, and low-stock alerts. |
| **"Sugar is 100kg available in shop"** | Updates Sugar stock to 100 kg and marks status as Sufficient. |
| **"Rice stock is going to end"** | Triggers low-stock alert, warns only 5 kg remaining, and recommends reordering. |
| **"What's the profit this month?"** | Summarizes monthly sales, expenses, and net profit (+24% growth). |
| **"Which item is in loss?"** | Identifies items sold below wholesale purchase cost (e.g. Maggi) with advice. |
| **"What are the market price changes?"** | Lists commodities with increasing and decreasing wholesale mandi rates. |
| **"Create a new shop type"** | Opens the AI Shop Type generator to adapt the store configuration. |
| **"Add 50 kg wheat flour"** | Automatically increments wheat flour stock by 50 kg. |

---

## 🚀 How to Run Locally

1. Open a terminal in the project directory:
   ```bash
   cd c:\Users\dell\Downloads\antigravity
   ```
2. Start any local HTTP server:
   ```bash
   # Using Python:
   python -m http.server 8080

   # Or using Node:
   npx serve .
   ```
3. Open your browser and navigate to:
   ```
   http://localhost:8080
   ```
4. Click the **Microphone** icon or say a command to interact with Jarvis!

---

## 🗄️ Setting Up Supabase (Optional)

1. Create a project at [supabase.com](https://supabase.com).
2. Go to the **SQL Editor** tab in your Supabase Dashboard.
3. Open `supabase-schema.sql` from this repository, copy its content, and paste it into the SQL Editor. Click **Run**.
4. Go to **Settings -> API** in Supabase and copy your:
   - **Project URL**
   - **anon / public Key**
5. In Shopo Robo, go to **Settings**, paste your URL and API Key, and click **Save & Connect Supabase**.
6. All store data will now sync to your cloud database in real time!
