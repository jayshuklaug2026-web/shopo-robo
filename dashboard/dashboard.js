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

// ── Inventory State (Phase 2) ──
let inventoryItems = [];
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
        nav_home: 'Home / मुख्य पृष्ठ',
        nav_inventory: 'Inventory / स्टॉक',
        nav_multi_store: 'Multi-Store Hub / शाखाएं',
        nav_shelf_scanner: 'Shelf Scanner / शेल्फ स्कैनर',
        nav_sales: 'Sales / बिक्री',
        nav_reports: 'Reports / रिपोर्ट्स',
        nav_news: 'News & Markets / समाचार',
        nav_autopilot: 'AI Autopilot / ऑटोपायलट',
        nav_notifications: 'Notifications / सूचनाएं',
        nav_memory: 'Business Memory / व्यापार स्मृति',
        nav_radar: 'Opportunity Radar / अवसर रडार',
        nav_assistant: 'AI Robo / सहायक',
        nav_settings: 'Settings / सेटिंग्स',
        news_view_title: 'News & Market Intelligence / ताज़ा समाचार व बाज़ार',
        ai_assistant_title: 'Shopo Robo Voice Assistant',
        ai_status_ready: 'Online • आपकी दुकान के लिए तैयार हूँ (Ready)',
        mic_tap_to_speak: 'माइक दबाकर बोलें (Tap Mic to Speak)',
        preset_label: 'यह बोलकर देखें:',
        overview_title: 'Business Overview / आज का हिसाब',
        metric_sales: "Today's Sales (आज की बिक्री)",
        metric_profit: 'Gross Profit (मुनाफ़ा)',
        metric_products: 'Total Products (कुल सामान)',
        metric_low_stock: 'Low Stock (कम स्टॉक)',
        metric_expiry: 'Near Expiry (जल्द एक्सपायरी)',
        actions_title: 'Quick Actions / त्वरित कार्य',
        act_add_prod: 'Add Product',
        act_scan: 'Scan Barcode',
        act_inventory: 'View Inventory',
        act_sale: 'Record Sale',
        act_reports: 'Reports',
        recent_sales_title: 'Recent Sales / हाल की बिक्री',
        alerts_title: 'Alerts / चेतावनियाँ',
        wizard_title: 'दुकान का सेटअप पूरा करें! (Setup Your Shop)',
        wizard_desc: 'अपनी दुकान का नाम और प्रकार चुनें ताकि शोपो रोबो आपका सही इन्वेंटरी डेटा तैयार कर सके।',
    },
    en: {
        nav_home: 'Home Dashboard',
        nav_inventory: 'Inventory & Stock',
        nav_multi_store: 'Multi-Store Hub',
        nav_shelf_scanner: 'Smart Shelf Scanner',
        nav_sales: 'Sales Register',
        nav_reports: 'Financial Reports',
        nav_news: 'News & Markets',
        nav_autopilot: 'AI Business Autopilot',
        nav_notifications: 'Notification Center',
        nav_memory: 'Business Memory Graph',
        nav_radar: 'Opportunity Radar',
        nav_assistant: 'AI Robo Assistant',
        nav_settings: 'Settings & Profile',
        news_view_title: 'News & Market Intelligence',
        ai_assistant_title: 'Shopo Robo AI Assistant',
        ai_status_ready: 'Online • Ready to assist your store',
        mic_tap_to_speak: 'Tap Microphone to Speak',
        preset_label: 'Try voice commands:',
        overview_title: 'Business Overview',
        metric_sales: "Today's Total Sales",
        metric_profit: 'Gross Profit Margin',
        metric_products: 'Total Catalog Products',
        metric_low_stock: 'Low Stock Products',
        metric_expiry: 'Nearing Expiry Products',
        actions_title: 'Quick Operations',
        act_add_prod: 'Add Product',
        act_scan: 'Scan Barcode',
        act_inventory: 'View Inventory',
        act_sale: 'Record Sale',
        act_reports: 'Business Reports',
        recent_sales_title: 'Recent Customer Sales',
        alerts_title: 'Inventory Alerts',
        wizard_title: 'Complete Your Shop Setup!',
        wizard_desc: 'Enter your shop name and store category to enable AI features.',
    },
    hinglish: {
        nav_home: 'Home / Dashboard',
        nav_inventory: 'Stock / Inventory',
        nav_multi_store: 'Multi-Store / Saari Dukaanein',
        nav_shelf_scanner: 'Shelf Scanner / Stock Check',
        nav_sales: 'Bikri / Sales',
        nav_reports: 'Munafa / Reports',
        nav_news: 'Taaza Khabar / News',
        nav_assistant: 'AI Robo Assistant',
        nav_settings: 'Settings / Profile',
        news_view_title: 'Live News & Market Rates',
        ai_assistant_title: 'Shopo Robo Assistant',
        ai_status_ready: 'Online • Dukaan assistant ready hai',
        mic_tap_to_speak: 'Mic dabayein aur boliye (Tap Mic)',
        preset_label: 'Try bol kar dekhein:',
        overview_title: "Today's Business Summary",
        metric_sales: "Today's Sales (Aaj ki bikri)",
        metric_profit: 'Gross Profit (Munafa)',
        metric_products: 'Total Items (Total stock)',
        metric_low_stock: 'Low Stock Alert',
        metric_expiry: 'Expiry Alert (Jald expiry)',
        actions_title: 'Quick Dukaan Actions',
        act_add_prod: 'Add Item',
        act_scan: 'Scan Barcode',
        act_inventory: 'Check Stock',
        act_sale: 'Record Bikri',
        act_reports: 'View Reports',
        recent_sales_title: 'Recent Sales History',
        alerts_title: 'Stock & Expiry Alerts',
        wizard_title: 'Setup your Dukaan profile!',
        wizard_desc: 'Dukaan ka name aur category select karein for smart AI inventory.',
    },
    es: {
        nav_home: 'Inicio / Panel',
        nav_inventory: 'Inventario / Stock',
        nav_sales: 'Ventas / Caja',
        nav_reports: 'Informes Financieros',
        nav_news: 'Noticias y Mercados',
        nav_assistant: 'Asistente IA Robo',
        nav_settings: 'Configuración / Perfil',
        news_view_title: 'Noticias e Inteligencia de Mercado',
        ai_assistant_title: 'Asistente de Voz Shopo Robo',
        ai_status_ready: 'En línea • Listo para ayudar a tu tienda',
        mic_tap_to_speak: 'Toca el micrófono para hablar',
        preset_label: 'Prueba comandos de voz:',
        overview_title: 'Resumen del Negocio',
        metric_sales: 'Ventas de Hoy',
        metric_profit: 'Margen de Beneficio Bruto',
        metric_products: 'Total de Productos',
        metric_low_stock: 'Stock Bajo',
        metric_expiry: 'Próximos a Vencer',
        actions_title: 'Operaciones Rápidas',
        act_add_prod: 'Añadir Producto',
        act_scan: 'Escanear Código',
        act_inventory: 'Ver Inventario',
        act_sale: 'Registrar Venta',
        act_reports: 'Informes',
        recent_sales_title: 'Ventas Recientes',
        alerts_title: 'Alertas de Inventario',
        wizard_title: '¡Completa la configuración de tu tienda!',
        wizard_desc: 'Ingresa el nombre y tipo de tienda para activar la IA.',
    },
    fr: {
        nav_home: 'Accueil / Tableau',
        nav_inventory: 'Inventaire / Stock',
        nav_sales: 'Ventes / Caisse',
        nav_reports: 'Rapports Financiers',
        nav_news: 'Actualités & Marchés',
        nav_assistant: 'Assistant IA Robo',
        nav_settings: 'Paramètres / Profil',
        news_view_title: 'Actualités & Intelligence du Marché',
        ai_assistant_title: 'Assistant Vocal Shopo Robo',
        ai_status_ready: 'En ligne • Prêt à vous assister',
        mic_tap_to_speak: 'Appuyez sur le micro pour parler',
        preset_label: 'Essayez des commandes:',
        overview_title: "Aperçu de l'Entreprise",
        metric_sales: "Ventes d'Aujourd'hui",
        metric_profit: 'Marge Brute',
        metric_products: 'Produits au Catalogue',
        metric_low_stock: 'Stock Faible',
        metric_expiry: 'Expiration Imminente',
        actions_title: 'Actions Rapides',
        act_add_prod: 'Ajouter Produit',
        act_scan: 'Scanner Code',
        act_inventory: 'Voir Stock',
        act_sale: 'Enregistrer Vente',
        act_reports: 'Rapports',
        recent_sales_title: 'Ventes Récentes',
        alerts_title: "Alertes d'Inventaire",
        wizard_title: 'Configurez votre magasin!',
        wizard_desc: 'Entrez le nom et la catégorie de votre boutique.',
    },
    ar: {
        nav_home: 'الرئيسية / لوحة التحكم',
        nav_inventory: 'المخزون والمنتجات',
        nav_sales: 'سجل المبيعات',
        nav_reports: 'التقارير المالية',
        nav_news: 'الأخبار والأسواق',
        nav_assistant: 'المساعد الذكي روبو',
        nav_settings: 'الإعدادات والملف',
        news_view_title: 'الأخبار ومعلومات الأسواق',
        ai_assistant_title: 'مساعد شوبو روبو الصوتي',
        ai_status_ready: 'متصل • جاهز لمساعدتك',
        mic_tap_to_speak: 'اضغط على الميكروفون للتحدث',
        preset_label: 'جرب الأوامر الصوتية:',
        overview_title: 'نظرة عامة على النشاط',
        metric_sales: 'مبيعات اليوم',
        metric_profit: 'هامش الربح الإجمالي',
        metric_products: 'إجمالي المنتجات',
        metric_low_stock: 'مخزون منخفض',
        metric_expiry: 'قريب الانتهاء',
        actions_title: 'إجراءات سريعة',
        act_add_prod: 'إضافة منتج',
        act_scan: 'مسح الباركود',
        act_inventory: 'عرض المخزون',
        act_sale: 'تسجيل عملية بيع',
        act_reports: 'التقارير',
        recent_sales_title: 'المبيعات الأخيرة',
        alerts_title: 'تنبيهات المخزون',
        wizard_title: 'أكمل إعداد متجرك!',
        wizard_desc: 'أدخل اسم متجرك وفئته لتفعيل ميزات الذكاء الاصطناعي.',
    },
    zh: {
        nav_home: '首页 / 仪表板',
        nav_inventory: '库存与产品',
        nav_sales: '销售记录',
        nav_reports: '财务报表',
        nav_news: '新闻与市场',
        nav_assistant: 'AI 智能助手',
        nav_settings: '设置与档案',
        news_view_title: '新闻与市场动态',
        ai_assistant_title: 'Shopo Robo 语音助手',
        ai_status_ready: '在线 • 随时为您服务',
        mic_tap_to_speak: '轻点麦克风说话',
        preset_label: '尝试语音指令：',
        overview_title: '业务概览',
        metric_sales: '今日总销售额',
        metric_profit: '毛利率',
        metric_products: '产品目录总数',
        metric_low_stock: '低库存商品',
        metric_expiry: '临近保质期',
        actions_title: '快捷操作',
        act_add_prod: '添加商品',
        act_scan: '扫描条形码',
        act_inventory: '查看库存',
        act_sale: '记录销售',
        act_reports: '商业报表',
        recent_sales_title: '近期顾客销售',
        alerts_title: '库存预警',
        wizard_title: '完善您的店铺配置！',
        wizard_desc: '输入您的店铺名称和类别以启用智能AI功能。',
    },
    ja: {
        nav_home: 'ホーム / ダッシュボード',
        nav_inventory: '在庫・商品管理',
        nav_sales: '売上レジスター',
        nav_reports: '財務レポート',
        nav_news: 'ニュース＆市況',
        nav_assistant: 'AIロボアシスタント',
        nav_settings: '設定・プロフィール',
        news_view_title: 'ニュース＆市場インテリジェンス',
        ai_assistant_title: 'Shopo Robo 音声アシスタント',
        ai_status_ready: 'オンライン • いつでもお手伝いします',
        mic_tap_to_speak: 'マイクをタップして話す',
        preset_label: '音声コマンドをお試しください:',
        overview_title: '店舗業績の概要',
        metric_sales: '本日の売上合計',
        metric_profit: '粗利益マージン',
        metric_products: '登録商品総数',
        metric_low_stock: '在庫不足商品',
        metric_expiry: '賞味期限間近',
        actions_title: 'クイック操作',
        act_add_prod: '商品追加',
        act_scan: 'バーコードスキャン',
        act_inventory: '在庫一覧',
        act_sale: '売上記録',
        act_reports: '業績レポート',
        recent_sales_title: '直近の販売履歴',
        alerts_title: '在庫アラート',
        wizard_title: '店舗の初期設定を完了しましょう！',
        wizard_desc: '店舗名と業種を選択してAI機能を有効化してください。',
    },
    bn: {
        nav_home: 'হোম / ড্যাশবোর্ড',
        nav_inventory: 'ইনভেন্টরি ও স্টক',
        nav_sales: 'বিক্রয় রেজিস্টার',
        nav_reports: 'আর্থিক রিপোর্ট',
        nav_news: 'সংবাদ ও বাজার দর',
        nav_assistant: 'এআই রোবো সহায়ক',
        nav_settings: 'সেটিংস ও প্রোফাইল',
        news_view_title: 'সংবাদ ও বাজার বুদ্ধিমত্তা',
        ai_assistant_title: 'শোপো রোবো ভয়েস অ্যাসিস্ট্যান্ট',
        ai_status_ready: 'অনলাইন • আপনার দোকানে সাহায্য করতে প্রস্তুত',
        mic_tap_to_speak: 'কথা বলতে মাইকে চাপ দিন',
        preset_label: 'ভয়েস কমান্ড চেষ্টা করুন:',
        overview_title: 'ব্যবসায়িক পর্যালোচনা',
        metric_sales: 'আজকের মোট বিক্রয়',
        metric_profit: 'মোট মুনাফা (মার্জিন)',
        metric_products: 'ক্যাটালগ পণ্য',
        metric_low_stock: 'স্বল্প স্টক পণ্য',
        metric_expiry: 'মেয়াদোত্তীর্ণের কাছাকাছি',
        actions_title: 'দ্রুত অপারেশন',
        act_add_prod: 'পণ্য যোগ করুন',
        act_scan: 'বারকোড স্ক্যান',
        act_inventory: 'স্টক দেখুন',
        act_sale: 'বিক্রয় রেকর্ড',
        act_reports: 'রিপোর্ট দেখুন',
        recent_sales_title: 'সাম্প্রতিক বিক্রয়',
        alerts_title: 'ইনভেন্টরি সতর্কতা',
        wizard_title: 'দোকান সেটআপ সম্পন্ন করুন!',
        wizard_desc: 'স্মার্ট এআই ফিচারের জন্য দোকানের নাম ও ক্যাটাগরি দিন।',
    },
    mr: {
        nav_home: 'मुख्य पृष्ठ / डॅशबोर्ड',
        nav_inventory: 'इन्व्हेंटरी व स्टॉक',
        nav_sales: 'विक्री नोंदवही',
        nav_reports: 'आर्थिक अहवाल',
        nav_news: 'बातम्या व बाजारभाव',
        nav_assistant: 'एआय रोबो सहाय्यक',
        nav_settings: 'सेटिंग्ज व प्रोफाईल',
        news_view_title: 'ताज्या बातम्या व बाजारभाव',
        ai_assistant_title: 'शोपो रोबो व्हॉईस असिस्टंट',
        ai_status_ready: 'ऑनलाईन • दुकानासाठी तयार आहे',
        mic_tap_to_speak: 'माईक दाबून बोला',
        preset_label: 'हे विचारून पहा:',
        overview_title: 'आजचा हिशोब व व्यवसाय सारांश',
        metric_sales: 'आजची एकूण विक्री',
        metric_profit: 'एकूण नफा (Gross Profit)',
        metric_products: 'एकूण उत्पादने',
        metric_low_stock: 'कमी साठा',
        metric_expiry: 'लवकर कालबाह्य',
        actions_title: 'जलद कृती',
        act_add_prod: 'माल जोडा',
        act_scan: 'बारकोड स्कॅन',
        act_inventory: 'स्टॉक तपासा',
        act_sale: 'विक्री नोंदवा',
        act_reports: 'अहवाल',
        recent_sales_title: 'अलीकडील विक्री',
        alerts_title: 'साठा सूचना',
        wizard_title: 'दुकानाची माहिती पूर्ण करा!',
        wizard_desc: 'एआय वैशिष्ट्ये सुरू करण्यासाठी नाव व प्रकार निवडा.',
    },
    te: {
        nav_home: 'హోమ్ / డాష్‌బోర్డ్',
        nav_inventory: 'ఇన్వెంటరీ & స్టాక్',
        nav_sales: 'అమ్మకాల రిజిస్టర్',
        nav_reports: 'ఆర్థిక నివేదికలు',
        nav_news: 'వార్తలు & మార్కెట్ ధరలు',
        nav_assistant: 'AI రోబో అసిస్టెంట్',
        nav_settings: 'సెట్టింగ్‌లు & ప్రొఫైల్',
        news_view_title: 'వార్తలు & మార్కెట్ సమాచారం',
        ai_assistant_title: 'షోపో రోబో వాయిస్ అసిస్టెంట్',
        ai_status_ready: 'ఆన్‌లైన్ • మీ దుకాణానికి సహాయం చేయడానికి సిద్ధంగా ఉంది',
        mic_tap_to_speak: 'మాట్లాడటానికి మైక్ నొక్కండి',
        preset_label: 'వాయిస్ ఆదేశాలు ప్రయత్నించండి:',
        overview_title: 'వ్యాపార సమాచారం',
        metric_sales: 'నేటి మొత్తం అమ్మకాలు',
        metric_profit: 'స్థూల లాభం',
        metric_products: 'మొత్తం ఉత్పత్తులు',
        metric_low_stock: 'తక్కువ స్టాక్ వస్తువులు',
        metric_expiry: 'గడువు సమీపించినవి',
        actions_title: 'త్వరిత చర్యలు',
        act_add_prod: 'వస్తువును జోడించండి',
        act_scan: 'బార్‌కోడ్ స్కాన్',
        act_inventory: 'స్టాక్ చూడండి',
        act_sale: 'అమ్మకం నమోదు',
        act_reports: 'నివేదికలు',
        recent_sales_title: 'ఇటీవలి అమ్మకాలు',
        alerts_title: 'స్టాక్ హెచ్చరికలు',
        wizard_title: 'మీ షాప్ సెటప్ పూర్తి చేయండి!',
        wizard_desc: 'స్మార్ట్ AI ఫీచర్ల కోసం షాప్ పేరు మరియు వర్గాన్ని ఎంచుకోండి.',
    },
    ta: {
        nav_home: 'முகப்பு / டாஷ்போர்டு',
        nav_inventory: 'சரக்கு & இருப்பு',
        nav_sales: 'விற்பனைப் பதிவேடு',
        nav_reports: 'நிதி அறிக்கைகள்',
        nav_news: 'செய்திகள் & சந்தை விலை',
        nav_assistant: 'AI ரோபோ உதவியாளர்',
        nav_settings: 'அமைப்புகள் & சுயவிவரம்',
        news_view_title: 'செய்திகள் & சந்தை நுண்ணறிவு',
        ai_assistant_title: 'ஷோபோ ரோபோ குரல் உதவியாளர்',
        ai_status_ready: 'ஆன்லைன் • உதவத் தயாராக உள்ளது',
        mic_tap_to_speak: 'பேச மைக்கை அழுத்தவும்',
        preset_label: 'குரல் கட்டளைகளை முயற்சிக்கவும்:',
        overview_title: 'வணிக மேலோட்டம்',
        metric_sales: 'இன்றைய மொத்த விற்பனை',
        metric_profit: 'மொத்த லாபம் (Profit)',
        metric_products: 'மொத்தப் பொருட்கள்',
        metric_low_stock: 'குறைந்த இருப்பு',
        metric_expiry: 'காலாவதி நெருங்குகிறது',
        actions_title: 'விரைவுச் செயல்பாடுகள்',
        act_add_prod: 'பொருளைச் சேர்',
        act_scan: 'பார்கோடு ஸ்கேன்',
        act_inventory: 'இருப்பைப் பார்',
        act_sale: 'விற்பனை பதிவு',
        act_reports: 'அறிக்கைகள்',
        recent_sales_title: 'சமீபத்திய விற்பனை',
        alerts_title: 'இருப்பு எச்சரிக்கைகள்',
        wizard_title: 'கடை அமைப்பை முடிக்கவும்!',
        wizard_desc: 'AI அம்சங்களுக்காக கடையின் பெயர் மற்றும் வகையை உள்ளிடவும்.',
    },
    gu: {
        nav_home: 'હોમ / ડેશબોર્ડ',
        nav_inventory: 'ઇન્વેન્ટરી અને સ્ટોક',
        nav_sales: 'વેચાણ રજિસ્ટર',
        nav_reports: 'નાણાકીય અહેવાલો',
        nav_news: 'સમાચાર અને બજારભાવ',
        nav_assistant: 'AI રોબો સહાયક',
        nav_settings: 'સેટિંગ્સ અને પ્રોફાઇલ',
        news_view_title: 'સમાચાર અને બજાર ગુપ્તચર',
        ai_assistant_title: 'શોપો રોબો વૉઇસ આસિસ્ટન્ટ',
        ai_status_ready: 'ઓનલાઇન • તમારી દુકાન માટે તૈયાર છે',
        mic_tap_to_speak: 'વાત કરવા માટે માઈક દબાવો',
        preset_label: 'આ બોલીને જુઓ:',
        overview_title: 'વ્યવસાયિક અવલોકન (આજનો હિસાબ)',
        metric_sales: 'આજનું કુલ વેચાણ',
        metric_profit: 'કુલ નફો (ગ્રોસ પ્રોફિટ)',
        metric_products: 'કુલ પ્રોડક્ટ્સ',
        metric_low_stock: 'ઓછો સ્ટોક',
        metric_expiry: 'નજીકની એક્સપાયરી',
        actions_title: 'ઝડપી કાર્યો',
        act_add_prod: 'સામાન ઉમેરો',
        act_scan: 'બારકોડ સ્કેન',
        act_inventory: 'સ્ટોક જુઓ',
        act_sale: 'વેચાણ નોંધો',
        act_reports: 'રિપોર્ટ્સ',
        recent_sales_title: 'તાજેતરનું વેચાણ',
        alerts_title: 'સ્ટોક ચેતવણીઓ',
        wizard_title: 'દુકાનનું સેટઅપ પૂર્ણ કરો!',
        wizard_desc: 'સ્માર્ટ AI સુવિધાઓ માટે દુકાનનું નામ અને શ્રેણી પસંદ કરો.',
    },
    ur: {
        nav_home: 'ہوم / ڈیش بورڈ',
        nav_inventory: 'انوینٹری اور اسٹاک',
        nav_sales: 'سیلز رجسٹر',
        nav_reports: 'مالیاتی رپورٹس',
        nav_news: 'خبریں اور منڈی ریٹس',
        nav_assistant: 'اے آئی روبو معاون',
        nav_settings: 'ترتیبات و پروفائل',
        news_view_title: 'خبریں اور مارکیٹ انٹیلی جنس',
        ai_assistant_title: 'شوپو روبو وائس اسسٹنٹ',
        ai_status_ready: 'آن لائن • دکان کی مدد کے لیے تیار ہوں',
        mic_tap_to_speak: 'بات کرنے کے لیے مائیک دبائیں',
        preset_label: 'یہ احکامات بولیں:',
        overview_title: 'کاروباری جائزہ (آج کا حساب)',
        metric_sales: 'آج کی کل فروخت',
        metric_profit: 'مجموعی منافع',
        metric_products: 'کل اشیاء',
        metric_low_stock: 'کم اسٹاک کی الرٹ',
        metric_expiry: 'قریب المیعاد تاریخ',
        actions_title: 'فوری اقدامات',
        act_add_prod: 'سامان شامل کریں',
        act_scan: 'بارکوڈ اسکین',
        act_inventory: 'اسٹاک چیک کریں',
        act_sale: 'فروخت درج کریں',
        act_reports: 'رپورٹس دیکھیں',
        recent_sales_title: 'حالیہ فروخت',
        alerts_title: 'اسٹاک کی تنبیہات',
        wizard_title: 'دکان کا سیٹ اپ مکمل کریں!',
        wizard_desc: 'اے آئی انوینٹری فعال کرنے کے لیے دکان کا نام اور زمرہ درج کریں۔',
    },
    de: {
        nav_home: 'Home / Dashboard',
        nav_inventory: 'Inventar & Bestand',
        nav_sales: 'Verkaufsregister',
        nav_reports: 'Finanzberichte',
        nav_news: 'Nachrichten & Märkte',
        nav_assistant: 'KI-Robo-Assistent',
        nav_settings: 'Einstellungen & Profil',
        news_view_title: 'Nachrichten & Marktinformationen',
        ai_assistant_title: 'Shopo Robo Sprachassistent',
        ai_status_ready: 'Online • Bereit, Ihren Laden zu unterstützen',
        mic_tap_to_speak: 'Mikrofon zum Sprechen tippen',
        preset_label: 'Sprachbefehle ausprobieren:',
        overview_title: 'Geschäftsübersicht',
        metric_sales: 'Heutige Gesamtverkäufe',
        metric_profit: 'Bruttogewinnspanne',
        metric_products: 'Katalogprodukte gesamt',
        metric_low_stock: 'Niedriger Bestand',
        metric_expiry: 'Ablaufend',
        actions_title: 'Schnellaktionen',
        act_add_prod: 'Produkt hinzufügen',
        act_scan: 'Barcode scannen',
        act_inventory: 'Inventar anzeigen',
        act_sale: 'Verkauf buchen',
        act_reports: 'Berichte',
        recent_sales_title: 'Letzte Verkäufe',
        alerts_title: 'Bestandswarnungen',
        wizard_title: 'Laden-Setup abschließen!',
        wizard_desc: 'Geben Sie Ladenname und Kategorie ein, um KI-Funktionen zu nutzen.',
    },
    ru: {
        nav_home: 'Главная / Панель',
        nav_inventory: 'Склад и товары',
        nav_sales: 'Реестр продаж',
        nav_reports: 'Финансовые отчеты',
        nav_news: 'Новости и рынки',
        nav_assistant: 'ИИ Робо-ассистент',
        nav_settings: 'Настройки и профиль',
        news_view_title: 'Новости и анализ рынка',
        ai_assistant_title: 'Голосовой помощник Shopo Robo',
        ai_status_ready: 'В сети • Готов помочь вашему магазину',
        mic_tap_to_speak: 'Нажмите микрофон, чтобы говорить',
        preset_label: 'Попробуйте голосовые команды:',
        overview_title: 'Обзор бизнеса за сегодня',
        metric_sales: 'Сегодняшние продажи',
        metric_profit: 'Валовая прибыль',
        metric_products: 'Всего товаров в каталоге',
        metric_low_stock: 'Мало на складе',
        metric_expiry: 'Истекает срок годности',
        actions_title: 'Быстрые действия',
        act_add_prod: 'Добавить товар',
        act_scan: 'Сканировать штрихкод',
        act_inventory: 'Просмотр склада',
        act_sale: 'Записать продажу',
        act_reports: 'Отчеты',
        recent_sales_title: 'Недавние продажи',
        alerts_title: 'Оповещения склада',
        wizard_title: 'Завершите настройку магазина!',
        wizard_desc: 'Укажите название и категорию магазина для умного ИИ-учета.',
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

function setLanguage(lang, persist = true) {
    currentLanguage = lang;
    userPreferences.ui_language = lang;

    // Handle RTL layouts for Arabic and Urdu
    const isRtl = (lang === 'ar' || lang === 'ur');
    document.documentElement.setAttribute('dir', isRtl ? 'rtl' : 'ltr');
    document.documentElement.setAttribute('lang', lang);

    // Update active button pills in header
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.lang === lang);
    });

    // Update Settings UI Lang dropdown if present
    const prefUi = document.getElementById('prefUiLang');
    if (prefUi) prefUi.value = lang;

    // Apply translations across all data-i18n elements
    const dict = I18N[lang] || I18N.hi || I18N.en;
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.dataset.i18n;
        if (dict[key]) {
            el.textContent = dict[key];
        }
    });

    // Update input placeholders
    updateInputPlaceholders(lang);

    // Update live clock date format & weekday
    updateLiveClockDisplay();

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
        } else if (lang === 'ar' || lang === 'ur') {
            cmdInput.placeholder = "اكتب أو تحدث هنا... e.g. 'أرباح اليوم'";
        } else if (lang === 'es') {
            cmdInput.placeholder = "Escribe o habla aquí... e.g. 'Ganancia de hoy'";
        } else if (lang === 'fr') {
            cmdInput.placeholder = "Tapez ou parlez ici... e.g. 'Bénéfice du jour'";
        } else {
            cmdInput.placeholder = "Type or speak command... e.g. 'Show today\'s profit'";
        }
    }

    const assistantViewInput = document.getElementById('assistantViewInput');
    if (assistantViewInput) {
        if (lang === 'hi') {
            assistantViewInput.placeholder = "किसी भी उद्योग, मंडी, मौसम, सरकारी योजना या दुकान के बारे में पूछें...";
        } else if (lang === 'hinglish') {
            assistantViewInput.placeholder = "Dukaan, mandi, mausam, ya kisi bhi topic pe poochhein...";
        } else {
            assistantViewInput.placeholder = "Ask anything about business, mandi rates, weather, schemes, or store...";
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
        updateListeningUI(true);
    };

    recognizer.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        document.getElementById('cmdInput').value = transcript;
        processAICommand(transcript);
    };

    recognizer.onerror = (event) => {
        console.warn('Speech error:', event.error);
        isListening = false;
        updateListeningUI(false);
        showSimulatedResponse(
            "माइक अनुमति नहीं मिली या ऑडियो साफ़ नहीं था। कृपया टाइप करके अपना सवाल पूछें। (Microphone permission was not granted or audio was unclear. Please type your command.)"
        );
    };

    recognizer.onend = () => {
        isListening = false;
        updateListeningUI(false);
    };

    return recognizer;
}

