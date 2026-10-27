/**
 * Shopo Robo — Dashboard Controller
 * ===================================
 * Manages the main dukaan dashboard, welcome experience modal,
 * voice microphone recognition, navigation views, and quick modals.
 */

// ── State ──
let currentUser = null;
let currentLanguage = 'hi';
let speechRecognition = null;


let isListening = false;
let isStartingRecognition = false;
let isProcessingAICommand = false;

// ── Inventory State (Phase 2) ──
let inventoryItems = [];
let lastModifiedProductId = null;
let inventorySummary = null;
let inventoryFilters = {
    q: '',
    category: '',
    low_stock: false,
    near_expiry: false,
};
let searchDebounceTimeout = null;

// ── Business & Sales State (Prompt 6A) ──
let businessFinancials = null;
let salesRecords = [];
let userExpenses = [];

// ── User Regional & Language Preferences State (Feature 1 & 4) ──
let userPreferences = {
    ui_language: 'hi',
    ai_language: 'hi',
    news_language: 'hi',
    date_format: 'DD/MM/YYYY',
    time_format: '12h',
    number_format: 'inr_lakhs',
    temperature_unit: 'celsius',
    selected_city: 'Delhi'
};

// ── 16 Supported Languages Metadata with Honest Completeness Tags ──
const SUPPORTED_LANGUAGES = [
    { code: 'hi', name: 'Hindi', nativeName: 'हिन्दी', status: 'verified', badgeText: '100% Verified', dir: 'ltr' },
    { code: 'en', name: 'English', nativeName: 'English', status: 'verified', badgeText: '100% Verified', dir: 'ltr' },
    { code: 'hinglish', name: 'Hinglish', nativeName: 'Hinglish (Colloquial)', status: 'verified', badgeText: '100% Verified', dir: 'ltr' },
    { code: 'es', name: 'Spanish', nativeName: 'Español', status: 'beta', badgeText: 'Beta Translation', dir: 'ltr' },
    { code: 'fr', name: 'French', nativeName: 'Français', status: 'beta', badgeText: 'Beta Translation', dir: 'ltr' },
    { code: 'ar', name: 'Arabic', nativeName: 'العربية', status: 'beta', badgeText: 'Beta Translation (RTL)', dir: 'rtl' },
    { code: 'zh', name: 'Chinese', nativeName: '中文 (Simplified)', status: 'beta', badgeText: 'Beta Translation', dir: 'ltr' },
    { code: 'ja', name: 'Japanese', nativeName: '日本語', status: 'beta', badgeText: 'Beta Translation', dir: 'ltr' },
    { code: 'bn', name: 'Bengali', nativeName: 'বাংলা', status: 'beta', badgeText: 'Beta Translation', dir: 'ltr' },
    { code: 'mr', name: 'Marathi', nativeName: 'मराठी', status: 'beta', badgeText: 'Beta Translation', dir: 'ltr' },
    { code: 'te', name: 'Telugu', nativeName: 'తెలుగు', status: 'beta', badgeText: 'Beta Translation', dir: 'ltr' },
    { code: 'ta', name: 'Tamil', nativeName: 'தமிழ்', status: 'beta', badgeText: 'Beta Translation', dir: 'ltr' },
    { code: 'gu', name: 'Gujarati', nativeName: 'ગુજરાતી', status: 'beta', badgeText: 'Beta Translation', dir: 'ltr' },
    { code: 'ur', name: 'Urdu', nativeName: 'اردو', status: 'beta', badgeText: 'Beta Translation (RTL)', dir: 'rtl' },
    { code: 'de', name: 'German', nativeName: 'Deutsch', status: 'beta', badgeText: 'Beta Translation', dir: 'ltr' },
];

// ── Lightweight Toast Notification Helper ──
function showToast(message, type = 'info') {
    console.log(`[Toast ${type}]`, message);
    try {
        let container = document.getElementById('toastContainer');
        if (!container && document.body) {
            container = document.createElement('div');
            container.id = 'toastContainer';
            container.style.cssText = 'position:fixed; bottom:24px; right:24px; z-index:9999; display:flex; flex-direction:column; gap:8px; pointer-events:none;';
            document.body.appendChild(container);
        }
        if (container) {
            const toast = document.createElement('div');
            toast.style.cssText = 'background:#1E293B; color:#F8FAFC; padding:10px 18px; border-radius:8px; font-size:0.88rem; box-shadow:0 4px 12px rgba(0,0,0,0.25); border-left:4px solid #10B981; pointer-events:auto; transition:opacity 0.3s;';
            toast.textContent = message;
            container.appendChild(toast);
            setTimeout(() => {
                toast.style.opacity = '0';
                setTimeout(() => toast.remove(), 350);
            }, 3000);
        }
    } catch (e) {
        // Fallback
    }
}

// ── Multi-language Dictionary (16 Languages) ──
const I18N = {
    hi: {
        nav_home: 'मुख्य पृष्ठ',
        nav_inventory: 'स्टॉक इन्वेंटरी',
        nav_multi_store: 'शाखाएं',
        nav_shelf_scanner: 'शेल्फ स्कैनर',
        nav_sales: 'बिक्री',
        nav_purchases: 'खरीद (स्टॉक)',
        nav_reports: 'रिपोर्ट्स',
        nav_barcode: 'बारकोड व QR स्कैनर',
        nav_settings: 'सेटिंग्स',
        nav_tools_header: 'विशेष व्यापार टूल्स',
        nav_news: 'ताज़ा समाचार व बाज़ार',
        nav_autopilot: 'AI ऑटोपायलट',
        nav_notifications: 'सूचनाएं',
        nav_memory: 'व्यापार स्मृति',
        nav_radar: 'अवसर रडार',
        nav_assistant: 'Your AI Accountant',
        nav_accountant: 'AI मुनीम एवं टैक्स',
        nav_competitor: 'प्रतिस्पर्धी रडार',
        nav_demand: 'ग्राहक मांग',
        nav_negotiation: 'मोलभाव कोच',
        nav_simulator: 'व्यापार सिमुलेटर',
        nav_time_machine: 'समय मशीन पूर्वानुमान',
        nav_translator: 'वॉइस अनुवादक',
        news_view_title: 'ताज़ा समाचार एवं मंडी भाव',
        ai_assistant_title: 'Your AI Accountant',
        ai_status_ready: 'ऑनलाइन • आपकी दुकान के लिए तैयार हूँ',
        mic_tap_to_speak: 'माइक दबाकर बोलें',
        mic_helper: 'माइक दबाकर अपनी भाषा में बोलें',
        mic_sub: 'स्टॉक, बिक्री, मंडी भाव और मौसम के लिए आसान वॉइस कमांड',
        preset_label: 'यह बोलकर देखें:',
        overview_title: 'आज का व्यापार हिसाब',
        metric_sales: 'आज की बिक्री',
        metric_profit: 'कुल मुनाफ़ा',
        metric_products: 'कुल सामान',
        metric_stock_val: 'स्टॉक मूल्य',
        metric_low_stock: 'कम स्टॉक सामान',
        metric_expiry: 'जल्द एक्सपायरी',
        actions_title: 'त्वरित कार्य',
        act_add_prod: 'सामान जोड़ें',
        act_scan: 'बारकोड स्कैन',
        act_inventory: 'स्टॉक देखें',
        act_sale: 'बिक्री दर्ज करें',
        act_reports: 'रिपोर्ट्स',
        recent_sales_title: 'हाल की बिक्री',
        alerts_title: 'चेतावनियाँ एवं अलर्ट',
        wizard_title: 'दुकान का सेटअप पूरा करें',
        wizard_desc: 'अपनी दुकान का नाम और प्रकार चुनें ताकि शोपो रोबो आपका सही इन्वेंटरी डेटा तैयार कर सके।',
        chart_sales_title: 'बिक्री एवं राजस्व ग्राफ',
        comp_title: 'प्रतिस्पर्धी मूल्य एवं बाज़ार विश्लेषण',
        comp_sub: 'स्थानीय बाज़ार भाव एवं प्रतिस्पर्धी मार्जिन ट्रैक करें',
        demand_title: 'ग्राहक मांग एवं आवश्यकता विश्लेषक',
        demand_sub: 'अपूर्ण ग्राहक मांगों और अधिक मांग वाले उत्पादों का विश्लेषण करें',
        neg_title: 'आपूर्तिकर्ता मोलभाव एवं बातचीत कोच',
        neg_sub: 'मंडी भाव और रणनीतिक खरीद मार्जिन सलाह',
        trans_title: 'व्यापारिक बहुभाषी अनुवादक',
        trans_sub: 'अंतरराज्यीय व्यापार के लिए त्वरित आवाज़ और टेक्स्ट अनुवाद',
        pref_ui_lang: 'स्क्रीन प्रदर्शन भाषा',
        pref_ai_lang: 'AI आवाज़ व चैट भाषा',
        pref_news_lang: 'समाचार फ़ीड भाषा',
        weather_humidity: 'नमी',
        weather_wind: 'हवा की गति',
        weather_rain: 'बारिश',
        weather_updated: 'अंतिम अपडेट',
        btn_detect_location: 'स्थान पहचानें',
        btn_confirm_action: 'सुरक्षित सहेजें',
        btn_cancel_action: 'रद्द करें',
        btn_logout: 'बाहर निकलें',
        nav_settings_lang: 'भाषा सेटिंग्स',
        setting_lang_title: 'स्क्रीन प्रदर्शन भाषा',
        setting_lang_desc: 'डैशबोर्ड मेनू, कार्ड और रिपोर्ट्स देखने के लिए अपनी पसंदीदा भाषा चुनें।'
    },
    en: {
        nav_home: 'Dashboard',
        nav_inventory: 'Inventory',
        nav_multi_store: 'Branches',
        nav_shelf_scanner: 'Shelf Scanner',
        nav_sales: 'Sales',
        nav_purchases: 'Purchases (Stock)',
        nav_reports: 'Reports',
        nav_barcode: 'Barcode & QR Scanner',
        nav_settings: 'Settings',
        nav_tools_header: 'Specialized Tools',
        nav_news: 'News & Markets',
        nav_autopilot: 'AI Autopilot',
        nav_notifications: 'Notifications',
        nav_memory: 'Business Memory',
        nav_radar: 'Opportunity Radar',
        nav_assistant: 'Your AI Accountant',
        nav_accountant: 'AI Accountant & Tax',
        nav_competitor: 'Competitor Radar',
        nav_demand: 'Customer Demand',
        nav_negotiation: 'Negotiation Coach',
        nav_simulator: 'Business Simulator',
        nav_time_machine: 'Time Machine Forecast',
        nav_translator: 'Voice Translator',
        news_view_title: 'News & Market Intelligence',
        ai_assistant_title: 'Your AI Accountant',
        ai_status_ready: 'Online • Ready to assist your shop',
        mic_tap_to_speak: 'Tap Mic to Speak',
        mic_helper: 'Tap microphone and speak in your language',
        mic_sub: 'Natural voice for stock, sales, prices, weather & schemes',
        preset_label: 'Try asking:',
        overview_title: 'Business Overview',
        metric_sales: "Today's Sales",
        metric_profit: 'Total Profit',
        metric_products: 'Total Items',
        metric_stock_val: 'Stock Value',
        metric_low_stock: 'Low Stock Items',
        metric_expiry: 'Near Expiry',
        actions_title: 'Quick Actions',
        act_add_prod: 'Add Product',
        act_scan: 'Scan Barcode',
        act_inventory: 'View Inventory',
        act_sale: 'Record Sale',
        act_reports: 'Reports',
        recent_sales_title: 'Recent Sales',
        alerts_title: 'Alerts & Notifications',
        wizard_title: 'Setup Your Shop Profile',
        wizard_desc: 'Enter your shop name and trade category to initialize your intelligent ledger.',
        chart_sales_title: 'Sales & Revenue Overview',
        comp_title: 'Competitor Price & Market Intelligence',
        comp_sub: 'Track local market prices and competitor margins',
        demand_title: 'Customer Demand Listener',
        demand_sub: 'Analyze unfulfilled requests and high-demand products',
        neg_title: 'Supplier Negotiation Coach',
        neg_sub: 'Strategic margin coaching and mandi price benchmarks',
        trans_title: 'Multilingual Business Translator',
        trans_sub: 'Instant voice and text translation for multi-state trade',
        pref_ui_lang: 'Display Language',
        pref_ai_lang: 'AI Voice & Chat Language',
        pref_news_lang: 'News Feed Language',
        weather_humidity: 'Humidity',
        weather_wind: 'Wind',
        weather_rain: 'Rain',
        weather_updated: 'Last Updated',
        btn_detect_location: 'Detect Location',
        btn_confirm_action: 'Confirm & Execute',
        btn_cancel_action: 'Cancel',
        btn_logout: 'Logout',
        nav_settings_lang: 'Language Settings',
        setting_lang_title: 'Display Language',
        setting_lang_desc: 'Choose your preferred language for the dashboard interface, menus, and reports.'
    },
    hinglish: {
        nav_home: 'Dashboard',
        nav_inventory: 'Stock Inventory',
        nav_multi_store: 'Dukaan Branches',
        nav_shelf_scanner: 'Shelf Scanner',
        nav_sales: 'Bikri',
        nav_purchases: 'Kharid (Stock)',
        nav_reports: 'Munafa Reports',
        nav_barcode: 'Barcode & QR Scanner',
        nav_settings: 'Settings',
        nav_tools_header: 'Dukaan Tools',
        nav_news: 'Khabar & Mandi Bhav',
        nav_autopilot: 'AI Autopilot',
        nav_notifications: 'Notifications',
        nav_memory: 'Dukaan Memory',
        nav_radar: 'Opportunity Radar',
        nav_assistant: 'Your AI Accountant',
        nav_accountant: 'AI Munim & Tax',
        nav_competitor: 'Competitor Radar',
        nav_demand: 'Customer Demand',
        nav_negotiation: 'Molbhav Coach',
        nav_simulator: 'What-If Simulator',
        nav_time_machine: 'Time Machine Forecast',
        nav_translator: 'Voice Translator',
        news_view_title: 'Live News & Mandi Rates',
        ai_assistant_title: 'Your AI Accountant',
        ai_status_ready: 'Online • Dukaan assistant ready hai',
        mic_tap_to_speak: 'Mic dabakar boliye',
        mic_helper: 'Mic dabakar apni boli me command dein',
        mic_sub: 'Stock, bikri, mandi bhav aur mausam ke voice commands',
        preset_label: 'Try bol kar dekhein:',
        overview_title: 'Aaj ka Dukaan Hisaab',
        metric_sales: 'Aaj ki Bikri',
        metric_profit: 'Kul Munafa',
        metric_products: 'Total Items',
        metric_stock_val: 'Stock Value',
        metric_low_stock: 'Low Stock Items',
        metric_expiry: 'Jald Expiry',
        actions_title: 'Quick Dukaan Actions',
        act_add_prod: 'Samaan Jodein',
        act_scan: 'Barcode Scan',
        act_inventory: 'Stock Check',
        act_sale: 'Bikri Likhein',
        act_reports: 'Reports Dekhein',
        recent_sales_title: 'Haal ki Bikri',
        alerts_title: 'Zaroori Alerts',
        wizard_title: 'Dukaan Profile Setup Karein',
        wizard_desc: 'Dukaan ka name aur category select karein smart AI ledger ke liye.',
        chart_sales_title: 'Bikri & Revenue Overview',
        comp_title: 'Market & Competitor Intel',
        comp_sub: 'Local market rates aur margins track karein',
        demand_title: 'Customer Demand Listener',
        demand_sub: 'Demand waale items aur customer requests analyze karein',
        neg_title: 'Supplier Molbhav Coach',
        neg_sub: 'Mandi rate aur strategic margin advice',
        trans_title: 'Business Voice Translator',
        trans_sub: 'Dusre states ke vyapar ke liye quick translation',
        pref_ui_lang: 'Display Language',
        pref_ai_lang: 'AI Voice & Chat Language',
        pref_news_lang: 'News Language',
        weather_humidity: 'Humidity',
        weather_wind: 'Hawa Speed',
        weather_rain: 'Barish',
        weather_updated: 'Last Updated',
        btn_detect_location: 'Location Detect Karein',
        btn_confirm_action: 'Confirm Karein',
        btn_cancel_action: 'Cancel',
        btn_logout: 'Logout',
        nav_settings_lang: 'Language Settings',
        setting_lang_title: 'App Display Language',
        setting_lang_desc: 'Dukaan ke dashboard, menus aur reports ke liye apni language select karein.'
    },
    mr: {
        nav_home: 'मुख्य पृष्ठ',
        nav_inventory: 'स्टॉक इन्व्हेंटरी',
        nav_multi_store: 'शाखा',
        nav_shelf_scanner: 'शेल्फ स्कॅनर',
        nav_sales: 'विक्री नोंद',
        nav_purchases: 'खरेदी (स्टॉक)',
        nav_reports: 'नफा अहवाल',
        nav_barcode: 'बारकोड स्कॅनर',
        nav_settings: 'सेटिंग्ज',
        nav_tools_header: 'व्यापार साधने',
        nav_news: 'बाजार बातम्या',
        nav_autopilot: 'AI ऑटोपायलट',
        nav_notifications: 'सूचना केंद्र',
        nav_memory: 'व्यापार स्मृती',
        nav_radar: 'संधी रडार',
        nav_assistant: 'Your AI Accountant',
        nav_accountant: 'AI मुनीम व कर',
        nav_competitor: 'स्पर्धक रडार',
        nav_demand: 'ग्राहक मागणी',
        nav_negotiation: 'घासाघीस मार्गदर्शक',
        nav_simulator: 'व्यापार सिम्युलेटर',
        nav_time_machine: 'भविष्य अंदाज',
        nav_translator: 'आवाज अनुवादक',
        news_view_title: 'बाजार आणि कृषी भाव बातम्या',
        ai_assistant_title: 'Your AI Accountant',
        ai_status_ready: 'ऑनलाइन • दुकानासाठी तयार आहे',
        mic_tap_to_speak: 'माइक दाबून बोला',
        mic_helper: 'माइकवर टॅप करा आणि मराठीत बोला',
        mic_sub: 'स्टॉक, विक्री आणि बाजार भावासाठी आवाज आज्ञा',
        preset_label: 'विचारून पहा:',
        overview_title: 'आजचा व्यवसाय ताळेबंद',
        metric_sales: 'आजची विक्री',
        metric_profit: 'एकूण नफा',
        metric_products: 'एकूण वस्तू',
        metric_stock_val: 'स्टॉक मूल्य',
        metric_low_stock: 'कमी स्टॉक',
        metric_expiry: 'मुदत संपत आलेला',
        actions_title: 'त्वरित कृती',
        act_add_prod: 'वस्तू जोडा',
        act_scan: 'बारकोड स्कॅन',
        act_inventory: 'स्टॉक तपासा',
        act_sale: 'विक्री नोंदवा',
        act_reports: 'अहवाल पहा',
        recent_sales_title: 'अलीकडील विक्री',
        alerts_title: 'सूचना आणि सूचना फलक',
        wizard_title: 'दुकान प्रोफाइल पूर्ण करा',
        wizard_desc: 'आपल्या दुकानाचे नाव आणि श्रेणी निवडा.',
        chart_sales_title: 'विक्री आणि महसूल आढावा',
        comp_title: 'स्पर्धक भाव विश्लेषण',
        comp_sub: 'स्थानिक बाजार भाव आणि नफा ट्रॅक करा',
        demand_title: 'ग्राहक मागणी विश्लेषक',
        demand_sub: 'अधिक मागणी असलेल्या वस्तूंचा आढावा',
        neg_title: 'घासाघीस मार्गदर्शक',
        neg_sub: 'मंडी भाव व खरेदी सल्ला',
        trans_title: 'व्यापारी अनुवादक',
        trans_sub: 'इतर राज्यातील व्यापारासाठी त्वरित भाषांतर',
        pref_ui_lang: 'स्क्रीन भाषा',
        pref_ai_lang: 'AI भाषा',
        pref_news_lang: 'बातम्यांची भाषा',
        weather_humidity: 'आर्द्रता',
        weather_wind: 'वाऱ्याचा वेग',
        weather_rain: 'पाऊस',
        weather_updated: 'शेवटचे अपडेट',
        btn_detect_location: 'स्थान ओळखा',
        btn_confirm_action: 'जतन करा',
        btn_cancel_action: 'रद्द करा',
        btn_logout: 'बाहेर पडा',
        nav_settings_lang: 'भाषा सेटिंग्ज',
        setting_lang_title: 'स्क्रीन प्रदर्शन भाषा',
        setting_lang_desc: 'डॅशबोर्ड आणि अहवालांसाठी आपली आवडती भाषा निवडा.'
    },
    gu: {
        nav_home: 'મુખ્ય પૃષ્ઠ',
        nav_inventory: 'સ્ટોક ઇન્વેન્ટરી',
        nav_multi_store: 'શાખાઓ',
        nav_shelf_scanner: 'શેલ્ફ સ્કેનર',
        nav_sales: 'વેચાણ ખાતાવહી',
        nav_purchases: 'ખરીદી (સ્ટોક)',
        nav_reports: 'નફા અહેવાલ',
        nav_barcode: 'બારકોડ સ્કેનર',
        nav_settings: 'સેટિંગ્સ',
        nav_tools_header: 'વેપાર સાધનો',
        nav_news: 'બજાર સમાચાર',
        nav_autopilot: 'AI ઓટોપાયલટ',
        nav_notifications: 'સૂચના કેન્દ્ર',
        nav_memory: 'વેપાર સ્મૃતિ',
        nav_radar: 'તક રડાર',
        nav_assistant: 'Your AI Accountant',
        nav_accountant: 'AI મુનીમ અને ટેક્સ',
        nav_competitor: 'હરીફ રડાર',
        nav_demand: 'ગ્રાહક માંગ',
        nav_negotiation: 'ભાવતાલ કોચ',
        nav_simulator: 'વેપાર સિમ્યુલેટર',
        nav_time_machine: 'સમય આગાહી',
        nav_translator: 'અવાજ અનુવાદક',
        news_view_title: 'બજાર અને મંડી સમાચાર',
        ai_assistant_title: 'Your AI Accountant',
        ai_status_ready: 'ઓનલાઇન • દુકાન માટે તૈયાર છે',
        mic_tap_to_speak: 'માઇક દબાવીને બોલો',
        mic_helper: 'માઇક દબાવીને ગુજરાતીમાં બોલો',
        mic_sub: 'સ્ટોક, વેચાણ અને ભાવ માટે અવાજ કમાન્ડ',
        preset_label: 'પૂછી જુઓ:',
        overview_title: 'આજનો વેપાર હિસાબ',
        metric_sales: 'આજનું વેચાણ',
        metric_profit: 'કુલ નફો',
        metric_products: 'કુલ વસ્તુઓ',
        metric_stock_val: 'સ્ટોક કિંમત',
        metric_low_stock: 'ઓછો સ્ટોક',
        metric_expiry: 'મુદત પૂર્ણ થતી વસ્તુઓ',
        actions_title: 'ઝડપી કાર્યો',
        act_add_prod: 'વસ્તુ ઉમેરો',
        act_scan: 'બારકોડ સ્કેન',
        act_inventory: 'સ્ટોક જુઓ',
        act_sale: 'વેચાણ નોંધો',
        act_reports: 'અહેવાલો',
        recent_sales_title: 'તાજેતરનું વેચાણ',
        alerts_title: 'સૂચનાઓ અને ચેતવણી',
        wizard_title: 'દુકાન સેટઅપ પૂર્ણ કરો',
        wizard_desc: 'દુકાનનું નામ અને શ્રેણી પસંદ કરો.',
        chart_sales_title: 'વેચાણ અને આવક આલેખ',
        comp_title: 'હરીફ ભાવ વિશ્લેષણ',
        comp_sub: 'સ્થાનિક બજાર ભાવ ટ્રેક કરો',
        demand_title: 'ગ્રાહક માંગ વિશ્લેષક',
        demand_sub: 'વધુ માંગ ધરાવતી વસ્તુઓનો વિશ્લેષણ',
        neg_title: 'ભાવતાલ કોચ',
        neg_sub: 'મંડી ભાવ અને ખરીદી સલાહ',
        trans_title: 'વેપારી અનુવાદક',
        trans_sub: 'વેપાર માટે તાત્કાલિક અવાજ અનુવાદ',
        pref_ui_lang: 'સ્ક્રીન ભાષા',
        pref_ai_lang: 'AI ભાષા',
        pref_news_lang: 'સમાચાર ભાષા',
        weather_humidity: 'ભેજ',
        weather_wind: 'પવન ગતિ',
        weather_rain: 'વરસાદ',
        weather_updated: 'છેલ્લું અપડેટ',
        btn_detect_location: 'સ્થાન શોધો',
        btn_confirm_action: 'સાચવો',
        btn_cancel_action: 'રદ કરો',
        btn_logout: 'બહાર નીકળો',
        nav_settings_lang: 'ભાષા સેટિંગ્સ',
        setting_lang_title: 'ડિસ્પ્લે ભાષા',
        setting_lang_desc: 'ડેશબોર્ડ અને રિપોર્ટ્સ માટે તમારી પસંદગીની ભાષા પસંદ કરો.'
    },
    bn: {
        nav_home: 'ড্যাশবোর্ড',
        nav_inventory: 'মজুদ তালিকা',
        nav_multi_store: 'শাখা সমূহ',
        nav_shelf_scanner: 'শেল্ফ স্ক্যানার',
        nav_sales: 'বিক্রয় রেজিস্টার',
        nav_purchases: 'ক্রয় (স্টক)',
        nav_reports: 'লাভ-ক্ষতি রিপোর্ট',
        nav_barcode: 'বারকোড স্ক্যানার',
        nav_settings: 'সেটিংস',
        nav_tools_header: 'ব্যবসা সরঞ্জাম',
        nav_news: 'বাজার খবর',
        nav_autopilot: 'AI অটো পাইলট',
        nav_notifications: 'বিজ্ঞপ্তি',
        nav_memory: 'ব্যবসা মেমোরি',
        nav_radar: 'সুযোগ রাডার',
        nav_assistant: 'Your AI Accountant',
        nav_accountant: 'AI হিসাবরক্ষক ও ট্যাক্স',
        nav_competitor: 'প্রতিযোগী রাডার',
        nav_demand: 'গ্রাহকের চাহিদা',
        nav_negotiation: 'দরদাম কোচ',
        nav_simulator: 'ব্যবসা সিমুলেটর',
        nav_time_machine: 'ভবিষ্যদ্বাণী',
        nav_translator: 'ভয়েস অনুবাদক',
        news_view_title: 'বাজার ও কৃষিপণ্য সংবাদ',
        ai_assistant_title: 'Your AI Accountant',
        ai_status_ready: 'অনলাইন • দোকানের জন্য প্রস্তুত',
        mic_tap_to_speak: 'মাইক টিপে বলুন',
        mic_helper: 'মাইক চাপুন এবং বাংলায় কথা বলুন',
        mic_sub: 'স্টক, বিক্রয় ও বাজার দরের ভয়েস নির্দেশ',
        preset_label: 'জিজ্ঞাসা করুন:',
        overview_title: 'আজকের ব্যবসার হিসাব',
        metric_sales: 'আজকের বিক্রয়',
        metric_profit: 'মোট লাভ',
        metric_products: 'মোট পণ্য',
        metric_stock_val: 'মজুদ মূল্য',
        metric_low_stock: 'স্বল্প স্টক',
        metric_expiry: 'মেয়াদোত্তীর্ণের কাছাকাছি',
        actions_title: 'দ্রুত পদক্ষেপ',
        act_add_prod: 'পণ্য যোগ করুন',
        act_scan: 'বারকোড স্ক্যান',
        act_inventory: 'স্টক দেখুন',
        act_sale: 'বিক্রয় লিখুন',
        act_reports: 'রিপোর্ট দেখুন',
        recent_sales_title: 'সাম্প্রতিক বিক্রয়',
        alerts_title: 'সতর্কতা ও নোটিশ',
        wizard_title: 'দোকান সেটআপ সম্পন্ন করুন',
        wizard_desc: 'দোকানের নাম এবং বিভাগ নির্বাচন করুন।',
        chart_sales_title: 'বিক্রয় ও রাজস্ব বিবরণী',
        comp_title: 'প্রতিযোগী দর বিশ্লেষণ',
        comp_sub: 'স্থানীয় বাজার দর ও মার্জিন বিশ্লেষণ',
        demand_title: 'গ্রাহক চাহিদা বিশ্লেষক',
        demand_sub: 'উচ্চ চাহিদাসম্পন্ন পণ্যের তালিকা',
        neg_title: 'দরদাম কোচ',
        neg_sub: 'মন্ডি দর ও ক্রয় পরামর্শ',
        trans_title: 'ব্যবসায়িক অনুবাদক',
        trans_sub: 'আন্তঃরাজ্য বাণিজ্যের জন্য দ্রুত অনুবাদ',
        pref_ui_lang: 'প্রদর্শন ভাষা',
        pref_ai_lang: 'AI ভাষা',
        pref_news_lang: 'সংবাদ ভাষা',
        weather_humidity: 'আর্দ্রতা',
        weather_wind: 'বাতাসের গতি',
        weather_rain: 'বৃষ্টিপাত',
        weather_updated: 'সর্বশেষ আপডেট',
        btn_detect_location: 'অবস্থান শনাক্ত করুন',
        btn_confirm_action: 'সংরক্ষণ করুন',
        btn_cancel_action: 'বাতিল করুন',
        btn_logout: 'লগআউট',
        nav_settings_lang: 'ভাষা সেটিংস',
        setting_lang_title: 'ডিসপ্লে ভাষা',
        setting_lang_desc: 'ড্যাশবোর্ড এবং রিপোর্টের জন্য আপনার পছন্দের ভাষা নির্বাচন করুন।'
    },
    ta: {
        nav_home: 'முகப்பு பலகை',
        nav_inventory: 'சரக்கு இருப்பு',
        nav_multi_store: 'கிளைகள்',
        nav_shelf_scanner: 'ஷெல்ஃப் ஸ்கேனர்',
        nav_sales: 'விற்பனை ஏடு',
        nav_purchases: 'கொள்முதல் (சரக்கு)',
        nav_reports: 'லாப அறிக்கைகள்',
        nav_barcode: 'பார்கோடு ஸ்கேனர்',
        nav_settings: 'அமைப்புகள்',
        nav_tools_header: 'வணிகக் கருவிகள்',
        nav_news: 'சந்தை செய்திகள்',
        nav_autopilot: 'AI தானியங்கி',
        nav_notifications: 'அறிவிப்புகள்',
        nav_memory: 'வணிக நினைவகம்',
        nav_radar: 'வாய்ப்பு ரேடார்',
        nav_assistant: 'Your AI Accountant',
        nav_accountant: 'AI கணக்காளர் & வரி',
        nav_competitor: 'போட்டியாளர் ரேடார்',
        nav_demand: 'வாடிக்கையாளர் தேவை',
        nav_negotiation: 'பேரம்பேசுதல் வழிகாட்டி',
        nav_simulator: 'வணிக உருவகப்படுத்தி',
        nav_time_machine: 'எதிர்காலக் கணிப்பு',
        nav_translator: 'குரல் மொழிபெயர்ப்பாளர்',
        news_view_title: 'சந்தை விலை மற்றும் செய்திகள்',
        ai_assistant_title: 'Your AI Accountant',
        ai_status_ready: 'ஆன்லைன் • கடைக்கு உதவ தயார்',
        mic_tap_to_speak: 'மைக் அழுத்திப் பேசவும்',
        mic_helper: 'மைக்கை அழுத்தி தமிழில் பேசவும்',
        mic_sub: 'சரக்கு, விற்பனை மற்றும் சந்தை விலைக்கான குரல் கட்டளைகள்',
        preset_label: 'கேட்டுப் பாருங்கள்:',
        overview_title: 'இன்றைய வணிகக் கணக்கு',
        metric_sales: 'இன்றைய விற்பனை',
        metric_profit: 'மொத்த லாபம்',
        metric_products: 'மொத்த பொருட்கள்',
        metric_stock_val: 'சரக்கு மதிப்பு',
        metric_low_stock: 'குறைந்த இருப்பு',
        metric_expiry: 'விரைவில் காலாவதி',
        actions_title: 'விரைவு நடவடிக்கைகள்',
        act_add_prod: 'பொருள் சேர்க்க',
        act_scan: 'பார்கோடு ஸ்கேன்',
        act_inventory: 'இருப்பு பார்க்க',
        act_sale: 'விற்பனை பதிவு',
        act_reports: 'அறிக்கைகள்',
        recent_sales_title: 'சமீபத்திய விற்பனை',
        alerts_title: 'எச்சரிக்கைகள் & அறிவிப்புகள்',
        wizard_title: 'கடை சுயவிவரத்தை அமைக்கவும்',
        wizard_desc: 'கடையின் பெயர் மற்றும் வகையைத் தேர்ந்தெடுக்கவும்.',
        chart_sales_title: 'விற்பனை & வருவாய் வரைபடம்',
        comp_title: 'போட்டியாளர் விலை பகுப்பாய்வு',
        comp_sub: 'உள்ளூர் சந்தை விலைகளைக் கண்காணிக்கவும்',
        demand_title: 'வாடிக்கையாளர் தேவை கண்காணிப்பாளர்',
        demand_sub: 'அதிக தேவை உள்ள பொருட்களை பகுப்பாய்வு செய்யவும்',
        neg_title: 'பேரம்பேசுதல் வழிகாட்டி',
        neg_sub: 'சந்தை விலை மற்றும் கொள்முதல் ஆலோசனை',
        trans_title: 'வணிக மொழிபெயர்ப்பாளர்',
        trans_sub: 'வணிகத்திற்கான உடனடி குரல் மொழிபெயர்ப்பு',
        pref_ui_lang: 'திரை மொழி',
        pref_ai_lang: 'AI மொழி',
        pref_news_lang: 'செய்தி மொழி',
        weather_humidity: 'ஈரப்பதம்',
        weather_wind: 'காற்று வேகம்',
        weather_rain: 'மழைப்பொழிவு',
        weather_updated: 'கடைசி புதுப்பிப்பு',
        btn_detect_location: 'இருப்பிடத்தைக் கண்டறி',
        btn_confirm_action: 'சேமிக்க',
        btn_cancel_action: 'ரத்துசெய்',
        btn_logout: 'வெளியேறு',
        nav_settings_lang: 'மொழி அமைப்புகள்',
        setting_lang_title: 'காட்சி மொழி',
        setting_lang_desc: 'டாஷ்போர்டு மற்றும் அறிக்கைகளுக்கான உங்கள் விருப்ப மொழியைத் தேர்வுசெய்யவும்.'
    },
    te: {
        nav_home: 'డాష్‌బోర్డ్',
        nav_inventory: 'సరుకుల నిల్వ',
        nav_multi_store: 'శాఖలు',
        nav_shelf_scanner: 'షెల్ఫ్ స్కానర్',
        nav_sales: 'అమ్మకాల రిజిస్టర్',
        nav_purchases: 'కొనుగోళ్లు (స్టాక్)',
        nav_reports: 'లాభ నివేదికలు',
        nav_barcode: 'బార్‌కోడ్ స్కానర్',
        nav_settings: 'సెట్టింగ్‌లు',
        nav_tools_header: 'వ్యాపార సాధనాలు',
        nav_news: 'మార్కెట్ వార్తలు',
        nav_autopilot: 'AI ఆటోపైలట్',
        nav_notifications: 'నోటిఫికేషన్‌లు',
        nav_memory: 'వ్యాపార జ్ఞాపకశక్తి',
        nav_radar: 'అవకాశాల రాడార్',
        nav_assistant: 'Your AI Accountant',
        nav_accountant: 'AI అకౌంటెంట్ & పన్ను',
        nav_competitor: 'పోటీదారుల రాడార్',
        nav_demand: 'కస్టమర్ డిమాండ్',
        nav_negotiation: 'బేరసారాల కోచ్',
        nav_simulator: 'వ్యాపార సిమ్యులేటర్',
        nav_time_machine: 'భవిష్యత్ అంచనా',
        nav_translator: 'వాయిస్ అనువాదకుడు',
        news_view_title: 'మార్కెట్ ధరలు & తాజా వార్తలు',
        ai_assistant_title: 'Your AI Accountant',
        ai_status_ready: 'ఆన్‌లైన్ • దుకాణం కోసం సిద్ధంగా ఉంది',
        mic_tap_to_speak: 'మైక్ నొక్కి మాట్లాడండి',
        mic_helper: 'మైక్ నొక్కి తెలుగులో మాట్లాడండి',
        mic_sub: 'స్టాక్, అమ్మకాలు మరియు మార్కెట్ ధరల కోసం వాయిస్ కమాండ్‌లు',
        preset_label: 'అడగండి:',
        overview_title: 'నేటి వ్యాపార సారాంశం',
        metric_sales: 'నేటి అమ్మకాలు',
        metric_profit: 'మొత్తం లాభం',
        metric_products: 'మొత్తం వస్తువులు',
        metric_stock_val: 'స్టాక్ విలువ',
        metric_low_stock: 'తక్కువ స్టాక్',
        metric_expiry: 'గడువు ముగియనున్నవి',
        actions_title: 'శీఘ్ర చర్యలు',
        act_add_prod: 'వస్తువును జోడించండి',
        act_scan: 'బార్‌కోడ్ స్కాన్',
        act_inventory: 'స్టాక్ చూడండి',
        act_sale: 'అమ్మకం నమోదు',
        act_reports: 'నివేదికలు',
        recent_sales_title: 'ఇటీవలి అమ్మకాలు',
        alerts_title: 'హెచ్చరికలు & నోటీసులు',
        wizard_title: 'దుకాణం ప్రొఫైల్‌ను సెటప్ చేయండి',
        wizard_desc: 'దుకాణం పేరు మరియు వర్గాన్ని ఎంచుకోండి.',
        chart_sales_title: 'అమ్మకాలు & ఆదాయ విశ్లేషణ',
        comp_title: 'పోటీదారుల ధరల విశ్లేషణ',
        comp_sub: 'స్థానిక మార్కెట్ ధరలను ట్రాక్ చేయండి',
        demand_title: 'కస్టమర్ డిమాండ్ లిజనర్',
        demand_sub: 'ఎక్కువ డిమాండ్ ఉన్న వస్తువుల విశ్లేషణ',
        neg_title: 'బేరసారాల కోచ్',
        neg_sub: 'మార్కెట్ ధరలు & కొనుగోలు సలహా',
        trans_title: 'వ్యాపార అనువాదకుడు',
        trans_sub: 'వ్యాపారం కోసం శీఘ్ర వాయిస్ అనువాదం',
        pref_ui_lang: 'స్క్రీన్ భాష',
        pref_ai_lang: 'AI భాష',
        pref_news_lang: 'వార్తల భాష',
        weather_humidity: 'తేమ',
        weather_wind: 'గాలి వేగం',
        weather_rain: 'వర్షపాతం',
        weather_updated: 'చివరి అప్‌డేట్',
        btn_detect_location: 'లొకేషన్ గుర్తించండి',
        btn_confirm_action: 'సేవ్ చేయండి',
        btn_cancel_action: 'రద్దు చేయండి',
        btn_logout: 'లాగౌట్',
        nav_settings_lang: 'భాష సెట్టింగ్‌లు',
        setting_lang_title: 'డిస్ప్లే భాష',
        setting_lang_desc: 'డాష్‌బోర్డ్ మరియు నివేదికల కోసం మీ ప్రాధాన్య భాషను ఎంచుకోండి.'
    },
    ur: {
        nav_home: 'ڈیش بورڈ',
        nav_inventory: 'اسٹاک انوینٹری',
        nav_multi_store: 'شاخیں',
        nav_shelf_scanner: 'شیلف اسکینر',
        nav_sales: 'سیلز رجسٹر',
        nav_purchases: 'خریداری (اسٹاک)',
        nav_reports: 'منافع رپورٹس',
        nav_barcode: 'بارکوڈ اسکینر',
        nav_settings: 'ترتیبات',
        nav_tools_header: 'تجارتی ٹولز',
        nav_news: 'مارکیٹ خبریں',
        nav_autopilot: 'AI آٹو پائلٹ',
        nav_notifications: 'اطلاعات',
        nav_memory: 'کاروباری میموری',
        nav_radar: 'مواقع کا ریڈار',
        nav_assistant: 'Your AI Accountant',
        nav_accountant: 'AI اکاؤنٹنٹ و ٹیکس',
        nav_competitor: 'حریف ریڈار',
        nav_demand: 'گاہک کی مانگ',
        nav_negotiation: 'مول بھاؤ کوچ',
        nav_simulator: 'کاروبار سمیلیٹر',
        nav_time_machine: 'وقت کی پیشن گوئی',
        nav_translator: 'آواز مترجم',
        news_view_title: 'مارکیٹ ریٹس اور خبریں',
        ai_assistant_title: 'Your AI Accountant',
        ai_status_ready: 'آن لائن • دکان کی مدد کے لیے تیار',
        mic_tap_to_speak: 'مائیک دبا کر بولیں',
        mic_helper: 'مائیک دبائیں اور اردو میں بات کریں',
        mic_sub: 'اسٹاک، فروخت اور ریٹس کے صوتی احکامات',
        preset_label: 'پوچھ کر دیکھیں:',
        overview_title: 'آج کا کاروباری حساب',
        metric_sales: 'آج کی فروخت',
        metric_profit: 'کل منافع',
        metric_products: 'کل اشیاء',
        metric_stock_val: 'اسٹاک مالیت',
        metric_low_stock: 'کم اسٹاک',
        metric_expiry: 'قریبی میعاد ختم',
        actions_title: 'فوری اقدامات',
        act_add_prod: 'شے شامل کریں',
        act_scan: 'بارکوڈ اسکین',
        act_inventory: 'اسٹاک چیک کریں',
        act_sale: 'فروخت درج کریں',
        act_reports: 'رپورٹس دیکھیں',
        recent_sales_title: 'حالیہ فروخت',
        alerts_title: 'انتباہات و نوٹسز',
        wizard_title: 'دکان کی پروفائل مکمل کریں',
        wizard_desc: 'دکان کا نام اور زمرہ منتخب کریں۔',
        chart_sales_title: 'سیلز اور آمدنی گراف',
        comp_title: 'حریف قیمتوں کا تجزیہ',
        comp_sub: 'مقامی منڈی قیمتیں ٹریک کریں',
        demand_title: 'گاہک کی مانگ کا تجزیہ',
        demand_sub: 'زیادہ مانگ والی اشیاء کا جائزہ',
        neg_title: 'مول بھاؤ کوچ',
        neg_sub: 'منڈی ریٹس اور خریداری مشورہ',
        trans_title: 'تجارتی مترجم',
        trans_sub: 'تجارت کے لیے فوری صوتی ترجمہ',
        pref_ui_lang: 'ڈسپلے زبان',
        pref_ai_lang: 'AI زبان',
        pref_news_lang: 'خبروں کی زبان',
        weather_humidity: 'نمی',
        weather_wind: 'ہوا کی رفتار',
        weather_rain: 'بارش',
        weather_updated: 'آخری اپ ڈیٹ',
        btn_detect_location: 'مقام تلاش کریں',
        btn_confirm_action: 'محفوظ کریں',
        btn_cancel_action: 'منسوخ کریں',
        btn_logout: 'لاگ آؤٹ',
        nav_settings_lang: 'زبان کی ترتیبات',
        setting_lang_title: 'ڈسپلے زبان',
        setting_lang_desc: 'ڈیش بورڈ اور رپورٹس کے لیے اپنی پسندیدہ زبان منتخب کریں۔'
    },
    es: {
        nav_home: 'Panel Principal',
        nav_inventory: 'Inventario',
        nav_multi_store: 'Sucursales',
        nav_shelf_scanner: 'Escáner de Estantes',
        nav_sales: 'Registro de Ventas',
        nav_purchases: 'Compras (Stock)',
        nav_reports: 'Informes Financieros',
        nav_barcode: 'Escáner de Código de Barras',
        nav_settings: 'Configuración',
        nav_tools_header: 'Herramientas Comerciales',
        nav_news: 'Noticias y Mercados',
        nav_autopilot: 'Piloto Automático IA',
        nav_notifications: 'Notificaciones',
        nav_memory: 'Memoria Comercial',
        nav_radar: 'Radar de Oportunidades',
        nav_assistant: 'Your AI Accountant',
        nav_accountant: 'Contador IA e Impuestos',
        nav_competitor: 'Radar de Competidores',
        nav_demand: 'Demanda del Cliente',
        nav_negotiation: 'Asesor de Negociación',
        nav_simulator: 'Simulador de Negocio',
        nav_time_machine: 'Pronóstico Temporal',
        nav_translator: 'Traductor de Voz',
        news_view_title: 'Noticias e Inteligencia de Mercado',
        ai_assistant_title: 'Your AI Accountant',
        ai_status_ready: 'En línea • Listo para ayudar a tu tienda',
        mic_tap_to_speak: 'Toca el micrófono para hablar',
        mic_helper: 'Toca el micrófono y habla en tu idioma',
        mic_sub: 'Comandos de voz para stock, ventas y precios',
        preset_label: 'Prueba a preguntar:',
        overview_title: 'Resumen del Negocio',
        metric_sales: 'Ventas de Hoy',
        metric_profit: 'Beneficio Total',
        metric_products: 'Total de Productos',
        metric_stock_val: 'Valor del Stock',
        metric_low_stock: 'Stock Bajo',
        metric_expiry: 'Próximos a Vencer',
        actions_title: 'Acciones Rápidas',
        act_add_prod: 'Añadir Producto',
        act_scan: 'Escanear Código',
        act_inventory: 'Ver Inventario',
        act_sale: 'Registrar Venta',
        act_reports: 'Informes',
        recent_sales_title: 'Ventas Recientes',
        alerts_title: 'Alertas y Notificaciones',
        wizard_title: 'Configura el Perfil de tu Tienda',
        wizard_desc: 'Ingresa el nombre y tipo de tienda para activar la IA.',
        chart_sales_title: 'Ventas e Ingresos',
        comp_title: 'Análisis de Precios de Competidores',
        comp_sub: 'Rastrea precios locales y márgenes de competencia',
        demand_title: 'Monitor de Demanda de Clientes',
        demand_sub: 'Analiza solicitudes no atendidas y productos de alta demanda',
        neg_title: 'Asesor de Negociación',
        neg_sub: 'Precios de mercado y consejos de compra estratégica',
        trans_title: 'Traductor Comercial Multilingüe',
        trans_sub: 'Traducción instantánea de voz y texto para el comercio',
        pref_ui_lang: 'Idioma de Pantalla',
        pref_ai_lang: 'Idioma de Voz y Chat IA',
        pref_news_lang: 'Idioma de Noticias',
        weather_humidity: 'Humedad',
        weather_wind: 'Viento',
        weather_rain: 'Lluvia',
        weather_updated: 'Última actualización',
        btn_detect_location: 'Detectar Ubicación',
        btn_confirm_action: 'Confirmar y Guardar',
        btn_cancel_action: 'Cancelar',
        btn_logout: 'Cerrar Sesión',
        nav_settings_lang: 'Configuración de Idioma',
        setting_lang_title: 'Idioma de Pantalla',
        setting_lang_desc: 'Elige tu idioma preferido para el panel, menús e informes.'
    },
    fr: {
        nav_home: 'Tableau de Bord',
        nav_inventory: 'Inventaire',
        nav_multi_store: 'Succursales',
        nav_shelf_scanner: 'Scanner de Rayon',
        nav_sales: 'Ventes',
        nav_purchases: 'Achats (Stock)',
        nav_reports: 'Rapports',
        nav_barcode: 'Scanner Code-barres',
        nav_settings: 'Paramètres',
        nav_tools_header: 'Outils Métier',
        nav_news: 'Actualités & Marchés',
        nav_autopilot: 'Pilote Automatique IA',
        nav_notifications: 'Notifications',
        nav_memory: 'Mémoire Commerciale',
        nav_radar: "Radar d'Opportunités",
        nav_assistant: 'Your AI Accountant',
        nav_accountant: 'Comptable IA & Fiscalité',
        nav_competitor: 'Radar Concurrentiel',
        nav_demand: 'Demande Client',
        nav_negotiation: 'Coach Négociation',
        nav_simulator: "Simulateur d'Entreprise",
        nav_time_machine: 'Prévisions Temporelles',
        nav_translator: 'Traducteur Vocal',
        news_view_title: 'Intelligence de Marché',
        ai_assistant_title: 'Your AI Accountant',
        ai_status_ready: 'En ligne • Prêt à vous assister',
        mic_tap_to_speak: 'Appuyez pour parler',
        mic_helper: 'Touchez le micro et parlez',
        mic_sub: 'Commandes vocales pour stock, ventes et météo',
        preset_label: 'Essayez de demander :',
        overview_title: "Aperçu de l'Activité",
        metric_sales: 'Ventes du Jour',
        metric_profit: 'Bénéfice Total',
        metric_products: 'Total Produits',
        metric_stock_val: 'Valeur du Stock',
        metric_low_stock: 'Stock Faible',
        metric_expiry: 'Expiration Proche',
        actions_title: 'Actions Rapides',
        act_add_prod: 'Ajouter Produit',
        act_scan: 'Scanner Code-barres',
        act_inventory: 'Voir Stock',
        act_sale: 'Enregistrer Vente',
        act_reports: 'Rapports',
        recent_sales_title: 'Ventes Récentes',
        alerts_title: 'Alertes & Notifications',
        wizard_title: 'Configuration du Magasin',
        wizard_desc: 'Définissez le nom et la catégorie de votre magasin.',
        chart_sales_title: 'Aperçu des Ventes et Revenus',
        comp_title: 'Prix & Concurrence',
        comp_sub: 'Suivez les prix locaux et les marges',
        demand_title: 'Écoute de la Demande Client',
        demand_sub: 'Analyse des produits les plus demandés',
        neg_title: 'Coach de Négociation',
        neg_sub: 'Conseils sur les marges et prix de marché',
        trans_title: 'Traducteur Commercial',
        trans_sub: 'Traduction vocale instantanée pour le commerce',
        pref_ui_lang: "Langue d'Affichage",
        pref_ai_lang: "Langue de l'IA",
        pref_news_lang: 'Langue des Actualités',
        weather_humidity: 'Humidité',
        weather_wind: 'Vent',
        weather_rain: 'Pluie',
        weather_updated: 'Dernière mise à jour',
        btn_detect_location: 'Détecter la Position',
        btn_confirm_action: 'Confirmer',
        btn_cancel_action: 'Annuler',
        btn_logout: 'Déconnexion',
        nav_settings_lang: 'Paramètres de Langue',
        setting_lang_title: "Langue d'Affichage",
        setting_lang_desc: 'Choisissez votre langue pour le tableau de bord et les rapports.'
    },
    de: {
        nav_home: 'Übersicht',
        nav_inventory: 'Warenbestand',
        nav_multi_store: 'Filialen',
        nav_shelf_scanner: 'Regalscanner',
        nav_sales: 'Verkäufe',
        nav_purchases: 'Einkauf (Bestand)',
        nav_reports: 'Berichte',
        nav_barcode: 'Barcode-Scanner',
        nav_settings: 'Einstellungen',
        nav_tools_header: 'Geschäftstools',
        nav_news: 'Marktnachrichten',
        nav_autopilot: 'KI-Autopilot',
        nav_notifications: 'Benachrichtigungen',
        nav_memory: 'Geschäftsgedächtnis',
        nav_radar: 'Chancenradar',
        nav_assistant: 'Your AI Accountant',
        nav_accountant: 'KI-Buchhalter & Steuern',
        nav_competitor: 'Wettbewerbsradar',
        nav_demand: 'Kundennachfrage',
        nav_negotiation: 'Verhandlungscoach',
        nav_simulator: 'Geschäftssimulator',
        nav_time_machine: 'Zeitprognose',
        nav_translator: 'Sprachübersetzer',
        news_view_title: 'Markt- und Preisnachrichten',
        ai_assistant_title: 'Your AI Accountant',
        ai_status_ready: 'Online • Bereit für Ihren Laden',
        mic_tap_to_speak: 'Mikrofon zum Sprechen tippen',
        mic_helper: 'Mikrofon antippen und sprechen',
        mic_sub: 'Sprachbefehle für Bestand, Verkauf und Wetter',
        preset_label: 'Versuchen Sie zu fragen:',
        overview_title: 'Geschäftsübersicht',
        metric_sales: 'Heutige Verkäufe',
        metric_profit: 'Gesamtgewinn',
        metric_products: 'Artikel Gesamt',
        metric_stock_val: 'Warenwert',
        metric_low_stock: 'Geringer Bestand',
        metric_expiry: 'Bald ablaufend',
        actions_title: 'Schnellaktionen',
        act_add_prod: 'Artikel hinzufügen',
        act_scan: 'Barcode scannen',
        act_inventory: 'Bestand ansehen',
        act_sale: 'Verkauf erfassen',
        act_reports: 'Berichte',
        recent_sales_title: 'Letzte Verkäufe',
        alerts_title: 'Warnungen & Hinweise',
        wizard_title: 'Ladenprofil einrichten',
        wizard_desc: 'Geben Sie Name und Kategorie für Ihr intelligentes Hauptbuch ein.',
        chart_sales_title: 'Umsatz- und Verkaufsübersicht',
        comp_title: 'Wettbewerbspreisanalyse',
        comp_sub: 'Lokale Marktpreise und Margen verfolgen',
        demand_title: 'Kundennachfrage-Analyse',
        demand_sub: 'Analyse beliebter Produkte',
        neg_title: 'Verhandlungscoach',
        neg_sub: 'Strategische Margenberatung',
        trans_title: 'Geschäftsübersetzer',
        trans_sub: 'Sofortige Sprachübersetzung für den Handel',
        pref_ui_lang: 'Anzeigesprache',
        pref_ai_lang: 'KI-Sprache',
        pref_news_lang: 'Nachrichtensprache',
        weather_humidity: 'Luftfeuchtigkeit',
        weather_wind: 'Wind',
        weather_rain: 'Regen',
        weather_updated: 'Zuletzt aktualisiert',
        btn_detect_location: 'Standort ermitteln',
        btn_confirm_action: 'Bestätigen',
        btn_cancel_action: 'Abbrechen',
        btn_logout: 'Abmelden',
        nav_settings_lang: 'Spracheinstellungen',
        setting_lang_title: 'Anzeigesprache',
        setting_lang_desc: 'Wählen Sie Ihre bevorzugte Sprache für Menüs und Berichte.'
    },
    ar: {
        nav_home: 'لوحة التحكم',
        nav_inventory: 'المخزون',
        nav_multi_store: 'الفروع',
        nav_shelf_scanner: 'ماسح الرفوف',
        nav_sales: 'سجل المبيعات',
        nav_purchases: 'المشتريات (المخزون)',
        nav_reports: 'التقارير المالية',
        nav_barcode: 'ماسح الباركود',
        nav_settings: 'الإعدادات',
        nav_tools_header: 'أدوات الأعمال',
        nav_news: 'أخبار السوق',
        nav_autopilot: 'الطيار الآلي الذكي',
        nav_notifications: 'الإشعارات',
        nav_memory: 'ذاكرة العمل',
        nav_radar: 'رادار الفرص',
        nav_assistant: 'Your AI Accountant',
        nav_accountant: 'المحاسب الذكي والضرائب',
        nav_competitor: 'رادار المنافسين',
        nav_demand: 'طلب العملاء',
        nav_negotiation: 'مدرب التفاوض',
        nav_simulator: 'محاكي الأعمال',
        nav_time_machine: 'توقع الوقت',
        nav_translator: 'المترجم الصوتي',
        news_view_title: 'أخبار السوق والأسعار',
        ai_assistant_title: 'Your AI Accountant',
        ai_status_ready: 'متصل • جاهز لمساعدة متجرك',
        mic_tap_to_speak: 'اضغط للتحدث',
        mic_helper: 'المس الميكروفون وتحدث بلغتك',
        mic_sub: 'أوامر صوتية للمخزون والمبيعات والطقس',
        preset_label: 'جرب أن تسأل:',
        overview_title: 'ملخص الأعمال اليوم',
        metric_sales: 'مبيعات اليوم',
        metric_profit: 'إجمالي الربح',
        metric_products: 'إجمالي المنتجات',
        metric_stock_val: 'قيمة المخزون',
        metric_low_stock: 'مخزون منخفض',
        metric_expiry: 'قريب الانتهاء',
        actions_title: 'إجراءات سريعة',
        act_add_prod: 'إضافة منتج',
        act_scan: 'مسح الباركود',
        act_inventory: 'عرض المخزون',
        act_sale: 'تسجيل بيع',
        act_reports: 'التقارير',
        recent_sales_title: 'المبيعات الأخيرة',
        alerts_title: 'التنبيهات والإشعارات',
        wizard_title: 'إعداد ملف المتجر',
        wizard_desc: 'أدخل اسم وفئة متجرك لتفعيل السجل الذكي.',
        chart_sales_title: 'نظرة عامة على المبيعات والإيرادات',
        comp_title: 'تحليل أسعار المنافسين',
        comp_sub: 'تتبع الأسعار المحلية وهوامش المنافسة',
        demand_title: 'مستمع طلبات العملاء',
        demand_sub: 'تحليل المنتجات الأكثر طلباً',
        neg_title: 'مدرب التفاوض مع الموردين',
        neg_sub: 'نصائح حول هوامش الشراء',
        trans_title: 'مترجم الأعمال التجاري',
        trans_sub: 'ترجمة صوتية وفورية للتجارة',
        pref_ui_lang: 'لغة العرض',
        pref_ai_lang: 'لغة الذكاء الاصطناعي',
        pref_news_lang: 'لغة الأخبار',
        weather_humidity: 'الرطوبة',
        weather_wind: 'سرعة الرياح',
        weather_rain: 'الأمطار',
        weather_updated: 'آخر تحديث',
        btn_detect_location: 'تحديد الموقع',
        btn_confirm_action: 'تأكيد وحفظ',
        btn_cancel_action: 'إلغاء',
        btn_logout: 'تسجيل الخروج',
        nav_settings_lang: 'إعدادات اللغة',
        setting_lang_title: 'لغة واجهة العرض',
        setting_lang_desc: 'اختر لغتك المفضلة لعرض القوائم والتقارير.'
    },
    zh: {
        nav_home: '仪表板',
        nav_inventory: '库存管理',
        nav_multi_store: '分店管理',
        nav_shelf_scanner: '货架扫描仪',
        nav_sales: '销售记录',
        nav_purchases: '采购（进货）',
        nav_reports: '财务报告',
        nav_barcode: '条形码与二维码扫描',
        nav_settings: '系统设置',
        nav_tools_header: '专业工具',
        nav_news: '市场行情',
        nav_autopilot: 'AI 自动助理',
        nav_notifications: '通知中心',
        nav_memory: '商业记忆',
        nav_radar: '商业机遇雷达',
        nav_assistant: 'Your AI Accountant',
        nav_accountant: 'AI 会计与税务',
        nav_competitor: '竞争对手监测',
        nav_demand: '客户需求追踪',
        nav_negotiation: '商务谈判顾问',
        nav_simulator: '商业模拟器',
        nav_time_machine: '经营预测',
        nav_translator: '语音翻译',
        news_view_title: '市场动态与新闻',
        ai_assistant_title: 'Your AI Accountant',
        ai_status_ready: '在线 • 随时为您服务',
        mic_tap_to_speak: '点击麦克风说话',
        mic_helper: '轻点麦克风即可语音输入',
        mic_sub: '查询库存、记录销售、天气与行情',
        preset_label: '您可以尝试：',
        overview_title: '今日经营概况',
        metric_sales: '今日销售额',
        metric_profit: '总利润',
        metric_products: '商品总数',
        metric_stock_val: '库存总值',
        metric_low_stock: '缺货预警',
        metric_expiry: '临期商品',
        actions_title: '快捷操作',
        act_add_prod: '添加商品',
        act_scan: '扫码入库',
        act_inventory: '查看库存',
        act_sale: '记一笔账',
        act_reports: '查看报表',
        recent_sales_title: '近期销售记录',
        alerts_title: '重要提醒与预警',
        wizard_title: '完成店铺档案设置',
        wizard_desc: '选择您的店铺名称和类别以开启智能管理。',
        chart_sales_title: '销售与收入图表',
        comp_title: '竞争对手价格分析',
        comp_sub: '追踪本地市场行情与利润空间',
        demand_title: '客户需求分析',
        demand_sub: '分析热销商品与未满足的需求',
        neg_title: '进货谈判顾问',
        neg_sub: '批发行情与采购建议',
        trans_title: '多语言商务翻译',
        trans_sub: '实时语音与文本翻译',
        pref_ui_lang: '界面显示语言',
        pref_ai_lang: 'AI 语音语言',
        pref_news_lang: '新闻资讯语言',
        weather_humidity: '湿度',
        weather_wind: '风速',
        weather_rain: '降雨量',
        weather_updated: '更新时间',
        btn_detect_location: '定位当前城市',
        btn_confirm_action: '确认并执行',
        btn_cancel_action: '取消',
        btn_logout: '退出登录',
        nav_settings_lang: '语言设置',
        setting_lang_title: '界面显示语言',
        setting_lang_desc: '选择您在系统界面和报表中最常用的语言。'
    },
    ja: {
        nav_home: 'ダッシュボード',
        nav_inventory: '在庫管理',
        nav_multi_store: '店舗一覧',
        nav_shelf_scanner: '棚スキャナー',
        nav_sales: '売上台帳',
        nav_purchases: '仕入れ（在庫）',
        nav_reports: '財務レポート',
        nav_barcode: 'バーコードスキャナー',
        nav_settings: '設定',
        nav_tools_header: '業務ツール',
        nav_news: '市場ニュース',
        nav_autopilot: 'AIオートパイロット',
        nav_notifications: '通知',
        nav_memory: 'ビジネス記憶',
        nav_radar: 'ビジネスレーダー',
        nav_assistant: 'Your AI Accountant',
        nav_accountant: 'AI会計・税務',
        nav_competitor: '競合分析',
        nav_demand: '顧客需要',
        nav_negotiation: '交渉コーチ',
        nav_simulator: 'シミュレーター',
        nav_time_machine: '予測分析',
        nav_translator: '音声翻訳',
        news_view_title: '市場動向とニュース',
        ai_assistant_title: 'Your AI Accountant',
        ai_status_ready: 'オンライン • サポート準備完了',
        mic_tap_to_speak: 'タップして話す',
        mic_helper: 'マイクをタップして日本語で指示',
        mic_sub: '在庫、売上、相場、天気の音声操作',
        preset_label: 'おすすめの質問：',
        overview_title: '本日の業務サマリー',
        metric_sales: '本日の売上',
        metric_profit: '総利益',
        metric_products: '商品総数',
        metric_stock_val: '在庫総額',
        metric_low_stock: '在庫不足',
        metric_expiry: '賞味期限間近',
        actions_title: 'クイックアクション',
        act_add_prod: '商品追加',
        act_scan: 'コード読取',
        act_inventory: '在庫確認',
        act_sale: '売上記録',
        act_reports: 'レポート',
        recent_sales_title: '最近の売上',
        alerts_title: 'アラート通知',
        wizard_title: '店舗プロフィールの設定',
        wizard_desc: '店舗名と業種を設定してAI機能を有効化します。',
        chart_sales_title: '売上と収益の推移',
        comp_title: '競合価格分析',
        comp_sub: '地域相場とマージンを追跡',
        demand_title: '顧客需要モニター',
        demand_sub: '人気商品と未充足の需要を分析',
        neg_title: '仕入れ交渉コーチ',
        neg_sub: '仕入れ値とマージンのアドバイス',
        trans_title: 'ビジネス翻訳',
        trans_sub: '取引のための即時音声翻訳',
        pref_ui_lang: '表示言語',
        pref_ai_lang: 'AI言語',
        pref_news_lang: 'ニュース言語',
        weather_humidity: '湿度',
        weather_wind: '風速',
        weather_rain: '降水量',
        weather_updated: '更新時間',
        btn_detect_location: '現在地を取得',
        btn_confirm_action: '確定・保存',
        btn_cancel_action: 'キャンセル',
        btn_logout: 'ログアウト',
        nav_settings_lang: '言語設定',
        setting_lang_title: '表示言語の設定',
        setting_lang_desc: 'ダッシュボードやレポートの表示言語を選択してください。'
    },
    ru: {
        nav_home: 'Панель управления',
        nav_inventory: 'Склад и товары',
        nav_multi_store: 'Филиалы',
        nav_shelf_scanner: 'Сканер полок',
        nav_sales: 'Журнал продаж',
        nav_purchases: 'Закупки (Склад)',
        nav_reports: 'Отчеты о прибыли',
        nav_barcode: 'Сканер штрихкодов',
        nav_settings: 'Настройки',
        nav_tools_header: 'Бизнес-инструменты',
        nav_news: 'Новости рынка',
        nav_autopilot: 'AI Автопилот',
        nav_notifications: 'Уведомления',
        nav_memory: 'Память бизнеса',
        nav_radar: 'Радар возможностей',
        nav_assistant: 'Your AI Accountant',
        nav_accountant: 'AI Бухгалтер и налоги',
        nav_competitor: 'Радар конкурентов',
        nav_demand: 'Спрос клиентов',
        nav_negotiation: 'Советник по закупкам',
        nav_simulator: 'Бизнес-симулятор',
        nav_time_machine: 'Прогноз на будущее',
        nav_translator: 'Голосовой переводчик',
        news_view_title: 'Новости рынка и цены',
        ai_assistant_title: 'Your AI Accountant',
        ai_status_ready: 'В сети • Готов помочь вашему магазину',
        mic_tap_to_speak: 'Нажмите микрофон для ввода',
        mic_helper: 'Коснитесь микрофона и говорите',
        mic_sub: 'Голосовые команды для склада, продаж и погоды',
        preset_label: 'Попробуйте спросить:',
        overview_title: 'Сводка за сегодня',
        metric_sales: 'Продажи сегодня',
        metric_profit: 'Общая прибыль',
        metric_products: 'Всего товаров',
        metric_stock_val: 'Стоимость склада',
        metric_low_stock: 'Мало на складе',
        metric_expiry: 'Истекает срок',
        actions_title: 'Быстрые действия',
        act_add_prod: 'Добавить товар',
        act_scan: 'Сканировать код',
        act_inventory: 'Проверить склад',
        act_sale: 'Записать продажу',
        act_reports: 'Отчеты',
        recent_sales_title: 'Последние продажи',
        alerts_title: 'Предупреждения и алерты',
        wizard_title: 'Настройка профиля магазина',
        wizard_desc: 'Укажите название и категорию для умного учета.',
        chart_sales_title: 'График продаж и доходов',
        comp_title: 'Анализ цен конкурентов',
        comp_sub: 'Отслеживание рыночных цен и маржи',
        demand_title: 'Анализ спроса клиентов',
        demand_sub: 'Популярные товары и запросы',
        neg_title: 'Советник по переговорам',
        neg_sub: 'Рыночные цены и рекомендации',
        trans_title: 'Деловой переводчик',
        trans_sub: 'Мгновенный голосовой перевод',
        pref_ui_lang: 'Язык интерфейса',
        pref_ai_lang: 'Язык AI помощника',
        pref_news_lang: 'Язык новостей',
        weather_humidity: 'Влажность',
        weather_wind: 'Скорость ветра',
        weather_rain: 'Осадки',
        weather_updated: 'Обновлено',
        btn_detect_location: 'Определить локацию',
        btn_confirm_action: 'Подтвердить',
        btn_cancel_action: 'Отмена',
        btn_logout: 'Выйти',
        nav_settings_lang: 'Языковые настройки',
        setting_lang_title: 'Язык интерфейса',
        setting_lang_desc: 'Выберите язык для панели управления и отчетов.'
    }
};


// ════════════════════════════════════════════════
// SESSION VERIFICATION & STARTUP
// ════════════════════════════════════════════════

async function initDashboard() {
    const token = localStorage.getItem('shopo_auth_token');
    if (!token) {
        // Not logged in — redirect to auth
        window.location.href = '/auth/';
        return;
    }

    try {
        const response = await fetch('/api/auth/session', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await response.json();

        if (!response.ok || !data.success || !data.data?.user) {
            // Invalid or expired session
            localStorage.removeItem('shopo_auth_token');
            localStorage.removeItem('shopo_user');
            window.location.href = '/auth/';
            return;
        }

        currentUser = data.data.user;
        renderUserData(currentUser);

        // Load live dukaan inventory, sales, and business metrics
        loadIndustryTaxonomies();
        fetchInventorySummary();
        fetchInventory();
        fetchFinancials();
        fetchSales();

        // Feature 1, 2, 4: Regional Preferences, Clock, Weather & News Systems
        await loadUserPreferences();
        startLiveClock();
        fetchLiveWeather(userPreferences.selected_city || 'Delhi');
        initNewsSystem();
        initMarketRatesSystem();
        updateNotificationBadge();

        // Check if welcome modal should be displayed
        const hasSeenWelcome = localStorage.getItem('shopo_welcome_seen');
        if (!hasSeenWelcome) {
            openWelcomeModal();
        }
    } catch (err) {
        console.error('Session check failed:', err);
        // Offline or connection issue
    }
}

function renderUserData(user) {
    const fullName = user.full_name || 'Dukandar';
    const shopName = user.shop_name || 'My Shop';
    const initials = fullName.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'SR';

    // Header updates
    document.getElementById('headerShopName').textContent = shopName;
    document.getElementById('headerUserName').textContent = fullName;
    document.getElementById('headerUserInitials').textContent = initials;

    // Sidebar updates
    document.getElementById('sidebarUserName').textContent = fullName;
    document.getElementById('sidebarUserShop').textContent = shopName;
    document.getElementById('sidebarUserInitials').textContent = initials;

    // Welcome Greeting update (Prompt Section 3)
    const welcomeGreeting = document.getElementById('dashboardWelcomeGreeting');
    const welcomeSubtitle = document.getElementById('dashboardWelcomeSubtitle');
    if (welcomeGreeting) {
        const hour = new Date().getHours();
        let timeSalutation = "Good Morning!";
        if (hour >= 12 && hour < 17) timeSalutation = "Good Afternoon!";
        else if (hour >= 17 || hour < 4) timeSalutation = "Good Evening!";
        welcomeGreeting.textContent = `${timeSalutation} Here's what's happening with ${shopName} today.`;
    }
    if (welcomeSubtitle) {
        welcomeSubtitle.textContent = `Live dukaan overview • All metrics calculated from your saved business records.`;
    }

    // Settings view updates
    document.getElementById('settingsShopName').textContent = shopName;
    document.getElementById('settingsShopType').textContent = user.shop_type || 'Grocery & Kirana Store';
    document.getElementById('settingsOwnerName').textContent = fullName;
    document.getElementById('settingsMobile').textContent = user.mobile || '-';
    document.getElementById('settingsEmail').textContent = user.email || '-';

    // Setup Wizard visibility check
    const wizard = document.getElementById('setupWizardCard');
    if (!user.is_shop_setup_complete || !user.shop_name) {
        wizard.style.display = 'flex';
    } else {
        wizard.style.display = 'none';
    }
}

// ════════════════════════════════════════════════
// WELCOME EXPERIENCE MODAL
// ════════════════════════════════════════════════

function openWelcomeModal() {
    const modal = document.getElementById('welcomeModal');
    if (modal) modal.classList.add('active');
    closeUserDropdown();
}

function dismissWelcomeModal() {
    const modal = document.getElementById('welcomeModal');
    if (modal) modal.classList.remove('active');
    localStorage.setItem('shopo_welcome_seen', 'true');
}

// ════════════════════════════════════════════════
// NAVIGATION VIEW SWITCHER
// ════════════════════════════════════════════════

function switchNav(viewName) {
    // Hide all view sections
    document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));

    // Show target section
    const target = document.getElementById(`view-${viewName}`);
    if (target) {
        target.classList.add('active');
    }

    // Update desktop sidebar buttons
    document.querySelectorAll('.app-sidebar .nav-item').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === viewName);
    });

    // Update mobile nav buttons
    document.querySelectorAll('.mobile-nav-bar .mobile-nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.view === viewName);
    });

    // Close mobile drawer if open
    const sidebar = document.getElementById('appSidebar');
    if (sidebar) sidebar.classList.remove('open');

    // Trigger data refresh based on view
    if (viewName === 'inventory') {
        fetchInventory();
    } else if (viewName === 'home') {
        fetchInventorySummary();
        fetchFinancials();
        fetchSales();
    } else if (viewName === 'sales') {
        fetchSales();
        fetchFinancials();
    } else if (viewName === 'reports') {
        fetchFinancials();
    } else if (viewName === 'time_machine') {
        initTimeMachineView();
    } else if (viewName === 'accountant') {
        initAccountantView();
    } else if (viewName === 'simulator') {
        initSimulatorView();
    } else if (viewName === 'multi_store') {
        initMultiStoreView();
    } else if (viewName === 'shelf_scanner') {
        initShelfScannerView();
    } else if (viewName === 'competitor') {
        initCompetitorView();
    } else if (viewName === 'demand') {
        initDemandView();
    } else if (viewName === 'negotiation') {
        initNegotiationView();
    } else if (viewName === 'translator') {
        initTranslatorView();
    } else if (viewName === 'autopilot') {
        loadAutopilotView();
    } else if (viewName === 'notifications') {
        loadNotificationsView();
    } else if (viewName === 'memory') {
        loadMemoryGraphView();
    } else if (viewName === 'radar') {
        loadOpportunityRadarView();
    } else if (viewName === 'news') {
        if (currentNewsCategory === 'market_rates') {
            fetchMarketDashboard();
        } else {
            fetchNewsFeed(currentNewsCategory, currentNewsLang);
        }
    }


    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function toggleSidebar() {
    const sidebar = document.getElementById('appSidebar');
    if (sidebar) sidebar.classList.toggle('open');
}

// ════════════════════════════════════════════════
// LANGUAGE & REGION CONTROLLER (Feature 1)
// ════════════════════════════════════════════════


function t(key, lang = currentLanguage) {
    const dict = I18N[lang] || I18N[lang?.split('-')[0]] || I18N.hi || I18N.en;
    if (dict && dict[key]) return dict[key];
    if (I18N.en && I18N.en[key]) return I18N.en[key];
    if (I18N.hi && I18N.hi[key]) return I18N.hi[key];
    return '';
}

function openLanguageSettings() {
    switchNav('settings');
    closeUserDropdown();
    setTimeout(() => {
        const card = document.getElementById('settingLangCard');
        if (card) card.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 150);
}

function setLanguage(lang, persist = true) {
    if (!lang) lang = 'hi';
    currentLanguage = lang;
    userPreferences.ui_language = lang;

    // Handle RTL layouts for Arabic and Urdu
    const isRtl = (lang === 'ar' || lang === 'ur');
    document.documentElement.setAttribute('dir', isRtl ? 'rtl' : 'ltr');
    document.documentElement.setAttribute('lang', lang);

    // Save to persistent localStorage immediately
    localStorage.setItem('shopo_pref_ui_lang', lang);

    // Update active button pills in Settings & everywhere
    document.querySelectorAll('.lang-pill-btn, .lang-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.lang === lang);
    });

    // Update Settings UI Lang dropdown if present
    const prefUi = document.getElementById('prefUiLang');
    if (prefUi) prefUi.value = lang;
    const settingSelect = document.getElementById('settingLangSelect');
    if (settingSelect) settingSelect.value = lang;

    // Apply translations across all data-i18n elements
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        const text = t(key, lang);
        if (text) {
            el.textContent = text;
        }
    });

    // Apply translations across data-i18n-title
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const key = el.dataset.i18nTitle;
        const text = t(key, lang);
        if (text) {
            el.title = text;
        }
    });

    // Update input placeholders
    updateInputPlaceholders(lang);

    // Update live clock date format & weekday
    updateLiveClockDisplay();

    // Show saved indicator if in settings
    const savedNotice = document.getElementById('langSavedNotice');
    if (savedNotice && persist) {
        savedNotice.style.display = 'inline-flex';
        setTimeout(() => { savedNotice.style.display = 'none'; }, 2500);
    }

    // Persist to database if logged in and requested
    if (persist && currentUser) {
        saveUserPreferences({ ui_language: lang });
    }
}

function updateInputPlaceholders(lang) {
    const cmdInput = document.getElementById('cmdInput');
    if (cmdInput) {
        if (lang === 'hi') {
            cmdInput.placeholder = "यहाँ टाइप करें या बोलें... e.g. 'आज का मुनाफ़ा दिखाओ'";
        } else if (lang === 'hinglish') {
            cmdInput.placeholder = "Type karein ya boliye... e.g. 'Aaj ka munafa dikhao'";
        } else if (lang === 'mr') {
            cmdInput.placeholder = "येथे टाईप करा किंवा बोला... e.g. 'आजची विक्री दाखवा'";
        } else if (lang === 'gu') {
            cmdInput.placeholder = "અહીં ટાઈપ કરો અથવા બોલો... e.g. 'આજનો નફો બતાવો'";
        } else if (lang === 'ta') {
            cmdInput.placeholder = "இங்கே தட்டச்சு செய்யவும் அல்லது பேசவும்...";
        } else if (lang === 'te') {
            cmdInput.placeholder = "ఇక్కడ టైప్ చేయండి లేదా మాట్లాడండి...";
        } else if (lang === 'bn') {
            cmdInput.placeholder = "এখানে টাইপ করুন বা বলুন... e.g. 'আজকের লাভ দেখাও'";
        } else if (lang === 'ur') {
            cmdInput.placeholder = "یہاں ٹائپ کریں یا بولیں... e.g. 'آج کی فروخت'";
        } else if (lang === 'es') {
            cmdInput.placeholder = "Escribe o habla aquí... e.g. 'Ganancia de hoy'";
        } else if (lang === 'fr') {
            cmdInput.placeholder = "Tapez ou parlez ici... e.g. 'Bénéfice du jour'";
        } else if (lang === 'ar') {
            cmdInput.placeholder = "اكتب أو تحدث هنا... e.g. 'أرباح اليوم'";
        } else {
            cmdInput.placeholder = "Type or speak command... e.g. 'Show today's profit'";
        }
    }
}

// ════════════════════════════════════════════════
// AI ASSISTANT & MICROPHONE RECOGNITION
// ════════════════════════════════════════════════

function setupSpeechRecognition() {
    const SpeechClass = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechClass) {
        console.warn('SpeechRecognition not supported in this browser.');
        return null;
    }

    const recognizer = new SpeechClass();
    recognizer.continuous = false;
    recognizer.interimResults = false;
    recognizer.maxAlternatives = 1;

    recognizer.onstart = () => {
        isListening = true;
        isStartingRecognition = false;
        setAIAssistantState('listening');
    };

    recognizer.onresult = (event) => {
        isListening = false;
        isStartingRecognition = false;

        const transcript = event.results && event.results[0] && event.results[0][0] ? event.results[0][0].transcript : '';
        const trimmed = (transcript || '').trim();
        if (!trimmed) {
            setAIAssistantState('error', 'आवाज़ साफ़ नहीं आई (Could not hear clearly)');
            showSimulatedResponse(
                "⚠️ कोई आवाज़ साफ़ सुनाई नहीं दी। कृपया माइक दबाकर दोबारा बोलें या टाइप करें। (No speech detected. Please speak clearly or type.)"
            );
            return;
        }

        setAIAssistantState('processing');
        const input = document.getElementById('cmdInput');
        if (input) input.value = trimmed;
        processAICommand(trimmed);
    };

    recognizer.onerror = (event) => {
        console.warn('Speech recognition error:', event.error);
        isListening = false;
        isStartingRecognition = false;

        if (event.error === 'aborted') {
            setAIAssistantState('ready');
            return;
        }

        setAIAssistantState('error', 'माइक त्रुटि (Microphone error)');

        let errorMsg = "माइक में कुछ समस्या आई। कृपया टाइप करके अपना सवाल पूछें। (Speech recognition error. Please type your query.)";
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
            errorMsg = "⚠️ <strong>माइक अनुमति अस्वीकृत (Microphone Permission Denied):</strong> कृपया ब्राउज़र सेटिंग्स में जाकर माइक्रोफ़ोन की अनुमति (Allow) दें और पुनः प्रयास करें।";
        } else if (event.error === 'no-speech') {
            errorMsg = "⚠️ <strong>कोई आवाज़ नहीं मिली (No Speech Detected):</strong> माइक्रोफ़ोन ने कोई आवाज़ नहीं पकड़ी। कृपया माइक के पास बोलें या टाइप करें।";
        } else if (event.error === 'audio-capture') {
            errorMsg = "⚠️ <strong>माइक्रोफ़ोन नहीं मिला (Audio Capture Failed):</strong> माइक्रोफ़ोन हार्डवेयर उपलब्ध नहीं है या किसी अन्य ऐप द्वारा व्यस्त है।";
        } else if (event.error === 'network') {
            errorMsg = "⚠️ <strong>नेटवर्क त्रुटि (Speech Network Error):</strong> वॉइस सेवा से संपर्क नहीं हो सका। कृपया इंटरनेट जांचें या टाइप करें।";
        }
        showSimulatedResponse(errorMsg);
    };

    recognizer.onend = () => {
        isListening = false;
        isStartingRecognition = false;
        if (!isProcessingAICommand && (!window.speechSynthesis || !window.speechSynthesis.speaking)) {
            setAIAssistantState('ready');
        }
    };

    return recognizer;
}

function toggleVoiceInput() {
    // 1. Immediately cancel any ongoing speech synthesis to prevent echo feedback loops
    if (window.speechSynthesis && (window.speechSynthesis.speaking || window.speechSynthesis.pending)) {
        window.speechSynthesis.cancel();
    }

    // 2. Prevent initiating speech recognition while an AI command is actively in-flight
    if (isProcessingAICommand) {
        return;
    }

    if (!speechRecognition) {
        speechRecognition = setupSpeechRecognition();
    }

    if (!speechRecognition) {
        // Fallback for browsers without SpeechRecognition
        showSimulatedResponse(
            "आपका ब्राउज़र सीधे वॉइस इनपुट सपोर्ट नहीं करता। कृपया नीचे टेक्स्ट बॉक्स में टाइप करें। (Browser does not support Speech Recognition. Please use text input.)"
        );
        const input = document.getElementById('cmdInput');
        if (input) input.focus();
        return;
    }

    if (isListening) {
        try {
            speechRecognition.stop();
        } catch (e) {
            console.warn('Could not stop recognition:', e);
        }
        isListening = false;
        isStartingRecognition = false;
        updateListeningUI(false);
    } else {
        // Guard against rapid duplicate clicks (avoids InvalidStateError)
        if (isStartingRecognition) return;
        isStartingRecognition = true;

        // Set speech language based on current selection
        speechRecognition.lang = currentLanguage === 'en' ? 'en-IN' : 'hi-IN';
        try {
            speechRecognition.start();
        } catch (e) {
            console.warn('Could not start recognition:', e);
            isStartingRecognition = false;
            isListening = false;
            updateListeningUI(false);
        }
    }
}

let aiStateWatchdogTimer = null;

function setAIAssistantState(state, customMessage) {
    const micContainer = document.getElementById('micBtnContainer');
    const heroCard = document.getElementById('assistantHeroCard');
    const helperText = document.getElementById('micHelperText');
    const statusText = document.getElementById('aiStatusText');
    const micIcon = document.getElementById('micIcon') || (micContainer ? micContainer.querySelector('.mic-btn i') : null);

    if (!micContainer) return;

    // Clear any existing watchdog or auto-reset timers
    if (aiStateWatchdogTimer) {
        clearTimeout(aiStateWatchdogTimer);
        aiStateWatchdogTimer = null;
    }

    // Reset state classes
    micContainer.classList.remove(
        'state-ready', 'state-listening', 'state-processing', 
        'state-speaking', 'state-success', 'state-error', 'listening'
    );
    if (heroCard) {
        heroCard.classList.remove(
            'hero-state-listening', 'hero-state-processing', 
            'hero-state-speaking', 'hero-state-success', 'hero-state-error'
        );
    }

    micContainer.classList.add(`state-${state}`);
    if (heroCard && state !== 'ready') {
        heroCard.classList.add(`hero-state-${state}`);
    }

    if (state === 'listening') {
        micContainer.classList.add('listening');
    }

    // Dynamic icon switching
    if (micIcon) {
        micIcon.className = '';
        switch (state) {
            case 'listening':
                micIcon.className = 'fas fa-microphone-lines';
                break;
            case 'processing':
                micIcon.className = 'fas fa-circle-notch fa-spin';
                break;
            case 'speaking':
                micIcon.className = 'fas fa-volume-high';
                break;
            case 'success':
                micIcon.className = 'fas fa-check';
                break;
            case 'error':
                micIcon.className = 'fas fa-exclamation';
                break;
            case 'ready':
            default:
                micIcon.className = 'fas fa-microphone';
                break;
        }
    }

    switch (state) {
        case 'listening':
            if (helperText) helperText.textContent = customMessage || "सुन रहा हूँ... बोलिए (Listening...)";
            if (statusText) {
                statusText.innerHTML = '<span class="status-indicator-dot listening"></span> 🔴 सुन रहा हूँ... बोलिए (Listening to voice input...)';
                statusText.style.color = "#DC2626";
            }
            break;
        case 'processing':
            if (helperText) helperText.textContent = customMessage || "विचार कर रहा हूँ... (Thinking...)";
            if (statusText) {
                statusText.innerHTML = '<span class="status-indicator-dot processing"></span> ⚡ सोच रहा हूँ... (Processing AI Intelligence...)';
                statusText.style.color = "#D97706";
            }
            // Safety watchdog timer: never stay stuck in processing indefinitely if connection drops
            aiStateWatchdogTimer = setTimeout(() => {
                if (isProcessingAICommand) {
                    isProcessingAICommand = false;
                    const sendBtn = document.getElementById('aiSendBtn');
                    if (sendBtn) sendBtn.disabled = false;
                    setAIAssistantState('error', 'प्रतिक्रिया में अधिक समय लगा (Request timed out). कृपया पुनः प्रयास करें।');
                }
            }, 25000);
            break;
        case 'speaking':
            if (helperText) helperText.textContent = customMessage || "बोल रहा हूँ... (Speaking...)";
            if (statusText) {
                statusText.innerHTML = '<span class="status-indicator-dot speaking"></span> 🔊 उत्तर दे रहा हूँ... (Speaking...)';
                statusText.style.color = "#2563EB";
            }
            break;
        case 'success':
            if (helperText) helperText.textContent = customMessage || "सफलतापूर्वक पूर्ण! (Success!)";
            if (statusText) {
                statusText.innerHTML = '<span class="status-indicator-dot success"></span> ✅ कार्य पूर्ण हुआ (Completed)';
                statusText.style.color = "#16A34A";
            }
            aiStateWatchdogTimer = setTimeout(() => {
                if (!isListening && !isProcessingAICommand && (!window.speechSynthesis || !window.speechSynthesis.speaking)) {
                    setAIAssistantState('ready');
                }
            }, 2500);
            break;
        case 'error':
            if (helperText) helperText.textContent = customMessage || "कृपया पुनः प्रयास करें (Try Again)";
            if (statusText) {
                statusText.innerHTML = '<span class="status-indicator-dot error"></span> ⚠️ ' + (customMessage || "कृपया पुनः प्रयास करें (Please try again)");
                statusText.style.color = "#DC2626";
            }
            aiStateWatchdogTimer = setTimeout(() => {
                if (!isListening && !isProcessingAICommand && (!window.speechSynthesis || !window.speechSynthesis.speaking)) {
                    setAIAssistantState('ready');
                }
            }, 3500);
            break;
        case 'ready':
        default:
            if (helperText) helperText.textContent = (typeof I18N !== 'undefined' && I18N[currentLanguage]?.mic_tap_to_speak) || "माइक दबाकर बोलें (Tap Mic to Speak in Hindi, Hinglish, English)";
            if (statusText) {
                statusText.innerHTML = '<span class="status-indicator-dot ready"></span> Online &bull; Ready to help your shop (तैयार हूँ)';
                statusText.style.color = "var(--lime-700)";
            }
            break;
    }
}

function updateListeningUI(listening) {
    setAIAssistantState(listening ? 'listening' : 'ready');
}

function formatMarkdown(text) {
    if (!text) return '';
    return text
        .replace(/^### (.*$)/gim, '<h4 style="margin:12px 0 6px; font-weight:800; color:inherit;">$1</h4>')
        .replace(/^## (.*$)/gim, '<h3 style="margin:14px 0 8px; font-weight:800; color:inherit;">$1</h3>')
        .replace(/^# (.*$)/gim, '<h2 style="margin:16px 0 10px; font-weight:800; color:inherit;">$1</h2>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`([^`]+)`/g, '<code style="background:rgba(0,0,0,0.06); padding:2px 5px; border-radius:4px; font-family:monospace;">$1</code>')
        .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener" style="color:var(--lime-700); text-decoration:underline; font-weight:600;">$1</a>')
        .replace(/^---$/gim, '<hr style="border:none; border-top:1px solid rgba(0,0,0,0.1); margin:12px 0;">')
        .replace(/\n\n/g, '<br><br>')
        .replace(/\n(?:\*|-|•)\s+/g, '<br>&bull; ')
        .replace(/\n/g, '<br>');
}

function handleCommandSubmit(e) {
    if (e) {
        try { e.preventDefault(); } catch(err) {}
        try { e.stopPropagation(); } catch(err) {}
    }
    const input = document.getElementById('cmdInput');
    if (!input) return;
    const query = input.value.trim();
    if (!query) return;

    processAICommand(query);
    input.value = '';
}

function applyPresetCommand(text) {
    const input = document.getElementById('cmdInput');
    if (input) input.value = text;
    processAICommand(text);
}

let currentStagedActionToken = null;

async function processAICommand(query) {
    if (!query || !query.trim()) return;
    if (isProcessingAICommand) return; // Prevent duplicate rapid requests
    isProcessingAICommand = true;
    setAIAssistantState('processing');

    // If speech recognition is still running, stop it so it does not capture background noise while thinking
    if (speechRecognition && isListening) {
        try { speechRecognition.stop(); } catch(e) {}
        isListening = false;
        isStartingRecognition = false;
        updateListeningUI(false);
    }

    const box = document.getElementById('aiResponseBox');
    const body = document.getElementById('aiResponseBody');
    const intentBadge = document.getElementById('aiIntentBadge');
    const actionCard = document.getElementById('aiActionConfirmCard');
    const sendBtn = document.getElementById('aiSendBtn');

    if (sendBtn) sendBtn.disabled = true;

    if (box) {
        box.classList.add('show');
        box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    if (body) {
        body.innerHTML = `<span style="color:var(--text-muted);"><i class="fas fa-spinner fa-spin"></i> शोपो रोबो सोच रहा है (Processing universal query)...</span>`;
    }
    if (actionCard) actionCard.style.display = 'none';

    const token = localStorage.getItem('shopo_auth_token');
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    try {
        const resp = await fetch('/api/ai/chat', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                message: query.trim(),
                language: currentLanguage || 'hi'
            })
        });
        const res = await resp.json();

        if (res.success && res.data) {
            const data = res.data;
            const reply = data.reply_text || 'No response returned.';

            // Render Markdown formatting (bold, italics, lists, links)
            let formattedHtml = formatMarkdown(reply);

            if (body) {
                body.innerHTML = formattedHtml;
                if (box) box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }

            // Action status badges and intent badge text
            const intentMap = {
                'mandi_market_query': '🌾 APMC Mandi Benchmark',
                'live_weather_query': '🌤️ Live Weather Observation',
                'industrial_materials_query': '🏗️ Industrial Benchmark',
                'government_schemes_query': '🏛️ Official Govt Information',
                'business_inventory_query': '📦 Verified Store Records',
                'business_financials_query': '💰 Verified Store Financials',
                'consequential_action_staged': '⚠️ Action Confirmation Needed',
                'web_search_query': '🔍 Web Search Citations',
                'read_only_stock_query': '📦 Stock Check',
                'read_only_sales_query': '📊 Sales Summary',
                'read_only_profit_query': '📈 Profit Summary',
                'stock_valuation_query': '💰 Stock Valuation',
                'clarification_needed': '❓ Clarification Needed',
                'inward_stock_purchase': '📥 Inward Stock',
                'retail_sale': '🛒 Record Sale',
                'product_creation': '✨ New Product',
                'needs_login': '🔒 Login Required',
                'business_auth_required': '🔒 Login Required',
                'general_knowledge': '🌐 Universal Intelligence'
            };

            if (intentBadge) {
                if (data.action_status) {
                    renderActionStatusBadge(intentBadge, data.action_status);
                } else {
                    intentBadge.textContent = intentMap[data.intent] || 'Universal Intelligence';
                    intentBadge.style.background = 'var(--lime-100)';
                    intentBadge.style.color = 'var(--lime-800)';
                    intentBadge.style.border = 'none';
                }
            }

            // If action was executed directly via chat reply (status === 'saved')
            if (data.action_status === 'saved') {
                fetchInventory();
                fetchInventorySummary();
                fetchSales();
                fetchFinancials();
            }

            // Consequential Action Staged Check
            if (data.action_staged && data.action_staged.confirmation_token) {
                currentStagedActionToken = data.action_staged.confirmation_token;
                if (actionCard) {
                    const textEl = document.getElementById('aiActionConfirmText');
                    if (textEl) textEl.textContent = data.action_staged.summary;

                    const detailsEl = document.getElementById('aiActionProposedDetails');
                    if (detailsEl) {
                        detailsEl.innerHTML = renderProposedChangesHtml(data.action_staged.proposed_changes);
                    }

                    actionCard.style.display = 'block';

                    const confirmBtn = document.getElementById('btnConfirmAIAction');
                    const cancelBtn = document.getElementById('btnCancelAIAction');

                    if (confirmBtn) confirmBtn.onclick = () => executeStagedAction('confirm', intentBadge);
                    if (cancelBtn) cancelBtn.onclick = () => executeStagedAction('cancel', intentBadge);
                }
            } else {
                if (actionCard) actionCard.style.display = 'none';
            }

            // Spoken speech synthesis readout (Prevent echo feedback: halt speech recognition while speaking)
            if (window.speechSynthesis && data.spoken_text) {
                try {
                    window.speechSynthesis.cancel();
                    const cleanSpoken = data.spoken_text.replace(/[#*`_()]/g, '');
                    const utter = new SpeechSynthesisUtterance(cleanSpoken);
                    utter.lang = currentLanguage === 'en' ? 'en-IN' : 'hi-IN';
                    utter.rate = 1.0;

                    utter.onstart = () => {
                        setAIAssistantState('speaking');
                        // Ensure speech recognition is aborted if running so it does not capture the speaker's own voice
                        if (speechRecognition && isListening) {
                            try { speechRecognition.abort(); } catch(e){}
                            isListening = false;
                            isStartingRecognition = false;
                            updateListeningUI(false);
                        }
                    };

                    utter.onend = () => {
                        if (!currentStagedActionToken) {
                            setAIAssistantState('ready');
                        }
                    };

                    utter.onerror = () => {
                        if (!currentStagedActionToken) {
                            setAIAssistantState('ready');
                        }
                    };

                    window.speechSynthesis.speak(utter);
                } catch (e) {
                    console.warn('Speech synthesis error:', e);
                }
            }
        } else {
            if (body) body.innerHTML = `<span style="color:#DC2626;">❌ ${escapeHtml(res.message || 'Error communicating with AI engine.')}</span>`;
            setAIAssistantState('error', res.message || 'Error communicating with AI');
        }
    } catch (err) {
        console.error('AI chat failed:', err);
        if (body) body.innerHTML = `<span style="color:#DC2626;">❌ Server connection error. Please ensure backend is running.</span>`;
        setAIAssistantState('error', 'सर्वर कनेक्शन त्रुटि (Server Error)');
    } finally {
        isProcessingAICommand = false;
        if (sendBtn) sendBtn.disabled = false;
        if ((!window.speechSynthesis || !window.speechSynthesis.speaking) && !currentStagedActionToken) {
            setAIAssistantState('ready');
        }
    }
}

function renderActionStatusBadge(badgeEl, status) {
    if (!badgeEl) return;
    if (status === 'needs_clarification') {
        badgeEl.textContent = '❓ Needs clarification';
        badgeEl.style.background = '#FEF3C7';
        badgeEl.style.color = '#92400E';
        badgeEl.style.border = '1px solid #F59E0B';
    } else if (status === 'awaiting_confirmation') {
        badgeEl.textContent = '⚠️ Awaiting confirmation';
        badgeEl.style.background = '#FEF3C7';
        badgeEl.style.color = '#B45309';
        badgeEl.style.border = '1px solid #F59E0B';
    } else if (status === 'saved') {
        badgeEl.textContent = '✅ Saved';
        badgeEl.style.background = '#DCFCE7';
        badgeEl.style.color = '#15803D';
        badgeEl.style.border = '1px solid #22C55E';
    } else if (status === 'failed') {
        badgeEl.textContent = '❌ Failed';
        badgeEl.style.background = '#FEE2E2';
        badgeEl.style.color = '#B91C1C';
        badgeEl.style.border = '1px solid #EF4444';
    } else if (status === 'cancelled') {
        badgeEl.textContent = '🛑 Cancelled';
        badgeEl.style.background = '#F1F5F9';
        badgeEl.style.color = '#475569';
        badgeEl.style.border = '1px solid #94A3B8';
    } else if (status === 'needs_login') {
        badgeEl.textContent = '🔒 Login Required';
        badgeEl.style.background = '#FEE2E2';
        badgeEl.style.color = '#B91C1C';
        badgeEl.style.border = '1px solid #EF4444';
    }
}

function renderProposedChangesHtml(changes) {
    if (!changes || typeof changes !== 'object') return '';
    const rows = [];
    if (changes.product) rows.push(`<div><span style="color:var(--text-muted); font-size:0.75rem;">Product:</span><br><strong>${escapeHtml(changes.product)}</strong></div>`);
    if (changes.quantity_added !== undefined) rows.push(`<div><span style="color:var(--text-muted); font-size:0.75rem;">Quantity:</span><br><strong>+${changes.quantity_added} ${escapeHtml(changes.unit || '')}</strong></div>`);
    if (changes.total_purchase_cost) rows.push(`<div><span style="color:var(--text-muted); font-size:0.75rem;">Total Purchase Cost:</span><br><strong>₹${changes.total_purchase_cost}</strong></div>`);
    if (changes.unit_purchase_cost) rows.push(`<div><span style="color:var(--text-muted); font-size:0.75rem;">Unit Cost:</span><br><strong>₹${changes.unit_purchase_cost}/${escapeHtml(changes.unit || 'unit')}</strong></div>`);
    if (changes.intended_profit_per_unit) rows.push(`<div><span style="color:var(--text-muted); font-size:0.75rem;">Intended Profit:</span><br><strong>₹${changes.intended_profit_per_unit}/${escapeHtml(changes.unit || 'unit')}</strong></div>`);
    if (changes.suggested_selling_price) rows.push(`<div><span style="color:var(--text-muted); font-size:0.75rem;">Selling Price:</span><br><strong>₹${changes.suggested_selling_price}/${escapeHtml(changes.unit || 'unit')}</strong></div>`);
    if (changes.expiry_date) rows.push(`<div><span style="color:var(--text-muted); font-size:0.75rem;">Expiry Date:</span><br><strong>${escapeHtml(changes.expiry_date)}</strong></div>`);
    if (changes.arrival_date) rows.push(`<div><span style="color:var(--text-muted); font-size:0.75rem;">Arrival Date:</span><br><strong>${escapeHtml(changes.arrival_date)}</strong></div>`);
    if (changes.target_quantity !== undefined) rows.push(`<div><span style="color:var(--text-muted); font-size:0.75rem;">Target Stock:</span><br><strong>${changes.target_quantity} ${escapeHtml(changes.unit || '')}</strong></div>`);

    if (rows.length === 0) return '';
    return `<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap:8px; background:rgba(255,255,255,0.85); padding:10px; border-radius:6px; border:1px solid #CBD5E1; margin-top:8px;">${rows.join('')}</div>`;
}

async function executeStagedAction(decision, badgeEl) {
    if (!currentStagedActionToken) return;
    const token = localStorage.getItem('shopo_auth_token');
    const actionCard = document.getElementById('aiActionConfirmCard');
    const assistantActionCard = document.getElementById('assistantViewActionConfirmCard');
    const body = document.getElementById('aiResponseBody');

    try {
        const resp = await fetch('/api/ai/tools/confirm', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                confirmation_token: currentStagedActionToken,
                decision: decision
            })
        });
        const res = await resp.json();

        if (actionCard) actionCard.style.display = 'none';
        if (assistantActionCard) assistantActionCard.style.display = 'none';

        if (res.success) {
            if (decision !== 'cancel') {
                if (res.result && (res.result.product_id || res.result.id)) {
                    lastModifiedProductId = res.result.product_id || res.result.id;
                }
                setAIAssistantState('success', res.message || 'कार्रवाई सफलतापूर्वक पूर्ण हुई!');
            }
            if (badgeEl) renderActionStatusBadge(badgeEl, decision === 'cancel' ? 'cancelled' : 'saved');
            if (body) {
                const bg = decision === 'cancel' ? '#F1F5F9' : '#DCFCE7';
                const border = decision === 'cancel' ? '#94A3B8' : '#22C55E';
                const col = decision === 'cancel' ? '#334155' : '#14532D';
                body.innerHTML += `<br><br><div style="padding:10px; background:${bg}; border:1px solid ${border}; border-radius:6px; color:${col}; font-weight:700;">${escapeHtml(res.message || 'Action executed successfully!')}</div>`;
            }
            // Auto-refresh inventory & financials without full page reload
            fetchInventory();
            fetchInventorySummary();
            fetchSales();
            fetchFinancials();
            setAIAssistantState('success', decision === 'cancel' ? 'कार्य रद्द किया गया (Cancelled)' : 'सफलतापूर्वक पूर्ण (Action Saved!)');
        } else {
            if (badgeEl) renderActionStatusBadge(badgeEl, 'failed');
            alert(res.message || 'Action failed.');
            setAIAssistantState('error', 'कार्रवाई असफल (Action failed)');
        }
    } catch (err) {
        if (badgeEl) renderActionStatusBadge(badgeEl, 'failed');
        console.error('Error confirming action:', err);
        setAIAssistantState('error', 'कार्रवाई में समस्या आई');
    } finally {
        currentStagedActionToken = null;
    }
}

function handleAssistantViewSubmit(e) {
    if (e) e.preventDefault();
    const input = document.getElementById('assistantViewInput');
    if (!input) return;
    const query = input.value.trim();
    if (!query) return;

    processAssistantViewCommand(query);
    input.value = '';
}

function applyAssistantViewPreset(text) {
    const input = document.getElementById('assistantViewInput');
    if (input) input.value = text;
    processAssistantViewCommand(text);
}

async function processAssistantViewCommand(query) {
    const box = document.getElementById('assistantViewResponseBox');
    const body = document.getElementById('assistantViewResponseBody');
    const intentBadge = document.getElementById('assistantViewIntentBadge');
    const actionCard = document.getElementById('assistantViewActionConfirmCard');

    if (box) {
        box.classList.add('show');
        box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    if (body) {
        body.innerHTML = `<span style="color:var(--text-muted);"><i class="fas fa-spinner fa-spin"></i> शोपो रोबो सोच रहा है (Processing universal query)...</span>`;
    }
    if (actionCard) actionCard.style.display = 'none';

    const token = localStorage.getItem('shopo_auth_token');
    const headers = { 'Content-Type': 'application/json' };
    if (token) headers['Authorization'] = `Bearer ${token}`;

    try {
        const resp = await fetch('/api/ai/chat', {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({
                message: query,
                language: currentLanguage || 'hi'
            })
        });
        const res = await resp.json();

        if (res.success && res.data) {
            const data = res.data;
            const reply = data.reply_text || 'No response returned.';
            if (body) {
                body.innerHTML = formatMarkdown(reply);
                if (box) box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }

            const intentMap = {
                'mandi_market_query': '🌾 APMC Mandi Benchmark',
                'live_weather_query': '🌤️ Live Weather Observation',
                'industrial_materials_query': '🏗️ Industrial Benchmark',
                'government_schemes_query': '🏛️ Official Govt Information',
                'business_inventory_query': '📦 Verified Store Records',
                'business_financials_query': '💰 Verified Store Financials',
                'consequential_action_staged': '⚠️ Action Confirmation Needed',
                'web_search_query': '🔍 Web Search Citations',
                'read_only_stock_query': '📦 Stock Check',
                'read_only_sales_query': '📊 Sales Summary',
                'read_only_profit_query': '📈 Profit Summary',
                'stock_valuation_query': '💰 Stock Valuation',
                'clarification_needed': '❓ Clarification Needed',
                'inward_stock_purchase': '📥 Inward Stock',
                'retail_sale': '🛒 Record Sale',
                'product_creation': '✨ New Product',
                'needs_login': '🔒 Login Required',
                'business_auth_required': '🔒 Login Required',
                'general_knowledge': '🌐 Universal Intelligence'
            };

            if (intentBadge) {
                if (data.action_status) {
                    renderActionStatusBadge(intentBadge, data.action_status);
                } else {
                    intentBadge.textContent = intentMap[data.intent] || 'Universal Intelligence';
                    intentBadge.style.background = 'var(--lime-100)';
                    intentBadge.style.color = 'var(--lime-800)';
                    intentBadge.style.border = 'none';
                }
            }

            if (data.action_status === 'saved') {
                fetchInventory();
                fetchInventorySummary();
                fetchSales();
                fetchFinancials();
            }

            if (data.action_staged && data.action_staged.confirmation_token) {
                currentStagedActionToken = data.action_staged.confirmation_token;
                if (actionCard) {
                    const textEl = document.getElementById('assistantViewActionConfirmText');
                    if (textEl) textEl.textContent = data.action_staged.summary;

                    const detailsEl = document.getElementById('assistantViewActionProposedDetails');
                    if (detailsEl) {
                        detailsEl.innerHTML = renderProposedChangesHtml(data.action_staged.proposed_changes);
                    }

                    actionCard.style.display = 'block';

                    const confirmBtn = document.getElementById('btnConfirmAssistantAction');
                    const cancelBtn = document.getElementById('btnCancelAssistantAction');

                    if (confirmBtn) confirmBtn.onclick = () => executeStagedAction('confirm', intentBadge);
                    if (cancelBtn) cancelBtn.onclick = () => executeStagedAction('cancel', intentBadge);
                }
            } else {
                if (actionCard) actionCard.style.display = 'none';
            }
        } else {
            if (body) body.innerHTML = `<span style="color:#DC2626;">❌ ${escapeHtml(res.message || 'Error communicating with AI engine.')}</span>`;
        }
    } catch (err) {
        console.error('AI chat failed:', err);
        if (body) body.innerHTML = `<span style="color:#DC2626;">❌ Server connection error. Please ensure backend is running.</span>`;
    }
}


function showSimulatedResponse(text) {
    const box = document.getElementById('aiResponseBox');
    const body = document.getElementById('aiResponseBody');
    if (box && body) {
        const html = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        body.innerHTML = html;
        box.classList.add('show');
    }
}

// ════════════════════════════════════════════════
// MODAL CONTROLLERS & QUICK ACTIONS
// ════════════════════════════════════════════════

function openModal(id) {
    const m = document.getElementById(id);
    if (m) m.classList.add('active');
}

function closeModal(id) {
    if (id === 'barcodeModal') {
        stopBarcodeScanner();
    }
    const m = document.getElementById(id);
    if (m) m.classList.remove('active');
}

function closeBarcodeModal() {
    closeModal('barcodeModal');
}

function openAddProductModal() {
    openModal('addProductModal');
    handleCategoryChange('add');
}
function openBarcodeModal() {
    openModal('barcodeModal');
    resetScannerView();
    switchScannerTab('camera');
}
function openRecordSaleModal() { openModal('recordSaleModal'); }
function openSetupModal() {
    if (currentUser) {
        document.getElementById('quickShopName').value = currentUser.shop_name || '';
        document.getElementById('quickShopType').value = currentUser.shop_type || 'Grocery & Kirana Store';
        document.getElementById('quickShopAddress').value = currentUser.shop_address || '';
    }
    openModal('setupModal');
}
function openSettingsModal() {
    switchNav('settings');
    closeUserDropdown();
}

function toggleUserDropdown() {
    const dd = document.getElementById('userDropdown');
    if (dd) dd.classList.toggle('show');
}

function closeUserDropdown() {
    const dd = document.getElementById('userDropdown');
    if (dd) dd.classList.remove('show');
}

// Close user dropdown if clicking outside
window.addEventListener('click', (e) => {
    if (!e.target.closest('.user-dropdown-wrap')) {
        closeUserDropdown();
    }
});

// ════════════════════════════════════════════════
// INVENTORY CRUD & DATA FETCHING (Phase 2)
// ════════════════════════════════════════════════

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

async function fetchInventory() {
    const token = localStorage.getItem('shopo_auth_token');
    if (!token) return;

    const loadingEl = document.getElementById('inventoryLoadingState');
    if (loadingEl) loadingEl.style.display = 'flex';

    try {
        const params = new URLSearchParams();
        if (inventoryFilters.q) params.set('q', inventoryFilters.q);
        if (inventoryFilters.category) params.set('category', inventoryFilters.category);
        if (inventoryFilters.low_stock) params.set('low_stock', 'true');
        if (inventoryFilters.near_expiry) params.set('near_expiry', 'true');

        const resp = await fetch(`/api/inventory?${params.toString()}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();

        if (res.success && res.data) {
            inventoryItems = res.data.items || [];
            renderInventoryTable();
            renderAlertsFeed();
            populateSaleProductDropdown();
            checkFirstTimeUserStatus();
        }
    } catch (err) {
        console.error('Error fetching inventory:', err);
    } finally {
        if (loadingEl) loadingEl.style.display = 'none';
    }
}

async function fetchInventorySummary() {
    const token = localStorage.getItem('shopo_auth_token');
    if (!token) return;

    try {
        const resp = await fetch('/api/inventory/summary', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();

        if (res.success && res.data) {
            inventorySummary = res.data;
            updateOverviewMetrics();
            checkFirstTimeUserStatus();
        }
    } catch (err) {
        console.error('Error fetching inventory summary:', err);
    }
}

async function fetchFinancials() {
    const token = localStorage.getItem('shopo_auth_token');
    if (!token) return;

    try {
        const resp = await fetch('/api/analytics/financials', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();

        if (res.success && res.data) {
            businessFinancials = res.data;
            updateOverviewMetrics();
            renderReportsView();
            checkFirstTimeUserStatus();
        }
    } catch (err) {
        console.error('Error fetching financials:', err);
    }
}

async function fetchSales() {
    const token = localStorage.getItem('shopo_auth_token');
    if (!token) return;

    try {
        const resp = await fetch('/api/sales', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();

        if (res.success && res.data) {
            salesRecords = res.data.sales || [];
            renderRecentSalesFeed();
            renderSalesRegisterView();
            renderSalesOverviewChart();
            checkFirstTimeUserStatus();
        }
    } catch (err) {
        console.error('Error fetching sales:', err);
    }
}

function checkFirstTimeUserStatus() {
    const banner = document.getElementById('firstTimeWelcomeBanner');
    if (!banner) return;

    const totalItems = inventorySummary?.total_items ?? 0;
    const totalSales = businessFinancials?.total_sales_count ?? 0;

    // Show first-time helpful message when user has zero products and zero sales
    if (totalItems === 0 && totalSales === 0) {
        banner.style.display = 'flex';
    } else {
        banner.style.display = 'none';
    }
}

function updateOverviewMetrics() {
    // 1. Total Products
    const totalEl = document.getElementById('metricTotalItems');
    const totalSub = document.getElementById('metricTotalItemsSub');
    if (totalEl && inventorySummary) {
        totalEl.textContent = `${inventorySummary.total_items} items`;
    }
    if (totalSub && inventorySummary) {
        totalSub.textContent = `In ${inventorySummary.category_count || 0} categories`;
    }

    // 2. Low Stock Count
    const lowStockEl = document.getElementById('metricLowStock');
    const lowStockSub = document.getElementById('metricLowStockSub');
    const lowStockTrend = document.getElementById('metricLowStockTrend');
    if (lowStockEl && inventorySummary) {
        const cnt = inventorySummary.low_stock_count || 0;
        lowStockEl.textContent = `${cnt} items`;
        lowStockEl.style.color = cnt > 0 ? 'var(--yellow-500)' : 'var(--green-500)';
        if (lowStockSub) {
            lowStockSub.textContent = cnt > 0 ? `${cnt} items require reorder` : 'All stock levels normal';
        }
        if (lowStockTrend) {
            lowStockTrend.className = cnt > 0 ? 'metric-trend warn' : 'metric-trend';
        }
    }

    // 3. Near Expiry Count
    const expiryEl = document.getElementById('metricNearExpiry');
    const expirySub = document.getElementById('metricNearExpirySub');
    const expiryTrend = document.getElementById('metricNearExpiryTrend');
    if (expiryEl && inventorySummary) {
        const cnt = inventorySummary.near_expiry_count || 0;
        expiryEl.textContent = `${cnt} items`;
        expiryEl.style.color = cnt > 0 ? 'var(--red-500)' : 'var(--green-500)';
        if (expirySub) {
            expirySub.textContent = cnt > 0 ? `${cnt} items expiring in 30 days` : 'No items near expiry';
        }
        if (expiryTrend) {
            expiryTrend.className = cnt > 0 ? 'metric-trend alert' : 'metric-trend';
        }
    }

    // 4. Today's Sales Revenue (Verified Data-Driven)
    const salesEl = document.getElementById('metricSales');
    const salesSub = document.getElementById('metricSalesSub');
    const salesTrend = document.getElementById('metricSalesTrend');
    if (salesEl) {
        const todayRev = businessFinancials?.revenue?.today ?? 0;
        salesEl.textContent = `₹${todayRev.toLocaleString('en-IN')}`;
    }
    if (salesSub) {
        const cnt = businessFinancials?.today_sales_count ?? 0;
        salesSub.textContent = `${cnt} ${cnt === 1 ? 'sale' : 'sales'} recorded today`;
        if (salesTrend) {
            salesTrend.className = cnt > 0 ? 'metric-trend up' : 'metric-trend';
        }
    }

    // 5. Today's Gross Profit (Verified Data-Driven)
    const profitEl = document.getElementById('metricProfit');
    const profitSub = document.getElementById('metricProfitSub');
    const profitTrend = document.getElementById('metricProfitTrend');
    if (profitEl) {
        const todayProfit = businessFinancials?.gross_profit?.today ?? 0;
        profitEl.textContent = `₹${todayProfit.toLocaleString('en-IN')}`;
    }
    if (profitSub) {
        const margin = businessFinancials?.gross_profit?.today_margin_pct ?? 0.0;
        const cnt = businessFinancials?.today_sales_count ?? 0;
        if (cnt > 0) {
            profitSub.textContent = `Gross Margin: ${margin}% • Verified`;
            if (profitTrend) profitTrend.className = 'metric-trend up';
        } else {
            profitSub.textContent = 'Gross Margin: 0.0%';
            if (profitTrend) profitTrend.className = 'metric-trend';
        }
    }

    // 6. Stock Value (Prompt Section 4)
    const stockValEl = document.getElementById('metricStockValue');
    const stockValSub = document.getElementById('metricStockValueSub');
    if (stockValEl && inventorySummary) {
        const val = inventorySummary.total_purchase_value || 0;
        stockValEl.textContent = `₹${Math.round(val).toLocaleString('en-IN')}`;
    }
    if (stockValSub && inventorySummary) {
        const retailVal = inventorySummary.total_selling_value || 0;
        stockValSub.textContent = `Retail valuation: ₹${Math.round(retailVal).toLocaleString('en-IN')}`;
    }

    // 7. Profit & Loss Card (Prompt Section 5)
    const pnlGross = document.getElementById('pnlGrossRevenue');
    const pnlCogs = document.getElementById('pnlCOGS');
    const pnlExp = document.getElementById('pnlExpenses');
    const pnlNet = document.getElementById('pnlNetProfit');
    if (businessFinancials) {
        const rev = businessFinancials.revenue?.total ?? 0;
        const cogs = businessFinancials.cogs?.total ?? 0;
        const exp = businessFinancials.operating_expenses?.total ?? 0;
        const net = businessFinancials.net_profit?.total ?? (rev - cogs - exp);
        if (pnlGross) pnlGross.textContent = `₹${Math.round(rev).toLocaleString('en-IN')}`;
        if (pnlCogs) pnlCogs.textContent = `₹${Math.round(cogs).toLocaleString('en-IN')}`;
        if (pnlExp) pnlExp.textContent = `₹${Math.round(exp).toLocaleString('en-IN')}`;
        if (pnlNet) {
            pnlNet.textContent = `₹${Math.round(net).toLocaleString('en-IN')}`;
            pnlNet.className = net >= 0 ? 'pnl-val profit' : 'pnl-val';
        }
    }
}

function renderAlertsFeed() {
    const list = document.getElementById('alertsList');
    if (!list) return;

    if (!inventoryItems || inventoryItems.length === 0) {
        list.innerHTML = `
            <li class="empty-feed-state" id="emptyAlertsNotice">
                <i class="fas fa-boxes" style="color:var(--text-muted);"></i>
                <p>No inventory items yet. Add products to activate real-time stock alerts.</p>
            </li>
        `;
        return;
    }

    const now = new Date();
    const in30Days = new Date();
    in30Days.setDate(now.getDate() + 30);

    const alerts = [];

    inventoryItems.forEach(item => {
        const qty = Number(item.quantity);
        const threshold = Number(item.low_stock_threshold || 5);

        if (qty <= threshold) {
            alerts.push({
                type: 'low',
                icon: 'fas fa-exclamation-triangle',
                iconClass: 'metric-icon-yellow',
                title: `${item.product_name} (${qty} ${item.unit} left)`,
                meta: `Threshold: ${threshold} ${item.unit}`,
                badgeText: qty === 0 ? 'OUT OF STOCK' : 'LOW STOCK',
                badgeStyle: qty === 0 ? 'background:var(--red-100); color:var(--red-500);' : 'background:var(--yellow-100); color:#B45309;',
            });
        }

        if (item.expiry_date) {
            const expDate = new Date(item.expiry_date);
            if (expDate <= in30Days) {
                alerts.push({
                    type: 'expiry',
                    icon: 'fas fa-hourglass-end',
                    iconClass: 'metric-icon-red',
                    title: `${item.product_name} (Exp: ${item.expiry_date})`,
                    meta: `Expiring within 30 days`,
                    badgeText: 'EXPIRY',
                    badgeStyle: 'background:var(--red-100); color:#B91C1C;',
                });
            }
        }
    });

    if (alerts.length === 0) {
        list.innerHTML = `
            <li class="empty-feed-state" id="emptyAlertsNotice">
                <i class="fas fa-check-circle" style="color:var(--green-500);"></i>
                <p>All stock levels normal • No pending alerts</p>
            </li>
        `;
        return;
    }

    list.innerHTML = alerts.slice(0, 5).map(a => `
        <li class="activity-item">
            <div class="activity-left">
                <div class="activity-icon-badge ${a.iconClass}"><i class="${a.icon}"></i></div>
                <div class="activity-info">
                    <div class="activity-title">${escapeHtml(a.title)}</div>
                    <div class="activity-meta">${escapeHtml(a.meta)}</div>
                </div>
            </div>
            <div class="activity-right">
                <span style="font-size:0.75rem; padding:2px 8px; border-radius:12px; font-weight:700; ${a.badgeStyle}">${a.badgeText}</span>
            </div>
        </li>
    `).join('');
}

function renderRecentSalesFeed() {
    const list = document.getElementById('recentSalesList');
    if (!list) return;

    if (!salesRecords || salesRecords.length === 0) {
        list.innerHTML = `
            <li class="empty-feed-state" id="emptySalesNotice">
                <i class="fas fa-receipt"></i>
                <p>No sales recorded yet. Use 'Record Sale' to log transactions.</p>
            </li>
        `;
        return;
    }

    list.innerHTML = salesRecords.slice(0, 5).map(s => {
        const rev = Number(s.total_revenue || 0).toFixed(2);
        const mode = s.payment_mode || 'Cash';
        const dateStr = s.created_at ? s.created_at.slice(0, 16).replace('T', ' ') : 'Recent';
        return `
            <li class="activity-item">
                <div class="activity-left">
                    <div class="activity-icon-badge metric-icon-green"><i class="fas fa-shopping-bag"></i></div>
                    <div class="activity-info">
                        <div class="activity-title">${escapeHtml(s.product_name)} (${s.quantity} ${escapeHtml(s.unit)})</div>
                        <div class="activity-meta">${dateStr} &bull; ${escapeHtml(mode)}</div>
                    </div>
                </div>
                <div class="activity-right">
                    <div class="activity-val" style="color:var(--green-500);">+₹${rev}</div>
                </div>
            </li>
        `;
    }).join('');
}

function renderSalesRegisterView() {
    const countEl = document.getElementById('salesRegTodayCount');
    const todayRevEl = document.getElementById('salesRegTodayRev');
    const todayProfitEl = document.getElementById('salesRegTodayProfit');
    const totalRevEl = document.getElementById('salesRegTotalRev');
    const totalCountEl = document.getElementById('salesRegTotalCount');

    const emptyState = document.getElementById('salesEmptyState');
    const tableWrapper = document.getElementById('salesTableWrapper');
    const tbody = document.getElementById('salesTableBody');

    const todayCount = businessFinancials?.today_sales_count ?? 0;
    const todayRev = businessFinancials?.revenue?.today ?? 0;
    const todayProfit = businessFinancials?.gross_profit?.today ?? 0;
    const totalRev = businessFinancials?.revenue?.total ?? 0;
    const totalCount = businessFinancials?.total_sales_count ?? (salesRecords?.length || 0);

    if (countEl) countEl.textContent = `${todayCount} ${todayCount === 1 ? 'sale' : 'sales'}`;
    if (todayRevEl) todayRevEl.textContent = `₹${todayRev.toLocaleString('en-IN')}`;
    if (todayProfitEl) todayProfitEl.textContent = `+₹${todayProfit.toLocaleString('en-IN')} Gross Profit`;
    if (totalRevEl) totalRevEl.textContent = `₹${totalRev.toLocaleString('en-IN')}`;
    if (totalCountEl) totalCountEl.textContent = `${totalCount} total transactions`;

    if (!salesRecords || salesRecords.length === 0) {
        if (emptyState) emptyState.style.display = 'flex';
        if (tableWrapper) tableWrapper.style.display = 'none';
        return;
    }

    if (emptyState) emptyState.style.display = 'none';
    if (tableWrapper) tableWrapper.style.display = 'block';

    if (tbody) {
        tbody.innerHTML = salesRecords.map(s => {
            const dateStr = s.created_at ? s.created_at.slice(0, 16).replace('T', ' ') : '—';
            const price = Number(s.selling_price || 0).toFixed(2);
            const rev = Number(s.total_revenue || 0).toFixed(2);
            const gp = Number(s.gross_profit || 0).toFixed(2);
            return `
                <tr>
                    <td style="font-size:0.85rem; color:var(--text-secondary);">${dateStr}</td>
                    <td>
                        <strong style="color:var(--text-primary);">${escapeHtml(s.product_name)}</strong>
                    </td>
                    <td>${s.quantity} ${escapeHtml(s.unit)}</td>
                    <td>₹${price}</td>
                    <td style="font-weight:700; color:var(--text-primary);">₹${rev}</td>
                    <td style="font-weight:700; color:var(--green-500);">+₹${gp}</td>
                    <td>
                        <span style="font-size:0.8rem; background:var(--bg-main); padding:2px 8px; border-radius:6px; border:1px solid var(--border-color);">
                            ${escapeHtml(s.payment_mode || 'Cash')}
                        </span>
                    </td>
                </tr>
            `;
        }).join('');
    }
}

function renderReportsView() {
    const insufficientCard = document.getElementById('reportsInsufficientCard');
    const badge = document.getElementById('reportsDataBadge');

    const hasSales = businessFinancials?.has_sales ?? false;
    const isInsufficient = (businessFinancials?.status === 'insufficient_data') || !hasSales;

    if (insufficientCard) {
        insufficientCard.style.display = isInsufficient ? 'block' : 'none';
    }
    if (badge) {
        badge.textContent = isInsufficient ? 'Insufficient Data' : 'Verified Audit';
        badge.style.background = isInsufficient ? '#FEF3C7' : 'var(--lime-100)';
        badge.style.color = isInsufficient ? '#92400E' : 'var(--lime-800)';
    }

    const revTotal = businessFinancials?.revenue?.total ?? 0;
    const revMonthly = businessFinancials?.revenue?.monthly ?? 0;
    const cogsTotal = businessFinancials?.cogs?.total ?? 0;
    const opexTotal = businessFinancials?.operating_expenses?.total ?? 0;
    const grossTotal = businessFinancials?.gross_profit?.total ?? 0;
    const grossMargin = businessFinancials?.gross_profit?.gross_margin_pct ?? 0.0;
    const netTotal = businessFinancials?.net_profit?.total ?? 0;
    const netMargin = businessFinancials?.net_profit?.net_margin_pct ?? 0.0;

    const rRev = document.getElementById('reportRevVal');
    const rRevM = document.getElementById('reportRevMonthly');
    const rCogs = document.getElementById('reportCogsVal');
    const rOpex = document.getElementById('reportOpexVal');
    const rGross = document.getElementById('reportGrossVal');
    const rGrossM = document.getElementById('reportGrossMargin');
    const rNet = document.getElementById('reportNetVal');
    const rNetM = document.getElementById('reportNetMargin');

    if (rRev) rRev.textContent = `₹${revTotal.toLocaleString('en-IN')}`;
    if (rRevM) rRevM.textContent = `This Month: ₹${revMonthly.toLocaleString('en-IN')}`;
    if (rCogs) rCogs.textContent = `₹${cogsTotal.toLocaleString('en-IN')}`;
    if (rOpex) rOpex.textContent = `₹${opexTotal.toLocaleString('en-IN')}`;
    if (rGross) rGross.textContent = `₹${grossTotal.toLocaleString('en-IN')}`;
    if (rGrossM) rGrossM.textContent = `${grossMargin}% Gross Margin`;
    if (rNet) rNet.textContent = `₹${netTotal.toLocaleString('en-IN')}`;
    if (rNetM) rNetM.textContent = `${netMargin}% Net Margin`;
}

function renderInventoryTable() {
    const emptyState = document.getElementById('inventoryEmptyState');
    const tableWrapper = document.getElementById('inventoryTableWrapper');
    const tbody = document.getElementById('inventoryTableBody');

    if (!tbody || !emptyState || !tableWrapper) return;

    if (!inventoryItems || inventoryItems.length === 0) {
        tableWrapper.style.display = 'none';
        emptyState.style.display = 'flex';

        const isFiltered = inventoryFilters.q || inventoryFilters.category || inventoryFilters.low_stock || inventoryFilters.near_expiry;
        const titleEl = document.getElementById('emptyStateTitle');
        const descEl = document.getElementById('emptyStateDesc');

        if (isFiltered) {
            if (titleEl) titleEl.textContent = 'No Matching Products';
            if (descEl) descEl.textContent = 'No items found matching your current filter criteria. Try searching with different keywords or reset filters.';
        } else {
            if (titleEl) titleEl.textContent = 'No Products Added Yet';
            if (descEl) descEl.textContent = 'Your dukaan stock is empty. Click below to add your first product!';
        }
        return;
    }

    emptyState.style.display = 'none';
    tableWrapper.style.display = 'block';

    const now = new Date();
    const thirtyDaysFromNow = new Date();
    thirtyDaysFromNow.setDate(now.getDate() + 30);

    if (lastModifiedProductId) {
        setTimeout(() => {
            const el = tbody.querySelector('.row-highlight-flash');
            if (el) el.classList.remove('row-highlight-flash');
            lastModifiedProductId = null;
        }, 2200);
    }

    tbody.innerHTML = inventoryItems.map(item => {
        const qty = Number(item.quantity);
        const threshold = Number(item.low_stock_threshold || 5);
        const buyPrice = Number(item.purchase_price || 0);
        const sellPrice = Number(item.selling_price || 0);

        // Status pill
        let stockPillHtml = '';
        if (qty <= 0) {
            stockPillHtml = `<span class="stock-pill out-of-stock"><i class="fas fa-times-circle"></i> Out of Stock</span>`;
        } else if (qty <= threshold) {
            stockPillHtml = `<span class="stock-pill low-stock"><i class="fas fa-exclamation-triangle"></i> Low (${qty} ${escapeHtml(item.unit)})</span>`;
        } else {
            stockPillHtml = `<span class="stock-pill in-stock"><i class="fas fa-check-circle"></i> ${qty} ${escapeHtml(item.unit)}</span>`;
        }

        // Margin %
        let marginHtml = '';
        if (sellPrice > 0) {
            const marginPct = (((sellPrice - buyPrice) / sellPrice) * 100).toFixed(1);
            marginHtml = `<div class="margin-pill">${marginPct}% Margin</div>`;
        }

        // Expiry check
        let expiryHtml = '';
        if (item.expiry_date) {
            const expDate = new Date(item.expiry_date);
            const isNearExpiry = expDate <= thirtyDaysFromNow;
            expiryHtml = `
                <div style="font-size:0.8rem; color:var(--text-muted); margin-top:2px;">
                    Exp: ${escapeHtml(item.expiry_date)}
                </div>
            `;
            if (isNearExpiry) {
                expiryHtml += `<span class="expiry-alert-tag"><i class="fas fa-hourglass-end"></i> Near Expiry</span>`;
            }
        }

        const barcodeHtml = item.barcode
            ? `<span class="barcode-text">${escapeHtml(item.barcode)}</span>`
            : `<span style="color:var(--text-muted); font-size:0.82rem;">—</span>`;

        // Render industry attribute tags (e.g. Batch, Size, Grade, Fabric)
        let attrBadgesHtml = '';
        if (item.attributes && typeof item.attributes === 'object') {
            const badges = [];
            for (const [k, v] of Object.entries(item.attributes)) {
                if (v && String(v).trim()) {
                    const cleanK = k.replace(/_/g, ' ');
                    badges.push(`<span style="display:inline-block; font-size:0.7rem; background:#f1f5f9; color:#475569; padding:1px 6px; border-radius:4px; margin-right:4px; margin-top:3px; border:1px solid #e2e8f0;"><b>${escapeHtml(cleanK)}:</b> ${escapeHtml(String(v))}</span>`);
                }
            }
            if (badges.length > 0) {
                attrBadgesHtml = `<div style="margin-top:4px;">${badges.slice(0, 3).join('')}${badges.length > 3 ? `<span style="font-size:0.68rem; color:var(--text-muted);">+${badges.length - 3}</span>` : ''}</div>`;
            }
        }

        const isRecentlyModified = lastModifiedProductId && String(item.id) === String(lastModifiedProductId);
        return `
            <tr data-product-id="${item.id}" class="${isRecentlyModified ? 'row-highlight-flash' : ''}">
                <td>
                    <div class="prod-main-title">${escapeHtml(item.product_name)}</div>
                    ${item.brand ? `<div class="prod-sub-brand"><i class="fas fa-tag"></i> ${escapeHtml(item.brand)}</div>` : ''}
                    ${attrBadgesHtml}
                </td>
                <td>
                    <span class="category-tag">${escapeHtml(item.category || 'General')}</span>
                </td>
                <td>
                    ${stockPillHtml}
                </td>
                <td style="font-weight:600; color:var(--text-secondary);">
                    ₹${buyPrice.toFixed(2)}
                </td>
                <td>
                    <div style="font-weight:800; color:var(--text-primary);">₹${sellPrice.toFixed(2)}</div>
                    ${marginHtml}
                </td>
                <td>
                    ${barcodeHtml}
                    ${expiryHtml}
                </td>
                <td>
                    <div class="action-btn-group">
                        <button class="action-icon-btn" onclick="openProductDnaModal('${item.id}')" title="Product DNA / जीवन चक्र">
                            <i class="fas fa-dna" style="color:var(--lime-600);"></i>
                        </button>
                        <button class="action-icon-btn" onclick="openEditProductModal('${item.id}')" title="Edit Product">
                            <i class="fas fa-pencil-alt"></i>
                        </button>
                        <button class="action-icon-btn delete-btn" onclick="openDeleteConfirmModal('${item.id}', '${escapeHtml(item.product_name)}')" title="Delete Product">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// ── Search & Filter Controls ──
function handleInventorySearchInput(val) {
    if (searchDebounceTimeout) clearTimeout(searchDebounceTimeout);
    const clearBtn = document.getElementById('clearSearchBtn');
    if (clearBtn) clearBtn.style.display = val.trim() ? 'block' : 'none';

    searchDebounceTimeout = setTimeout(() => {
        inventoryFilters.q = val.trim();
        updateResetButtonVisibility();
        fetchInventory();
    }, 250);
}

function clearInventorySearch() {
    const input = document.getElementById('inventorySearchInput');
    if (input) input.value = '';
    const clearBtn = document.getElementById('clearSearchBtn');
    if (clearBtn) clearBtn.style.display = 'none';

    inventoryFilters.q = '';
    updateResetButtonVisibility();
    fetchInventory();
}

function handleCategoryFilterChange(val) {
    inventoryFilters.category = val;
    updateResetButtonVisibility();
    fetchInventory();
}

function toggleLowStockFilter() {
    inventoryFilters.low_stock = !inventoryFilters.low_stock;
    const chip = document.getElementById('chipLowStock');
    if (chip) chip.classList.toggle('active', inventoryFilters.low_stock);
    updateResetButtonVisibility();
    fetchInventory();
}

function toggleNearExpiryFilter() {
    inventoryFilters.near_expiry = !inventoryFilters.near_expiry;
    const chip = document.getElementById('chipNearExpiry');
    if (chip) chip.classList.toggle('active', inventoryFilters.near_expiry);
    updateResetButtonVisibility();
    fetchInventory();
}

function updateResetButtonVisibility() {
    const isFiltered = inventoryFilters.q || inventoryFilters.category || inventoryFilters.low_stock || inventoryFilters.near_expiry;
    const resetBtn = document.getElementById('btnResetFilters');
    if (resetBtn) resetBtn.style.display = isFiltered ? 'inline-flex' : 'none';
}

function resetAllInventoryFilters() {
    inventoryFilters = { q: '', category: '', low_stock: false, near_expiry: false };

    const searchInput = document.getElementById('inventorySearchInput');
    if (searchInput) searchInput.value = '';
    const clearBtn = document.getElementById('clearSearchBtn');
    if (clearBtn) clearBtn.style.display = 'none';

    const catSelect = document.getElementById('inventoryCategoryFilter');
    if (catSelect) catSelect.value = '';

    const chipLow = document.getElementById('chipLowStock');
    if (chipLow) chipLow.classList.remove('active');

    const chipExp = document.getElementById('chipNearExpiry');
    if (chipExp) chipExp.classList.remove('active');

    updateResetButtonVisibility();
    fetchInventory();
}

// ── Industry Taxonomy & Dynamic Category Attributes (Universal Support) ──
let loadedTaxonomies = [];

async function loadIndustryTaxonomies() {
    try {
        const resp = await fetch('/api/taxonomy');
        if (resp.ok) {
            const data = await resp.json();
            if (data.success && Array.isArray(data.data)) {
                loadedTaxonomies = data.data;
                populateTaxonomyDropdowns(loadedTaxonomies);
            }
        }
    } catch (e) {
        console.warn('Could not load taxonomies from API, using built-ins:', e);
    }
}

function populateTaxonomyDropdowns(taxList) {
    if (!taxList || taxList.length === 0) return;

    const selects = ['newProdCategory', 'editProdCategory', 'inventoryCategoryFilter'];
    selects.forEach(id => {
        const sel = document.getElementById(id);
        if (!sel) return;
        const currentVal = sel.value;
        const isFilter = id === 'inventoryCategoryFilter';

        sel.innerHTML = '';
        if (isFilter) {
            const optAll = document.createElement('option');
            optAll.value = '';
            optAll.textContent = 'All Categories (सभी श्रेणियां)';
            sel.appendChild(optAll);
        }

        taxList.forEach(tax => {
            const opt = document.createElement('option');
            opt.value = tax.name_en;
            const hiLabel = tax.name_hi ? ` / ${tax.name_hi}` : '';
            opt.textContent = `${tax.name_en}${hiLabel}`;
            sel.appendChild(opt);
        });

        if (currentVal) {
            sel.value = currentVal;
        }
    });
}

function findTaxonomyForCategory(catName) {
    if (!catName) return null;
    const lower = catName.toLowerCase().trim();
    if (loadedTaxonomies && loadedTaxonomies.length > 0) {
        for (const tax of loadedTaxonomies) {
            if (tax.id === lower || tax.name_en.toLowerCase() === lower || (tax.name_hi && tax.name_hi.toLowerCase() === lower)) {
                return tax;
            }
        }
        for (const tax of loadedTaxonomies) {
            if (lower.includes(tax.id) || tax.name_en.toLowerCase().includes(lower)) {
                return tax;
            }
            if (tax.keywords && tax.keywords.some(k => lower.includes(k))) {
                return tax;
            }
        }
    }

    // Built-in fallback mappings if API not loaded
    const builtInTaxonomies = {
        'pharmacy': {
            id: 'pharmacy_medical',
            name_en: 'Pharmacy & Medical Retail',
            attributes: [
                { key: 'batch_number', label: 'Batch Number', type: 'text' },
                { key: 'drug_schedule', label: 'Drug Schedule', type: 'select', options: ['OTC', 'Schedule H', 'Schedule H1', 'Schedule X'] },
                { key: 'salt_composition', label: 'Salt Composition', type: 'text' },
                { key: 'mfg_license', label: 'Mfg License No.', type: 'text' }
            ]
        },
        'textile': {
            id: 'textile_fashion',
            name_en: 'Textile & Apparel',
            attributes: [
                { key: 'size', label: 'Size (S/M/L/XL / 38/40)', type: 'text' },
                { key: 'fabric_type', label: 'Fabric (Cotton/Silk/Rayon)', type: 'text' },
                { key: 'color_pattern', label: 'Color / Pattern', type: 'text' },
                { key: 'gender_target', label: 'Target', type: 'select', options: ['Men', 'Women', 'Kids', 'Unisex'] }
            ]
        },
        'cement': {
            id: 'cement_steel_paints',
            name_en: 'Cement, Steel & Paints',
            attributes: [
                { key: 'grade', label: 'Grade (Fe550D / 53 Grade)', type: 'text' },
                { key: 'diameter_mm', label: 'Diameter (mm) / Size', type: 'text' },
                { key: 'color_shade', label: 'Shade Code / Finish', type: 'text' },
                { key: 'standard_cert', label: 'Standard (IS 1786 / IS 269)', type: 'text' }
            ]
        },
        'hardware': {
            id: 'hardware_tools',
            name_en: 'Hardware & Tools',
            attributes: [
                { key: 'material_grade', label: 'Material Grade (SS304/Brass/MS)', type: 'text' },
                { key: 'dimensions', label: 'Dimensions (Size / Length)', type: 'text' },
                { key: 'gauge', label: 'Gauge / Thickness', type: 'text' }
            ]
        },
        'grocery': {
            id: 'grocery_fmcg',
            name_en: 'Grocery & FMCG',
            attributes: [
                { key: 'mrp', label: 'MRP (₹)', type: 'number' },
                { key: 'fssai_license', label: 'FSSAI License No.', type: 'text' },
                { key: 'net_weight', label: 'Net Weight / Volume', type: 'text' }
            ]
        },
        'electronics': {
            id: 'electronics_mobiles',
            name_en: 'Electronics & Mobiles',
            attributes: [
                { key: 'model_number', label: 'Model Number', type: 'text' },
                { key: 'imei_serial', label: 'IMEI / Serial Number', type: 'text' },
                { key: 'warranty_period', label: 'Warranty Period (Months)', type: 'text' }
            ]
        },
        'agriculture': {
            id: 'agriculture_inputs',
            name_en: 'Agriculture & Seeds',
            attributes: [
                { key: 'crop_type', label: 'Crop Type', type: 'text' },
                { key: 'seed_variety', label: 'Variety / Hybrid', type: 'text' },
                { key: 'active_ingredient', label: 'Active Ingredient / Purity', type: 'text' }
            ]
        },
        'automotive': {
            id: 'automotive_spare_parts',
            name_en: 'Automotive Spare Parts',
            attributes: [
                { key: 'part_number', label: 'Part Number / OEM Code', type: 'text' },
                { key: 'compatible_vehicle', label: 'Compatible Vehicle Model', type: 'text' },
                { key: 'oem_brand', label: 'OEM Brand', type: 'text' }
            ]
        }
    };

    for (const [key, val] of Object.entries(builtInTaxonomies)) {
        if (lower.includes(key)) return val;
    }

    return null;
}

function renderCategoryAttributeFields(mode, categoryName, currentAttributes = {}) {
    const containerId = mode === 'add' ? 'addProdDynamicFieldsContainer' : 'editProdDynamicFieldsContainer';
    const container = document.getElementById(containerId);
    if (!container) return;

    const taxonomy = findTaxonomyForCategory(categoryName);
    if (!taxonomy || !taxonomy.attributes || taxonomy.attributes.length === 0) {
        container.style.display = 'none';
        container.innerHTML = '';
        return;
    }

    let fieldsHtml = `
        <div style="font-size:0.85rem; font-weight:700; color:var(--gray-800, #1e293b); margin-bottom:10px;">
            <i class="fas fa-tags" style="color:var(--lime-600, #16a34a); margin-right:6px;"></i>
            Specialized Category Attributes (${escapeHtml(taxonomy.name_en || taxonomy.id)}):
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
    `;

    taxonomy.attributes.forEach(attr => {
        const val = currentAttributes[attr.key] !== undefined ? currentAttributes[attr.key] : '';
        const reqStar = attr.required ? ' <span style="color:var(--red-500);">*</span>' : '';

        fieldsHtml += `<div class="form-group-dash" style="margin-bottom:0;">`;
        fieldsHtml += `<label style="font-size:0.8rem;">${escapeHtml(attr.label)}${reqStar}</label>`;

        if (attr.type === 'select' && Array.isArray(attr.options)) {
            fieldsHtml += `<select data-attr-key="${attr.key}" style="font-size:0.85rem; padding:6px 10px;">`;
            fieldsHtml += `<option value="">-- Select --</option>`;
            attr.options.forEach(opt => {
                const sel = String(val) === String(opt) ? ' selected' : '';
                fieldsHtml += `<option value="${escapeHtml(opt)}"${sel}>${escapeHtml(opt)}</option>`;
            });
            fieldsHtml += `</select>`;
        } else if (attr.type === 'date') {
            fieldsHtml += `<input type="date" data-attr-key="${attr.key}" value="${escapeHtml(String(val))}" style="font-size:0.85rem; padding:6px 10px;">`;
        } else if (attr.type === 'number') {
            fieldsHtml += `<input type="number" data-attr-key="${attr.key}" value="${escapeHtml(String(val))}" placeholder="${escapeHtml(attr.label)}" step="any" style="font-size:0.85rem; padding:6px 10px;">`;
        } else {
            fieldsHtml += `<input type="text" data-attr-key="${attr.key}" value="${escapeHtml(String(val))}" placeholder="${escapeHtml(attr.label)}" style="font-size:0.85rem; padding:6px 10px;">`;
        }
        fieldsHtml += `</div>`;
    });

    fieldsHtml += `</div>`;
    container.innerHTML = fieldsHtml;
    container.style.display = 'block';
}

function handleCategoryChange(mode) {
    const selId = mode === 'add' ? 'newProdCategory' : 'editProdCategory';
    const sel = document.getElementById(selId);
    if (!sel) return;
    renderCategoryAttributeFields(mode, sel.value);
}

// ── Add Product Form Handler (Live API) ──
async function handleAddProductSubmit(e) {
    e.preventDefault();
    const token = localStorage.getItem('shopo_auth_token');
    const errBox = document.getElementById('addProdError');
    if (errBox) errBox.style.display = 'none';

    const saveBtn = document.getElementById('saveProdBtn');
    if (saveBtn) saveBtn.disabled = true;

    // Collect dynamic attributes
    const attributes = {};
    const dynInputs = document.querySelectorAll('#addProdDynamicFieldsContainer [data-attr-key]');
    dynInputs.forEach(input => {
        const val = input.value.trim();
        if (val) attributes[input.dataset.attrKey] = val;
    });

    const payload = {
        product_name: document.getElementById('newProdName').value.trim(),
        category: document.getElementById('newProdCategory').value,
        brand: document.getElementById('newProdBrand').value.trim(),
        barcode: document.getElementById('newProdBarcode').value.trim(),
        sku: document.getElementById('newProdSku').value.trim(),
        purchase_price: parseFloat(document.getElementById('newProdBuy').value) || 0,
        selling_price: parseFloat(document.getElementById('newProdSell').value) || 0,
        quantity: parseFloat(document.getElementById('newProdQty').value) || 0,
        unit: document.getElementById('newProdUnit').value,
        low_stock_threshold: parseFloat(document.getElementById('newProdLowThreshold').value) || 5,
        expiry_date: document.getElementById('newProdExpiry').value || null,
        attributes: attributes
    };

    try {
        const resp = await fetch('/api/inventory', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });
        const res = await resp.json();

        if (res.success) {
            closeModal('addProductModal');
            if (res.item && res.item.id) {
                lastModifiedProductId = res.item.id;
            }
            // Reset form fields
            document.getElementById('newProdName').value = '';
            document.getElementById('newProdBrand').value = '';
            document.getElementById('newProdBarcode').value = '';
            document.getElementById('newProdSku').value = '';
            document.getElementById('newProdBuy').value = '';
            document.getElementById('newProdSell').value = '';
            document.getElementById('newProdQty').value = '';
            document.getElementById('newProdExpiry').value = '';

            fetchInventory();
            fetchInventorySummary();
            fetchFinancials();
            showSimulatedResponse(`✅ नया सामान जोड़ा गया: **${payload.product_name}** (${payload.quantity} ${payload.unit}) इन्वेंटरी में सफलतापूर्वक सेव हो गया!`);
        } else {
            if (errBox) {
                errBox.textContent = res.message || 'Error adding product.';
                errBox.style.display = 'block';
            }
        }
    } catch (err) {
        console.error('Failed to add product:', err);
        if (errBox) {
            errBox.textContent = 'Server connection error. Please try again.';
            errBox.style.display = 'block';
        }
    } finally {
        if (saveBtn) saveBtn.disabled = false;
    }
}

// ── Edit Product Modal & Submit (Live API) ──
function openEditProductModal(id) {
    const item = inventoryItems.find(it => it.id === id);
    if (!item) return;

    const errBox = document.getElementById('editProdError');
    if (errBox) errBox.style.display = 'none';

    document.getElementById('editProdId').value = item.id;
    document.getElementById('editProdName').value = item.product_name || '';
    document.getElementById('editProdCategory').value = item.category || 'General';
    document.getElementById('editProdBrand').value = item.brand || '';
    document.getElementById('editProdBarcode').value = item.barcode || '';
    document.getElementById('editProdSku').value = item.sku || '';
    document.getElementById('editProdBuy').value = item.purchase_price ?? '';
    document.getElementById('editProdSell').value = item.selling_price ?? '';
    document.getElementById('editProdQty').value = item.quantity ?? '';
    document.getElementById('editProdUnit').value = item.unit || 'pcs';
    document.getElementById('editProdLowThreshold').value = item.low_stock_threshold ?? 5;
    document.getElementById('editProdExpiry').value = item.expiry_date || '';

    // Render dynamic category attributes for edit
    renderCategoryAttributeFields('edit', item.category || 'General', item.attributes || {});

    openModal('editProductModal');
}

async function handleEditProductSubmit(e) {
    e.preventDefault();
    const token = localStorage.getItem('shopo_auth_token');
    const id = document.getElementById('editProdId').value;
    const errBox = document.getElementById('editProdError');
    if (errBox) errBox.style.display = 'none';

    const updateBtn = document.getElementById('updateProdBtn');
    if (updateBtn) updateBtn.disabled = true;

    // Collect dynamic attributes
    const attributes = {};
    const dynInputs = document.querySelectorAll('#editProdDynamicFieldsContainer [data-attr-key]');
    dynInputs.forEach(input => {
        const val = input.value.trim();
        if (val) attributes[input.dataset.attrKey] = val;
    });

    const payload = {
        product_name: document.getElementById('editProdName').value.trim(),
        category: document.getElementById('editProdCategory').value,
        brand: document.getElementById('editProdBrand').value.trim(),
        barcode: document.getElementById('editProdBarcode').value.trim(),
        sku: document.getElementById('editProdSku').value.trim(),
        purchase_price: parseFloat(document.getElementById('editProdBuy').value) || 0,
        selling_price: parseFloat(document.getElementById('editProdSell').value) || 0,
        quantity: parseFloat(document.getElementById('editProdQty').value) || 0,
        unit: document.getElementById('editProdUnit').value,
        low_stock_threshold: parseFloat(document.getElementById('editProdLowThreshold').value) || 5,
        expiry_date: document.getElementById('editProdExpiry').value || null,
        attributes: attributes
    };

    try {
        const resp = await fetch(`/api/inventory/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });
        const res = await resp.json();

        if (res.success) {
            closeModal('editProductModal');
            lastModifiedProductId = id;
            fetchInventory();
            fetchInventorySummary();
            fetchFinancials();
            showSimulatedResponse(`✏️ सामान अपडेट किया गया: **${payload.product_name}** की जानकारी सुरक्षित रूप से सेव हो गई!`);
        } else {
            if (errBox) {
                errBox.textContent = res.message || 'Error updating product.';
                errBox.style.display = 'block';
            }
        }
    } catch (err) {
        console.error('Failed to update product:', err);
        if (errBox) {
            errBox.textContent = 'Server connection error. Please try again.';
            errBox.style.display = 'block';
        }
    } finally {
        if (updateBtn) updateBtn.disabled = false;
    }
}

// ── Delete Confirmation Modal & Handler (Live API) ──
function openDeleteConfirmModal(id, name) {
    document.getElementById('deleteProdId').value = id;
    document.getElementById('deleteProdNameDisplay').textContent = name;
    openModal('deleteConfirmModal');
}

async function executeDeleteProduct() {
    const token = localStorage.getItem('shopo_auth_token');
    const id = document.getElementById('deleteProdId').value;
    const name = document.getElementById('deleteProdNameDisplay').textContent;

    try {
        const resp = await fetch(`/api/inventory/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();

        if (res.success) {
            closeModal('deleteConfirmModal');
            fetchInventory();
            fetchInventorySummary();
            fetchFinancials();
            showSimulatedResponse(`🗑️ सामान हटाया गया: **${name}** को इन्वेंटरी से डिलीट कर दिया गया।`);
        } else {
            alert(res.message || 'Error deleting product.');
        }
    } catch (err) {
        console.error('Failed to delete product:', err);
        alert('Server connection error. Please try again.');
    }
}

// ══════════════════════════════════════════════════════════════
// UNIVERSAL BARCODE & QR CODE SCANNER CLIENT ENGINE
// ══════════════════════════════════════════════════════════════

let html5QrScanner = null;
let scannerAvailableCameras = [];
let scannerActiveCameraId = null;
let scannerFacingMode = 'environment'; // default to back camera
let scannerIsRunning = false;
let scannerLastScannedCode = null;
let scannerLastScannedTime = 0;
let scannerTorchOn = false;

function switchScannerTab(tabName) {
    const tabs = ['camera', 'upload', 'manual', 'samples'];
    tabs.forEach(t => {
        const btn = document.getElementById(`scannerTab${t.charAt(0).toUpperCase() + t.slice(1)}`);
        const panel = document.getElementById(`scanner${t.charAt(0).toUpperCase() + t.slice(1)}Panel`);
        if (btn) btn.classList.toggle('active', t === tabName);
        if (panel) panel.style.display = (t === tabName) ? 'block' : 'none';
    });

    if (tabName === 'camera') {
        if (!scannerIsRunning) {
            startBarcodeScanner(scannerActiveCameraId);
        }
    } else {
        if (scannerIsRunning) {
            stopBarcodeScanner();
        }
    }
}

async function initScannerCameraDevices() {
    const select = document.getElementById('scannerCameraSelect');
    if (!select) return;

    if (typeof Html5Qrcode === 'undefined') {
        select.innerHTML = '<option value="">Scanner Library Loading...</option>';
        return;
    }

    try {
        const devices = await Html5Qrcode.getCameras();
        scannerAvailableCameras = devices || [];
        if (scannerAvailableCameras.length > 0) {
            let html = '';
            // Prefer back camera
            let defaultId = scannerAvailableCameras[0].id;
            scannerAvailableCameras.forEach((cam, idx) => {
                const label = cam.label || `Camera ${idx + 1}`;
                if (label.toLowerCase().includes('back') || label.toLowerCase().includes('environment') || label.toLowerCase().includes('rear')) {
                    defaultId = cam.id;
                }
                html += `<option value="${cam.id}">${escapeHtml(label)}</option>`;
            });
            select.innerHTML = html;
            select.value = defaultId;
            scannerActiveCameraId = defaultId;
        } else {
            select.innerHTML = '<option value="">No cameras detected</option>';
        }
    } catch (err) {
        console.warn('Camera enumeration error (permissions may be needed):', err);
        select.innerHTML = '<option value="">Default Camera / सामान्य कैमरा</option>';
    }
}

async function startBarcodeScanner(cameraId) {
    const statusText = document.getElementById('scannerStatusText');
    const reticle = document.getElementById('scannerReticle');
    const laser = document.getElementById('scannerLaser');

    if (typeof Html5Qrcode === 'undefined') {
        if (statusText) {
            statusText.innerHTML = '<span style="color:#DC2626;">⚠️ Scanner library not loaded. Use Manual Code or Upload Image.</span>';
        }
        return;
    }

    if (!html5QrScanner) {
        html5QrScanner = new Html5Qrcode("scannerReader", {
            formatsToSupport: [
                Html5QrcodeSupportedFormats.EAN_13,
                Html5QrcodeSupportedFormats.EAN_8,
                Html5QrcodeSupportedFormats.UPC_A,
                Html5QrcodeSupportedFormats.UPC_E,
                Html5QrcodeSupportedFormats.CODE_128,
                Html5QrcodeSupportedFormats.CODE_39,
                Html5QrcodeSupportedFormats.CODE_93,
                Html5QrcodeSupportedFormats.CODABAR,
                Html5QrcodeSupportedFormats.ITF,
                Html5QrcodeSupportedFormats.QR_CODE,
                Html5QrcodeSupportedFormats.DATA_MATRIX,
                Html5QrcodeSupportedFormats.AZTEC
            ],
            verbose: false
        });
    }

    if (scannerIsRunning) {
        await stopBarcodeScanner();
    }

    const config = {
        fps: 15,
        qrbox: { width: 250, height: 160 },
        aspectRatio: 1.5
    };

    const cameraConfig = cameraId ? { deviceId: { exact: cameraId } } : { facingMode: scannerFacingMode };

    try {
        if (statusText) {
            statusText.innerHTML = '<i class="fas fa-spinner fa-spin" style="color:var(--lime-600);"></i> <span>Starting camera stream... / कैमरा शुरू हो रहा है...</span>';
        }

        await html5QrScanner.start(
            cameraConfig,
            config,
            (decodedText, decodedResult) => {
                onBarcodeScanSuccess(decodedText, decodedResult);
            },
            (errorMessage) => {
                // Throttle silent scan failures during continuous frame analysis
            }
        );

        scannerIsRunning = true;
        if (reticle) reticle.style.display = 'flex';
        if (laser) laser.style.display = 'block';
        if (statusText) {
            statusText.innerHTML = '<i class="fas fa-check-circle" style="color:var(--green-500);"></i> <span>Align barcode or QR code inside the box / कोड को बॉक्स के बीच रखें</span>';
        }

        // Check torch capability
        checkTorchCapability();

        // Populate camera list once permission is granted
        if (scannerAvailableCameras.length === 0) {
            initScannerCameraDevices();
        }
    } catch (err) {
        scannerIsRunning = false;
        if (reticle) reticle.style.display = 'none';
        if (laser) laser.style.display = 'none';

        const errMsg = err ? (err.message || err.toString()) : '';
        let userAdvice = 'Camera access was blocked or not available.';
        if (errMsg.includes('NotAllowedError') || errMsg.includes('Permission denied')) {
            userAdvice = 'कैमरा अनुमति अस्वीकृत (Camera Permission Denied). कृपया ब्राउज़र सेटिंग्स में कैमरा अनुमति दें या नीचे मैन्युअल कोड / फोटो अपलोड का उपयोग करें।';
        } else if (errMsg.includes('NotFoundError') || errMsg.includes('DevicesNotFoundError')) {
            userAdvice = 'कोई कैमरा नहीं मिला (No Camera Found). कृपया फोटो अपलोड या मैन्युअल कोड का उपयोग करें।';
        } else if (window.location.protocol !== 'https:' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
            userAdvice = 'कैमरा सुरक्षित कनेक्शन (HTTPS/Localhost) मांगता है। कृपया मैन्युअल कोड या फोटो अपलोड का उपयोग करें।';
        }

        if (statusText) {
            statusText.innerHTML = `
                <div style="background:#FEE2E2; border:1px solid #FCA5A5; color:#991B1B; padding:10px 14px; border-radius:8px; font-size:0.85rem; text-align:left; width:100%;">
                    <strong><i class="fas fa-exclamation-triangle"></i> कैमरा शुरू नहीं हो सका:</strong><br>
                    <span>${escapeHtml(userAdvice)}</span>
                    <div style="margin-top:8px; display:flex; gap:8px;">
                        <button type="button" class="btn-dash btn-dash-primary" style="padding:4px 10px; font-size:0.78rem;" onclick="switchScannerTab('manual')">
                            <i class="fas fa-keyboard"></i> Use Manual Code
                        </button>
                        <button type="button" class="btn-dash btn-dash-secondary" style="padding:4px 10px; font-size:0.78rem;" onclick="switchScannerTab('upload')">
                            <i class="fas fa-file-image"></i> Upload Image
                        </button>
                    </div>
                </div>
            `;
        }
    }
}

async function stopBarcodeScanner() {
    if (html5QrScanner && scannerIsRunning) {
        try {
            await html5QrScanner.stop();
        } catch (e) {
            console.warn('Error stopping scanner:', e);
        }
    }
    scannerIsRunning = false;
    scannerTorchOn = false;
    const torchBtn = document.getElementById('scannerTorchBtn');
    if (torchBtn) {
        torchBtn.style.display = 'none';
        torchBtn.innerHTML = '<i class="fas fa-bolt"></i> Flash';
    }
    const reticle = document.getElementById('scannerReticle');
    const laser = document.getElementById('scannerLaser');
    if (reticle) reticle.style.display = 'none';
    if (laser) laser.style.display = 'none';
}

function onScannerCameraChange(newCameraId) {
    if (!newCameraId) return;
    scannerActiveCameraId = newCameraId;
    if (scannerIsRunning) {
        startBarcodeScanner(newCameraId);
    }
}

function toggleCameraFacing() {
    scannerFacingMode = (scannerFacingMode === 'environment') ? 'user' : 'environment';
    scannerActiveCameraId = null;
    startBarcodeScanner(null);
}

function checkTorchCapability() {
    const torchBtn = document.getElementById('scannerTorchBtn');
    if (!torchBtn) return;
    try {
        if (html5QrScanner && typeof html5QrScanner.getRunningTrackCapabilities === 'function') {
            const caps = html5QrScanner.getRunningTrackCapabilities();
            if (caps && caps.torch) {
                torchBtn.style.display = 'inline-flex';
                return;
            }
        }
    } catch (e) {}
    torchBtn.style.display = 'none';
}

async function toggleTorch() {
    const torchBtn = document.getElementById('scannerTorchBtn');
    if (!html5QrScanner || !scannerIsRunning) return;
    try {
        scannerTorchOn = !scannerTorchOn;
        await html5QrScanner.applyVideoConstraints({
            advanced: [{ torch: scannerTorchOn }]
        });
        if (torchBtn) {
            torchBtn.innerHTML = scannerTorchOn ? '<i class="fas fa-bolt" style="color:var(--lime-600);"></i> Flash On' : '<i class="fas fa-bolt"></i> Flash';
        }
    } catch (e) {
        console.warn('Torch toggle not supported on this track:', e);
    }
}

async function handleScannerFileSelect(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    const statusText = document.getElementById('scannerStatusText');
    if (statusText) {
        statusText.innerHTML = '<i class="fas fa-spinner fa-spin" style="color:var(--lime-600);"></i> Decoding image file... / फोटो स्कैन हो रही है...';
    }

    if (!html5QrScanner) {
        html5QrScanner = new Html5Qrcode("scannerReader", { verbose: false });
    }

    try {
        const decodedText = await html5QrScanner.scanFile(file, true);
        if (decodedText) {
            onBarcodeScanSuccess(decodedText, { result: { format: { formatName: "IMAGE_FILE" } } });
        }
    } catch (err) {
        alert('चित्र में कोई स्पष्ट बारकोड या क्यूआर कोड नहीं मिला (No readable barcode found in image). कृपया स्पष्ट फोटो अपलोड करें या मैन्युअल कोड लिखें।');
        if (statusText) {
            statusText.innerHTML = '<span style="color:#DC2626;">❌ बारकोड नहीं मिला। कृपया पुनः प्रयास करें।</span>';
        }
    }
    event.target.value = '';
}

function submitManualScannerCode() {
    const input = document.getElementById('scannerManualInput');
    const val = input ? input.value.trim() : '';
    if (!val) {
        alert('कृपया कोई बारकोड, ISBN या SKU कोड दर्ज करें (Please enter a code).');
        return;
    }
    lookupScannedCode(val, 'MANUAL_ENTRY');
}

function onBarcodeScanSuccess(decodedText, decodedResult) {
    if (!decodedText) return;
    const clean = decodedText.trim();

    // Debounce duplicate detections of same code within 2.5 seconds
    const now = Date.now();
    if (scannerLastScannedCode === clean && (now - scannerLastScannedTime) < 2500) {
        return;
    }
    scannerLastScannedCode = clean;
    scannerLastScannedTime = now;

    // Visual capture feedback: pause laser line, flash reticle
    const laser = document.getElementById('scannerLaser');
    if (laser) {
        laser.style.display = 'none';
    }
    const reticle = document.getElementById('scannerReticle');
    if (reticle) {
        reticle.classList.remove('scanner-captured-flash');
        void reticle.offsetWidth;
        reticle.classList.add('scanner-captured-flash');
    }

    // Haptic vibration feedback if supported
    if (navigator.vibrate) {
        try { navigator.vibrate([40, 30, 40]); } catch (e) {}
    }

    const formatName = decodedResult && decodedResult.result && decodedResult.result.format
        ? (decodedResult.result.format.formatName || 'BARCODE')
        : 'AUTO';

    lookupScannedCode(clean, formatName);
}

async function lookupScannedCode(code, formatHint) {
    const statusText = document.getElementById('scannerStatusText');
    const resultBox = document.getElementById('scannerResultBox');

    if (statusText) {
        statusText.innerHTML = `<i class="fas fa-spinner fa-spin" style="color:var(--lime-600);"></i> <span>Searching catalogues for <strong>${escapeHtml(code)}</strong>...</span>`;
    }

    if (resultBox) {
        resultBox.style.display = 'block';
        resultBox.innerHTML = `
            <div style="text-align:center; padding:20px; color:var(--text-secondary);">
                <i class="fas fa-spinner fa-spin" style="font-size:1.6rem; color:var(--lime-600); margin-bottom:8px;"></i><br>
                <span>Looking up product code <strong>${escapeHtml(code)}</strong> in dukaan stock & verified catalogues...</span>
            </div>
        `;
    }

    const token = localStorage.getItem('shopo_auth_token');
    try {
        const resp = await fetch('/api/inventory/scan/lookup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ code: code, format: formatHint })
        });

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            renderScannerError(errData.message || 'Lookup failed.');
            return;
        }

        const data = await resp.json();
        renderScannerResult(data);
    } catch (err) {
        console.error('Scan lookup error:', err);
        renderScannerError('Network connection error while looking up barcode.');
    }
}

function renderScannerError(msg) {
    const resultBox = document.getElementById('scannerResultBox');
    if (!resultBox) return;
    resultBox.style.display = 'block';
    resultBox.style.background = '#FEE2E2';
    resultBox.style.borderColor = '#FCA5A5';
    resultBox.innerHTML = `
        <div style="color:#991B1B;">
            <i class="fas fa-exclamation-circle"></i> <strong>Error:</strong> ${escapeHtml(msg)}<br>
            <div style="margin-top:10px;">
                <button type="button" class="btn-dash btn-dash-secondary" style="padding:4px 12px; font-size:0.8rem;" onclick="resetScannerView()">
                    Try Again / पुनः प्रयास
                </button>
            </div>
        </div>
    `;
}

function renderScannerResult(res) {
    const resultBox = document.getElementById('scannerResultBox');
    if (!resultBox) return;
    resultBox.style.display = 'block';

    const status = res.status;
    const code = res.code || '';
    const codeType = res.code_type || 'BARCODE';

    // ── CASE A: PRODUCT FOUND IN STORE ──
    if (status === 'found_in_store') {
        const p = res.product || {};
        resultBox.style.background = 'var(--lime-50)';
        resultBox.style.borderColor = 'var(--lime-400)';
        resultBox.innerHTML = `
            <div class="scanner-result-header">
                <div>
                    <span class="scanner-badge in-store">
                        <i class="fas fa-check-circle"></i> In Dukaan Stock / दुकान में उपलब्ध
                    </span>
                    <h3 class="scanner-product-title">${escapeHtml(p.product_name)}</h3>
                </div>
            </div>
            <div class="scanner-product-meta">
                <span><strong>Category:</strong> ${escapeHtml(p.category || 'General')}</span>
                <span><strong>Available Stock:</strong> <span style="color:var(--lime-800); font-weight:700;">${p.quantity} ${escapeHtml(p.unit || 'pcs')}</span></span>
                <span><strong>Selling Price:</strong> ₹${p.selling_price}</span>
                <span><strong>Purchase Cost:</strong> ₹${p.purchase_price}</span>
                <span><strong>Barcode:</strong> <code>${escapeHtml(code)}</code></span>
            </div>

            <!-- Action Buttons for Existing Product -->
            <div class="scanner-action-btn-row">
                <button type="button" class="btn-dash btn-dash-primary" onclick="toggleScannerReceiveStockForm('${escapeHtml(p.id)}', '${escapeHtml(p.product_name)}', '${escapeHtml(p.unit || 'pcs')}', ${p.purchase_price || 0}, ${p.selling_price || 0})">
                    <i class="fas fa-plus-circle"></i> Receive Stock (+ माल आया)
                </button>
                <button type="button" class="btn-dash btn-dash-secondary" onclick="closeBarcodeModal(); openEditProductModal('${p.id}');">
                    <i class="fas fa-edit"></i> Edit Product
                </button>
                <button type="button" class="btn-dash btn-dash-secondary" onclick="resetScannerView()">
                    <i class="fas fa-redo"></i> Scan Next
                </button>
            </div>

            <!-- Inline Receive Stock Form (Initially Hidden) -->
            <div id="scannerReceiveStockCard" class="scanner-inline-form-card" style="display:none;">
                <h4 style="margin:0 0 6px 0; color:var(--text-primary); font-size:0.9rem;">
                    <i class="fas fa-truck-loading" style="color:var(--lime-600);"></i>
                    Receive Inbound Stock for ${escapeHtml(p.product_name)}
                </h4>
                <div class="scanner-form-grid">
                    <div class="scanner-form-field">
                        <label>Quantity to Add / मात्रा</label>
                        <input type="number" id="scRcvQty" step="any" min="0.1" value="10" placeholder="10">
                    </div>
                    <div class="scanner-form-field">
                        <label>Unit / इकाई</label>
                        <input type="text" id="scRcvUnit" value="${escapeHtml(p.unit || 'pcs')}" readonly>
                    </div>
                    <div class="scanner-form-field">
                        <label>Purchase Cost (₹) / खरीद दर</label>
                        <input type="number" id="scRcvCost" step="any" min="0" value="${p.purchase_price || 0}">
                    </div>
                    <div class="scanner-form-field">
                        <label>Retail Price (₹) / बिक्री दर</label>
                        <input type="number" id="scRcvSell" step="any" min="0" value="${p.selling_price || 0}">
                    </div>
                </div>
                <div style="margin-top:12px; display:flex; gap:8px;">
                    <button type="button" class="btn-dash btn-dash-primary" onclick="submitInlineStockReceipt('${p.id}', '${escapeHtml(p.product_name)}')">
                        <i class="fas fa-check"></i> Confirm & Update Stock
                    </button>
                    <button type="button" class="btn-dash btn-dash-secondary" onclick="document.getElementById('scannerReceiveStockCard').style.display='none'">
                        Cancel
                    </button>
                </div>
            </div>
        `;
        return;
    }

    // ── CASE B: FOUND IN EXTERNAL CATALOGUE (NOT IN SHOP) ──
    if (status === 'found_external') {
        const p = res.product || {};
        resultBox.style.background = '#F0F9FF';
        resultBox.style.borderColor = '#7DD3FC';
        resultBox.innerHTML = `
            <div class="scanner-result-header">
                <div>
                    <span class="scanner-badge external">
                        <i class="fas fa-globe"></i> ${escapeHtml(res.source || 'Verified Catalogue')}
                    </span>
                    <h3 class="scanner-product-title">${escapeHtml(p.product_name)}</h3>
                </div>
            </div>
            <p style="font-size:0.83rem; color:#0369A1; margin:0 0 10px 0;">
                Product identified externally. Please provide your purchase cost, selling price, and initial stock quantity to add it to your dukaan.
            </p>
            <div class="scanner-product-meta">
                <span><strong>Brand:</strong> ${escapeHtml(p.brand || 'N/A')}</span>
                <span><strong>Category:</strong> ${escapeHtml(p.category || 'General')}</span>
                <span><strong>Barcode:</strong> <code>${escapeHtml(code)}</code></span>
                ${p.mrp ? `<span><strong>MRP:</strong> ₹${p.mrp}</span>` : ''}
            </div>

            <!-- Inline Product Registration Form -->
            <div class="scanner-inline-form-card">
                <h4 style="margin:0 0 6px 0; color:var(--text-primary); font-size:0.9rem;">
                    <i class="fas fa-plus-circle" style="color:var(--lime-600);"></i>
                    Register into Dukaan Inventory
                </h4>
                <div class="scanner-form-grid">
                    <div class="scanner-form-field" style="grid-column: 1 / -1;">
                        <label>Product Name / उत्पाद का नाम *</label>
                        <input type="text" id="scRegName" value="${escapeHtml(p.product_name)}">
                    </div>
                    <div class="scanner-form-field">
                        <label>Category / श्रेणी *</label>
                        <select id="scRegCategory">
                            <option value="Grocery, FMCG, and Supermarkets" ${p.category === 'Grocery, FMCG, and Supermarkets' ? 'selected' : ''}>Grocery & FMCG / किराना</option>
                            <option value="Dairy, Milk Products, Poultry, and Animal Husbandry" ${p.category && p.category.includes('Dairy') ? 'selected' : ''}>Dairy & Milk / डेयरी</option>
                            <option value="Pharmacy and Medical Retail" ${p.category && p.category.includes('Pharmacy') ? 'selected' : ''}>Pharmacy & Medical / दवा</option>
                            <option value="Hardware and Construction Materials" ${p.category && p.category.includes('Hardware') ? 'selected' : ''}>Hardware & Tools / हार्डवेयर</option>
                            <option value="Cement, Steel, Paint, Pipes, and Electrical Supplies" ${p.category && p.category.includes('Electrical') ? 'selected' : ''}>Electrical & Paints / बिजली</option>
                            <option value="Textile, Clothing, Fashion, and Apparel" ${p.category && p.category.includes('Textile') ? 'selected' : ''}>Textile & Clothing / कपड़ा</option>
                            <option value="Electronics, Mobiles, and Computers" ${p.category && p.category.includes('Electronics') ? 'selected' : ''}>Electronics / इलेक्ट्रॉनिक्स</option>
                            <option value="Stationery, Books, and School Supplies" ${p.category && p.category.includes('Stationery') ? 'selected' : ''}>Books & Stationery / किताबें</option>
                            <option value="General" ${!p.category || p.category === 'General' ? 'selected' : ''}>Other / सामान्य</option>
                        </select>
                    </div>
                    <div class="scanner-form-field">
                        <label>Initial Stock / प्रारंभिक स्टॉक *</label>
                        <input type="number" id="scRegQty" step="any" min="0" placeholder="e.g. 10">
                    </div>
                    <div class="scanner-form-field">
                        <label>Unit / इकाई *</label>
                        <input type="text" id="scRegUnit" value="${escapeHtml(p.unit || 'pcs')}">
                    </div>
                    <div class="scanner-form-field">
                        <label>Purchase Cost (₹) / खरीद दर *</label>
                        <input type="number" id="scRegPurchase" step="any" min="0" placeholder="e.g. 80">
                    </div>
                    <div class="scanner-form-field">
                        <label>Selling Price (₹) / बिक्री दर *</label>
                        <input type="number" id="scRegSelling" step="any" min="0" placeholder="e.g. 95">
                    </div>
                </div>
                <div style="margin-top:12px; display:flex; gap:8px;">
                    <button type="button" class="btn-dash btn-dash-primary" onclick="submitInlineProductRegistration('${escapeHtml(code)}')">
                        <i class="fas fa-save"></i> Save Product to Dukaan
                    </button>
                    <button type="button" class="btn-dash btn-dash-secondary" onclick="resetScannerView()">
                        Cancel
                    </button>
                </div>
            </div>
        `;
        return;
    }

    // ── CASE C: COMPLETELY UNKNOWN CODE ──
    if (status === 'unknown_code') {
        resultBox.style.background = '#FFFBEB';
        resultBox.style.borderColor = '#FCD34D';
        resultBox.innerHTML = `
            <div class="scanner-result-header">
                <div>
                    <span class="scanner-badge unknown">
                        <i class="fas fa-question-circle"></i> New Code / अपरिचित कोड
                    </span>
                    <h3 class="scanner-product-title">Code: ${escapeHtml(code)}</h3>
                </div>
            </div>
            <p style="font-size:0.83rem; color:#92400E; margin:0 0 10px 0;">
                Product code not found in store or external catalogues. You can create a new product using this code.
            </p>

            <div class="scanner-inline-form-card">
                <h4 style="margin:0 0 6px 0; color:var(--text-primary); font-size:0.9rem;">
                    <i class="fas fa-plus-circle" style="color:var(--lime-600);"></i>
                    Create New Product
                </h4>
                <div class="scanner-form-grid">
                    <div class="scanner-form-field" style="grid-column: 1 / -1;">
                        <label>Product Name / उत्पाद का नाम *</label>
                        <input type="text" id="scRegName" placeholder="e.g. Havells 10A Switch, Fortune Mustard Oil 1L">
                    </div>
                    <div class="scanner-form-field">
                        <label>Category / श्रेणी *</label>
                        <select id="scRegCategory">
                            <option value="Grocery, FMCG, and Supermarkets">Grocery & FMCG / किराना</option>
                            <option value="Pharmacy and Medical Retail">Pharmacy & Medical / दवा</option>
                            <option value="Hardware and Construction Materials">Hardware & Tools / हार्डवेयर</option>
                            <option value="Cement, Steel, Paint, Pipes, and Electrical Supplies">Electrical & Paints / बिजली</option>
                            <option value="Textile, Clothing, Fashion, and Apparel">Textile & Clothing / कपड़ा</option>
                            <option value="Electronics, Mobiles, and Computers">Electronics / इलेक्ट्रॉनिक्स</option>
                            <option value="Dairy, Milk Products, Poultry, and Animal Husbandry">Dairy / डेयरी</option>
                            <option value="Stationery, Books, and School Supplies">Books & Stationery / स्टेशनरी</option>
                            <option value="General">Other / सामान्य</option>
                        </select>
                    </div>
                    <div class="scanner-form-field">
                        <label>Initial Stock / स्टॉक *</label>
                        <input type="number" id="scRegQty" step="any" min="0" placeholder="10">
                    </div>
                    <div class="scanner-form-field">
                        <label>Unit / इकाई *</label>
                        <input type="text" id="scRegUnit" value="pcs" placeholder="pcs, kg, box...">
                    </div>
                    <div class="scanner-form-field">
                        <label>Purchase Cost (₹) / खरीद दर *</label>
                        <input type="number" id="scRegPurchase" step="any" min="0" placeholder="0">
                    </div>
                    <div class="scanner-form-field">
                        <label>Selling Price (₹) / बिक्री दर *</label>
                        <input type="number" id="scRegSelling" step="any" min="0" placeholder="0">
                    </div>
                </div>
                <div style="margin-top:12px; display:flex; gap:8px;">
                    <button type="button" class="btn-dash btn-dash-primary" onclick="submitInlineProductRegistration('${escapeHtml(code)}')">
                        <i class="fas fa-save"></i> Register Product
                    </button>
                    <button type="button" class="btn-dash btn-dash-secondary" onclick="resetScannerView()">
                        Cancel
                    </button>
                </div>
            </div>
        `;
        return;
    }

    // ── CASE D: QR PAYLOAD RATHER THAN PRODUCT IDENTIFIER ──
    if (status === 'qr_payload') {
        resultBox.style.background = '#FAF5FF';
        resultBox.style.borderColor = '#D8B4FE';
        resultBox.innerHTML = `
            <div class="scanner-result-header">
                <div>
                    <span class="scanner-badge qr-info">
                        <i class="fas fa-qrcode"></i> ${escapeHtml(res.payload_type || 'QR Code')}
                    </span>
                    <h3 class="scanner-product-title">QR Payload Decoded</h3>
                </div>
            </div>
            <p style="font-size:0.85rem; color:#6B21A8; margin:0 0 10px 0;">
                ${escapeHtml(res.message || 'Scanned code contains a QR payload rather than a product barcode.')}
            </p>
            <div style="background:#FFFFFF; border:1px solid #E9D5FF; padding:10px 14px; border-radius:8px; font-size:0.85rem; word-break:break-all; font-family:monospace; margin-bottom:12px;">
                ${escapeHtml(res.safe_display || code)}
            </div>
            <div class="scanner-action-btn-row">
                <button type="button" class="btn-dash btn-dash-primary" onclick="openAddProductModalWithBarcode('${escapeHtml(code)}')">
                    <i class="fas fa-plus"></i> Register Product Using this Code
                </button>
                <button type="button" class="btn-dash btn-dash-secondary" onclick="resetScannerView()">
                    <i class="fas fa-redo"></i> Scan Another
                </button>
            </div>
        `;
        return;
    }

    // ── CASE E: AMBIGUOUS MATCH (MULTIPLE PRODUCTS) ──
    if (status === 'ambiguous_match') {
        const candidates = res.candidates || [];
        let candHtml = '';
        candidates.forEach(c => {
            candHtml += `
                <div style="background:#FFFFFF; border:1px solid var(--border-color); padding:10px 14px; border-radius:8px; display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <div>
                        <strong>${escapeHtml(c.product_name)}</strong> (${escapeHtml(c.category)})<br>
                        <span style="font-size:0.8rem; color:var(--text-secondary);">Stock: ${c.quantity} ${escapeHtml(c.unit)} &bull; Price: ₹${c.selling_price}</span>
                    </div>
                    <button type="button" class="btn-dash btn-dash-primary" style="padding:4px 10px; font-size:0.8rem;" onclick="toggleScannerReceiveStockForm('${c.id}', '${escapeHtml(c.product_name)}', '${escapeHtml(c.unit)}', 0, ${c.selling_price})">
                        Select
                    </button>
                </div>
            `;
        });

        resultBox.style.background = '#F0F9FF';
        resultBox.style.borderColor = '#7DD3FC';
        resultBox.innerHTML = `
            <div class="scanner-result-header">
                <div>
                    <span class="scanner-badge external">
                        <i class="fas fa-layer-group"></i> Multiple Matches / एकाधिक उत्पाद
                    </span>
                    <h3 class="scanner-product-title">${candidates.length} Products Found</h3>
                </div>
            </div>
            <p style="font-size:0.83rem; color:var(--text-secondary); margin:0 0 10px 0;">
                Multiple products match this code in your inventory. Select the correct item:
            </p>
            ${candHtml}
            <div style="margin-top:8px;">
                <button type="button" class="btn-dash btn-dash-secondary" onclick="resetScannerView()">
                    Cancel / पुनः स्कैन
                </button>
            </div>
        `;
        return;
    }
}

function toggleScannerReceiveStockForm(id, name, unit, cost, sell) {
    const card = document.getElementById('scannerReceiveStockCard');
    if (!card) return;
    card.style.display = card.style.display === 'none' ? 'block' : 'none';
    const costInput = document.getElementById('scRcvCost');
    const sellInput = document.getElementById('scRcvSell');
    if (costInput && cost) costInput.value = cost;
    if (sellInput && sell) sellInput.value = sell;
}

async function submitInlineStockReceipt(productId, productName) {
    const qtyInput = document.getElementById('scRcvQty');
    const costInput = document.getElementById('scRcvCost');
    const sellInput = document.getElementById('scRcvSell');

    const qty = parseFloat(qtyInput ? qtyInput.value : 0) || 0;
    const cost = parseFloat(costInput ? costInput.value : 0) || 0;
    const sell = parseFloat(sellInput ? sellInput.value : 0) || 0;

    if (qty <= 0) {
        alert('कृपया वैध मात्रा दर्ज करें (Quantity must be greater than zero).');
        return;
    }

    const token = localStorage.getItem('shopo_auth_token');
    try {
        const resp = await fetch('/api/inventory/scan/receive-stock', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                product_id: productId,
                product_name: productName,
                quantity: qty,
                purchase_price: cost,
                selling_price: sell
            })
        });

        const data = await resp.json();
        if (!resp.ok) {
            alert('Stock update failed: ' + (data.message || 'Error'));
            return;
        }

        alert(`✅ ${data.message}`);
        // Refresh store inventory table & metrics
        if (typeof loadInventory === 'function') loadInventory();
        if (typeof loadInventorySummary === 'function') loadInventorySummary();
        closeBarcodeModal();
    } catch (e) {
        console.error('Receive stock error:', e);
        alert('Server connection error while receiving stock.');
    }
}

async function submitInlineProductRegistration(barcode) {
    const nameInput = document.getElementById('scRegName');
    const catInput = document.getElementById('scRegCategory');
    const qtyInput = document.getElementById('scRegQty');
    const unitInput = document.getElementById('scRegUnit');
    const costInput = document.getElementById('scRegPurchase');
    const sellInput = document.getElementById('scRegSelling');

    const name = nameInput ? nameInput.value.trim() : '';
    const cat = catInput ? catInput.value : 'General';
    const qty = parseFloat(qtyInput ? qtyInput.value : 0);
    const unit = unitInput ? unitInput.value.trim() : 'pcs';
    const cost = parseFloat(costInput ? costInput.value : 0);
    const sell = parseFloat(sellInput ? sellInput.value : 0);

    if (!name) {
        alert('कृपया उत्पाद का नाम दर्ज करें (Product name is required).');
        return;
    }
    if (isNaN(sell) || sell < 0) {
        alert('कृपया वैध बिक्री मूल्य दर्ज करें (Valid selling price is required).');
        return;
    }
    if (isNaN(qty) || qty < 0) {
        alert('कृपया वैध प्रारंभिक स्टॉक दर्ज करें (Valid quantity is required).');
        return;
    }

    const token = localStorage.getItem('shopo_auth_token');
    const payload = {
        product_name: name,
        category: cat,
        barcode: barcode || null,
        quantity: isNaN(qty) ? 0 : qty,
        unit: unit || 'pcs',
        purchase_price: isNaN(cost) ? 0 : cost,
        selling_price: sell
    };

    try {
        const resp = await fetch('/api/inventory/scan/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });

        const data = await resp.json();
        if (!resp.ok) {
            alert('Product registration failed: ' + (data.message || data.error || 'Conflict or Error'));
            return;
        }

        alert(`✅ ${data.message || 'Product registered successfully!'}`);
        if (typeof loadInventory === 'function') loadInventory();
        if (typeof loadInventorySummary === 'function') loadInventorySummary();
        closeBarcodeModal();
    } catch (e) {
        console.error('Registration error:', e);
        alert('Server connection error while registering product.');
    }
}

function openAddProductModalWithBarcode(barcode) {
    closeBarcodeModal();
    const barcodeInput = document.getElementById('newProdBarcode');
    if (barcodeInput) barcodeInput.value = barcode;
    openAddProductModal();
}

function resetScannerView() {
    const resultBox = document.getElementById('scannerResultBox');
    if (resultBox) {
        resultBox.style.display = 'none';
        resultBox.innerHTML = '';
    }
    const statusText = document.getElementById('scannerStatusText');
    if (statusText) {
        statusText.innerHTML = '<i class="fas fa-info-circle" style="color:var(--lime-600);"></i> <span>Point camera at any product barcode or QR code / बारकोड या QR सामने लाएं</span>';
    }
    const reticle = document.getElementById('scannerReticle');
    if (reticle) {
        reticle.classList.remove('scanner-captured-flash');
    }
    const laser = document.getElementById('scannerLaser');
    if (laser && scannerIsRunning) {
        laser.style.display = 'block';
    }
    scannerLastScannedCode = null;
}

// Backward-compatibility wrapper for any legacy button or script
function simulateBarcodeScan(code, defaultName) {
    lookupScannedCode(code, 'SIMULATION');
}

function prepareAddScannedProduct(name, barcode) {
    closeBarcodeModal();
    const nameInput = document.getElementById('newProdName');
    const barInput = document.getElementById('newProdBarcode');
    if (nameInput) nameInput.value = name;
    if (barInput) barInput.value = barcode;
    openAddProductModal();
}

// ── Real Sales Recording (Prompt 6A) ──
function populateSaleProductDropdown() {
    const select = document.getElementById('saleProdSelect');
    if (!select) return;

    if (!inventoryItems || inventoryItems.length === 0) {
        select.innerHTML = '<option value="" disabled selected>No products in inventory — please add products first</option>';
        return;
    }

    let html = '<option value="">-- Select product from inventory --</option>';
    inventoryItems.forEach(item => {
        html += `<option value="${item.id}">${escapeHtml(item.product_name)} (${item.quantity} ${escapeHtml(item.unit)} in stock — ₹${item.selling_price})</option>`;
    });
    select.innerHTML = html;
}

function handleSaleProductSelectChange(productId) {
    const item = (inventoryItems || []).find(it => it.id === productId);
    const hint = document.getElementById('saleProdStockHint');
    const priceInput = document.getElementById('saleUnitPrice');
    const qtyInput = document.getElementById('saleQty');

    if (!item) {
        if (hint) hint.textContent = '';
        calculateSaleTotalPreview();
        return;
    }

    if (priceInput) priceInput.value = item.selling_price;
    if (qtyInput && Number(qtyInput.value) <= 0) qtyInput.value = 1;

    if (hint) {
        hint.innerHTML = `<span style="color:var(--lime-700); font-weight:600;"><i class="fas fa-cubes"></i> Available Stock: ${item.quantity} ${escapeHtml(item.unit)}</span> &bull; <span style="color:var(--text-secondary);">Cost: ₹${item.purchase_price}</span>`;
    }

    calculateSaleTotalPreview();
}

function calculateSaleTotalPreview() {
    const qty = parseFloat(document.getElementById('saleQty')?.value) || 0;
    const price = parseFloat(document.getElementById('saleUnitPrice')?.value) || 0;
    const previewEl = document.getElementById('saleTotalAmountPreview');
    if (previewEl) {
        const total = (qty * price).toFixed(2);
        previewEl.textContent = `₹${total}`;
    }
}

function openRecordSaleModal() {
    populateSaleProductDropdown();
    const errBox = document.getElementById('recordSaleError');
    if (errBox) errBox.style.display = 'none';

    const hint = document.getElementById('saleProdStockHint');
    if (hint) hint.textContent = '';

    const priceInput = document.getElementById('saleUnitPrice');
    if (priceInput) priceInput.value = '';

    const qtyInput = document.getElementById('saleQty');
    if (qtyInput) qtyInput.value = 1;

    calculateSaleTotalPreview();
    openModal('recordSaleModal');
}

async function handleRecordSaleSubmit(e) {
    e.preventDefault();
    const token = localStorage.getItem('shopo_auth_token');
    const prodId = document.getElementById('saleProdSelect').value;
    const qty = parseFloat(document.getElementById('saleQty').value) || 0;
    const unitPrice = parseFloat(document.getElementById('saleUnitPrice').value) || 0;
    const paymentMode = document.getElementById('salePaymentMode').value;
    const errBox = document.getElementById('recordSaleError');
    const btn = document.getElementById('btnCompleteSale');

    if (!prodId) {
        if (errBox) {
            errBox.textContent = 'Please select a product from your inventory.';
            errBox.style.display = 'block';
        }
        return;
    }

    if (qty <= 0) {
        if (errBox) {
            errBox.textContent = 'Sale quantity must be greater than zero.';
            errBox.style.display = 'block';
        }
        return;
    }

    const item = (inventoryItems || []).find(it => it.id === prodId);
    if (!item) {
        if (errBox) {
            errBox.textContent = 'Selected product could not be found.';
            errBox.style.display = 'block';
        }
        return;
    }

    if (btn) btn.disabled = true;
    if (errBox) errBox.style.display = 'none';

    try {
        const resp = await fetch('/api/sales', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                product_id: item.id,
                product_name: item.product_name,
                quantity: qty,
                selling_price: unitPrice,
                cost_price: item.purchase_price,
                unit: item.unit,
                payment_mode: paymentMode,
            })
        });
        const res = await resp.json();

        if (res.success) {
            closeModal('recordSaleModal');
            // Refresh inventory, sales, and business financials
            fetchInventory();
            fetchInventorySummary();
            fetchSales();
            fetchFinancials();

            const total = (qty * unitPrice).toFixed(2);
            showSimulatedResponse(`✅ बिक्री दर्ज हुई: **${item.product_name}** (${qty} ${item.unit}) &bull; ₹${total} (${paymentMode})। इन्वेंटरी और मुनाफ़ा अपडेट हो गया!`);
        } else {
            if (errBox) {
                errBox.textContent = res.message || 'Error recording sale.';
                errBox.style.display = 'block';
            }
        }
    } catch (err) {
        console.error('Failed to record sale:', err);
        if (errBox) {
            errBox.textContent = 'Server connection error. Please try again.';
            errBox.style.display = 'block';
        }
    } finally {
        if (btn) btn.disabled = false;
    }
}

// ── Quick Shop Setup Form Submission (Calls Backend) ──
async function handleQuickShopSetupSubmit(e) {
    e.preventDefault();
    const shopName = document.getElementById('quickShopName').value.trim();
    const shopType = document.getElementById('quickShopType').value;
    const shopAddress = document.getElementById('quickShopAddress').value.trim();

    const token = localStorage.getItem('shopo_auth_token');
    try {
        const resp = await fetch('/api/auth/shop/setup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                shop_name: shopName,
                shop_type: shopType,
                shop_address: shopAddress
            })
        });
        const res = await resp.json();

        if (res.success) {
            closeModal('setupModal');
            currentUser.shop_name = shopName;
            currentUser.shop_type = shopType;
            currentUser.shop_address = shopAddress;
            currentUser.is_shop_setup_complete = true;
            renderUserData(currentUser);
            showSimulatedResponse(`🎉 दुकान की जानकारी अपडेट हो गई: **${shopName}** (${shopType})!`);
        } else {
            alert(res.message || 'Error updating shop');
        }
    } catch (err) {
        console.error('Failed to update shop:', err);
    }
}

// ════════════════════════════════════════════════
// FEATURE 1: USER PREFERENCES CONTROLLER
// ════════════════════════════════════════════════

async function loadUserPreferences() {
    // 1. Instant restore from localStorage to prevent flash of wrong language
    const localLang = localStorage.getItem('shopo_pref_ui_lang');
    if (localLang) {
        userPreferences.ui_language = localLang;
        setLanguage(localLang, false);
    }

    const token = localStorage.getItem('shopo_auth_token');
    if (!token) return;

    try {
        const resp = await fetch('/api/user/preferences', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();
        if (resp.ok && res.success && res.data) {
            userPreferences = Object.assign(userPreferences, res.data);
            // If user has saved db preference, prioritize it
            const prefLang = userPreferences.ui_language || localLang || 'hi';
            setLanguage(prefLang, false);
            applyUserPreferencesUI(userPreferences);
        }
    } catch (err) {
        console.warn('Could not load user preferences:', err);
    }
}

function applyUserPreferencesUI(prefs) {
    if (prefs.ui_language) {
        setLanguage(prefs.ui_language, false);
    }
    
    // Populate form dropdowns in Settings
    const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el && val !== undefined) el.value = val;
    };
    setVal('prefUiLang', prefs.ui_language);
    setVal('prefAiLang', prefs.ai_language);
    setVal('prefNewsLang', prefs.news_language);
    setVal('prefDateFormat', prefs.date_format);
    setVal('prefTimeFormat', prefs.time_format);
    setVal('prefNumberFormat', prefs.number_format);
    setVal('prefTempUnit', prefs.temperature_unit);
    setVal('prefCity', prefs.selected_city);

    // Update city dropdown in weather widget
    const wcCity = document.getElementById('wcCitySelect');
    if (wcCity && prefs.selected_city) {
        wcCity.value = prefs.selected_city;
    }

    // Set news language buttons
    if (prefs.news_language) {
        currentNewsLang = prefs.news_language;
        updateNewsLangUI(prefs.news_language);
    }
}

async function saveUserPreferences(partialUpdates) {
    const token = localStorage.getItem('shopo_auth_token');
    if (!token) return;

    const payload = Object.assign({}, partialUpdates);
    try {
        const resp = await fetch('/api/user/preferences', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });
        const res = await resp.json();
        if (res.success && res.data) {
            userPreferences = Object.assign(userPreferences, res.data);
        }
    } catch (err) {
        console.error('Failed to save preferences:', err);
    }
}

async function handleSavePreferences(e) {
    if (e && e.preventDefault) e.preventDefault();
    const btn = document.getElementById('btnSavePreferences');
    if (btn) btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

    const updates = {
        ui_language: document.getElementById('prefUiLang')?.value || 'hi',
        ai_language: document.getElementById('prefAiLang')?.value || 'hi',
        news_language: document.getElementById('prefNewsLang')?.value || 'hi',
        date_format: document.getElementById('prefDateFormat')?.value || 'DD/MM/YYYY',
        time_format: document.getElementById('prefTimeFormat')?.value || '12h',
        number_format: document.getElementById('prefNumberFormat')?.value || 'inr_lakhs',
        temperature_unit: document.getElementById('prefTempUnit')?.value || 'celsius',
        selected_city: document.getElementById('prefCity')?.value || 'Delhi'
    };

    await saveUserPreferences(updates);
    applyUserPreferencesUI(userPreferences);
    fetchLiveWeather(userPreferences.selected_city);

    if (btn) btn.innerHTML = '<i class="fas fa-check"></i> Saved!';
    setTimeout(() => {
        if (btn) btn.innerHTML = '<i class="fas fa-save"></i> Save Preferences / प्राथमिकताएं सहेजें';
    }, 2000);
}

function previewUiLanguage(lang) {
    setLanguage(lang, false);
}

// ════════════════════════════════════════════════
// FEATURE 1: LARGE LANGUAGE SELECTOR MODAL
// ════════════════════════════════════════════════

function openLanguageModal() {
    renderLanguageModalGrid('');
    const input = document.getElementById('langModalSearchInput');
    if (input) input.value = '';
    const modal = document.getElementById('languageModal');
    if (modal) modal.classList.add('active');
}

function filterLanguagesInModal(query) {
    renderLanguageModalGrid(query);
}

function renderLanguageModalGrid(query) {
    const grid = document.getElementById('langModalGrid');
    if (!grid) return;

    const q = (query || '').toLowerCase().trim();
    const filtered = SUPPORTED_LANGUAGES.filter(lang => {
        return !q || lang.name.toLowerCase().includes(q) || lang.nativeName.toLowerCase().includes(q) || lang.code.toLowerCase().includes(q);
    });

    if (filtered.length === 0) {
        grid.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding:20px; color:var(--text-muted);">No languages match your search.</div>';
        return;
    }

    grid.innerHTML = filtered.map(lang => {
        const isSelected = currentLanguage === lang.code;
        const badgeClass = lang.status === 'verified' ? 'verified' : 'beta';
        return `
            <div class="lang-card ${isSelected ? 'selected' : ''}" data-lang="${lang.code}" onclick="selectLanguageFromModal('${lang.code}')">
                <div class="lang-card-native">${lang.nativeName}</div>
                <div class="lang-card-english">${lang.name} (${lang.code.toUpperCase()})</div>
                <span class="lang-completeness-badge ${badgeClass}">${lang.badgeText}</span>
            </div>
        `;
    }).join('');
}

function selectLanguageFromModal(code) {
    setLanguage(code, true);
    closeModal('languageModal');
}

// ════════════════════════════════════════════════
// FEATURE 4: LIVE DATE, TIME, LOCATION & WEATHER
// ════════════════════════════════════════════════

let liveClockInterval = null;
let currentLiveWeatherData = null;

const INDIAN_CITIES_COORDS = {
    'Delhi': { lat: 28.6139, lon: 77.2090 },
    'Mumbai': { lat: 19.0760, lon: 72.8777 },
    'Bengaluru': { lat: 12.9716, lon: 77.5946 },
    'Kolkata': { lat: 22.5726, lon: 88.3639 },
    'Chennai': { lat: 13.0827, lon: 80.2707 },
    'Hyderabad': { lat: 17.3850, lon: 78.4867 },
    'Ahmedabad': { lat: 23.0225, lon: 72.5714 },
    'Pune': { lat: 18.5204, lon: 73.8567 },
    'Jaipur': { lat: 26.9124, lon: 75.7873 },
    'Lucknow': { lat: 26.8467, lon: 80.9462 },
    'Kanpur': { lat: 26.4499, lon: 80.3319 },
    'Patna': { lat: 25.5941, lon: 85.1376 },
    'Bhopal': { lat: 23.2599, lon: 77.4126 },
    'Indore': { lat: 22.7196, lon: 75.8577 },
    'Chandigarh': { lat: 30.7333, lon: 76.7794 },
    'Surat': { lat: 21.1702, lon: 72.8311 },
    'Nagpur': { lat: 21.1458, lon: 79.0882 },
    'Visakhapatnam': { lat: 17.6868, lon: 83.2185 },
    'Ludhiana': { lat: 30.9010, lon: 75.8573 },
    'Agra': { lat: 27.1767, lon: 78.0081 },
    'Varanasi': { lat: 25.3176, lon: 82.9739 },
    'Srinagar': { lat: 34.0837, lon: 74.7973 },
    'Amritsar': { lat: 31.6340, lon: 74.8723 },
    'Raipur': { lat: 21.2514, lon: 81.6296 },
    'Ranchi': { lat: 23.3441, lon: 85.3096 },
    'Guwahati': { lat: 26.1445, lon: 91.7362 }
};

function startLiveClock() {
    if (liveClockInterval) clearInterval(liveClockInterval);
    updateLiveClockDisplay();
    liveClockInterval = setInterval(updateLiveClockDisplay, 1000);
}

function updateLiveClockDisplay() {
    const timeEl = document.getElementById('wcLiveTime');
    const ampmEl = document.getElementById('wcAmPm');
    const dateEl = document.getElementById('wcLiveDate');
    if (!timeEl || !dateEl) return;

    const now = new Date();
    const is24h = userPreferences.time_format === '24h';

    let hours = now.getHours();
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');

    if (is24h) {
        timeEl.textContent = `${String(hours).padStart(2, '0')}:${minutes}:${seconds}`;
        if (ampmEl) ampmEl.textContent = '';
    } else {
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12 || 12;
        timeEl.textContent = `${String(hours).padStart(2, '0')}:${minutes}:${seconds}`;
        if (ampmEl) ampmEl.textContent = ampm;
    }

    const dayNames = {
        hi: ['रविवार', 'सोमवार', 'मंगलवार', 'बुधवार', 'गुरुवार', 'शुक्रवार', 'शनिवार'],
        hinglish: ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
        en: ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
        es: ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'],
        fr: ['Dimanche', 'Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'],
        ar: ['الأحد', 'الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'],
        ur: ['اتوار', 'پیر', 'منگل', 'بدھ', 'جمعرات', 'جمعہ', 'ہفتہ']
    };
    const dayOfWeek = (dayNames[currentLanguage] || dayNames.en)[now.getDay()];

    const dd = String(now.getDate()).padStart(2, '0');
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const yyyy = now.getFullYear();

    let dateStr = `${dd}/${mm}/${yyyy}`;
    if (userPreferences.date_format === 'MM/DD/YYYY') {
        dateStr = `${mm}/${dd}/${yyyy}`;
    } else if (userPreferences.date_format === 'YYYY-MM-DD') {
        dateStr = `${yyyy}-${mm}-${dd}`;
    }

    dateEl.textContent = `${dayOfWeek}, ${dateStr}`;
}

let weatherAbortController = null;

async function fetchLiveWeather(city, coords) {
    if (!city) city = userPreferences.selected_city || 'Delhi';

    // Abort previous in-flight request to avoid race conditions
    if (weatherAbortController) {
        weatherAbortController.abort();
    }
    weatherAbortController = new AbortController();

    const refreshIcon = document.getElementById('wcRefreshIcon');
    const condEl = document.getElementById('wcTempCondition');

    if (refreshIcon) refreshIcon.classList.add('fa-spin');
    if (condEl && !currentLiveWeatherData) {
        condEl.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading Live Weather...';
    }

    try {
        let url = `/api/market/weather?city=${encodeURIComponent(city)}`;
        if (coords && coords.lat !== undefined && coords.lon !== undefined) {
            url = `/api/market/weather?lat=${encodeURIComponent(coords.lat)}&lon=${encodeURIComponent(coords.lon)}&city=${encodeURIComponent(city)}`;
        }

        const resp = await fetch(url, { signal: weatherAbortController.signal });
        const res = await resp.json();
        const w = (res && res.data) ? res.data : res;

        if (res && res.success && w && (w.temperature_celsius !== undefined && w.temperature_celsius !== null)) {
            currentLiveWeatherData = w;
            renderLiveWeatherUI(w);
        } else {
            const errDetail = (res && (res.message || res.error)) ? (res.message || res.error) : 'Weather update timed out.';
            renderWeatherErrorUI(errDetail, w);
        }
    } catch (err) {
        if (err.name === 'AbortError') return;
        console.warn('Weather fetch failed:', err);
        renderWeatherErrorUI('Unable to reach live weather provider. Check connection.');
    } finally {
        if (refreshIcon) refreshIcon.classList.remove('fa-spin');
    }
}

function renderLiveWeatherUI(w) {
    if (!w) return;
    const tempValEl = document.getElementById('wcTempVal');
    const tempCondEl = document.getElementById('wcTempCondition');
    const tempRangeEl = document.getElementById('wcTempRange');
    const iconEl = document.getElementById('wcTempIcon');
    const humidityEl = document.getElementById('wcHumidity');
    const windEl = document.getElementById('wcWind');
    const rainEl = document.getElementById('wcRain');
    const advisoryEl = document.getElementById('wcStorageAdvisory');
    const badgeEl = document.getElementById('wcSourceBadge');

    let temp = w.temperature_celsius;
    let maxT = w.max_temp_celsius;
    let minT = w.min_temp_celsius;
    let unitSymbol = '°C';

    if (userPreferences.temperature_unit === 'fahrenheit') {
        if (temp !== undefined && temp !== null) temp = (temp * 9/5) + 32;
        if (maxT !== undefined && maxT !== null) maxT = (maxT * 9/5) + 32;
        if (minT !== undefined && minT !== null) minT = (minT * 9/5) + 32;
        unitSymbol = '°F';
    }

    const headerTempEl = document.getElementById('headerWeatherTemp');
    const headerIconEl = document.getElementById('headerWeatherIcon');
    if (headerTempEl && temp !== undefined && temp !== null) {
        headerTempEl.textContent = `${Math.round(temp)}${unitSymbol}`;
    }
    if (headerIconEl && w.icon) {
        headerIconEl.textContent = w.icon;
    }

    if (tempValEl) tempValEl.textContent = (temp !== undefined && temp !== null) ? `${Math.round(temp)}${unitSymbol}` : `--${unitSymbol}`;
    if (tempCondEl) tempCondEl.textContent = w.condition || 'Clear Sky';
    if (tempRangeEl) {
        const hStr = (maxT !== undefined && maxT !== null) ? `${Math.round(maxT)}${unitSymbol}` : '--';
        const lStr = (minT !== undefined && minT !== null) ? `${Math.round(minT)}${unitSymbol}` : '--';
        tempRangeEl.textContent = `H: ${hStr} | L: ${lStr}`;
    }
    if (humidityEl) humidityEl.textContent = (w.relative_humidity_pct !== undefined && w.relative_humidity_pct !== null) ? `${w.relative_humidity_pct}%` : '--%';
    if (windEl) windEl.textContent = (w.wind_speed_kmh !== undefined && w.wind_speed_kmh !== null) ? `${w.wind_speed_kmh} km/h` : '-- km/h';
    if (rainEl) rainEl.textContent = (w.precipitation_mm !== undefined && w.precipitation_mm !== null) ? `${w.precipitation_mm} mm` : '0 mm';
    if (advisoryEl) advisoryEl.textContent = w.business_storage_advisory || 'Normal storage conditions. Good ventilation recommended.';
    if (badgeEl) {
        badgeEl.textContent = w.is_stale ? 'Cached Observation: Open-Meteo' : 'Verified Feed: Open-Meteo Live API';
    }

    let icon = '☀️';
    const cond = (w.condition || '').toLowerCase();
    if (cond.includes('rain') || cond.includes('shower') || cond.includes('drizzle')) icon = '🌧️';
    else if (cond.includes('cloud') || cond.includes('overcast')) icon = '⛅';
    else if (cond.includes('thunder')) icon = '⛈️';
    else if (cond.includes('snow') || cond.includes('freez') || cond.includes('hail')) icon = '🌨️';
    else if (cond.includes('fog') || cond.includes('mist')) icon = '🌫️';
    if (iconEl) iconEl.textContent = icon;

    const updatedTimeEl = document.getElementById('wcUpdatedTime');
    if (updatedTimeEl) {
        if (w.retrieval_timestamp) {
            try {
                const d = new Date(w.retrieval_timestamp);
                updatedTimeEl.textContent = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            } catch(e) {
                updatedTimeEl.textContent = 'Live';
            }
        } else {
            updatedTimeEl.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
    }
}

function renderWeatherErrorUI(errMsg, fallbackData) {
    const tempCondEl = document.getElementById('wcTempCondition');
    const advisoryEl = document.getElementById('wcStorageAdvisory');
    const badgeEl = document.getElementById('wcSourceBadge');

    if (tempCondEl) {
        tempCondEl.innerHTML = `<span style="color:#FCA5A5; font-size:0.8rem;"><i class="fas fa-exclamation-triangle"></i> Feed Offline &bull; <a href="javascript:void(0)" onclick="retryLiveWeather()" style="color:#FDE047; text-decoration:underline;">Retry</a></span>`;
    }
    if (advisoryEl) {
        advisoryEl.textContent = (fallbackData && fallbackData.business_storage_advisory)
            ? fallbackData.business_storage_advisory
            : 'Standard dry indoor storage recommended. Ensure adequate warehouse ventilation.';
    }
    if (badgeEl) {
        badgeEl.textContent = 'Weather Feed Offline (Click Retry)';
    }
}

function handleCityChange(city) {
    userPreferences.selected_city = city;
    fetchLiveWeather(city);
    saveUserPreferences({ selected_city: city });
}

function retryLiveWeather() {
    const sel = document.getElementById('wcCitySelect');
    const city = (sel && sel.value) ? sel.value : (userPreferences.selected_city || 'Delhi');
    fetchLiveWeather(city);
}

async function detectUserLocation() {
    const sel = document.getElementById('wcCitySelect');
    const btn = document.querySelector('.wc-geo-btn');

    if (!navigator.geolocation) {
        if (btn) {
            btn.innerHTML = '<i class="fas fa-exclamation-circle"></i> ' + (currentLanguage === 'hi' ? 'GPS उपलब्ध नहीं' : 'GPS Unsupported');
            setTimeout(() => {
                btn.innerHTML = '<i class="fas fa-crosshairs"></i> <span id="wcGeoBtnText">' + (t('btn_detect_location') || 'Detect Location') + '</span>';
            }, 3500);
        }
        return;
    }

    if (btn) btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> ' + (currentLanguage === 'hi' ? 'पहचान रहा है...' : 'Detecting...');

    navigator.geolocation.getCurrentPosition(
        async (pos) => {
            const userLat = pos.coords.latitude;
            const userLon = pos.coords.longitude;
            let detectedName = '';

            // Step 1: Real reverse geocoding via BigDataCloud free client API
            try {
                const geoUrl = `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${userLat}&longitude=${userLon}&localityLanguage=en`;
                const r = await fetch(geoUrl, { signal: AbortSignal.timeout(4000) });
                if (r.ok) {
                    const data = await r.json();
                    detectedName = data.city || data.locality || data.principalSubdivision || '';
                }
            } catch (e) {
                console.warn('Reverse geocode lookup error:', e);
            }

            // Step 2: Proximity fallback from INDIAN_CITIES_COORDS if reverse geocode is empty
            if (!detectedName && typeof INDIAN_CITIES_COORDS !== 'undefined') {
                let minDistance = Infinity;
                for (const [cityName, coords] of Object.entries(INDIAN_CITIES_COORDS)) {
                    const dLat = coords.lat - userLat;
                    const dLon = coords.lon - userLon;
                    const dist = Math.sqrt(dLat * dLat + dLon * dLon);
                    if (dist < minDistance) {
                        minDistance = dist;
                        detectedName = cityName;
                    }
                }
            }

            if (!detectedName) detectedName = 'Local Region';

            // Add or select detected city in dropdown
            let selectEl = document.getElementById('wcCitySelect');
            if (selectEl) {
                let existingOpt = Array.from(selectEl.options).find(o => o.value.toLowerCase() === detectedName.toLowerCase());
                if (!existingOpt) {
                    const opt = document.createElement('option');
                    opt.value = detectedName;
                    opt.textContent = `📍 ${detectedName} (Detected)`;
                    selectEl.insertBefore(opt, selectEl.firstChild);
                    selectEl.value = detectedName;
                } else {
                    selectEl.value = existingOpt.value;
                }
            }

            userPreferences.selected_city = detectedName;
            saveUserPreferences({ selected_city: detectedName });
            fetchLiveWeather(detectedName, { lat: userLat, lon: userLon });

            if (btn) btn.innerHTML = '<i class="fas fa-check"></i> ' + detectedName;
            setTimeout(() => {
                if (btn) btn.innerHTML = '<i class="fas fa-crosshairs"></i> <span id="wcGeoBtnText">' + (t('btn_detect_location') || 'Detect Location') + '</span>';
            }, 3500);
        },
        (err) => {
            console.warn('Geolocation denied or failed:', err);
            let reasonText = 'Permission Denied';
            if (err.code === 1) reasonText = currentLanguage === 'hi' ? 'अनुमति अस्वीकृत' : 'Permission Denied';
            else if (err.code === 3) reasonText = currentLanguage === 'hi' ? 'समय समाप्त' : 'GPS Timeout';
            else if (err.code === 2) reasonText = currentLanguage === 'hi' ? 'स्थान अनुपलब्ध' : 'Location Unavailable';

            if (btn) btn.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${reasonText}`;
            setTimeout(() => {
                if (btn) btn.innerHTML = '<i class="fas fa-crosshairs"></i> <span id="wcGeoBtnText">' + (t('btn_detect_location') || 'Detect Location') + '</span>';
            }, 3500);
        },
        { timeout: 8000, maximumAge: 60000, enableHighAccuracy: true }
    );
}

// ════════════════════════════════════════════════
// FEATURE 2 & 3: NEWS & MARKET INTELLIGENCE CONTROLLER
// ════════════════════════════════════════════════

let currentNewsCategory = 'top';
let currentNewsLang = 'hi';
let currentMarketCategoryFilter = 'all';
let cachedNewsFeedArticles = [];
let cachedMarketDashboardRates = [];

function initNewsSystem() {
    const newsView = document.getElementById('view-news');
    if (newsView && newsView.classList.contains('active')) {
        fetchNewsFeed(currentNewsCategory, currentNewsLang);
    }
}

function switchNewsTab(cat) {
    currentNewsCategory = cat;

    document.querySelectorAll('.news-tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.cat === cat);
    });

    const articlesSec = document.getElementById('newsArticlesSection');
    const ratesSec = document.getElementById('marketRatesSection');

    if (cat === 'market_rates') {
        if (articlesSec) articlesSec.style.display = 'none';
        if (ratesSec) ratesSec.style.display = 'block';
        fetchMarketDashboard();
    } else {
        if (ratesSec) ratesSec.style.display = 'none';
        if (articlesSec) articlesSec.style.display = 'block';
        const q = document.getElementById('newsSearchInput')?.value || '';
        fetchNewsFeed(cat, currentNewsLang, q);
    }
}

function switchNewsLang(lang) {
    currentNewsLang = lang;
    updateNewsLangUI(lang);
    userPreferences.news_language = lang;
    saveUserPreferences({ news_language: lang });

    if (currentNewsCategory !== 'market_rates') {
        const q = document.getElementById('newsSearchInput')?.value || '';
        fetchNewsFeed(currentNewsCategory, lang, q);
    }
}

function updateNewsLangUI(lang) {
    const btnHi = document.getElementById('btnNewsLangHi');
    const btnEn = document.getElementById('btnNewsLangEn');
    if (btnHi) btnHi.classList.toggle('active', lang === 'hi');
    if (btnEn) btnEn.classList.toggle('active', lang === 'en');
}

function refreshCurrentNewsTab() {
    const spinner = document.getElementById('newsRefreshSpinner');
    if (spinner) spinner.classList.add('fa-spin');

    if (currentNewsCategory === 'market_rates') {
        fetchMarketDashboard().finally(() => {
            setTimeout(() => { if (spinner) spinner.classList.remove('fa-spin'); }, 600);
        });
    } else {
        const q = document.getElementById('newsSearchInput')?.value || '';
        fetchNewsFeed(currentNewsCategory, currentNewsLang, q).finally(() => {
            setTimeout(() => { if (spinner) spinner.classList.remove('fa-spin'); }, 600);
        });
    }
}

let newsSearchTimeout = null;
function handleNewsSearch(query) {
    clearTimeout(newsSearchTimeout);
    newsSearchTimeout = setTimeout(() => {
        if (currentNewsCategory === 'market_rates') {
            handleMarketFilter(query);
        } else {
            fetchNewsFeed(currentNewsCategory, currentNewsLang, query);
        }
    }, 350);
}

async function fetchNewsFeed(category, lang, query) {
    const container = document.getElementById('newsGridContainer');
    if (!container) return;

    container.innerHTML = `
        <div style="grid-column: 1/-1; text-align:center; padding:40px; color:var(--text-muted);">
            <i class="fas fa-spinner fa-spin" style="font-size:2rem; color:var(--lime-600); margin-bottom:12px;"></i>
            <div>Loading verified RSS headlines... / ताज़ा ख़बरें लोड हो रही हैं...</div>
        </div>
    `;

    try {
        const url = `/api/news?category=${encodeURIComponent(category)}&lang=${encodeURIComponent(lang)}&q=${encodeURIComponent(query || '')}`;
        const resp = await fetch(url);
        const res = await resp.json();

        const articles = res.items || res.articles || [];
        if (res.success && articles && articles.length > 0) {
            cachedNewsFeedArticles = articles;
            renderNewsArticles(articles, res.is_stale, res.cached_at, res.source);
        } else {
            container.innerHTML = `
                <div style="grid-column:1/-1; text-align:center; padding:40px; background:#FFF; border:1px solid var(--border-color); border-radius:var(--radius-lg);">
                    <i class="fas fa-exclamation-circle" style="font-size:2rem; color:var(--yellow-500); margin-bottom:10px;"></i>
                    <h4>No articles found for this category or query.</h4>
                    <p style="color:var(--text-muted); font-size:0.88rem; margin-top:6px;">Try switching language, choosing another category, or clearing your search filter.</p>
                    <button type="button" class="btn-dash btn-dash-secondary" onclick="refreshCurrentNewsTab()" style="margin-top:12px;">
                        <i class="fas fa-sync-alt"></i> Refresh Feeds / पुनः प्रयास करें
                    </button>
                </div>
            `;
        }
    } catch (err) {
        container.innerHTML = `
            <div style="grid-column:1/-1; text-align:center; padding:40px; background:#FFF; border:1px solid var(--border-color); border-radius:var(--radius-lg);">
                <i class="fas fa-wifi" style="font-size:2rem; color:var(--red-500); margin-bottom:10px;"></i>
                <h4>Unable to connect to live news service.</h4>
                <p style="color:var(--text-muted); font-size:0.88rem;">Please check your internet connection or server status.</p>
                <button type="button" class="btn-dash btn-dash-secondary" onclick="refreshCurrentNewsTab()" style="margin-top:12px;">
                    <i class="fas fa-sync-alt"></i> Try Again / पुनः प्रयास करें
                </button>
            </div>
        `;
    }
}

function renderNewsArticles(articles, isStale, cachedAt, sourceName) {
    const container = document.getElementById('newsGridContainer');
    if (!container) return;

    if (!articles || articles.length === 0) {
        container.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:40px; color:var(--text-muted);">No headlines available.</div>';
        return;
    }

    const cachedTimeStr = cachedAt ? new Date(cachedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
    const staleWarning = isStale ? `
        <div style="grid-column:1/-1; background:#FEF3C7; color:#92400E; padding:10px 16px; border-radius:var(--radius-md); font-size:0.85rem; font-weight:700; display:flex; align-items:center; justify-content:space-between;">
            <span>⚠️ Offline Cached Feed: Showing previously retrieved news headlines.</span>
            <span style="font-size:0.78rem; font-weight:600; opacity:0.85;">Last updated: ${cachedTimeStr || 'Earlier today'}</span>
        </div>
    ` : '';

    container.innerHTML = staleWarning + articles.map((art, idx) => {
        const titleSafe = (art.title || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
        const snippetSafe = (art.snippet || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
        const pubSafe = (art.publisher || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
        const linkSafe = encodeURI(art.link || '#');
        const pubDateStr = (art.published_at || art.pub_date || '').slice(0, 16);

        return `
            <div class="news-card">
                <div>
                    <div class="news-meta-row" style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <span class="news-publisher news-publisher-badge">${art.publisher || 'Verified Feed'}</span>
                        <span class="news-time" style="font-size:0.78rem; color:var(--text-muted);"><i class="far fa-clock"></i> ${pubDateStr}</span>
                    </div>
                    <h3 class="news-card-title">
                        <a href="${linkSafe}" target="_blank" rel="noopener noreferrer">${art.title}</a>
                    </h3>
                    <div class="news-card-snippet">${art.snippet || ''}</div>
                </div>
                <div class="news-card-actions">
                    <button type="button" class="btn-ai-summary btn-summarize" onclick="openArticleSummary('${art.id}', '${titleSafe}', '${snippetSafe}', '${pubSafe}', '${linkSafe}')">
                        <i class="fas fa-sparkles"></i> AI Summary
                    </button>
                    <a href="${linkSafe}" target="_blank" rel="noopener noreferrer" class="link-read-more" style="font-size:0.85rem; font-weight:700; color:var(--lime-600); text-decoration:none;">
                        Read Source <i class="fas fa-external-link-alt" style="font-size:0.75rem;"></i>
                    </a>
                </div>
            </div>
        `;
    }).join('');
}

async function openArticleSummary(id, title, snippet, publisher, link) {
    const modal = document.getElementById('aiSummaryModal');
    if (modal) modal.classList.add('active');

    const titleEl = document.getElementById('summaryArticleTitle');
    const metaEl = document.getElementById('summaryArticleMeta');
    const contentEl = document.getElementById('summaryArticleContent');
    const linkEl = document.getElementById('summaryArticleOriginalLink');

    if (titleEl) titleEl.textContent = title;
    if (metaEl) metaEl.textContent = `Publisher: ${publisher || 'Public Source'}`;
    if (linkEl) linkEl.href = link;
    if (contentEl) contentEl.innerHTML = '<div style="text-align:center; padding:20px;"><i class="fas fa-spinner fa-spin" style="font-size:1.5rem; color:var(--lime-600); margin-bottom:8px;"></i><div>Generating AI business summary...</div></div>';

    try {
        const resp = await fetch('/api/news/summarize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: title,
                snippet: snippet,
                publisher: publisher,
                link: link,
                lang: currentLanguage === 'hi' ? 'hi' : 'en'
            })
        });
        const res = await resp.json();
        if (res.success && res.summary) {
            if (contentEl) {
                contentEl.innerHTML = `
                    <div style="font-size:0.95rem; line-height:1.6; color:#0F172A; white-space:pre-line;">
                        ${res.summary}
                    </div>
                `;
            }
        } else {
            if (contentEl) contentEl.textContent = snippet || 'No summary available.';
        }
    } catch (err) {
        if (contentEl) contentEl.textContent = snippet || 'Could not generate summary.';
    }
}

// ════════════════════════════════════════════════
// FEATURE 3: MARKET & MANDI RATES CONTROLLER
// ════════════════════════════════════════════════

function initMarketRatesSystem() {
    // Prepared for demand loading
}

async function fetchMarketDashboard(category, query) {
    const tableBody = document.getElementById('ratesTableBody');
    if (!tableBody) return;

    tableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:30px;"><i class="fas fa-spinner fa-spin" style="color:var(--lime-600);"></i> Loading benchmark quotes...</td></tr>';

    const cat = category || currentMarketCategoryFilter || 'all';
    const q = query || document.getElementById('marketSearchInput')?.value || '';

    try {
        const url = `/api/market/dashboard?category=${encodeURIComponent(cat)}&search=${encodeURIComponent(q)}`;
        const resp = await fetch(url);
        const res = await resp.json();

        const quotesList = res.items || res.quotes;
        if (res.success && quotesList && quotesList.length > 0) {
            cachedMarketDashboardRates = quotesList;
            renderMarketRatesTable(quotesList);
        } else {
            tableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:30px;">No benchmark quotes available.</td></tr>';
        }
    } catch (err) {
        tableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:30px; color:var(--red-500);">Failed to load verified rates.</td></tr>';
    }
}

function renderMarketRatesTable(items) {
    const tableBody = document.getElementById('ratesTableBody');
    if (!tableBody) return;

    if (!items || items.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:30px; color:var(--text-muted);">No matching benchmark quotes.</td></tr>';
        return;
    }

    tableBody.innerHTML = items.map(it => {
        let changeHtml = '<span class="price-change-tag flat">➖ 0.00%</span>';
        const chgRs = it.price_change_rs !== undefined ? it.price_change_rs : it.change_rs;
        const chgPct = it.price_change_pct !== undefined ? it.price_change_pct : it.change_pct;
        if (chgRs !== undefined && chgRs !== null) {
            if (chgRs > 0) {
                changeHtml = `<span class="price-change-tag up">📈 +₹${chgRs} (+${chgPct}%)</span>`;
            } else if (chgRs < 0) {
                changeHtml = `<span class="price-change-tag down">📉 -₹${Math.abs(chgRs)} (${chgPct}%)</span>`;
            }
        }

        const normVal = it.normalized_price_inr !== undefined ? it.normalized_price_inr : it.normalized_price;
        const normUnit = it.normalized_unit || 'kg';
        const normStr = (normVal !== undefined && normVal !== null)
            ? `<span class="norm-unit-pill">₹${Number(normVal).toFixed(2)} / ${normUnit}</span>`
            : '-';

        const displayName = it.name || it.item || it.commodity || 'Commodity Quote';
        const spec = it.variety || it.specification || '';
        const loc = it.location || (it.mandi ? `${it.mandi}, ${it.state}` : (it.applicable_location || 'National'));

        return `
            <tr>
                <td><strong>${displayName}</strong><br><span style="font-size:0.75rem; color:var(--text-muted);">${spec}</span></td>
                <td><span style="font-size:0.78rem; text-transform:uppercase; font-weight:700; color:var(--lime-700);">${it.category}</span></td>
                <td><strong>₹${Number(it.price || it.modal_price).toLocaleString('en-IN')}</strong> <span style="font-size:0.8rem; color:var(--text-muted);">${it.unit}</span></td>
                <td>${changeHtml}</td>
                <td>${normStr}</td>
                <td>${loc}</td>
                <td style="font-size:0.78rem; color:var(--text-secondary);">${it.source || 'Verified Benchmark'}<br><em>${it.limitations || ''}</em></td>
            </tr>
        `;
    }).join('');
}

function filterMarketRates(cat) {
    currentMarketCategoryFilter = cat;
    ['btnRateFilterAll', 'btnRateFilterAgri', 'btnRateFilterInd', 'btnRateFilterBullion'].forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.classList.remove('active');
    });

    if (cat === 'all') document.getElementById('btnRateFilterAll')?.classList.add('active');
    else if (cat === 'agricultural') document.getElementById('btnRateFilterAgri')?.classList.add('active');
    else if (cat === 'industrial') document.getElementById('btnRateFilterInd')?.classList.add('active');
    else if (cat === 'bullion') document.getElementById('btnRateFilterBullion')?.classList.add('active');

    fetchMarketDashboard(cat);
}

function handleMarketFilter(query) {
    if (!cachedMarketDashboardRates) return;
    const q = (query || '').toLowerCase().trim();
    if (!q) {
        renderMarketRatesTable(cachedMarketDashboardRates);
        return;
    }
    const filtered = cachedMarketDashboardRates.filter(r => {
        const name = (r.item || r.commodity || '').toLowerCase();
        const loc = (r.mandi || r.state || r.applicable_location || '').toLowerCase();
        return name.includes(q) || loc.includes(q);
    });
    renderMarketRatesTable(filtered);
}

async function handleUnitCompare(e) {
    if (e && e.preventDefault) e.preventDefault();
    const box = document.getElementById('calcResultBox');
    if (!box) return;

    const pA = parseFloat(document.getElementById('calcPriceA')?.value || 0);
    const uA = document.getElementById('calcUnitA')?.value || 'kg';
    const pB = parseFloat(document.getElementById('calcPriceB')?.value || 0);
    const uB = document.getElementById('calcUnitB')?.value || 'kg';

    if (pA <= 0 || pB <= 0) {
        box.style.display = 'block';
        box.style.background = '#FEE2E2';
        box.style.color = '#B91C1C';
        box.textContent = 'Please enter valid positive numbers for both quotes.';
        return;
    }

    try {
        const resp = await fetch('/api/market/compare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                item_a: { price: pA, unit: uA, name: 'Quote A' },
                item_b: { price: pB, unit: uB, name: 'Quote B' }
            })
        });
        const res = await resp.json();
        box.style.display = 'block';

        if (res.success && res.data) {
            const d = res.data;
            box.style.background = '#DCFCE7';
            box.style.color = '#15803D';
            box.innerHTML = `
                <div>${d.explanation_hindi}</div>
                <div style="font-size:0.8rem; margin-top:4px; opacity:0.85;">${d.explanation_english}</div>
            `;
        } else {
            box.style.background = '#FEF3C7';
            box.style.color = '#92400E';
            box.textContent = res.error || 'Cannot compare incompatible units.';
        }
    } catch (err) {
        box.style.display = 'block';
        box.style.background = '#FEE2E2';
        box.style.color = '#B91C1C';
        box.textContent = 'Comparison request failed.';
    }
}

// ── Logout ──
async function handleLogout() {
    const token = localStorage.getItem('shopo_auth_token');
    if (token) {
        try {
            await fetch('/api/auth/logout', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
        } catch (e) {
            // Ignore network errors on logout
        }
    }
    localStorage.removeItem('shopo_auth_token');
    localStorage.removeItem('shopo_user');
    window.location.href = '/auth/';
}

// ════════════════════════════════════════════════
// GROUP A: ADVANCED BUSINESS INTELLIGENCE
// 1. AI Business Time Machine
// 2. AI Digital Accountant
// 3. What-If Business Simulator
// ════════════════════════════════════════════════

// ── Time Machine Controller ──
function initTimeMachineView() {
    applyTimePreset('this_vs_last_month');
    fetchTimeMachinePatterns();
    fetchTimeMachineForecast(30);
}

function applyTimePreset(preset) {
    const now = new Date();
    const pad = n => String(n).padStart(2, '0');
    const toYMD = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

    if (preset === 'this_vs_last_month') {
        const thisMonthStart = new Date(now.getFullYear(), now.getMonth(), 1);
        const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0);

        const aStart = document.getElementById('tmPeriodAStart');
        const aEnd = document.getElementById('tmPeriodAEnd');
        const bStart = document.getElementById('tmPeriodBStart');
        const bEnd = document.getElementById('tmPeriodBEnd');
        if (aStart) aStart.value = toYMD(thisMonthStart);
        if (aEnd) aEnd.value = toYMD(now);
        if (bStart) bStart.value = toYMD(lastMonthStart);
        if (bEnd) bEnd.value = toYMD(lastMonthEnd);

        const aLbl = document.getElementById('tmPeriodALabel');
        const bLbl = document.getElementById('tmPeriodBLabel');
        if (aLbl) aLbl.value = 'This Month';
        if (bLbl) bLbl.value = 'Last Month';
    } else if (preset === 'last_30_days') {
        const d30Ago = new Date(now.getTime() - (30 * 86400000));
        const d60Ago = new Date(now.getTime() - (60 * 86400000));

        const aStart = document.getElementById('tmPeriodAStart');
        const aEnd = document.getElementById('tmPeriodAEnd');
        const bStart = document.getElementById('tmPeriodBStart');
        const bEnd = document.getElementById('tmPeriodBEnd');
        if (aStart) aStart.value = toYMD(d30Ago);
        if (aEnd) aEnd.value = toYMD(now);
        if (bStart) bStart.value = toYMD(d60Ago);
        if (bEnd) bEnd.value = toYMD(d30Ago);

        const aLbl = document.getElementById('tmPeriodALabel');
        const bLbl = document.getElementById('tmPeriodBLabel');
        if (aLbl) aLbl.value = 'Last 30 Days';
        if (bLbl) bLbl.value = 'Prior 30 Days';
    }
}

async function handleTimeMachineCompareSubmit(e) {
    if (e) e.preventDefault();
    const token = localStorage.getItem('shopo_auth_token');
    const btn = document.getElementById('btnRunTimeCompare');
    if (btn) btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Comparing...';

    const payload = {
        period_a: {
            start: document.getElementById('tmPeriodAStart')?.value,
            end: document.getElementById('tmPeriodAEnd')?.value,
            label: document.getElementById('tmPeriodALabel')?.value || 'Period A'
        },
        period_b: {
            start: document.getElementById('tmPeriodBStart')?.value,
            end: document.getElementById('tmPeriodBEnd')?.value,
            label: document.getElementById('tmPeriodBLabel')?.value || 'Period B'
        }
    };

    try {
        const res = await fetch('/api/bi/time-machine/compare', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        const json = await res.json();
        if (btn) btn.innerHTML = '<i class="fas fa-play"></i> Compare Periods / तुलना करें';

        if (json.success && json.data) {
            renderTimeMachineComparison(json.data);
        } else {
            alert(json.message || 'Comparison failed.');
        }
    } catch (err) {
        if (btn) btn.innerHTML = '<i class="fas fa-play"></i> Compare Periods / तुलना करें';
        console.error('Time machine compare error:', err);
    }
}

function renderTimeMachineComparison(data) {
    const resBox = document.getElementById('tmComparisonResults');
    const grid = document.getElementById('tmComparisonGrid');
    const insightsBox = document.getElementById('tmInsightsBox');
    if (!resBox || !grid) return;

    resBox.style.display = 'block';
    const a = data.period_a?.metrics || {};
    const b = data.period_b?.metrics || {};
    const d = data.deltas || {};

    const formatDiff = (pct, abs) => {
        const sym = pct >= 0 ? '+' : '';
        const color = pct >= 0 ? '#16A34A' : '#DC2626';
        return `<span style="color:${color}; font-weight:700;">${sym}${pct}% (${sym}₹${Math.abs(abs).toLocaleString('en-IN')})</span>`;
    };

    grid.innerHTML = `
        <div class="metric-card">
            <div class="metric-label">Total Revenue (${data.period_a?.label || 'A'})</div>
            <div class="metric-value">₹${(a.total_revenue || 0).toLocaleString('en-IN')}</div>
            <div class="metric-sub">vs ₹${(b.total_revenue || 0).toLocaleString('en-IN')} • ${formatDiff(d.revenue?.percentage || 0, d.revenue?.absolute || 0)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Gross Profit (${data.period_a?.label || 'A'})</div>
            <div class="metric-value">₹${(a.gross_profit || 0).toLocaleString('en-IN')}</div>
            <div class="metric-sub">vs ₹${(b.gross_profit || 0).toLocaleString('en-IN')} • ${formatDiff(d.gross_profit?.percentage || 0, d.gross_profit?.absolute || 0)}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Net Profit (${data.period_a?.label || 'A'})</div>
            <div class="metric-value">₹${(a.net_profit || 0).toLocaleString('en-IN')}</div>
            <div class="metric-sub">Margin: ${a.gross_margin_pct || 0}%</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Transactions & AOV</div>
            <div class="metric-value">${a.transaction_count || 0} orders</div>
            <div class="metric-sub">Avg Order Value: ₹${(a.average_order_value || 0).toLocaleString('en-IN')}</div>
        </div>
    `;

    if (insightsBox) {
        insightsBox.innerHTML = `
            <strong><i class="fas fa-lightbulb"></i> AI Historical Insights:</strong>
            <ul style="margin:6px 0 0 18px; padding:0;">
                ${(data.insights || []).map(i => `<li>${i}</li>`).join('')}
            </ul>
        `;
    }
}

async function fetchTimeMachinePatterns() {
    const token = localStorage.getItem('shopo_auth_token');
    const container = document.getElementById('tmSeasonalityContent');
    if (!container) return;

    try {
        const res = await fetch('/api/bi/time-machine/patterns?days_back=90', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const json = await res.json();
        if (json.success && json.data) {
            const d = json.data;
            const daysHtml = (d.day_of_week_performance || []).map(item => `
                <div style="display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid var(--border-color); font-size:0.85rem;">
                    <span style="font-weight:${item.day === d.peak_day ? '800; color:var(--lime-700);' : '500;'}">${item.day} ${item.day === d.peak_day ? '⭐ (Peak)' : ''}</span>
                    <span style="font-weight:700;">₹${(item.revenue || 0).toLocaleString('en-IN')} (${item.transactions} orders)</span>
                </div>
            `).join('');

            const anomaliesHtml = (d.anomalies || []).length > 0 ? `
                <div style="margin-top:12px; background:#FEF3C7; border:1px solid #FDE68A; border-radius:var(--radius-md); padding:10px; font-size:0.82rem; color:#92400E;">
                    <strong><i class="fas fa-exclamation-triangle"></i> Detected Outliers:</strong>
                    <ul style="margin:4px 0 0 16px; padding:0;">
                        ${d.anomalies.map(a => `<li>${a.date}: ${a.description}</li>`).join('')}
                    </ul>
                </div>
            ` : '<div style="margin-top:10px; font-size:0.8rem; color:var(--text-muted);">No abnormal spikes or crashes detected.</div>';

            container.innerHTML = `
                <div style="margin-bottom:8px; font-size:0.85rem; color:var(--text-secondary);">
                    Analyzed <strong>${d.total_records_analyzed}</strong> transactions across recent history.
                </div>
                ${daysHtml}
                ${anomaliesHtml}
            `;
        }
    } catch (e) {
        console.error('Failed to fetch patterns:', e);
    }
}

async function fetchTimeMachineForecast(horizon = 30) {
    const token = localStorage.getItem('shopo_auth_token');
    const container = document.getElementById('tmForecastContent');
    if (!container) return;

    try {
        const res = await fetch('/api/bi/time-machine/forecast', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ horizon_days: horizon })
        });
        const json = await res.json();
        if (json.success && json.data) {
            const f = json.data;
            const s = f.summary || {};
            container.innerHTML = `
                <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap:10px; margin-bottom:14px;">
                    <div style="background:var(--bg-light); border-radius:var(--radius-md); padding:10px;">
                        <div style="font-size:0.75rem; color:var(--text-muted); font-weight:700;">7-DAY PROJECTED</div>
                        <div style="font-size:1.1rem; font-weight:900; color:var(--text-primary);">₹${(s['7_day_projected_revenue'] || 0).toLocaleString('en-IN')}</div>
                    </div>
                    <div style="background:var(--bg-light); border-radius:var(--radius-md); padding:10px;">
                        <div style="font-size:0.75rem; color:var(--text-muted); font-weight:700;">30-DAY PROJECTED</div>
                        <div style="font-size:1.1rem; font-weight:900; color:var(--text-primary);">₹${(s['30_day_projected_revenue'] || 0).toLocaleString('en-IN')}</div>
                    </div>
                    <div style="background:var(--bg-light); border-radius:var(--radius-md); padding:10px;">
                        <div style="font-size:0.75rem; color:var(--text-muted); font-weight:700;">EST. 30D EXPENSES</div>
                        <div style="font-size:1.1rem; font-weight:900; color:#DC2626;">₹${(s['projected_30d_expenses'] || 0).toLocaleString('en-IN')}</div>
                    </div>
                    <div style="background:var(--bg-light); border-radius:var(--radius-md); padding:10px;">
                        <div style="font-size:0.75rem; color:var(--text-muted); font-weight:700;">EST. NET PROFIT</div>
                        <div style="font-size:1.1rem; font-weight:900; color:#16A34A;">₹${(s['projected_30d_net_profit'] || 0).toLocaleString('en-IN')}</div>
                    </div>
                </div>
                <div style="font-size:0.8rem; color:var(--text-muted); line-height:1.4;">
                    <i class="fas fa-shield-alt"></i> ${f.disclaimer}
                </div>
            `;
        }
    } catch (e) {
        console.error('Failed to fetch forecast:', e);
    }
}

// ── Digital Accountant Controller ──
function initAccountantView() {
    fetchAccountantHealthScore();
    fetchAccountantLedger();
    fetchAccountantCashflow();
    fetchAccountantTaxReadiness();
}

async function fetchAccountantHealthScore() {
    const token = localStorage.getItem('shopo_auth_token');
    try {
        const res = await fetch('/api/bi/accountant/health-score', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const json = await res.json();
        if (json.success && json.data) {
            const h = json.data;
            const scoreEl = document.getElementById('healthScoreVal');
            const gradeEl = document.getElementById('healthGradeBadge');
            const summaryEl = document.getElementById('healthSummaryText');
            const pillarsEl = document.getElementById('healthPillarsGrid');
            const recsEl = document.getElementById('healthRecommendationsBox');

            if (scoreEl) scoreEl.textContent = h.score;
            if (gradeEl) {
                gradeEl.textContent = h.grade;
                gradeEl.style.background = h.score >= 70 ? '#DCFCE7' : (h.score >= 50 ? '#FEF3C7' : '#FEE2E2');
                gradeEl.style.color = h.score >= 70 ? '#15803D' : (h.score >= 50 ? '#92400E' : '#B91C1C');
            }
            if (summaryEl) summaryEl.textContent = h.summary;

            if (pillarsEl && h.breakdown) {
                pillarsEl.innerHTML = `
                    <div style="background:var(--bg-light); border-radius:var(--radius-sm); padding:6px 10px; font-size:0.8rem;">
                        <span style="color:var(--text-muted);">Liquidity:</span> <strong>${h.breakdown.liquidity_score}</strong>
                    </div>
                    <div style="background:var(--bg-light); border-radius:var(--radius-sm); padding:6px 10px; font-size:0.8rem;">
                        <span style="color:var(--text-muted);">Margins:</span> <strong>${h.breakdown.profitability_score}</strong>
                    </div>
                    <div style="background:var(--bg-light); border-radius:var(--radius-sm); padding:6px 10px; font-size:0.8rem;">
                        <span style="color:var(--text-muted);">Expenses:</span> <strong>${h.breakdown.expense_ratio_score}</strong>
                    </div>
                    <div style="background:var(--bg-light); border-radius:var(--radius-sm); padding:6px 10px; font-size:0.8rem;">
                        <span style="color:var(--text-muted);">Collections:</span> <strong>${h.breakdown.collection_efficiency_score}</strong>
                    </div>
                `;
            }

            if (recsEl) {
                recsEl.innerHTML = `
                    <div style="font-weight:700; color:var(--text-primary); margin-bottom:4px;"><i class="fas fa-bolt" style="color:var(--lime-600);"></i> Accountant Action Plan:</div>
                    <ul style="margin:0 0 0 16px; padding:0; color:var(--text-secondary);">
                        ${(h.recommendations || []).map(r => `<li>${r}</li>`).join('')}
                    </ul>
                `;
            }
        }
    } catch (e) {
        console.error('Failed to fetch health score:', e);
    }
}

async function fetchAccountantLedger() {
    const token = localStorage.getItem('shopo_auth_token');
    const typeFilter = document.getElementById('ledgerTypeFilter')?.value || '';
    const tbody = document.getElementById('ledgerTableBody');
    if (!tbody) return;

    try {
        const url = `/api/bi/accountant/ledger${typeFilter ? `?entry_type=${typeFilter}` : ''}`;
        const res = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const json = await res.json();
        if (json.success && json.data) {
            const d = json.data;
            const arEl = document.getElementById('ledgerTotalAr');
            const apEl = document.getElementById('ledgerTotalAp');
            const netEl = document.getElementById('ledgerNetWorking');
            const arOverEl = document.getElementById('ledgerOverdueArCount');
            const apOverEl = document.getElementById('ledgerOverdueApCount');

            if (arEl) arEl.textContent = `₹${(d.total_receivables_pending || 0).toLocaleString('en-IN')}`;
            if (apEl) apEl.textContent = `₹${(d.total_payables_pending || 0).toLocaleString('en-IN')}`;
            if (netEl) netEl.textContent = `₹${(d.net_working_capital_position || 0).toLocaleString('en-IN')}`;
            if (arOverEl) arOverEl.textContent = `${d.overdue_counts?.receivables || 0} overdue`;
            if (apOverEl) apOverEl.textContent = `${d.overdue_counts?.payables || 0} overdue`;

            // Aging buckets badges
            const pillsEl = document.getElementById('agingBucketsPills');
            if (pillsEl && d.aging_buckets) {
                const arB = d.aging_buckets.receivables || {};
                pillsEl.innerHTML = `
                    <span class="badge" style="background:#DCFCE7; color:#15803D;">0-30 Days: ₹${(arB['0_30'] || 0).toLocaleString('en-IN')}</span>
                    <span class="badge" style="background:#FEF9C3; color:#854D0E;">31-60 Days: ₹${(arB['31_60'] || 0).toLocaleString('en-IN')}</span>
                    <span class="badge" style="background:#FED7AA; color:#9A3412;">61-90 Days: ₹${(arB['61_90'] || 0).toLocaleString('en-IN')}</span>
                    <span class="badge" style="background:#FEE2E2; color:#991B1B;">90+ Days (Overdue): ₹${(arB['90_plus'] || 0).toLocaleString('en-IN')}</span>
                `;
            }

            const items = d.active_ledger_items || [];
            if (items.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; color:var(--text-muted); padding:20px;">No active ledger entries found. Record a receivable or payable above!</td></tr>';
                return;
            }

            tbody.innerHTML = items.map(item => {
                const isRec = item.entry_type === 'receivable';
                const statusBadge = item.status === 'paid'
                    ? '<span class="badge" style="background:#DCFCE7; color:#15803D;">Paid</span>'
                    : (item.status === 'overdue'
                        ? '<span class="badge" style="background:#FEE2E2; color:#B91C1C;">Overdue</span>'
                        : '<span class="badge" style="background:#FEF3C7; color:#92400E;">Pending</span>');

                return `
                    <tr>
                        <td><span style="font-weight:700; color:${isRec ? '#16A34A' : '#DC2626'};">${isRec ? 'Receivable (उधार)' : 'Payable (देय)'}</span></td>
                        <td><strong>${item.party_name}</strong> ${item.invoice_ref ? `<span style="font-size:0.75rem; color:var(--text-muted);">(${item.invoice_ref})</span>` : ''}</td>
                        <td>₹${(item.amount || 0).toLocaleString('en-IN')}</td>
                        <td>₹${(item.paid_amount || 0).toLocaleString('en-IN')}</td>
                        <td><strong style="color:${isRec ? '#16A34A' : '#DC2626'};">₹${(item.balance_pending || (item.amount - item.paid_amount)).toLocaleString('en-IN')}</strong></td>
                        <td>${item.due_date || '-'}</td>
                        <td>${statusBadge}</td>
                        <td>
                            <div style="display:flex; gap:6px;">
                                <button type="button" class="btn-dash btn-dash-secondary" style="padding:4px 8px; font-size:0.75rem;" onclick="handleUpdateLedgerPayment('${item.id}', ${item.amount})">
                                    <i class="fas fa-check"></i> Pay
                                </button>
                                <button type="button" class="btn-dash btn-dash-secondary" style="padding:4px 8px; font-size:0.75rem; color:var(--red-500);" onclick="handleDeleteLedgerEntry('${item.id}')">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
        }
    } catch (e) {
        console.error('Failed to fetch ledger:', e);
    }
}

async function handleRecordLedgerSubmit(e) {
    if (e) e.preventDefault();
    const token = localStorage.getItem('shopo_auth_token');
    const payload = {
        entry_type: document.getElementById('ledgerEntryType')?.value,
        party_name: document.getElementById('ledgerPartyName')?.value,
        amount: parseFloat(document.getElementById('ledgerAmount')?.value || 0),
        due_date: document.getElementById('ledgerDueDate')?.value,
        invoice_ref: document.getElementById('ledgerInvoiceRef')?.value,
        notes: document.getElementById('ledgerNotes')?.value,
    };

    try {
        const res = await fetch('/api/bi/accountant/ledger', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        const json = await res.json();
        if (json.success) {
            closeModal('addLedgerModal');
            fetchAccountantLedger();
            fetchAccountantHealthScore();
        } else {
            alert(json.message || 'Failed to save entry.');
        }
    } catch (err) {
        console.error('Record ledger error:', err);
    }
}

async function handleUpdateLedgerPayment(itemId, totalAmount) {
    const input = prompt(`Enter total paid amount for this record (up to ₹${totalAmount}):`, totalAmount);
    if (input === null) return;
    const paidVal = parseFloat(input);
    if (isNaN(paidVal) || paidVal < 0) {
        alert('Please enter a valid amount.');
        return;
    }

    const token = localStorage.getItem('shopo_auth_token');
    try {
        const res = await fetch(`/api/bi/accountant/ledger/${itemId}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ paid_amount: paidVal })
        });
        const json = await res.json();
        if (json.success) {
            fetchAccountantLedger();
            fetchAccountantHealthScore();
        } else {
            alert(json.message || 'Update failed.');
        }
    } catch (e) {
        console.error('Failed to update ledger payment:', e);
    }
}

async function handleDeleteLedgerEntry(itemId) {
    if (!confirm('Are you sure you want to delete this ledger entry?')) return;
    const token = localStorage.getItem('shopo_auth_token');
    try {
        const res = await fetch(`/api/bi/accountant/ledger/${itemId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const json = await res.json();
        if (json.success) {
            fetchAccountantLedger();
            fetchAccountantHealthScore();
        }
    } catch (e) {
        console.error('Failed to delete entry:', e);
    }
}

async function fetchAccountantCashflow() {
    const token = localStorage.getItem('shopo_auth_token');
    const container = document.getElementById('accountantCashflowContent');
    if (!container) return;

    try {
        const res = await fetch('/api/bi/accountant/cashflow', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const json = await res.json();
        if (json.success && json.data) {
            const cf = json.data;
            container.innerHTML = `
                <div style="font-size:0.9rem; font-weight:700; color:${cf.liquidity_risk_detected ? '#DC2626' : '#16A34A'}; margin-bottom:8px;">
                    ${cf.advisory}
                </div>
                <div style="display:flex; justify-content:space-between; font-size:0.85rem; padding:6px 0; border-bottom:1px solid var(--border-color);">
                    <span>Projected Inflow:</span> <strong>₹${(cf.total_projected_inflow || 0).toLocaleString('en-IN')}</strong>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:0.85rem; padding:6px 0; border-bottom:1px solid var(--border-color);">
                    <span>Projected Outflow:</span> <strong style="color:#DC2626;">₹${(cf.total_projected_outflow || 0).toLocaleString('en-IN')}</strong>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:0.85rem; padding:6px 0;">
                    <span>Net 30-Day Liquidity Shift:</span> <strong>₹${(cf.net_projected_cash_change || 0).toLocaleString('en-IN')}</strong>
                </div>
            `;
        }
    } catch (e) {
        console.error('Failed to fetch cash flow:', e);
    }
}

async function fetchAccountantTaxReadiness() {
    const token = localStorage.getItem('shopo_auth_token');
    const container = document.getElementById('accountantTaxContent');
    if (!container) return;

    try {
        const res = await fetch('/api/bi/accountant/tax-readiness', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const json = await res.json();
        if (json.success && json.data) {
            const t = json.data;
            const slabsHtml = Object.entries(t.slabs || {}).map(([slab, val]) => `
                <div style="display:flex; justify-content:space-between; font-size:0.82rem; padding:4px 0;">
                    <span>${slab}</span>
                    <span>Turnover: ₹${(val.taxable_turnover || 0).toLocaleString('en-IN')} (GST: ₹${(val.tax_collected || 0).toFixed(2)})</span>
                </div>
            `).join('');

            container.innerHTML = `
                <div style="margin-bottom:10px;">${slabsHtml}</div>
                <div style="border-top:1px dashed var(--border-color); padding-top:8px; font-size:0.85rem;">
                    <div style="display:flex; justify-content:space-between;">
                        <span>Output GST:</span> <strong>₹${(t.total_output_gst || 0).toFixed(2)}</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; color:#15803D;">
                        <span>Est. Input Tax Credit (ITC):</span> <strong>-₹${(t.estimated_input_tax_credit || 0).toFixed(2)}</strong>
                    </div>
                    <div style="display:flex; justify-content:space-between; font-weight:800; margin-top:4px;">
                        <span>Net GST Payable:</span> <strong>₹${(t.net_estimated_gst_payable || 0).toFixed(2)}</strong>
                    </div>
                </div>
            `;
        }
    } catch (e) {
        console.error('Failed to fetch tax readiness:', e);
    }
}

// ── What-If Simulator Controller ──
let currentSimScenario = 'price_change';
let lastSimulationResult = null;

function initSimulatorView() {
    switchSimTab('price_change');
    fetchSavedScenarios();
}

function switchSimTab(scenarioType) {
    currentSimScenario = scenarioType;
    ['tabSimPrice', 'tabSimCost', 'tabSimBogo', 'tabSimHire'].forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.classList.remove('active');
    });

    if (scenarioType === 'price_change') document.getElementById('tabSimPrice')?.classList.add('active');
    else if (scenarioType === 'cost_increase') document.getElementById('tabSimCost')?.classList.add('active');
    else if (scenarioType === 'bogo_promo') document.getElementById('tabSimBogo')?.classList.add('active');
    else if (scenarioType === 'hiring_expense') document.getElementById('tabSimHire')?.classList.add('active');

    renderSimInputs();
}

function renderSimInputs() {
    const container = document.getElementById('simInputsContainer');
    if (!container) return;

    if (currentSimScenario === 'price_change') {
        container.innerHTML = `
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:14px;">
                <div>
                    <label style="font-size:0.85rem; font-weight:700;">Price Adjustment (% Change):</label>
                    <input type="number" id="simPriceDelta" value="10" step="1" style="width:100%; margin-top:4px;">
                    <span style="font-size:0.75rem; color:var(--text-muted);">Use positive (+10%) for price rise, negative (-5%) for discount.</span>
                </div>
                <div>
                    <label style="font-size:0.85rem; font-weight:700;">Price Elasticity Coefficient:</label>
                    <input type="number" id="simElasticity" value="-0.90" step="0.05" style="width:100%; margin-top:4px;">
                    <span style="font-size:0.75rem; color:var(--text-muted);">Retail grocery average is -0.85 to -1.10.</span>
                </div>
            </div>
        `;
    } else if (currentSimScenario === 'cost_increase') {
        container.innerHTML = `
            <div style="max-width:320px;">
                <label style="font-size:0.85rem; font-weight:700;">Supplier Wholesale Cost Hike (%):</label>
                <input type="number" id="simCostDelta" value="15" step="1" min="1" style="width:100%; margin-top:4px;">
                <span style="font-size:0.75rem; color:var(--text-muted);">Simulate impact of commodity wholesale inflation.</span>
            </div>
        `;
    } else if (currentSimScenario === 'bogo_promo') {
        container.innerHTML = `
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:14px;">
                <div>
                    <label style="font-size:0.85rem; font-weight:700;">Effective Promotion Discount (%):</label>
                    <input type="number" id="simPromoDiscount" value="25" step="5" min="5" max="90" style="width:100%; margin-top:4px;">
                    <span style="font-size:0.75rem; color:var(--text-muted);">e.g. 50% for BOGO or 25% flat promo.</span>
                </div>
                <div>
                    <label style="font-size:0.85rem; font-weight:700;">Projected Volume Multiplier:</label>
                    <input type="number" id="simVolumeMult" value="2.2" step="0.1" min="1.0" style="width:100%; margin-top:4px;">
                    <span style="font-size:0.75rem; color:var(--text-muted);">Expected sales velocity boost (e.g. 2.2x).</span>
                </div>
            </div>
        `;
    } else if (currentSimScenario === 'hiring_expense') {
        container.innerHTML = `
            <div style="max-width:320px;">
                <label style="font-size:0.85rem; font-weight:700;">New Staff Monthly Salary (₹):</label>
                <input type="number" id="simMonthlySalary" value="15000" step="500" min="1000" style="width:100%; margin-top:4px;">
                <span style="font-size:0.75rem; color:var(--text-muted);">Calculates exact breakeven retail sales required.</span>
            </div>
        `;
    }
}

async function executeCurrentSimulation() {
    const token = localStorage.getItem('shopo_auth_token');
    let params = {};

    if (currentSimScenario === 'price_change') {
        params = {
            price_delta_pct: parseFloat(document.getElementById('simPriceDelta')?.value || 10),
            price_elasticity: parseFloat(document.getElementById('simElasticity')?.value || -0.90)
        };
    } else if (currentSimScenario === 'cost_increase') {
        params = {
            supplier_cost_delta_pct: parseFloat(document.getElementById('simCostDelta')?.value || 15)
        };
    } else if (currentSimScenario === 'bogo_promo') {
        params = {
            discount_pct: parseFloat(document.getElementById('simPromoDiscount')?.value || 25),
            volume_multiplier: parseFloat(document.getElementById('simVolumeMult')?.value || 2.2)
        };
    } else if (currentSimScenario === 'hiring_expense') {
        params = {
            monthly_salary: parseFloat(document.getElementById('simMonthlySalary')?.value || 15000)
        };
    }

    try {
        const res = await fetch('/api/bi/simulator/run', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ scenario_type: currentSimScenario, params: params })
        });
        const json = await res.json();
        if (json.success && json.data) {
            lastSimulationResult = json.data;
            renderSimulationOutcome(json.data);
        } else {
            alert(json.message || 'Simulation execution failed.');
        }
    } catch (e) {
        console.error('Simulation error:', e);
    }
}

function renderSimulationOutcome(sim) {
    const card = document.getElementById('simOutcomeCard');
    const grid = document.getElementById('simMetricsGrid');
    const verdictBox = document.getElementById('simVerdictBox');
    if (!card || !grid || !verdictBox) return;

    card.style.display = 'block';
    const b = sim.baseline || {};
    const s = sim.simulated || {};

    grid.innerHTML = `
        <div class="metric-card">
            <div class="metric-label">Simulated Monthly Revenue</div>
            <div class="metric-value">₹${(s.revenue || 0).toLocaleString('en-IN')}</div>
            <div class="metric-sub">Baseline: ₹${(b.revenue || 0).toLocaleString('en-IN')}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Simulated Gross Profit</div>
            <div class="metric-value">₹${(s.gross_profit || 0).toLocaleString('en-IN')}</div>
            <div class="metric-sub">Margin: ${s.gross_margin_pct || 0}%</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">Simulated Net Profit</div>
            <div class="metric-value" style="color:${(s.net_profit || 0) >= (b.net_profit || 0) ? '#16A34A' : '#DC2626'};">
                ₹${(s.net_profit || 0).toLocaleString('en-IN')}
            </div>
            <div class="metric-sub">Shift: ₹${((s.net_profit || 0) - (b.net_profit || 0)).toLocaleString('en-IN')}</div>
        </div>
    `;

    verdictBox.innerHTML = `
        <div style="font-size:0.85rem; text-transform:uppercase; color:#166534; font-weight:800; margin-bottom:4px;">
            <i class="fas fa-check-circle"></i> AI Simulator Recommendation:
        </div>
        <div>${sim.verdict}</div>
    `;
}

async function saveCurrentSimulation() {
    if (!lastSimulationResult) {
        alert('Please run a simulation before saving.');
        return;
    }
    const name = prompt('Enter a name for this decision brief:', `${currentSimScenario.replace('_', ' ').toUpperCase()} Scenario`);
    if (!name) return;

    const token = localStorage.getItem('shopo_auth_token');
    try {
        const res = await fetch('/api/bi/simulator/scenarios', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                scenario_type: currentSimScenario,
                parameters: lastSimulationResult.parameters,
                results: lastSimulationResult
            })
        });
        const json = await res.json();
        if (json.success) {
            alert('Simulation scenario saved successfully!');
            fetchSavedScenarios();
        }
    } catch (e) {
        console.error('Failed to save scenario:', e);
    }
}

async function fetchSavedScenarios() {
    const token = localStorage.getItem('shopo_auth_token');
    const listEl = document.getElementById('savedScenariosList');
    if (!listEl) return;

    try {
        const res = await fetch('/api/bi/simulator/scenarios', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const json = await res.json();
        if (json.success && json.data) {
            const scens = json.data.scenarios || [];
            if (scens.length === 0) {
                listEl.textContent = 'No saved simulation scenarios yet.';
                return;
            }

            listEl.innerHTML = scens.map(s => `
                <div style="display:flex; justify-content:space-between; align-items:center; padding:10px; border-bottom:1px solid var(--border-color);">
                    <div>
                        <strong>${s.name}</strong> <span style="font-size:0.8rem; color:var(--text-muted);">(${s.scenario_type})</span>
                        <div style="font-size:0.8rem; color:var(--text-secondary); margin-top:2px;">${s.results?.verdict ? s.results.verdict.slice(0, 100) + '...' : ''}</div>
                    </div>
                    <button type="button" class="btn-dash btn-dash-secondary" style="color:var(--red-500); padding:4px 8px; font-size:0.8rem;" onclick="deleteSavedScenario('${s.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `).join('');
        }
    } catch (e) {
        console.error('Failed to fetch saved scenarios:', e);
    }
}

async function deleteSavedScenario(id) {
    if (!confirm('Delete this saved scenario?')) return;
    const token = localStorage.getItem('shopo_auth_token');
    try {
        await fetch(`/api/bi/simulator/scenarios/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        fetchSavedScenarios();
    } catch (e) {
        console.error('Failed to delete scenario:', e);
    }
}

// ════════════════════════════════════════════════
// FEATURE B.1: PRODUCT DNA & TRACEABILITY
// ════════════════════════════════════════════════

let currentDnaData = null;
let currentDnaEvents = [];

async function openProductDnaModal(productId) {
    const token = localStorage.getItem('shopo_auth_token');
    const modal = document.getElementById('productDnaModal');
    if (!modal) return;

    // Reset fields
    document.getElementById('dnaAdjustProductId').value = productId;
    document.getElementById('dnaStatCurrentStock').textContent = '--';
    document.getElementById('dnaStatBuyPrice').textContent = '₹--';
    document.getElementById('dnaStatSellPrice').textContent = '₹--';
    document.getElementById('dnaStatLifetimeSold').textContent = '--';
    document.getElementById('dnaStatLifetimeAdded').textContent = '--';
    document.getElementById('dnaTimelineFeed').innerHTML = `
        <div style="text-align:center; padding:20px; color:var(--text-muted); font-size:0.88rem;">
            <i class="fas fa-spinner fa-spin"></i> Loading product history...
        </div>
    `;

    openModal('productDnaModal');

    try {
        const res = await fetch(`/api/inventory/${productId}/dna`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const json = await res.json();
        if (json.success && json.data) {
            currentDnaData = json.data;
            const p = json.data.product || {};
            const sum = json.data.summary || {};
            currentDnaEvents = json.data.timeline || [];

            document.getElementById('dnaProductSubTitle').textContent = `${p.product_name || 'Product'} (${p.category || 'General'}) • Traceability Audit`;
            document.getElementById('dnaStatCurrentStock').textContent = `${p.quantity || 0} ${p.unit || 'pcs'}`;
            document.getElementById('dnaStatBuyPrice').textContent = `₹${parseFloat(p.purchase_price || 0).toFixed(2)}`;
            document.getElementById('dnaStatSellPrice').textContent = `₹${parseFloat(p.selling_price || 0).toFixed(2)}`;
            document.getElementById('dnaStatLifetimeSold').textContent = `${sum.lifetime_units_sold || 0} units`;
            document.getElementById('dnaStatLifetimeAdded').textContent = `${sum.lifetime_units_added || 0} units`;

            renderDnaTimeline(currentDnaEvents);
        } else {
            document.getElementById('dnaTimelineFeed').innerHTML = `
                <div style="text-align:center; padding:16px; color:var(--red-500);">
                    ${escapeHtml(json.message || 'Could not load Product DNA.')}
                </div>
            `;
        }
    } catch (e) {
        console.error('Error fetching Product DNA:', e);
        document.getElementById('dnaTimelineFeed').innerHTML = `
            <div style="text-align:center; padding:16px; color:var(--red-500);">
                Network error loading Product DNA timeline.
            </div>
        `;
    }
}

function renderDnaTimeline(events) {
    const feed = document.getElementById('dnaTimelineFeed');
    if (!feed) return;

    if (!events || events.length === 0) {
        feed.innerHTML = `
            <div style="text-align:center; padding:20px; color:var(--text-muted); font-size:0.88rem;">
                No lifecycle events recorded for this product yet.
            </div>
        `;
        return;
    }

    const eventIcons = {
        'creation': { icon: 'fa-plus-circle', color: '#16A34A', bg: '#DCFCE7', label: 'Created' },
        'stock_addition': { icon: 'fa-arrow-circle-down', color: '#2563EB', bg: '#DBEAFE', label: 'Stock In' },
        'stock_reduction': { icon: 'fa-arrow-circle-up', color: '#DC2626', bg: '#FEE2E2', label: 'Stock Deducted' },
        'sale': { icon: 'fa-cash-register', color: '#059669', bg: '#D1FAE5', label: 'Customer Sale' },
        'price_change': { icon: 'fa-tag', color: '#D97706', bg: '#FEF3C7', label: 'Price Update' },
        'batch_update': { icon: 'fa-barcode', color: '#7C3AED', bg: '#EDE9FE', label: 'Batch / Expiry' },
        'supplier_change': { icon: 'fa-truck', color: '#4F46E5', bg: '#E0E7FF', label: 'Supplier Update' },
        'adjustment': { icon: 'fa-sliders-h', color: '#B45309', bg: '#FEF3C7', label: 'Stock Adjustment' }
    };

    feed.innerHTML = events.map(ev => {
        const meta = eventIcons[ev.event_type] || { icon: 'fa-history', color: '#475569', bg: '#F1F5F9', label: ev.event_type };
        const d = new Date(ev.created_at);
        const dateStr = d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) + ' ' + d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

        let detailText = '';
        if (ev.quantity_change !== null && ev.quantity_change !== undefined) {
            const prefix = ev.quantity_change > 0 ? '+' : '';
            detailText += `<span style="font-weight:700; color:${ev.quantity_change >= 0 ? '#16A34A' : '#DC2626'}; margin-right:8px;">${prefix}${ev.quantity_change} units</span>`;
        }
        if (ev.previous_value && ev.new_value) {
            detailText += `<span style="font-size:0.8rem; color:var(--text-muted);">${escapeHtml(ev.previous_value)} &rarr; <b>${escapeHtml(ev.new_value)}</b></span>`;
        } else if (ev.new_value) {
            detailText += `<span style="font-size:0.8rem; color:var(--text-muted);"><b>${escapeHtml(ev.new_value)}</b></span>`;
        }

        let reasonBadge = '';
        if (ev.reason) {
            reasonBadge = `<span style="display:inline-block; font-size:0.75rem; background:#F1F5F9; color:#334155; padding:2px 6px; border-radius:4px; margin-left:6px; border:1px solid #CBD5E1;">Reason: ${escapeHtml(ev.reason)}</span>`;
        }

        let notesHtml = '';
        if (ev.notes) {
            notesHtml = `<div style="font-size:0.8rem; color:var(--text-secondary); margin-top:4px; font-style:italic;">"${escapeHtml(ev.notes)}"</div>`;
        }

        return `
            <div style="display:flex; gap:12px; align-items:flex-start; padding:10px 12px; background:#FFF; border:1px solid var(--border-color); border-radius:var(--radius-md);">
                <div style="width:36px; height:36px; border-radius:50%; background:${meta.bg}; color:${meta.color}; display:flex; align-items:center; justify-content:center; flex-shrink:0;">
                    <i class="fas ${meta.icon}"></i>
                </div>
                <div style="flex:1;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">
                        <div>
                            <span style="font-weight:700; font-size:0.88rem; color:var(--text-primary);">${meta.label}</span>
                            ${reasonBadge}
                        </div>
                        <span style="font-size:0.75rem; color:var(--text-muted);">${dateStr}</span>
                    </div>
                    <div style="margin-top:4px;">
                        ${detailText}
                    </div>
                    ${notesHtml}
                </div>
            </div>
        `;
    }).join('');
}

function filterDnaTimeline(filterType) {
    if (!currentDnaEvents) return;
    if (filterType === 'all') {
        renderDnaTimeline(currentDnaEvents);
    } else {
        const filtered = currentDnaEvents.filter(ev => ev.event_type === filterType);
        renderDnaTimeline(filtered);
    }
}

function toggleDnaAdjustForm() {
    const form = document.getElementById('dnaAdjustForm');
    const icon = document.getElementById('dnaAdjustFormToggleIcon');
    if (!form) return;
    if (form.style.display === 'none' || !form.style.display) {
        form.style.display = 'block';
        if (icon) icon.innerHTML = '<i class="fas fa-chevron-up"></i>';
    } else {
        form.style.display = 'none';
        if (icon) icon.innerHTML = '<i class="fas fa-chevron-down"></i>';
    }
}

async function handleDnaManualAdjustmentSubmit(e) {
    e.preventDefault();
    const productId = document.getElementById('dnaAdjustProductId').value;
    const action = document.getElementById('dnaAdjustAction').value;
    const qty = parseFloat(document.getElementById('dnaAdjustQty').value);
    const reason = document.getElementById('dnaAdjustReason').value;
    const batch = document.getElementById('dnaAdjustBatch').value.trim();
    const notes = document.getElementById('dnaAdjustNotes').value.trim();

    if (!productId || isNaN(qty) || qty <= 0 || !reason) {
        alert('Please specify an adjustment action, quantity greater than 0, and a mandatory reason.');
        return;
    }

    const token = localStorage.getItem('shopo_auth_token');
    let targetNewQty = qty;
    if (currentDnaData && currentDnaData.product) {
        const cur = parseFloat(currentDnaData.product.quantity || 0);
        if (action === 'addition') targetNewQty = cur + qty;
        else if (action === 'reduction') targetNewQty = Math.max(0, cur - qty);
        else targetNewQty = qty;
    }

    try {
        const res = await fetch(`/api/inventory/${productId}/dna/adjust`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                adjustment_type: action,
                quantity: qty,
                new_quantity: targetNewQty,
                reason: reason,
                batch_number: batch || undefined,
                notes: notes || undefined
            })
        });
        const json = await res.json();
        if (json.success) {
            alert('Stock adjustment recorded successfully.');
            // Reset form
            document.getElementById('dnaAdjustForm').reset();
            toggleDnaAdjustForm();
            // Refresh modal DNA data
            openProductDnaModal(productId);
            // Refresh inventory table
            fetchInventory();
        } else {
            alert(json.message || 'Failed to record stock adjustment.');
        }
    } catch (err) {
        console.error('Error recording stock adjustment:', err);
        alert('Network error recording stock adjustment.');
    }
}

// ════════════════════════════════════════════════
// FEATURE B.2: MULTI-STORE HUB
// ════════════════════════════════════════════════

let multiStoreList = [];

async function initMultiStoreView() {
    await fetchMultiStoreAnalytics();
    await fetchMultiStoreTransfers();
}

async function fetchMultiStoreAnalytics() {
    const token = localStorage.getItem('shopo_auth_token');
    const container = document.getElementById('multiStoreCardsContainer');
    if (!container) return;

    try {
        const res = await fetch('/api/stores/analytics', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const json = await res.json();
        if (json.success && json.data) {
            const c = json.data.consolidated || {};
            const stores = json.data.stores || [];
            multiStoreList = stores;

            // Render KPIs
            document.getElementById('msActiveStoresCount').textContent = c.total_stores || stores.length;
            document.getElementById('msConsolidatedValuation').textContent = `₹${parseFloat(c.consolidated_inventory_valuation || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            document.getElementById('msTotalStockUnits').textContent = `${c.total_stock_units || 0} total units in stock`;
            document.getElementById('msConsolidatedRevenue').textContent = `₹${parseFloat(c.consolidated_revenue || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            document.getElementById('msConsolidatedProfit').textContent = `₹${parseFloat(c.consolidated_net_profit || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
            document.getElementById('msConsolidatedMargin').textContent = `${c.consolidated_profit_margin_pct || 0}% margin`;

            // Render Store Cards
            if (stores.length === 0) {
                container.innerHTML = `<div style="color:var(--text-muted); font-size:0.9rem;">No branches registered yet. Click "Add Branch" to expand.</div>`;
                return;
            }

            container.innerHTML = stores.map(st => {
                const isPrimary = st.is_primary;
                return `
                    <div style="background:#FFF; border:1.5px solid var(--border-color); border-radius:var(--radius-lg); padding:18px; position:relative;">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px;">
                            <div>
                                <h4 style="font-weight:800; font-size:1.05rem; color:var(--text-primary); margin-bottom:2px;">
                                    ${escapeHtml(st.name)}
                                </h4>
                                <div style="font-size:0.8rem; color:var(--text-muted);">
                                    <i class="fas fa-map-marker-alt"></i> ${escapeHtml(st.address || 'Local Dukaan')}
                                </div>
                            </div>
                            ${isPrimary ? `<span class="badge" style="background:var(--lime-100); color:var(--lime-800); font-weight:800; font-size:0.75rem; padding:3px 8px; border:1px solid var(--lime-300);"><i class="fas fa-crown"></i> Primary</span>` : `<span class="badge" style="background:#F1F5F9; color:#475569; font-size:0.75rem; padding:3px 8px;">Branch</span>`}
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:14px; padding-top:12px; border-top:1px dashed var(--border-color);">
                            <div>
                                <div style="font-size:0.75rem; color:var(--text-muted);">Stock Valuation</div>
                                <div style="font-weight:700; color:var(--text-primary); font-size:0.95rem;">₹${parseFloat(st.inventory_valuation || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                            </div>
                            <div>
                                <div style="font-size:0.75rem; color:var(--text-muted);">Total Revenue</div>
                                <div style="font-weight:700; color:#16A34A; font-size:0.95rem;">₹${parseFloat(st.total_sales || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                            </div>
                            <div>
                                <div style="font-size:0.75rem; color:var(--text-muted);">Catalog Products</div>
                                <div style="font-weight:600; font-size:0.9rem;">${st.product_count || 0} items</div>
                            </div>
                            <div>
                                <div style="font-size:0.75rem; color:var(--text-muted);">Stock Units</div>
                                <div style="font-weight:600; font-size:0.9rem;">${st.total_quantity || 0} units</div>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
    } catch (e) {
        console.error('Error fetching multi-store analytics:', e);
    }
}

async function fetchMultiStoreTransfers() {
    const token = localStorage.getItem('shopo_auth_token');
    const tbody = document.getElementById('multiStoreTransfersTableBody');
    if (!tbody) return;

    try {
        const res = await fetch('/api/stores/transfers', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const json = await res.json();
        if (json.success && json.data) {
            const list = json.data.transfers || [];
            if (list.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:16px; color:var(--text-muted);">No stock transfers recorded yet.</td></tr>`;
                return;
            }

            tbody.innerHTML = list.map(tr => {
                const d = new Date(tr.created_at);
                const dateStr = d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) + ' ' + d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
                return `
                    <tr>
                        <td style="font-size:0.82rem; color:var(--text-muted);">${dateStr}</td>
                        <td style="font-weight:600;">${escapeHtml(tr.product_name || tr.product_id)}</td>
                        <td>${escapeHtml(tr.source_store_name || tr.source_store_id)}</td>
                        <td>${escapeHtml(tr.dest_store_name || tr.dest_store_id)}</td>
                        <td style="font-weight:700; color:#2563EB;">${tr.quantity}</td>
                        <td style="font-size:0.85rem; color:var(--text-secondary);">${escapeHtml(tr.transfer_reason || '—')}</td>
                        <td><span class="stock-pill in-stock"><i class="fas fa-check"></i> ${escapeHtml(tr.status)}</span></td>
                    </tr>
                `;
            }).join('');
        }
    } catch (e) {
        console.error('Error fetching stock transfers:', e);
    }
}

async function handleCreateStoreSubmit(e) {
    e.preventDefault();
    const token = localStorage.getItem('shopo_auth_token');
    const name = document.getElementById('newStoreName').value.trim();
    const address = document.getElementById('newStoreAddress').value.trim();
    const phone = document.getElementById('newStorePhone').value.trim();
    const gstin = document.getElementById('newStoreGstin').value.trim();
    const notes = document.getElementById('newStoreNotes').value.trim();

    if (!name) {
        alert('Please enter a store branch name.');
        return;
    }

    try {
        const res = await fetch('/api/stores', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ name, address, phone, gstin, notes })
        });
        const json = await res.json();
        if (json.success) {
            closeModal('addBranchModal');
            document.getElementById('newStoreName').value = '';
            document.getElementById('newStoreAddress').value = '';
            document.getElementById('newStorePhone').value = '';
            document.getElementById('newStoreGstin').value = '';
            document.getElementById('newStoreNotes').value = '';
            await fetchMultiStoreAnalytics();
            alert('Branch store created successfully!');
        } else {
            alert(json.message || 'Failed to create branch store.');
        }
    } catch (err) {
        console.error('Error creating store branch:', err);
        alert('Network error creating store branch.');
    }
}

async function openTransferStockModal() {
    const token = localStorage.getItem('shopo_auth_token');
    try {
        const res = await fetch('/api/stores', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const json = await res.json();
        if (json.success && json.data) {
            const stores = json.data.stores || [];
            if (stores.length < 2) {
                alert('You need at least 2 branches to execute an inter-store transfer. Please create another branch first.');
                openModal('addBranchModal');
                return;
            }

            const srcSelect = document.getElementById('transferSourceStore');
            const destSelect = document.getElementById('transferDestStore');

            srcSelect.innerHTML = stores.map((s, idx) => `<option value="${s.id}" ${idx === 0 ? 'selected' : ''}>${escapeHtml(s.name)}</option>`).join('');
            destSelect.innerHTML = stores.map((s, idx) => `<option value="${s.id}" ${idx === 1 ? 'selected' : ''}>${escapeHtml(s.name)}</option>`).join('');

            handleTransferSourceStoreChange();
            openModal('transferStockModal');
        }
    } catch (e) {
        console.error('Error opening transfer modal:', e);
    }
}

function handleTransferSourceStoreChange() {
    // Populate products available
    const prodSelect = document.getElementById('transferProductSelect');
    if (!prodSelect) return;

    if (!inventoryItems || inventoryItems.length === 0) {
        prodSelect.innerHTML = `<option value="">No inventory items available</option>`;
        document.getElementById('transferAvailableStockText').textContent = 'Available: 0';
        return;
    }

    prodSelect.innerHTML = inventoryItems.map(item => `
        <option value="${item.id}" data-qty="${item.quantity}">${escapeHtml(item.product_name)} (Available: ${item.quantity} ${item.unit || 'pcs'})</option>
    `).join('');

    handleTransferProductChange();
}

function handleTransferProductChange() {
    const prodSelect = document.getElementById('transferProductSelect');
    const availText = document.getElementById('transferAvailableStockText');
    if (!prodSelect || !availText) return;

    const opt = prodSelect.options[prodSelect.selectedIndex];
    if (opt) {
        const qty = opt.getAttribute('data-qty') || 0;
        availText.textContent = `Available in Source Store: ${qty}`;
    }
}

async function handleStockTransferSubmit(e) {
    e.preventDefault();
    const token = localStorage.getItem('shopo_auth_token');
    const src = document.getElementById('transferSourceStore').value;
    const dst = document.getElementById('transferDestStore').value;
    const prodId = document.getElementById('transferProductSelect').value;
    const qty = parseFloat(document.getElementById('transferQuantity').value);
    const reason = document.getElementById('transferReason').value.trim();

    if (!src || !dst || !prodId || isNaN(qty) || qty <= 0 || !reason) {
        alert('Please fill all transfer fields with valid numbers and reason.');
        return;
    }

    if (src === dst) {
        alert('Source and destination stores must be different.');
        return;
    }

    try {
        const res = await fetch('/api/stores/transfers', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                source_store_id: src,
                dest_store_id: dst,
                product_id: prodId,
                quantity: qty,
                reason: reason
            })
        });
        const json = await res.json();
        if (json.success) {
            closeModal('transferStockModal');
            document.getElementById('transferQuantity').value = '';
            document.getElementById('transferReason').value = '';
            await fetchMultiStoreAnalytics();
            await fetchMultiStoreTransfers();
            fetchInventory();
            alert('Stock transfer completed successfully!');
        } else {
            alert(json.message || 'Stock transfer failed.');
        }
    } catch (err) {
        console.error('Error executing stock transfer:', err);
        alert('Network error executing stock transfer.');
    }
}

// ════════════════════════════════════════════════
// FEATURE B.3: SMART SHELF SCANNER
// ════════════════════════════════════════════════

let currentShelfFile = null;
let currentShelfScanData = null;

async function initShelfScannerView() {
    const token = localStorage.getItem('shopo_auth_token');
    const storeSelect = document.getElementById('shelfScanStoreSelect');
    if (storeSelect) {
        try {
            const res = await fetch('/api/stores', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const json = await res.json();
            if (json.success && json.data) {
                const stores = json.data.stores || [];
                storeSelect.innerHTML = stores.map(s => `<option value="${s.id}">${escapeHtml(s.name)} ${s.is_primary ? '(Primary)' : ''}</option>`).join('');
            }
        } catch (e) {
            console.error('Error fetching stores for shelf scanner:', e);
        }
    }
    fetchShelfScansHistory();
}

function handleShelfFileSelected(event) {
    const file = event.target.files && event.target.files[0];
    if (!file) return;

    // Validate type and size
    const allowed = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowed.includes(file.type)) {
        alert('Invalid file format. Please upload JPG, PNG, or WebP images only.');
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        alert('File size exceeds the 10MB limit. Please upload a smaller photo.');
        return;
    }

    currentShelfFile = file;
    const previewImg = document.getElementById('shelfScanPreviewImg');
    const placeholder = document.getElementById('shelfScanPreviewPlaceholder');
    const btnScan = document.getElementById('btnRunShelfScan');

    const reader = new FileReader();
    reader.onload = (e) => {
        if (previewImg) {
            previewImg.src = e.target.result;
            previewImg.style.display = 'block';
        }
        if (placeholder) placeholder.style.display = 'none';
        if (btnScan) btnScan.disabled = false;
    };
    reader.readAsDataURL(file);
}

function clearShelfScan() {
    currentShelfFile = null;
    currentShelfScanData = null;
    const fileInput = document.getElementById('shelfScanFileInput');
    if (fileInput) fileInput.value = '';
    const previewImg = document.getElementById('shelfScanPreviewImg');
    if (previewImg) {
        previewImg.src = '';
        previewImg.style.display = 'none';
    }
    const placeholder = document.getElementById('shelfScanPreviewPlaceholder');
    if (placeholder) placeholder.style.display = 'block';
    const btnScan = document.getElementById('btnRunShelfScan');
    if (btnScan) btnScan.disabled = true;
    const resCard = document.getElementById('shelfScanResultCard');
    if (resCard) resCard.style.display = 'none';
}

async function runShelfAnalysis() {
    if (!currentShelfFile) {
        alert('Please choose or capture a shelf photo first.');
        return;
    }

    const token = localStorage.getItem('shopo_auth_token');
    const storeId = document.getElementById('shelfScanStoreSelect')?.value;
    const btnScan = document.getElementById('btnRunShelfScan');
    const originalText = btnScan.innerHTML;
    btnScan.disabled = true;
    btnScan.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Analyzing Shelf...`;

    try {
        const formData = new FormData();
        formData.append('image', currentShelfFile);
        if (storeId) formData.append('store_id', storeId);

        const res = await fetch('/api/shelf-scanner/analyze', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        const json = await res.json();
        const d = json.data || json;
        if (json.success && (d.detected_items || d.matched_items || d.scan_id)) {
            currentShelfScanData = d;
            renderShelfScanResults(d);
        } else {
            alert(json.message || 'Shelf analysis failed.');
        }
    } catch (err) {
        console.error('Error during shelf analysis:', err);
        alert('Network error while analyzing shelf image.');
    } finally {
        btnScan.disabled = false;
        btnScan.innerHTML = originalText;
    }
}

function renderShelfScanResults(data) {
    const card = document.getElementById('shelfScanResultCard');
    const tbody = document.getElementById('shelfCandidatesTableBody');
    if (!card || !tbody) return;

    card.style.display = 'block';
    const items = data.detected_items || [];
    const matched = items.filter(it => it.catalog_match && it.catalog_match.matched);
    const unmatched = items.filter(it => !it.catalog_match || !it.catalog_match.matched);

    document.getElementById('shelfDetectedCount').textContent = items.length;
    document.getElementById('shelfMatchedCount').textContent = matched.length;
    document.getElementById('shelfUnmatchedCount').textContent = unmatched.length;
    document.getElementById('shelfAuditScanId').textContent = `Scan ID: ${data.scan_id || 'manual'}`;

    const badge = document.getElementById('shelfScanEngineBadge');
    if (badge) {
        if (data.analysis_mode === 'offline_audit_fallback') {
            badge.textContent = 'Catalog Audit Mode';
            badge.style.background = '#FEF3C7';
            badge.style.color = '#92400E';
        } else {
            badge.textContent = 'Gemini Vision Active';
            badge.style.background = '#ECFDF5';
            badge.style.color = '#065F46';
        }
    }

    if (items.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding:16px; color:var(--text-muted);">No products detected in shelf photo.</td></tr>`;
        return;
    }

    tbody.innerHTML = items.map((it, idx) => {
        const cm = it.catalog_match || {};
        const isMatched = cm.matched;
        const currentStock = cm.current_stock !== undefined ? cm.current_stock : '--';
        const observed = it.observed_count || 1;
        const diff = (isMatched && typeof currentStock === 'number') ? (observed - currentStock) : 0;
        const diffText = diff > 0 ? `+${diff}` : `${diff}`;
        const diffColor = diff === 0 ? '#16A34A' : (diff > 0 ? '#2563EB' : '#DC2626');

        return `
            <tr data-index="${idx}">
                <td style="font-weight:600;">
                    ${escapeHtml(it.name || 'Candidate')}
                    ${it.confidence ? `<span style="font-size:0.75rem; color:var(--text-muted);"> (${Math.round(it.confidence * 100)}%)</span>` : ''}
                </td>
                <td>
                    ${isMatched ? `<span style="color:#16A34A; font-weight:700;"><i class="fas fa-check-circle"></i> ${escapeHtml(cm.product_name)}</span>` : `<span style="color:#D97706;"><i class="fas fa-question-circle"></i> ${escapeHtml(it.status || 'New Candidate')}</span>`}
                </td>
                <td style="font-weight:600;">${currentStock}</td>
                <td>
                    <span style="font-weight:700; color:var(--text-primary);">${observed}</span>
                    <span style="font-size:0.75rem; color:var(--text-muted); font-style:italic;">(est)</span>
                </td>
                <td style="font-weight:700; color:${diffColor};">${isMatched ? diffText : '—'}</td>
                <td>
                    <input type="number" class="shelf-confirmed-qty" data-index="${idx}" value="${observed}" min="0" step="any" style="width:80px; padding:4px 6px; font-size:0.85rem; border:1px solid var(--border-color); border-radius:var(--radius-sm);">
                </td>
                <td>
                    <label style="display:flex; align-items:center; gap:6px; font-size:0.85rem; cursor:pointer;">
                        <input type="checkbox" class="shelf-apply-check" data-index="${idx}" ${isMatched ? 'checked' : ''}>
                        <span>Apply</span>
                    </label>
                </td>
            </tr>
        `;
    }).join('');

    card.scrollIntoView({ behavior: 'smooth' });
}

async function applyShelfAuditAdjustments() {
    if (!currentShelfScanData) {
        alert('No active shelf scan data found.');
        return;
    }

    const items = currentShelfScanData.detected_items || [];
    const checkBoxes = document.querySelectorAll('.shelf-apply-check');
    const adjustments = [];

    checkBoxes.forEach(cb => {
        if (cb.checked) {
            const idx = parseInt(cb.dataset.index);
            const it = items[idx];
            if (it && it.catalog_match && it.catalog_match.matched && it.catalog_match.product_id) {
                const qtyInput = document.querySelector(`.shelf-confirmed-qty[data-index="${idx}"]`);
                const confirmedQty = qtyInput ? parseFloat(qtyInput.value) : it.observed_count;
                adjustments.push({
                    product_id: it.catalog_match.product_id,
                    current_stock: it.catalog_match.current_stock,
                    observed_count: it.observed_count,
                    confirmed_quantity: confirmedQty,
                    discrepancy: confirmedQty - (it.catalog_match.current_stock || 0),
                    matched_product: it.catalog_match.product_name
                });
            }
        }
    });

    if (adjustments.length === 0) {
        alert('No matched products selected for adjustment. Please check "Apply" next to products you wish to update.');
        return;
    }

    // STRICT CONFIRMATION GUARD
    const confirmMessage = `CONFIRMATION GUARD:\n\nYou are about to apply ${adjustments.length} physical stock adjustment(s) to your dukaan inventory.\n\nDo you want to proceed?`;
    if (!confirm(confirmMessage)) {
        return;
    }

    const token = localStorage.getItem('shopo_auth_token');
    const storeId = document.getElementById('shelfScanStoreSelect')?.value;

    try {
        const res = await fetch('/api/shelf-scanner/confirm', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                scan_id: currentShelfScanData.scan_id,
                store_id: storeId,
                confirmed: true,
                adjustments: adjustments,
                audit_notes: 'Confirmed via Smart Shelf Scanner review'
            })
        });
        const json = await res.json();
        if (json.success) {
            alert(`Audit applied successfully! ${adjustments.length} product(s) updated in inventory.`);
            clearShelfScan();
            fetchInventory();
            fetchShelfScansHistory();
        } else {
            alert(json.message || 'Failed to apply adjustments.');
        }
    } catch (e) {
        console.error('Error applying shelf audit adjustments:', e);
        alert('Network error applying shelf adjustments.');
    }
}

async function fetchShelfScansHistory() {
    const token = localStorage.getItem('shopo_auth_token');
    const listEl = document.getElementById('shelfScansHistoryList');
    if (!listEl) return;

    try {
        const res = await fetch('/api/shelf-scanner/scans', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const json = await res.json();
        if (json.success && json.data) {
            const scans = json.data.scans || [];
            if (scans.length === 0) {
                listEl.textContent = 'No shelf audits performed yet.';
                return;
            }

            listEl.innerHTML = scans.map(sc => {
                const d = new Date(sc.created_at);
                const dateStr = d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) + ' ' + d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
                const statusColor = sc.status === 'confirmed' ? '#16A34A' : '#D97706';
                return `
                    <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 12px; border-bottom:1px solid var(--border-color); font-size:0.85rem;">
                        <div>
                            <strong>Scan #${sc.id}</strong> &bull; <span style="color:var(--text-muted);">${dateStr}</span>
                            <div style="color:var(--text-secondary); margin-top:2px;">
                                ${sc.detected_count || 0} items detected &bull; Store: ${escapeHtml(sc.store_name || sc.store_id || 'Primary')}
                            </div>
                        </div>
                        <span class="badge" style="background:#F1F5F9; color:${statusColor}; font-weight:700; padding:3px 8px; border:1px solid var(--border-color);">
                            ${escapeHtml(sc.status)}
                        </span>
                    </div>
                `;
            }).join('');
        }
    } catch (e) {
        console.error('Error fetching shelf scans history:', e);
    }
}

// ════════════════════════════════════════════════════════════════
// GROUP C: MARKET & GROWTH CONTROLLERS
// ════════════════════════════════════════════════════════════════

// ────────────────────────────────────────────────────────────────
// 1. AI Competitor Intelligence
// ────────────────────────────────────────────────────────────────

let currentCompetitorLandscape = null;

async function initCompetitorView() {
    loadCompetitorLandscape();
}

async function loadCompetitorLandscape() {
    const token = localStorage.getItem('shopo_auth_token');
    const tableBody = document.getElementById('competitorTableBody');
    if (tableBody) {
        tableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:var(--text-muted);"><i class="fas fa-spinner fa-spin"></i> Analyzing competitor prices & verified Mandi benchmarks...</td></tr>';
    }

    try {
        const resp = await fetch('/api/competitor/landscape', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        const res = await resp.json();
        if (!res.success) {
            if (tableBody) tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:#DC2626; padding:20px;">${escapeHtml(res.message || 'Failed to load competitor data.')}</td></tr>`;
            return;
        }

        const data = res.data;
        currentCompetitorLandscape = data;
        renderCompetitorLandscape(data);
        loadUserCompetitorBenchmarks();
    } catch (e) {
        console.error('Error fetching competitor landscape:', e);
        if (tableBody) tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:#DC2626; padding:20px;">Network error loading competitor landscape.</td></tr>`;
    }
}

function renderCompetitorLandscape(data) {
    // Summary counts
    const s = data.summary || {};
    const mgEl = document.getElementById('compMarginGainCount');
    const hrEl = document.getElementById('compHigherRiskCount');
    const cpEl = document.getElementById('compCompetitiveCount');
    const ndEl = document.getElementById('compNoDataCount');

    if (mgEl) mgEl.textContent = s.margin_gain_opportunities || 0;
    if (hrEl) hrEl.textContent = s.higher_price_risks || 0;
    if (cpEl) cpEl.textContent = s.competitive_count || 0;
    if (ndEl) ndEl.textContent = s.no_data_count || 0;

    // Insights
    const insEn = document.getElementById('compInsightEn');
    const insHi = document.getElementById('compInsightHi');
    if (insEn) insEn.textContent = data.overall_insight_en || 'Pricing landscape updated.';
    if (insHi) insHi.textContent = data.overall_insight_hi || 'प्रतिस्पर्धी विश्लेषण अद्यतन किया गया।';

    // Results table
    const tableBody = document.getElementById('competitorTableBody');
    if (!tableBody) return;

    const results = data.results || [];
    if (results.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:var(--text-muted);">No products found in your inventory to benchmark. Add items in Stock tab.</td></tr>';
        return;
    }

    tableBody.innerHTML = results.map(item => {
        let oppBadge = '';
        let diffText = '--';

        if (!item.data_available) {
            oppBadge = '<span class="badge" style="background:#F3F4F6; color:#6B7280; border:1px solid #D1D5DB;">Data Unavailable</span>';
        } else if (item.opportunity_type === 'margin_gain_opportunity') {
            oppBadge = '<span class="badge" style="background:#ECFDF5; color:#065F46; border:1px solid #A7F3D0; font-weight:700;"><i class="fas fa-arrow-up"></i> Margin Gain</span>';
            diffText = `<span style="color:#16A34A; font-weight:700;">+₹${item.price_diff_rs} (+${item.price_diff_pct}%)</span>`;
        } else if (item.opportunity_type === 'higher_price_risk') {
            oppBadge = '<span class="badge" style="background:#FEF2F2; color:#991B1B; border:1px solid #FECACA; font-weight:700;"><i class="fas fa-arrow-down"></i> High Price Risk</span>';
            diffText = `<span style="color:#DC2626; font-weight:700;">₹${item.price_diff_rs} (${item.price_diff_pct}%)</span>`;
        } else {
            oppBadge = '<span class="badge" style="background:#EFF6FF; color:#1D4ED8; border:1px solid #BFDBFE;">Market Parity</span>';
            diffText = `<span style="color:#2563EB;">₹${item.price_diff_rs} (${item.price_diff_pct}%)</span>`;
        }

        const compPriceText = item.data_available ? `₹${parseFloat(item.competitor_price).toFixed(2)}` : '<span style="color:var(--text-muted);">Pending</span>';
        const confBadge = item.data_available
            ? (item.match_confidence === 'exact'
                ? '<span class="badge" style="background:#F0FDF4; color:#15803D; font-size:0.78rem;">Exact Match</span>'
                : '<span class="badge" style="background:#FFFBEB; color:#B45309; font-size:0.78rem;">Approximate</span>')
            : '--';

        const sourceDesc = item.benchmarks && item.benchmarks.length > 0
            ? `${escapeHtml(item.benchmarks[0].source)}`
            : '<span style="color:var(--text-muted);">No verified source</span>';

        return `
            <tr>
                <td>
                    <strong>${escapeHtml(item.product_name)}</strong>
                    <div style="font-size:0.8rem; color:var(--text-muted);">${escapeHtml(item.category || 'General')} &bull; ${escapeHtml(item.unit || 'unit')}</div>
                </td>
                <td><strong style="color:var(--text-primary);">₹${parseFloat(item.selling_price).toFixed(2)}</strong></td>
                <td><strong>${compPriceText}</strong></td>
                <td>${diffText}</td>
                <td>${oppBadge}</td>
                <td>${confBadge}</td>
                <td style="font-size:0.82rem; color:var(--text-secondary); max-width:200px;">
                    <div>${sourceDesc}</div>
                    <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">${escapeHtml(item.insight_en)}</div>
                </td>
            </tr>
        `;
    }).join('');
}

async function loadUserCompetitorBenchmarks() {
    const token = localStorage.getItem('shopo_auth_token');
    const container = document.getElementById('userBenchmarksList');
    if (!container) return;

    try {
        const resp = await fetch('/api/competitor/benchmarks', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();
        if (!res.success || !res.data || res.data.length === 0) {
            container.innerHTML = '<div style="color:var(--text-muted);">No local observations recorded yet. Click "Record Local Observation" to log competitor shelf prices.</div>';
            return;
        }

        container.innerHTML = res.data.map(b => `
            <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 14px; border-bottom:1px solid var(--border-color); font-size:0.88rem;">
                <div>
                    <strong>${escapeHtml(b.competitor_name)}</strong> &bull; <span style="color:var(--text-primary); font-weight:700;">₹${parseFloat(b.observed_price).toFixed(2)}</span>
                    <span style="color:var(--text-muted);">for ${escapeHtml(b.product_name)} (${escapeHtml(b.location || 'Local Area')})</span>
                    ${b.notes ? `<div style="font-size:0.8rem; color:var(--text-secondary); margin-top:2px;">"${escapeHtml(b.notes)}"</div>` : ''}
                </div>
                <button type="button" class="btn-dash btn-dash-secondary" style="padding:4px 8px; color:#DC2626; border-color:#FCA5A5;" onclick="deleteCompetitorObservation('${b.id}')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `).join('');
    } catch (e) {
        console.error('Error loading user benchmarks:', e);
    }
}

async function handleRecordCompetitorObservation(e) {
    e.preventDefault();
    const token = localStorage.getItem('shopo_auth_token');
    const payload = {
        competitor_name: document.getElementById('obsCompetitorName').value.trim(),
        product_name: document.getElementById('obsProductName').value.trim(),
        competitor_price: parseFloat(document.getElementById('obsPrice').value),
        match_confidence: document.getElementById('obsMatchType').value,
        category: document.getElementById('obsCategory').value.trim() || 'General',
        location: document.getElementById('obsLocation').value.trim() || 'Local Area',
        notes: document.getElementById('obsNotes').value.trim()
    };

    try {
        const resp = await fetch('/api/competitor/benchmarks', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });
        const res = await resp.json();
        if (res.success) {
            closeModal('addCompetitorModal');
            showToast('Observation recorded successfully! / निरीक्षण सुरक्षित हुआ।');
            loadCompetitorLandscape();
        } else {
            alert(res.message || 'Failed to save observation.');
        }
    } catch (err) {
        console.error('Error saving observation:', err);
        alert('Network error saving competitor observation.');
    }
}

async function deleteCompetitorObservation(id) {
    if (!confirm('Delete this competitor observation? / क्या आप इसे हटाना चाहते हैं?')) return;
    const token = localStorage.getItem('shopo_auth_token');
    try {
        const resp = await fetch(`/api/competitor/benchmarks/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();
        if (res.success) {
            showToast('Observation deleted.');
            loadCompetitorLandscape();
        }
    } catch (e) {
        console.error('Error deleting observation:', e);
    }
}


// ────────────────────────────────────────────────────────────────
// 2. Customer Demand Listening
// ────────────────────────────────────────────────────────────────

let currentDemandAnalysis = null;

async function initDemandView() {
    loadCustomerDemandAnalysis();
}

async function loadCustomerDemandAnalysis() {
    const token = localStorage.getItem('shopo_auth_token');
    const days = document.getElementById('demandDaysSelect')?.value || 30;
    const tableBody = document.getElementById('demandTableBody');

    if (tableBody) {
        tableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:var(--text-muted);"><i class="fas fa-spinner fa-spin"></i> Calculating sales velocity and customer demand trends...</td></tr>';
    }

    try {
        const resp = await fetch(`/api/demand/analysis?days=${days}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();
        if (!res.success) {
            if (tableBody) tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:#DC2626; padding:20px;">${escapeHtml(res.message || 'Failed to load demand analysis.')}</td></tr>`;
            return;
        }

        const data = res.data;
        currentDemandAnalysis = data;
        renderCustomerDemand(data);
    } catch (e) {
        console.error('Error loading demand analysis:', e);
        if (tableBody) tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; color:#DC2626; padding:20px;">Network error loading demand analysis.</td></tr>`;
    }
}

function renderCustomerDemand(data) {
    const s = data.summary || {};
    const starEl = document.getElementById('demandStarCount');
    const stEl = document.getElementById('demandStockoutCount');
    const reqEl = document.getElementById('demandRequestsCount');
    const lostEl = document.getElementById('demandLostRev');

    if (starEl) starEl.textContent = s.star_seller_count || 0;
    if (stEl) stEl.textContent = s.stockout_suppressed_count || 0;
    if (reqEl) reqEl.textContent = s.total_demand_requests_logged || 0;
    if (lostEl) lostEl.textContent = `₹${(s.estimated_lost_revenue_inr || 0).toLocaleString('en-IN')}`;

    const takeEn = document.getElementById('demandTakeawayEn');
    const takeHi = document.getElementById('demandTakeawayHi');
    if (takeEn) takeEn.textContent = data.overall_takeaway_en || 'Demand metrics computed.';
    if (takeHi) takeHi.textContent = data.overall_takeaway_hi || 'मांग विश्लेषण अद्यतन हुआ।';

    // Product Demand Table
    const tableBody = document.getElementById('demandTableBody');
    if (tableBody) {
        const items = data.items || [];
        if (items.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:var(--text-muted);">No products found to analyze demand.</td></tr>';
        } else {
            tableBody.innerHTML = items.map(itm => {
                let tierBadge = '';
                if (itm.demand_tier === 'star_seller') {
                    tierBadge = '<span class="badge" style="background:#FEF9C3; color:#854D0E; border:1px solid #FDE047; font-weight:700;"><i class="fas fa-star"></i> Star Seller</span>';
                } else if (itm.demand_tier === 'stockout_suppressed') {
                    tierBadge = '<span class="badge" style="background:#FEF2F2; color:#991B1B; border:1px solid #FECACA; font-weight:700;"><i class="fas fa-exclamation-circle"></i> Stockout Suppressed</span>';
                } else if (itm.demand_tier === 'declining') {
                    tierBadge = '<span class="badge" style="background:#F3F4F6; color:#4B5563; border:1px solid #D1D5DB;">Declining</span>';
                } else if (itm.demand_tier === 'low_data') {
                    tierBadge = '<span class="badge" style="background:#F8FAFC; color:#64748B;">Limited Data</span>';
                } else {
                    tierBadge = '<span class="badge" style="background:#ECFDF5; color:#065F46;">Consistent</span>';
                }

                const stockPill = itm.is_stocked_out
                    ? '<span class="badge" style="background:#FEE2E2; color:#991B1B; font-weight:700;">OUT OF STOCK</span>'
                    : `<strong>${itm.current_stock}</strong> ${escapeHtml(itm.unit)}`;

                return `
                    <tr>
                        <td>
                            <strong>${escapeHtml(itm.product_name)}</strong>
                            <div style="font-size:0.8rem; color:var(--text-muted);">${escapeHtml(itm.category || 'General')}</div>
                        </td>
                        <td>${stockPill}</td>
                        <td><strong>${itm.velocity_per_day}</strong> ${escapeHtml(itm.unit)}/day</td>
                        <td>${itm.total_units_sold} ${escapeHtml(itm.unit)}</td>
                        <td><strong>₹${parseFloat(itm.total_revenue).toFixed(2)}</strong></td>
                        <td>${tierBadge}</td>
                        <td style="font-size:0.82rem; color:var(--text-secondary); max-width:220px;">
                            ${escapeHtml(itm.insight_en)}
                        </td>
                    </tr>
                `;
            }).join('');
        }
    }

    // Customer Requests Table
    const reqBody = document.getElementById('demandRequestsTableBody');
    if (reqBody) {
        const requests = data.demand_requests || [];
        if (requests.length === 0) {
            reqBody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:var(--text-muted);">No customer demand requests logged yet. Use "Log Customer Request" above when a customer asks for an unstocked item.</td></tr>';
        } else {
            reqBody.innerHTML = requests.map(r => {
                const urgencyColor = r.urgency === 'high' ? '#DC2626' : r.urgency === 'medium' ? '#CA8A04' : '#6B7280';
                return `
                    <tr>
                        <td><strong>${escapeHtml(r.product_name)}</strong></td>
                        <td>${escapeHtml(r.category || 'General')}</td>
                        <td><span class="badge" style="background:#EFF6FF; color:#1D4ED8; font-weight:700;">${r.request_count} customers</span></td>
                        <td>${r.estimated_budget ? `₹${parseFloat(r.estimated_budget).toFixed(2)}` : '--'}</td>
                        <td style="font-size:0.82rem; color:var(--text-secondary);">${escapeHtml(r.customer_notes || '--')}</td>
                        <td>
                            <select onchange="updateCustomerDemandStatus('${r.id}', this.value)" style="padding:3px 6px; border-radius:4px; font-size:0.82rem; border:1px solid var(--border-color);">
                                <option value="logged" ${r.status === 'logged' ? 'selected' : ''}>Logged</option>
                                <option value="sourcing" ${r.status === 'sourcing' ? 'selected' : ''}>Sourcing</option>
                                <option value="stocked" ${r.status === 'stocked' ? 'selected' : ''}>Stocked</option>
                                <option value="declined" ${r.status === 'declined' ? 'selected' : ''}>Declined</option>
                            </select>
                        </td>
                        <td>
                            <button type="button" class="btn-dash btn-dash-secondary" style="padding:3px 8px; color:#DC2626; border-color:#FCA5A5;" onclick="deleteCustomerDemandRequest('${r.id}')">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
        }
    }
}

async function handleLogCustomerDemand(e) {
    e.preventDefault();
    const token = localStorage.getItem('shopo_auth_token');
    const payload = {
        product_name: document.getElementById('demandReqProductName').value.trim(),
        request_count: parseInt(document.getElementById('demandReqCount').value, 10) || 1,
        estimated_budget: parseFloat(document.getElementById('demandReqBudget').value) || 0,
        category: document.getElementById('demandReqCategory').value.trim() || 'General',
        urgency: document.getElementById('demandReqUrgency').value,
        customer_notes: document.getElementById('demandReqNotes').value.trim()
    };

    try {
        const resp = await fetch('/api/demand/requests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });
        const res = await resp.json();
        if (res.success) {
            closeModal('logDemandModal');
            showToast('Customer demand request logged! / ग्राहक मांग दर्ज हुई।');
            loadCustomerDemandAnalysis();
        } else {
            alert(res.message || 'Failed to log demand request.');
        }
    } catch (err) {
        console.error('Error logging demand:', err);
        alert('Network error logging demand request.');
    }
}

async function updateCustomerDemandStatus(id, newStatus) {
    const token = localStorage.getItem('shopo_auth_token');
    try {
        await fetch(`/api/demand/requests/${id}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ status: newStatus })
        });
        showToast('Demand status updated.');
    } catch (e) {
        console.error('Error updating demand status:', e);
    }
}

async function deleteCustomerDemandRequest(id) {
    if (!confirm('Delete this demand request?')) return;
    const token = localStorage.getItem('shopo_auth_token');
    try {
        const resp = await fetch(`/api/demand/requests/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();
        if (res.success) {
            showToast('Demand request deleted.');
            loadCustomerDemandAnalysis();
        }
    } catch (e) {
        console.error('Error deleting demand request:', e);
    }
}


// ────────────────────────────────────────────────────────────────
// 3. AI Negotiation Coach
// ────────────────────────────────────────────────────────────────

let currentNegotiationResult = null;

async function initNegotiationView() {
    loadNegotiationHistory();
}

async function handleGenerateNegotiation(e) {
    e.preventDefault();
    const token = localStorage.getItem('shopo_auth_token');
    const btn = document.getElementById('btnGenerateNeg');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating Strategy...';
    }

    const payload = {
        supplier_name: document.getElementById('negSupplierName').value.trim(),
        product_name: document.getElementById('negProductName').value.trim(),
        quoted_price: parseFloat(document.getElementById('negQuotedPrice').value),
        quantity: parseFloat(document.getElementById('negQuantity').value) || 1,
        scenario: document.getElementById('negScenario').value,
        target_price: parseFloat(document.getElementById('negTargetPrice').value) || 0
    };

    try {
        const resp = await fetch('/api/negotiation/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });
        const res = await resp.json();
        if (!res.success) {
            alert(res.message || 'Failed to generate negotiation plan.');
            return;
        }

        const data = res.data;
        currentNegotiationResult = data;

        // Render card
        document.getElementById('negResTargetPrice').textContent = `₹${data.target_price.toFixed(2)}`;
        document.getElementById('negResQuotedPrice').textContent = `Quoted: ₹${data.quoted_price.toFixed(2)}`;
        document.getElementById('negResDiscountPct').textContent = `${data.target_discount_pct}% Off`;
        document.getElementById('negResUnitSavings').textContent = `Saving ₹${data.unit_savings.toFixed(2)}/unit`;
        document.getElementById('negResTotalSavings').textContent = `₹${data.total_savings.toFixed(2)}`;
        document.getElementById('negResDealValue').textContent = `Total deal: ₹${data.total_deal_value.toFixed(2)}`;

        document.getElementById('negResRationaleEn').textContent = data.rationale_en;
        document.getElementById('negResRationaleHi').textContent = data.rationale_hi;

        document.getElementById('negScriptHi').textContent = data.script_hi;
        document.getElementById('negScriptEn').textContent = data.script_en;
        document.getElementById('negScriptHinglish').textContent = data.script_hinglish;

        const resCard = document.getElementById('negResultCard');
        if (resCard) {
            resCard.style.display = 'block';
            resCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    } catch (err) {
        console.error('Error generating negotiation:', err);
        alert('Network error generating negotiation plan.');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-magic"></i> Generate Persuasive Scripts / रणनीति तैयार करें';
        }
    }
}

function copyNegotiationScript(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    navigator.clipboard.writeText(el.textContent).then(() => {
        showToast('Script copied to clipboard! Ready to paste in WhatsApp/SMS.');
    }).catch(() => {
        showToast('Script text ready to copy.');
    });
}

async function saveCurrentNegotiationScenario() {
    if (!currentNegotiationResult) return;
    const token = localStorage.getItem('shopo_auth_token');

    try {
        const resp = await fetch('/api/negotiation/scenarios', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                supplier_name: currentNegotiationResult.supplier_name,
                product_name: currentNegotiationResult.product_name,
                quoted_price: currentNegotiationResult.quoted_price,
                target_price: currentNegotiationResult.target_price,
                quantity: currentNegotiationResult.quantity,
                scenario: currentNegotiationResult.scenario,
                script_hi: currentNegotiationResult.script_hi,
                script_en: currentNegotiationResult.script_en,
                script_hinglish: currentNegotiationResult.script_hinglish,
                assumptions_notes: currentNegotiationResult.rationale_en
            })
        });
        const res = await resp.json();
        if (res.success) {
            showToast('Negotiation draft saved to history.');
            loadNegotiationHistory();
        } else {
            alert(res.message || 'Failed to save negotiation.');
        }
    } catch (e) {
        console.error('Error saving negotiation:', e);
    }
}

async function loadNegotiationHistory() {
    const token = localStorage.getItem('shopo_auth_token');
    const container = document.getElementById('savedNegotiationsList');
    if (!container) return;

    try {
        const resp = await fetch('/api/negotiation/scenarios', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();
        if (!res.success || !res.data || res.data.length === 0) {
            container.innerHTML = '<div style="color:var(--text-muted);">No saved negotiation scenarios yet.</div>';
            return;
        }

        container.innerHTML = res.data.map(n => `
            <div style="display:flex; justify-content:space-between; align-items:center; padding:12px 14px; border-bottom:1px solid var(--border-color); font-size:0.88rem;">
                <div>
                    <strong>${escapeHtml(n.supplier_name)}</strong> &bull; ${escapeHtml(n.product_name)} (${n.quantity} units)
                    <div style="color:var(--text-secondary); margin-top:2px;">
                        Quoted ₹${n.quoted_price} ➔ <strong>Target ₹${n.target_price}</strong> &bull; Scenario: ${escapeHtml(n.scenario.replace('_', ' '))}
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span class="badge" style="background:#EFF6FF; color:#1D4ED8; font-weight:700;">${escapeHtml(n.status)}</span>
                    <button type="button" class="btn-dash btn-dash-secondary" style="padding:4px 8px; color:#DC2626; border-color:#FCA5A5;" onclick="deleteNegotiationScenario('${n.id}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        console.error('Error loading negotiation history:', e);
    }
}

async function deleteNegotiationScenario(id) {
    if (!confirm('Delete this negotiation scenario?')) return;
    const token = localStorage.getItem('shopo_auth_token');
    try {
        const resp = await fetch(`/api/negotiation/scenarios/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();
        if (res.success) {
            showToast('Negotiation scenario deleted.');
            loadNegotiationHistory();
        }
    } catch (e) {
        console.error('Error deleting negotiation scenario:', e);
    }
}


// ────────────────────────────────────────────────────────────────
// 4. AI Business Translator
// ────────────────────────────────────────────────────────────────

let currentTranslatorTarget = 'hi';

function initTranslatorView() {
    setTranslatorTarget('hi');
}

function setTranslatorTarget(lang) {
    currentTranslatorTarget = lang;
    ['btnTransHi', 'btnTransHinglish', 'btnTransEn'].forEach(id => {
        const btn = document.getElementById(id);
        if (btn) btn.classList.remove('active');
    });

    if (lang === 'hi') {
        document.getElementById('btnTransHi')?.classList.add('active');
    } else if (lang === 'hinglish') {
        document.getElementById('btnTransHinglish')?.classList.add('active');
    } else {
        document.getElementById('btnTransEn')?.classList.add('active');
    }
}

function loadTranslatorTemplate(type) {
    const textarea = document.getElementById('transSourceText');
    const ctxSelect = document.getElementById('transContext');
    if (!textarea) return;

    if (type === 'payment') {
        textarea.value = 'Dear customer, please pay outstanding balance of ₹2,450 for your 10 kg Basmati Rice purchase by 2026-10-20.';
        if (ctxSelect) ctxSelect.value = 'customer_notes';
        setTranslatorTarget('hi');
    } else if (type === 'sale') {
        textarea.value = 'Sold 15 pcs Tata Tea at ₹120 each. Total amount received ₹1,800 via UPI.';
        if (ctxSelect) ctxSelect.value = 'invoice_receipt';
        setTranslatorTarget('hi');
    } else if (type === 'damaged') {
        textarea.value = 'Consignment arrived with 4 damaged bags out of 50 bags. Requesting ₹1,600 credit note on next bill.';
        if (ctxSelect) ctxSelect.value = 'business_query';
        setTranslatorTarget('hinglish');
    } else if (type === 'order') {
        textarea.value = 'We require quotation for 100 quintals of FAQ Grade Wheat at Mandi benchmark rate for delivery by Friday.';
        if (ctxSelect) ctxSelect.value = 'business_query';
        setTranslatorTarget('hi');
    }
}

async function executeBusinessTranslation() {
    const text = document.getElementById('transSourceText')?.value.trim();
    if (!text) {
        alert('Please enter or paste business text to translate.');
        return;
    }

    const token = localStorage.getItem('shopo_auth_token');
    const context = document.getElementById('transContext')?.value || 'business_query';
    const outputEl = document.getElementById('transOutputText');
    const entitiesBar = document.getElementById('transEntitiesBar');
    const btn = document.getElementById('btnRunTranslate');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Translating...';
    }

    try {
        const resp = await fetch('/api/translator/translate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                text: text,
                target_lang: currentTranslatorTarget,
                context: context
            })
        });
        const res = await resp.json();
        if (!res.success) {
            if (outputEl) outputEl.textContent = res.message || 'Translation failed.';
            return;
        }

        const d = res.data;
        if (outputEl) outputEl.textContent = d.translated_text;

        const langBadge = document.getElementById('transDetectedLang');
        if (langBadge) langBadge.textContent = `Source: ${d.source_language.toUpperCase()}`;

        const provLabel = document.getElementById('transProviderLabel');
        if (provLabel) provLabel.textContent = `Provider: ${d.provider} (${d.confidence} confidence)`;

        // Render preserved entities
        if (entitiesBar) {
            if (d.preserved_entities && d.preserved_entities.length > 0) {
                entitiesBar.innerHTML = d.preserved_entities.map(ent => `
                    <span class="badge" style="background:#DCFCE7; color:#166534; border:1px solid #86EFAC; font-weight:700; padding:4px 10px;">
                        <i class="fas fa-check"></i> ${escapeHtml(ent)}
                    </span>
                `).join('');
            } else {
                entitiesBar.innerHTML = '<span style="color:#166534;">No numerical quantities detected. General semantic translation applied.</span>';
            }
        }
    } catch (e) {
        console.error('Error executing translation:', e);
        if (outputEl) outputEl.textContent = 'Network error contacting translator service.';
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-language"></i> Translate / अनुवाद करें';
        }
    }
}

function copyTranslatedText() {
    const text = document.getElementById('transOutputText')?.textContent;
    if (!text || text.includes('Translation will appear here')) return;
    navigator.clipboard.writeText(text).then(() => {
        showToast('Translated text copied to clipboard!');
    }).catch(() => {
        showToast('Text copied.');
    });
}


// ════════════════════════════════════════════════════════════
// GROUP D: AI BUSINESS AUTOPILOT CONTROLLER
// ════════════════════════════════════════════════════════════

let activeAutopilotActions = [];

async function loadAutopilotView() {
    const token = localStorage.getItem('shopo_auth_token');
    const container = document.getElementById('autopilotActionsContainer');
    const emptyState = document.getElementById('autopilotEmptyState');

    try {
        // Fetch status counts
        const statusResp = await fetch('/api/autopilot/status', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const statusData = await statusResp.json();
        if (statusData.success && statusData.summary) {
            const s = statusData.summary;
            document.getElementById('apCountProposed').textContent = s.proposed;
            document.getElementById('apCountApproved').textContent = s.approved;
            document.getElementById('apCountExecuted').textContent = s.executed;
        }

        // Fetch proposed recommendations
        const recResp = await fetch('/api/autopilot/recommendations?status=proposed', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const recData = await recResp.json();

        if (recData.success && recData.actions && recData.actions.length > 0) {
            activeAutopilotActions = recData.actions;
            if (emptyState) emptyState.style.display = 'none';

            // Render action cards
            const cardsHtml = recData.actions.map(act => {
                const pColor = act.priority === 'urgent' ? '#EF4444' : act.priority === 'high' ? '#F59E0B' : '#3B82F6';
                const pBg = act.priority === 'urgent' ? '#FEF2F2' : act.priority === 'high' ? '#FFFBEB' : '#EFF6FF';
                return `
                    <div class="card" style="border-left: 4px solid ${pColor}; padding:18px 20px; background:var(--bg-card); border-radius:var(--radius-lg); box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:10px;">
                            <div>
                                <span class="badge" style="background:${pBg}; color:${pColor}; font-weight:700; margin-bottom:6px; display:inline-block;">
                                    ${escapeHtml(act.priority.toUpperCase())} PRIORITY &bull; ${escapeHtml(act.category.toUpperCase())}
                                </span>
                                <h3 style="font-size:1.1rem; color:var(--text-primary); margin:0;">${escapeHtml(act.title)}</h3>
                            </div>
                            <span class="badge" style="background:#F1F5F9; color:#475569; font-size:0.75rem;">
                                ${(act.confidence * 100).toFixed(0)}% Confidence
                            </span>
                        </div>
                        <p style="font-size:0.92rem; color:var(--text-secondary); line-height:1.5; margin-bottom:12px;">
                            ${escapeHtml(act.reason)}
                        </p>
                        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:10px; font-size:0.85rem; margin-bottom:14px;">
                            <div style="background:#F0FDF4; border:1px solid #DCFCE7; padding:8px 12px; border-radius:var(--radius-md); color:#166534;">
                                <strong>Expected Outcome:</strong> ${escapeHtml(act.expected_outcome || 'Improves store efficiency')}
                            </div>
                            <div style="background:#FFFBEB; border:1px solid #FEF3C7; padding:8px 12px; border-radius:var(--radius-md); color:#92400E;">
                                <strong>Uncertainty / Note:</strong> ${escapeHtml(act.uncertainty_notes || 'Verify current lead times')}
                            </div>
                        </div>
                        <div style="display:flex; justify-content:flex-end; gap:8px;">
                            <button type="button" class="btn-dash btn-dash-primary" onclick="openAutopilotActionModal('${act.id}')">
                                <i class="fas fa-eye"></i> Review & Approve / समीक्षा करें
                            </button>
                        </div>
                    </div>
                `;
            }).join('');

            container.innerHTML = cardsHtml;
        } else {
            activeAutopilotActions = [];
            container.innerHTML = '';
            if (emptyState) emptyState.style.display = 'block';
            container.appendChild(emptyState);
        }
    } catch (e) {
        console.error('Error loading Autopilot view:', e);
    }
}

async function triggerAutopilotScan() {
    const token = localStorage.getItem('shopo_auth_token');
    showToast('Running proactive store scan...');
    try {
        const resp = await fetch('/api/autopilot/scan', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();
        if (res.success) {
            showToast(`Scan complete. Found ${res.data.newly_generated_in_scan} new tasks.`);
            loadAutopilotView();
            updateNotificationBadge();
        } else {
            showToast('Scan error: ' + (res.error || 'Failed'));
        }
    } catch (e) {
        console.error('Error triggering scan:', e);
        showToast('Network error triggering scan.');
    }
}

async function toggleAutopilotAuditTrail() {
    const card = document.getElementById('autopilotAuditTrailCard');
    const list = document.getElementById('autopilotAuditTrailList');
    if (!card) return;

    if (card.style.display === 'block') {
        card.style.display = 'none';
        return;
    }

    const token = localStorage.getItem('shopo_auth_token');
    try {
        const resp = await fetch('/api/autopilot/audit-trail', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();
        if (res.success && res.audit_trail) {
            if (res.audit_trail.length === 0) {
                list.innerHTML = '<div style="color:var(--text-muted);">No audit log entries recorded yet.</div>';
            } else {
                list.innerHTML = res.audit_trail.slice(0, 15).map(t => `
                    <div style="padding:8px 12px; background:var(--bg-main); border-radius:var(--radius-sm); border:1px solid var(--border-color); display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <strong>${escapeHtml(t.actor)}</strong> &bull; Transitioned status:
                            <span class="badge" style="background:#F1F5F9; color:#475569;">${t.previous_status}</span> ➔
                            <span class="badge" style="background:#EFF6FF; color:#1D4ED8;">${t.new_status}</span>
                            <div style="color:var(--text-muted); font-size:0.8rem; margin-top:2px;">${escapeHtml(t.notes || '')}</div>
                        </div>
                        <span style="font-size:0.75rem; color:var(--text-muted);">${(t.created_at || '').slice(0, 19).replace('T', ' ')}</span>
                    </div>
                `).join('');
            }
            card.style.display = 'block';
        }
    } catch (e) {
        console.error('Error loading audit trail:', e);
    }
}

function openAutopilotActionModal(actionId) {
    const action = activeAutopilotActions.find(a => a.id === actionId);
    if (!action) return;

    document.getElementById('modalApActionId').value = action.id;
    document.getElementById('modalApTitle').textContent = action.title;
    document.getElementById('modalApBadge').textContent = `${action.priority.toUpperCase()} PRIORITY`;
    document.getElementById('modalApReason').textContent = action.reason;
    document.getElementById('modalApOutcome').textContent = action.expected_outcome || 'Operational efficiency improved';
    document.getElementById('modalApUncertainty').textContent = action.uncertainty_notes || 'Standard operational variance applies';

    const payloadEl = document.getElementById('modalApPayload');
    if (action.action_type === 'restock_order' && action.proposed_payload?.items) {
        payloadEl.innerHTML = action.proposed_payload.items.map(it => `
            <div style="display:flex; justify-content:space-between; padding:4px 0; border-bottom:1px dashed #E2E8F0;">
                <span><strong>${escapeHtml(it.product_name)}</strong> (Current: ${it.current_stock})</span>
                <span style="color:#16A34A; font-weight:700;">Order: +${it.proposed_order_qty} units</span>
            </div>
        `).join('');
    } else {
        payloadEl.textContent = JSON.stringify(action.proposed_payload || {}, null, 2);
    }

    // Toggle button states based on status
    const btnApprove = document.getElementById('btnModalApApprove');
    const btnExecute = document.getElementById('btnModalApExecute');
    if (action.status === 'approved') {
        if (btnApprove) btnApprove.style.display = 'none';
        if (btnExecute) btnExecute.style.display = 'inline-flex';
    } else {
        if (btnApprove) btnApprove.style.display = 'inline-flex';
        if (btnExecute) btnExecute.style.display = 'inline-flex';
    }

    openModal('autopilotActionModal');
}

async function submitAutopilotDecision(decision) {
    const actionId = document.getElementById('modalApActionId').value;
    if (!actionId) return;

    const token = localStorage.getItem('shopo_auth_token');
    showToast(`Submitting ${decision}...`);

    try {
        const resp = await fetch(`/api/autopilot/action/${actionId}/review`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                decision: decision,
                snooze_hours: 24,
                notes: `Action ${decision} by store manager in dashboard`
            })
        });
        const res = await resp.json();
        if (res.success) {
            closeModal('autopilotActionModal');
            showToast(res.message || `Action ${decision} completed successfully.`);
            loadAutopilotView();
            updateNotificationBadge();
        } else {
            showToast('Error: ' + (res.error || 'Action failed'));
        }
    } catch (e) {
        console.error('Error submitting action decision:', e);
        showToast('Network error processing decision.');
    }
}


// ════════════════════════════════════════════════════════════
// GROUP D: INTELLIGENT NOTIFICATION CENTER CONTROLLER
// ════════════════════════════════════════════════════════════

let currentNotifFilter = 'all';

async function loadNotificationsView(filter) {
    if (filter) currentNotifFilter = filter;
    const token = localStorage.getItem('shopo_auth_token');
    const listEl = document.getElementById('notificationsList');
    const emptyEl = document.getElementById('notificationsEmptyState');

    let url = '/api/notifications';
    if (currentNotifFilter === 'unread') {
        url += '?status=unread';
    } else if (currentNotifFilter !== 'all') {
        url += `?category=${currentNotifFilter}`;
    }

    try {
        const resp = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();

        if (res.success && res.notifications && res.notifications.length > 0) {
            if (emptyEl) emptyEl.style.display = 'none';

            listEl.innerHTML = res.notifications.map(n => {
                const sColor = n.severity === 'critical' ? '#EF4444' : n.severity === 'warning' ? '#F59E0B' : '#3B82F6';
                const sBg = n.severity === 'critical' ? '#FEF2F2' : n.severity === 'warning' ? '#FFFBEB' : '#EFF6FF';
                const isUnread = n.status === 'unread';

                return `
                    <div class="card" style="border-left: 4px solid ${sColor}; padding:14px 18px; background:var(--bg-card); border-radius:var(--radius-lg); ${isUnread ? 'border: 1px solid #CBD5E1; box-shadow: 0 2px 4px rgba(0,0,0,0.06);' : 'opacity:0.85;'}">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:10px;">
                            <div>
                                <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
                                    <span class="badge" style="background:${sBg}; color:${sColor}; font-weight:700; font-size:0.75rem;">
                                        ${escapeHtml(n.severity.toUpperCase())}
                                    </span>
                                    <span class="badge" style="background:#F1F5F9; color:#475569; font-size:0.75rem;">
                                        ${escapeHtml(n.category.toUpperCase())}
                                    </span>
                                    ${isUnread ? '<span class="badge" style="background:#EF4444; color:#fff; font-size:0.68rem; font-weight:700;">NEW</span>' : ''}
                                </div>
                                <h4 style="font-size:1rem; color:var(--text-primary); margin:0 0 4px 0;">${escapeHtml(n.title)}</h4>
                                <p style="font-size:0.88rem; color:var(--text-secondary); line-height:1.4; margin:0 0 8px 0;">${escapeHtml(n.message)}</p>
                            </div>
                            <span style="font-size:0.75rem; color:var(--text-muted); white-space:nowrap;">
                                ${(n.created_at || '').slice(0, 16).replace('T', ' ')}
                            </span>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px; border-top:1px dashed #E2E8F0; padding-top:8px;">
                            <div>
                                ${n.action_link ? `<button type="button" class="btn-dash btn-dash-secondary" style="font-size:0.8rem; padding:4px 10px;" onclick="switchNav('${n.action_link.replace('#view-', '')}')">Go to View</button>` : ''}
                            </div>
                            <div style="display:flex; gap:6px;">
                                ${isUnread ? `<button type="button" class="btn-dash btn-dash-secondary" style="font-size:0.8rem; padding:4px 10px;" onclick="markNotifRead('${n.id}')"><i class="fas fa-check"></i> Read</button>` : ''}
                                <button type="button" class="btn-dash btn-dash-secondary" style="font-size:0.8rem; padding:4px 10px;" onclick="snoozeNotif('${n.id}')"><i class="fas fa-clock"></i> Snooze 24h</button>
                                <button type="button" class="btn-dash btn-dash-secondary" style="font-size:0.8rem; padding:4px 10px; color:#DC2626;" onclick="dismissNotif('${n.id}')"><i class="fas fa-times"></i> Dismiss</button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            listEl.innerHTML = '';
            if (emptyEl) emptyEl.style.display = 'block';
            listEl.appendChild(emptyEl);
        }

        updateNotificationBadge();
    } catch (e) {
        console.error('Error loading notifications:', e);
    }
}

async function triggerNotificationScan() {
    const token = localStorage.getItem('shopo_auth_token');
    showToast('Scanning alerts across inventory and orders...');
    try {
        const resp = await fetch('/api/notifications/scan', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();
        if (res.success) {
            showToast(`Scan complete: ${res.data.total_active} active alerts.`);
            loadNotificationsView();
            updateNotificationBadge();
        }
    } catch (e) {
        console.error('Error scanning notifications:', e);
    }
}

async function updateNotificationBadge() {
    const badge = document.getElementById('headerNotifBadge');
    if (!badge) return;

    const token = localStorage.getItem('shopo_auth_token');
    if (!token) return;

    try {
        const resp = await fetch('/api/notifications?status=unread', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();
        if (res.success && res.unread_count > 0) {
            badge.textContent = res.unread_count;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    } catch (e) {
        // silent fail
    }
}

async function markNotifRead(id) {
    const token = localStorage.getItem('shopo_auth_token');
    try {
        await fetch(`/api/notifications/${id}/mark-read`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        loadNotificationsView();
    } catch (e) {
        console.error('Error marking read:', e);
    }
}

async function dismissNotif(id) {
    const token = localStorage.getItem('shopo_auth_token');
    try {
        await fetch(`/api/notifications/${id}/dismiss`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        showToast('Notification dismissed');
        loadNotificationsView();
    } catch (e) {
        console.error('Error dismissing notification:', e);
    }
}

async function snoozeNotif(id) {
    const token = localStorage.getItem('shopo_auth_token');
    try {
        await fetch(`/api/notifications/${id}/snooze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ hours: 24 })
        });
        showToast('Notification snoozed for 24 hours');
        loadNotificationsView();
    } catch (e) {
        console.error('Error snoozing notification:', e);
    }
}

function filterNotifications(filter) {
    document.querySelectorAll('.notif-filter-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.filter === filter);
    });
    loadNotificationsView(filter);
}

async function openNotifPreferencesModal() {
    const token = localStorage.getItem('shopo_auth_token');
    try {
        const resp = await fetch('/api/notifications/preferences', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();
        if (res.success && res.preferences) {
            const p = res.preferences;
            document.getElementById('prefStock').checked = !!p.stock_alerts;
            document.getElementById('prefExpiry').checked = !!p.expiry_alerts;
            document.getElementById('prefPayment').checked = !!p.payment_alerts;
            document.getElementById('prefAutopilot').checked = !!p.autopilot_alerts;
        }
    } catch (e) {
        console.error('Error loading preferences:', e);
    }
    openModal('notificationPreferencesModal');
}

async function saveNotificationPreferences() {
    const token = localStorage.getItem('shopo_auth_token');
    const prefs = {
        stock_alerts: document.getElementById('prefStock').checked ? 1 : 0,
        expiry_alerts: document.getElementById('prefExpiry').checked ? 1 : 0,
        payment_alerts: document.getElementById('prefPayment').checked ? 1 : 0,
        autopilot_alerts: document.getElementById('prefAutopilot').checked ? 1 : 0
    };

    try {
        const resp = await fetch('/api/notifications/preferences', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(prefs)
        });
        const res = await resp.json();
        if (res.success) {
            closeModal('notificationPreferencesModal');
            showToast('Preferences updated successfully.');
            triggerNotificationScan();
        }
    } catch (e) {
        console.error('Error saving preferences:', e);
    }
}


// ════════════════════════════════════════════════════════════
// GROUP D: BUSINESS MEMORY GRAPH CONTROLLER
// ════════════════════════════════════════════════════════════

async function loadMemoryGraphView() {
    const token = localStorage.getItem('shopo_auth_token');
    try {
        const resp = await fetch('/api/memory/graph', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();
        if (res.success && res.graph) {
            const g = res.graph;
            document.getElementById('memoryNodesCount').textContent = g.nodes_count;
            document.getElementById('memoryEdgesCount').textContent = g.edges_count;

            // Render entity pills
            const pillsEl = document.getElementById('memoryEntitiesPills');
            pillsEl.innerHTML = g.nodes.filter(n => n.id !== 'store_root').map(n => {
                const color = n.type === 'product' ? '#2563EB' : n.type === 'supplier' ? '#16A34A' : '#7C3AED';
                const bg = n.type === 'product' ? '#EFF6FF' : n.type === 'supplier' ? '#F0FDF4' : '#F5F3FF';
                return `
                    <span class="badge" style="background:${bg}; color:${color}; font-size:0.85rem; padding:6px 12px; cursor:pointer;" onclick="applyMemoryQuery('${escapeHtml(n.label)}')">
                        <i class="fas fa-${n.type === 'supplier' ? 'truck' : 'box'}"></i> ${escapeHtml(n.label)} (${n.type})
                    </span>
                `;
            }).join('');

            // Render table of recent memories
            const tbody = document.getElementById('memoryTableBody');
            tbody.innerHTML = (g.memories || []).slice(0, 15).map(m => `
                <tr>
                    <td><strong>${escapeHtml(m.entity_name)}</strong> <span style="font-size:0.75rem; color:var(--text-muted);">(${m.entity_type})</span></td>
                    <td>${escapeHtml(m.fact_value)}</td>
                    <td><span class="badge" style="background:#F1F5F9; color:#475569;">${escapeHtml(m.source_table)}</span></td>
                    <td>
                        <span class="badge" style="background:${m.fact_type === 'verified_record' ? '#DCFCE7' : '#FEF3C7'}; color:${m.fact_type === 'verified_record' ? '#166534' : '#92400E'};">
                            ${m.fact_type === 'verified_record' ? 'Verified Fact' : 'AI Derived'}
                        </span>
                    </td>
                    <td style="color:var(--text-muted);">${(m.event_timestamp || '').slice(0, 10)}</td>
                </tr>
            `).join('');
        }
    } catch (e) {
        console.error('Error loading memory graph:', e);
    }
}

async function searchMemoryGraph() {
    const input = document.getElementById('memorySearchInput');
    const q = input?.value.trim();
    if (!q) return;

    const token = localStorage.getItem('shopo_auth_token');
    const card = document.getElementById('memoryAnswerCard');
    const ansText = document.getElementById('memoryAnswerText');
    const evList = document.getElementById('memoryEvidenceList');
    const confBadge = document.getElementById('memoryConfidenceBadge');

    try {
        const resp = await fetch(`/api/memory/query?q=${encodeURIComponent(q)}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();
        if (res.success && res.data) {
            const d = res.data;
            card.style.display = 'block';
            ansText.textContent = d.answer;
            confBadge.textContent = d.found ? 'Record Verified (सत्यापित)' : 'No Records';

            if (d.evidence && d.evidence.length > 0) {
                evList.innerHTML = d.evidence.map(ev => `
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:var(--radius-sm); padding:6px 10px;">
                        <strong>${escapeHtml(ev.entity)}:</strong> ${escapeHtml(ev.fact)}
                        <span style="color:var(--text-muted); font-size:0.75rem; display:block; margin-top:2px;">
                            Source: ${escapeHtml(ev.source)} &bull; ${ev.timestamp ? ev.timestamp.slice(0, 10) : ''}
                        </span>
                    </div>
                `).join('');
            } else {
                evList.innerHTML = '<div style="color:var(--text-muted);">No supporting primary records located.</div>';
            }
        }
    } catch (e) {
        console.error('Error querying memory:', e);
    }
}

function applyMemoryQuery(query) {
    const input = document.getElementById('memorySearchInput');
    if (input) {
        input.value = query;
        searchMemoryGraph();
    }
}

async function refreshMemoryGraph() {
    const token = localStorage.getItem('shopo_auth_token');
    showToast('Synchronizing business memory from store records...');
    try {
        const resp = await fetch('/api/memory/refresh', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();
        if (res.success) {
            showToast(`Memory synchronized (${res.memories_synced} facts linked).`);
            loadMemoryGraphView();
        }
    } catch (e) {
        console.error('Error syncing memories:', e);
    }
}


// ════════════════════════════════════════════════════════════
// GROUP D: BUSINESS OPPORTUNITY RADAR CONTROLLER
// ════════════════════════════════════════════════════════════

async function loadOpportunityRadarView() {
    const token = localStorage.getItem('shopo_auth_token');
    const grid = document.getElementById('radarOpportunitiesGrid');
    const emptyState = document.getElementById('radarEmptyState');

    try {
        const resp = await fetch('/api/opportunity-radar/scan', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();

        if (res.success && res.data) {
            const d = res.data;
            document.getElementById('radarTotalCount').textContent = d.opportunity_count || 0;
            document.getElementById('radarTotalImpact').textContent = `₹${(d.total_projected_impact_rs || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;

            if (d.opportunities && d.opportunities.length > 0) {
                if (emptyState) emptyState.style.display = 'none';

                grid.innerHTML = d.opportunities.map(opp => {
                    const typeLabel = opp.opportunity_type.replace(/_/g, ' ').toUpperCase();
                    return `
                        <div class="card" style="padding:18px 20px; background:var(--bg-card); border-radius:var(--radius-lg); border:1px solid var(--border-color); display:flex; flex-direction:column; justify-content:space-between;">
                            <div>
                                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                                    <span class="badge" style="background:#DCFCE7; color:#15803D; font-weight:700; font-size:0.75rem;">
                                        <i class="fas fa-radar"></i> ${escapeHtml(typeLabel)}
                                    </span>
                                    <span class="badge" style="background:#F1F5F9; color:#475569; font-size:0.75rem;">
                                        ${(opp.confidence * 100).toFixed(0)}% Confidence
                                    </span>
                                </div>
                                <h3 style="font-size:1.05rem; color:var(--text-primary); margin:0 0 8px 0;">${escapeHtml(opp.title)}</h3>
                                <p style="font-size:0.88rem; color:var(--text-secondary); line-height:1.45; margin-bottom:12px;">${escapeHtml(opp.explanation)}</p>

                                <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:var(--radius-md); padding:10px 12px; margin-bottom:12px; font-size:0.82rem;">
                                    <strong>Est. Financial Impact:</strong>
                                    <span style="color:#15803D; font-weight:700; font-size:0.95rem; margin-left:4px;">₹${(opp.expected_impact_rs || 0).toFixed(2)}</span>
                                    <div style="color:var(--text-muted); margin-top:2px;">Window: ${escapeHtml(opp.date_range_analyzed || 'Last 30 Days')}</div>
                                </div>
                            </div>
                            <div>
                                <div style="background:#EFF6FF; border:1px solid #BFDBFE; border-radius:var(--radius-md); padding:8px 12px; font-size:0.82rem; color:#1E40AF; margin-bottom:10px;">
                                    👉 <strong>Next Step:</strong> ${escapeHtml(opp.recommended_action)}
                                </div>
                                <div style="display:flex; justify-content:flex-end;">
                                    <button type="button" class="btn-dash btn-dash-secondary" style="font-size:0.8rem; padding:4px 10px; color:#DC2626;" onclick="dismissRadarItem('${opp.id}')">
                                        <i class="fas fa-eye-slash"></i> Dismiss
                                    </button>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
            } else {
                grid.innerHTML = '';
                if (emptyState) emptyState.style.display = 'block';
                grid.appendChild(emptyState);
            }
        }
    } catch (e) {
        console.error('Error loading opportunity radar:', e);
    }
}

async function dismissRadarItem(itemId) {
    const token = localStorage.getItem('shopo_auth_token');
    try {
        const resp = await fetch(`/api/opportunity-radar/dismiss/${itemId}`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();
        if (res.success) {
            showToast('Opportunity dismissed');
            loadOpportunityRadarView();
        }
    } catch (e) {
        console.error('Error dismissing radar item:', e);
    }
}


// ── Start on DOMContentLoaded ──
document.addEventListener('DOMContentLoaded', () => {
    initDashboard();

    // Make entire command input container focusable on tap/click
    const cmdForm = document.getElementById('aiCommandForm');
    if (cmdForm) {
        cmdForm.addEventListener('click', (e) => {
            if (!e.target.closest('#aiSendBtn')) {
                const input = document.getElementById('cmdInput');
                if (input && document.activeElement !== input) {
                    input.focus();
                }
            }
        });
    }
});



// ── Modern SaaS Helpers (Prompt Redesign) ──
function renderSalesOverviewChart() {
    const container = document.getElementById('salesOverviewChartContainer');
    if (!container) return;

    if (!salesRecords || salesRecords.length === 0) {
        container.innerHTML = `
            <div class="empty-sales-chart" id="emptySalesChartNotice">
                <div class="empty-chart-icon"><i class="fas fa-chart-bar"></i></div>
                <div class="empty-chart-title">No Sales Transactions Recorded Yet</div>
                <div class="empty-chart-desc">Record sales to generate live daily volume curves and real revenue analytics.</div>
            </div>
        `;
        return;
    }

    // Group sales by day (last 7 recorded days)
    const dailyTotals = {};
    const sorted = [...salesRecords].sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0));
    
    sorted.forEach(s => {
        let dateStr = 'Today';
        if (s.created_at) {
            try {
                const d = new Date(s.created_at);
                dateStr = d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
            } catch (e) {}
        }
        const amt = parseFloat(s.total_price || s.selling_price || 0) || 0;
        dailyTotals[dateStr] = (dailyTotals[dateStr] || 0) + amt;
    });

    const entries = Object.entries(dailyTotals).slice(-7);
    const maxVal = Math.max(...entries.map(e => e[1]), 100);

    let barsHtml = entries.map(([date, total]) => {
        const heightPct = Math.max(14, Math.round((total / maxVal) * 100));
        return `
            <div style="flex:1; display:flex; flex-direction:column; align-items:center; height:120px; justify-content:flex-end;">
                <div style="font-size:0.72rem; font-weight:700; color:var(--color-primary-green); margin-bottom:4px; font-variant-numeric:tabular-nums;">₹${Math.round(total)}</div>
                <div style="width:100%; max-width:36px; height:${heightPct}%; background:linear-gradient(180deg, var(--color-primary-green), #22C55E); border-radius:6px 6px 0 0; transition:height 0.4s ease;" title="${date}: ₹${total}"></div>
                <div style="font-size:0.72rem; color:var(--color-text-secondary); margin-top:6px; white-space:nowrap;">${date}</div>
            </div>
        `;
    }).join('');

    container.innerHTML = `
        <div style="display:flex; align-items:flex-end; gap:12px; height:140px; padding:12px 10px 0; border-bottom:1px solid var(--color-border);">
            ${barsHtml}
        </div>
    `;
}

function handleGlobalSearch(event) {
    if (event.key === 'Enter') {
        const query = event.target.value.trim();
        if (!query) return;
        const isQuestion = query.includes('?') || /^(what|how|why|kya|aaj|mera|stock|mandi|bhav|weather|mausam)/i.test(query);
        if (isQuestion) {
            focusAIAssistant();
            const input = document.getElementById('cmdInput');
            if (input) {
                input.value = query;
                handleCommandSubmit(event);
            }
        } else {
            switchNav('inventory');
            const searchInput = document.getElementById('inventorySearchInput');
            if (searchInput) {
                searchInput.value = query;
                handleInventorySearchInput(query);
            }
        }
    }
}

function focusAIAssistant() {
    const homeView = document.getElementById('view-home');
    if (!homeView || !homeView.classList.contains('active')) {
        switchNav('home');
    }
    const card = document.getElementById('assistantHeroCard');
    const input = document.getElementById('cmdInput');
    if (card) {
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        card.classList.add('pulse-focus');
        setTimeout(() => card.classList.remove('pulse-focus'), 1400);
    }
    if (input) {
        setTimeout(() => input.focus(), 200);
    }
}

function scrollToWeatherWidget() {
    switchNav('home');
    const widget = document.getElementById('weatherClockWidget');
    if (widget) {
        widget.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function toggleMoreTools() {
    const sub = document.getElementById('moreToolsSubNav');
    const arrow = document.getElementById('moreToolsArrow');
    if (!sub) return;
    const isHidden = sub.style.display === 'none';
    sub.style.display = isHidden ? 'flex' : 'none';
    if (arrow) {
        arrow.style.transform = isHidden ? 'rotate(0deg)' : 'rotate(-90deg)';
    }
}