function toggleVoiceInput() {
    if (!speechRecognition) {
        speechRecognition = setupSpeechRecognition();
    }

    if (!speechRecognition) {
        // Fallback for browsers without SpeechRecognition
        showSimulatedResponse(
            "आपका ब्राउज़र सीधे वॉइस इनपुट सपोर्ट नहीं करता। कृपया नीचे टेक्स्ट बॉक्स में टाइप करें। (Browser does not support Speech Recognition. Please use text input.)"
        );
        document.getElementById('cmdInput').focus();
        return;
    }

    if (isListening) {
        speechRecognition.stop();
    } else {
        // Set speech language based on current selection
        speechRecognition.lang = currentLanguage === 'en' ? 'en-IN' : 'hi-IN';
        try {
            speechRecognition.start();
        } catch (e) {
            console.warn('Could not start recognition:', e);
        }
    }
}

function updateListeningUI(listening) {
    const micContainer = document.getElementById('micBtnContainer');
    const helperText = document.getElementById('micHelperText');
    const statusText = document.getElementById('aiStatusText');

    if (listening) {
        micContainer.classList.add('listening');
        helperText.textContent = "सुन रहा हूँ... बोलिए (Listening...)";
        statusText.textContent = "🔴 Listening to voice input...";
        statusText.style.color = "#DC2626";
    } else {
        micContainer.classList.remove('listening');
        helperText.textContent = I18N[currentLanguage]?.mic_tap_to_speak || "माइक दबाकर बोलें";
        statusText.textContent = "Online • आपकी दुकान के लिए तैयार हूँ (Ready)";
        statusText.style.color = "var(--lime-700)";
    }
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
    if (e) e.preventDefault();
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
    const box = document.getElementById('aiResponseBox');
    const body = document.getElementById('aiResponseBody');
    const intentBadge = document.getElementById('aiIntentBadge');
    const actionCard = document.getElementById('aiActionConfirmCard');

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

            // Spoken speech synthesis readout (Module 8)
            if (window.speechSynthesis && data.spoken_text) {
                try {
                    window.speechSynthesis.cancel();
                    const cleanSpoken = data.spoken_text.replace(/[#*`_()]/g, '');
                    const utter = new SpeechSynthesisUtterance(cleanSpoken);
                    utter.lang = currentLanguage === 'en' ? 'en-IN' : 'hi-IN';
                    utter.rate = 1.0;
                    window.speechSynthesis.speak(utter);
                } catch (e) {}
            }
        } else {
            if (body) body.innerHTML = `<span style="color:#DC2626;">❌ ${escapeHtml(res.message || 'Error communicating with AI engine.')}</span>`;
        }
    } catch (err) {
        console.error('AI chat failed:', err);
        if (body) body.innerHTML = `<span style="color:#DC2626;">❌ Server connection error. Please ensure backend is running.</span>`;
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
        } else {
            if (badgeEl) renderActionStatusBadge(badgeEl, 'failed');
            alert(res.message || 'Action failed.');
        }
    } catch (err) {
        if (badgeEl) renderActionStatusBadge(badgeEl, 'failed');
        console.error('Error confirming action:', err);
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
    const m = document.getElementById(id);
    if (m) m.classList.remove('active');
}

function openAddProductModal() {
    openModal('addProductModal');
    handleCategoryChange('add');
}
function openBarcodeModal() {
    openModal('barcodeModal');
    document.getElementById('barcodeResultBox').style.display = 'none';
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

        return `
            <tr>
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

// ── Barcode Scanner Simulator (Connected to Real Inventory) ──
function simulateBarcodeScan(code, defaultName) {
    const resultBox = document.getElementById('barcodeResultBox');
    resultBox.style.display = 'block';

    const match = inventoryItems.find(it => it.barcode === code);

    if (match) {
        resultBox.style.background = 'var(--lime-50)';
        resultBox.style.borderColor = 'var(--lime-400)';
        resultBox.innerHTML = `
            <div style="color:var(--lime-800);">
                <i class="fas fa-check-circle" style="color:var(--green-500);"></i>
                <strong>Found in Stock:</strong> ${escapeHtml(match.product_name)}<br>
                <span style="font-size:0.8rem; color:var(--text-secondary);">
                    Stock: ${match.quantity} ${escapeHtml(match.unit)} &bull; Sell: ₹${match.selling_price} &bull; Barcode: ${code}
                </span>
                <div style="margin-top:8px;">
                    <button class="btn-dash btn-dash-primary" style="padding:4px 12px; font-size:0.8rem;" onclick="closeModal('barcodeModal'); openEditProductModal('${match.id}');">
                        <i class="fas fa-edit"></i> Edit Product
                    </button>
                </div>
            </div>
        `;
    } else {
        resultBox.style.background = '#FFFBEB';
        resultBox.style.borderColor = '#FCD34D';
        resultBox.innerHTML = `
            <div style="color:#92400E;">
                <i class="fas fa-info-circle"></i>
                Scanned: <strong>${defaultName}</strong> (${code})<br>
                <span style="font-size:0.8rem; color:var(--text-secondary);">Not yet in your dukaan inventory.</span>
                <div style="margin-top:8px;">
                    <button class="btn-dash btn-dash-primary" style="padding:4px 12px; font-size:0.8rem;" onclick="prepareAddScannedProduct('${escapeHtml(defaultName)}', '${code}')">
                        <i class="fas fa-plus"></i> Add to Inventory
                    </button>
                </div>
            </div>
        `;
    }
}

function prepareAddScannedProduct(name, barcode) {
    closeModal('barcodeModal');
    document.getElementById('newProdName').value = name;
    document.getElementById('newProdBarcode').value = barcode;
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
    const token = localStorage.getItem('shopo_auth_token');
    if (!token) return;

    try {
        const resp = await fetch('/api/user/preferences', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const res = await resp.json();
        if (res.success && res.data) {
            userPreferences = Object.assign(userPreferences, res.data);
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

function detectUserLocation() {
    const sel = document.getElementById('wcCitySelect');
    const fallbackCity = (sel && sel.value) ? sel.value : (userPreferences.selected_city || 'Delhi');

    if (!navigator.geolocation) {
        const btn = document.querySelector('.wc-geo-btn');
        if (btn) {
            btn.innerHTML = '<i class="fas fa-info-circle"></i> GPS Unsupported';
            setTimeout(() => { btn.innerHTML = '<i class="fas fa-crosshairs"></i> Detect Location'; }, 3000);
        }
        fetchLiveWeather(fallbackCity);
        return;
    }

    const btn = document.querySelector('.wc-geo-btn');
    if (btn) btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Detecting...';

    navigator.geolocation.getCurrentPosition(
        (pos) => {
            const userLat = pos.coords.latitude;
            const userLon = pos.coords.longitude;

            let closestCity = fallbackCity;
            let minDistance = Infinity;

            for (const [cityName, coords] of Object.entries(INDIAN_CITIES_COORDS)) {
                const dLat = coords.lat - userLat;
                const dLon = coords.lon - userLon;
                const dist = Math.sqrt(dLat * dLat + dLon * dLon);
                if (dist < minDistance) {
                    minDistance = dist;
                    closestCity = cityName;
                }
            }

            const selectEl = document.getElementById('wcCitySelect');
            if (selectEl) selectEl.value = closestCity;

            userPreferences.selected_city = closestCity;
            saveUserPreferences({ selected_city: closestCity });
            fetchLiveWeather(closestCity, { lat: userLat, lon: userLon });

            if (btn) btn.innerHTML = '<i class="fas fa-check"></i> ' + closestCity;
            setTimeout(() => {
                if (btn) btn.innerHTML = '<i class="fas fa-crosshairs"></i> Detect Location';
            }, 3000);
        },
        (err) => {
            console.warn('Geolocation denied or failed:', err);
            let reasonText = 'Permission Denied';
            if (err.code === 3) reasonText = 'GPS Timeout';
            else if (err.code === 2) reasonText = 'Position Unavailable';

            if (btn) btn.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${reasonText}`;
            setTimeout(() => {
                if (btn) btn.innerHTML = '<i class="fas fa-crosshairs"></i> Detect Location';
            }, 3000);

            // Graceful fallback to manual city
            fetchLiveWeather(fallbackCity);
        },
        { timeout: 8000, maximumAge: 300000, enableHighAccuracy: false }
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
});

