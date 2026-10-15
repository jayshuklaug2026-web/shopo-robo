"""
Shopo Robo - Multi-Language & Voice Pack Definitions
Supports major Indian regional languages + Global languages for Tier-3 shopkeeper accessibility.
"""

LANGUAGES = {
    'hi': {
        'name': '🇮🇳 हिन्दी (Hindi)',
        'app_title': 'शोपो रोबो - एआई स्टॉक एवं दुकान साथी',
        'welcome_msg': 'नमस्ते! मैं हूँ आपका शोपो रोबो। आपकी दुकान का स्मार्ट एआई साथी।',
        'tabs': {
            'inventory': '📦 स्टॉक मेन्यू',
            'voice': '🎙️ एआई वॉइस साथी',
            'barcode': '📷 बारकोड स्कैनर',
            'market': '📈 मंडी एवं बाज़ार भाव',
            'calculator': '🧮 मुनाफा एवं EBITDA',
            'settings': '⚙️ सेटिंग्स'
        },
        'stats': {
            'stock_value': 'कुल स्टॉक मूल्य',
            'items_count': 'कुल उत्पाद',
            'monthly_profit': 'इस माह का मुनाफा',
            'low_stock': 'कम स्टॉक अलर्ट'
        },
        'buttons': {
            'add_item': '+ नया सामान जोड़ें',
            'start_mic': '🎙️ बोलकर बताएं',
            'stop_mic': '⏹️ सुनना बंद करें',
            'scan_barcode': '📷 बारकोड स्कैन करें',
            'calculate': '🧮 गणना करें',
            'save': '💾 सुरक्षित करें'
        },
        'labels': {
            'item_name': 'सामान का नाम',
            'category': 'श्रेणी (Category)',
            'quantity': 'उपलब्ध मात्रा (Stock)',
            'expiry': 'एक्सपायरी डेट',
            'buy_price': 'खरीद मूल्य (Cost)',
            'sell_price': 'बिक्री मूल्य (Sell Price)',
            'unit': 'इकाई (kg/pkt/L)',
            'profit_gain': 'प्रति इकाई मुनाफा',
            'status': 'स्थिति'
        }
    },
    'en': {
        'name': '🇮🇳 English (India)',
        'app_title': 'Shopo Robo - AI Stock & Store Companion',
        'welcome_msg': 'Welcome! I am your Shopo Robo. Your smart AI assistant for your shop.',
        'tabs': {
            'inventory': '📦 Stock Menu',
            'voice': '🎙️ AI Voice Partner',
            'barcode': '📷 Barcode Scanner',
            'market': '📈 Mandi & Market Trends',
            'calculator': '🧮 Profit & EBITDA Calc',
            'settings': '⚙️ Settings'
        },
        'stats': {
            'stock_value': 'Total Stock Value',
            'items_count': 'Total Items',
            'monthly_profit': 'Monthly Profit',
            'low_stock': 'Low Stock Alert'
        },
        'buttons': {
            'add_item': '+ Add Item',
            'start_mic': '🎙️ Speak to Assistant',
            'stop_mic': '⏹️ Stop Listening',
            'scan_barcode': '📷 Scan Barcode',
            'calculate': '🧮 Calculate',
            'save': '💾 Save'
        },
        'labels': {
            'item_name': 'Item Name',
            'category': 'Category',
            'quantity': 'Available Stock',
            'expiry': 'Expiry Date',
            'buy_price': 'Cost Price (Buy)',
            'sell_price': 'Selling Price',
            'unit': 'Unit (kg/pkt/L)',
            'profit_gain': 'Profit Gain',
            'status': 'Status'
        }
    },
    'mr': {
        'name': '🇮🇳 मराठी (Marathi)',
        'app_title': 'शोपो रोबो - एआय दुकान व्यवस्थापक',
        'welcome_msg': 'नमस्कार! मी आपला शोपो रोबो. आपल्या दुकानाचे स्मार्ट एआय सहाय्यक.',
        'tabs': {
            'inventory': '📦 स्टॉक यादी',
            'voice': '🎙️ एआय व्हॉइस',
            'barcode': '📷 बारकोड स्कॅनर',
            'market': '📈 बाजार भाव',
            'calculator': '🧮 नफा आणि तोटा',
            'settings': '⚙️ सेटिंग्ज'
        },
        'stats': {
            'stock_value': 'एकूण स्टॉक मूल्य',
            'items_count': 'एकूण वस्तू',
            'monthly_profit': 'या महिन्याचा नफा',
            'low_stock': 'कमी स्टॉक अलर्ट'
        },
        'buttons': {
            'add_item': '+ नवीन वस्तू जोडा',
            'start_mic': '🎙️ बोलून सांगा',
            'stop_mic': '⏹️ थांबवा',
            'scan_barcode': '📷 बारकोड स्कॅन',
            'calculate': '🧮 गणना करा',
            'save': '💾 सेव्ह करा'
        },
        'labels': {
            'item_name': 'वस्तूचे नाव',
            'category': 'वर्गवारी',
            'quantity': 'शिल्लक साठा',
            'expiry': 'कालबाह्य तारीख',
            'buy_price': 'खरेदी किंमत',
            'sell_price': 'विक्री किंमत',
            'unit': 'एकक',
            'profit_gain': 'नफा',
            'status': 'स्थिती'
        }
    },
    'gu': {
        'name': '🇮🇳 ગુજરાતી (Gujarati)',
        'app_title': 'શોપો રોબો - સ્માર્ટ દુકાન એઆઈ',
        'welcome_msg': 'નમસ્તે! હું તમારો શોપો રોબો છું. તમારી દુકાનનો સ્માર્ટ એઆઈ સાથી.',
        'tabs': {
            'inventory': '📦 સ્ટોક મેનૂ',
            'voice': '🎙️ એઆઈ વોઇસ',
            'barcode': '📷 બારકોડ સ્કેનર',
            'market': '📈 બજાર ભાવ',
            'calculator': '🧮 નફો અને EBITDA',
            'settings': '⚙️ સેટિંગ્સ'
        },
        'stats': {
            'stock_value': 'કુલ સ્ટોક મૂલ્ય',
            'items_count': 'કુલ વસ્તુઓ',
            'monthly_profit': 'આ મહિનાનો નફો',
            'low_stock': 'ઓછો સ્ટોક ચેતવણી'
        },
        'buttons': {
            'add_item': '+ નવી વસ્તુ ઉમેરો',
            'start_mic': '🎙️ બોલીને કહો',
            'stop_mic': '⏹️ બંધ કરો',
            'scan_barcode': '📷 બારકોડ સ્કેન કરો',
            'calculate': '🧮 ગણતરી કરો',
            'save': '💾 સાચવો'
        },
        'labels': {
            'item_name': 'વસ્તુનું નામ',
            'category': 'શ્રેણી',
            'quantity': 'ઉપલબ્ધ સ્ટોક',
            'expiry': 'એક્સપાયરી તારીખ',
            'buy_price': 'ખરીદી ભાવ',
            'sell_price': 'વેચાણ ભાવ',
            'unit': 'એકમ',
            'profit_gain': 'નફો',
            'status': 'સ્થિતિ'
        }
    },
    'ta': {
        'name': '🇮🇳 தமிழ் (Tamil)',
        'app_title': 'ஷோபோ ரோபோ - AI கடை உதவியாளர்',
        'welcome_msg': 'வணக்கம்! நான் உங்கள் ஷோபோ ரோபோ. உங்கள் கடையின் AI உதவியாளர்.',
        'tabs': {
            'inventory': '📦 இருப்பு பட்டியல்',
            'voice': '🎙️ AI குரல்',
            'barcode': '📷 பார்கோடு ஸ்கேனர்',
            'market': '📈 சந்தை விலை',
            'calculator': '🧮 லாபம் கணக்கீடு',
            'settings': '⚙️ அமைப்புகள்'
        },
        'stats': {
            'stock_value': 'மொத்த இருப்பு மதிப்பு',
            'items_count': 'மொத்த பொருட்கள்',
            'monthly_profit': 'மாதாந்திர லாபம்',
            'low_stock': 'குறைந்த இருப்பு எச்சரிக்கை'
        },
        'buttons': {
            'add_item': '+ பொருள் சேர்க்க',
            'start_mic': '🎙️ பேசவும்',
            'stop_mic': '⏹️ நிறுத்து',
            'scan_barcode': '📷 பார்கோடு ஸ்கேன்',
            'calculate': '🧮 கணக்கிடு',
            'save': '💾 சேமிக்கவும்'
        },
        'labels': {
            'item_name': 'பொருள் பெயர்',
            'category': 'வகை',
            'quantity': 'இருப்பு அளவு',
            'expiry': 'காலாவதி தேதி',
            'buy_price': 'வாங்கிய விலை',
            'sell_price': 'விற்பனை விலை',
            'unit': 'அலகு',
            'profit_gain': 'லாபம்',
            'status': 'நிலை'
        }
    },
    'te': {
        'name': '🇮🇳 తెలుగు (Telugu)',
        'app_title': 'షోపో రోబో - AI స్టాక్ అసిస్టెంట్',
        'welcome_msg': 'నమస్కారం! నేను మీ షోపో రోబో. మీ షాప్ స్మార్ట్ AI అసిస్టెంట్.',
        'tabs': {
            'inventory': '📦 స్టాక్ మెనూ',
            'voice': '🎙️ AI వాయిస్',
            'barcode': '📷 బార్‌కోడ్ స్కానర్',
            'market': '📈 మార్కెట్ ధరలు',
            'calculator': '🧮 లాభం కాలిక్యులేటర్',
            'settings': '⚙️ సెట్టింగులు'
        },
        'stats': {
            'stock_value': 'మొత్తం స్టాక్ విలువ',
            'items_count': 'మొత్తం వస్తువులు',
            'monthly_profit': 'ఈ నెల లాభం',
            'low_stock': 'తక్కువ స్టాక్ హెచ్చరిక'
        },
        'buttons': {
            'add_item': '+ వస్తువు జోడించు',
            'start_mic': '🎙️ మాట్లాడండి',
            'stop_mic': '⏹️ ఆపు',
            'scan_barcode': '📷 బార్‌కోడ్ స్కాన్',
            'calculate': '🧮 లెక్కించండి',
            'save': '💾 సేవ్ చేయండి'
        },
        'labels': {
            'item_name': 'వస్తువు పేరు',
            'category': 'వర్గం',
            'quantity': 'స్టాక్ పరిమాణం',
            'expiry': 'గడువు తేదీ',
            'buy_price': 'కొనుగోలు ధర',
            'sell_price': 'అమ్మకం ధర',
            'unit': 'యూనిట్',
            'profit_gain': 'లాభం',
            'status': 'స్థితి'
        }
    },
    'bn': {
        'name': '🇮🇳 বাংলা (Bengali)',
        'app_title': 'শোপো রোবো - AI স্টক সহকারী',
        'welcome_msg': 'নমস্কার! আমি আপনার শোপো রোবো। আপনার দোকানের স্মার্ট AI সহকারী।',
        'tabs': {
            'inventory': '📦 স্টক তালিকা',
            'voice': '🎙️ AI ভয়েস',
            'barcode': '📷 বারকোড স্ক্যানার',
            'market': '📈 বাজার দর',
            'calculator': '🧮 লাভ ক্যালকুলেটর',
            'settings': '⚙️ সেটিংস'
        },
        'stats': {
            'stock_value': 'মোট স্টক মূল্য',
            'items_count': 'মোট সামগ্রী',
            'monthly_profit': 'মাসিক লাভ',
            'low_stock': 'কম স্টক সতর্কতা'
        },
        'buttons': {
            'add_item': '+ নতুন পণ্য যুক্ত করুন',
            'start_mic': '🎙️ কথা বলুন',
            'stop_mic': '⏹️ থামুন',
            'scan_barcode': '📷 বারকোড স্ক্যান',
            'calculate': '🧮 গণনা করুন',
            'save': '💾 সংরক্ষণ করুন'
        },
        'labels': {
            'item_name': 'পণ্যের নাম',
            'category': 'বিভাগ',
            'quantity': 'উপলব্ধ স্টক',
            'expiry': 'মেয়াদোত্তীর্ণ তারিখ',
            'buy_price': 'ক্রয় মূল্য',
            'sell_price': 'বিক্রয় মূল্য',
            'unit': 'একক',
            'profit_gain': 'লাভ',
            'status': 'অবস্থা'
        }
    },
    'kn': {
        'name': '🇮🇳 ಕನ್ನಡ (Kannada)',
        'app_title': 'ಶೋಪೋ ರೋಬೋ - AI ಅಂಗಡಿ ಸಹಾಯಕ',
        'welcome_msg': 'ನಮಸ್ಕಾರ! ನಾನು ನಿಮ್ಮ ಶೋಪೋ ರೋಬೋ. ನಿಮ್ಮ ಅಂಗಡಿಯ AI ಸಹಾಯಕ.',
        'tabs': {
            'inventory': '📦 ದಾಸ್ತಾನು ಪಟ್ಟಿ',
            'voice': '🎙️ AI ವಾಯ್ಸ್',
            'barcode': '📷 ಬಾರ್‌ಕೋಡ್ ಸ್ಕ್ಯಾನರ್',
            'market': '📈 ಮಾರುಕಟ್ಟೆ ದರ',
            'calculator': '🧮 ಲಾಭದ ಲೆಕ್ಕಾಚಾರ',
            'settings': '⚙️ ಸೆಟ್ಟಿಂಗ್ಸ್'
        },
        'stats': {
            'stock_value': 'ಒಟ್ಟು ದಾಸ್ತಾನು ಮೌಲ್ಯ',
            'items_count': 'ಒಟ್ಟು ವಸ್ತುಗಳು',
            'monthly_profit': 'ಮಾಸಿಕ ಲಾಭ',
            'low_stock': 'ಕಡಿಮೆ ದಾಸ್ತಾನು ಎಚ್ಚರಿಕೆ'
        },
        'buttons': {
            'add_item': '+ ಹೊಸ ವಸ್ತು ಸೇರಿಸಿ',
            'start_mic': '🎙️ ಮಾತನಾಡಿ',
            'stop_mic': '⏹️ ನಿಲ್ಲಿಸಿ',
            'scan_barcode': '📷 ಬಾರ್‌ಕೋಡ್ ಸ್ಕ್ಯಾನ್',
            'calculate': '🧮 ಲೆಕ್ಕ ಮಾಡಿ',
            'save': '💾 ಉಳಿಸಿ'
        },
        'labels': {
            'item_name': 'ವಸ್ತುವಿನ ಹೆಸರು',
            'category': 'ವರ್ಗ',
            'quantity': 'ದಾಸ್ತಾನು ಪ್ರಮಾಣ',
            'expiry': 'ಅವಧಿ ಮುಗಿಯುವ ದಿನಾಂಕ',
            'buy_price': 'ಖರೀದಿ ಬೆಲೆ',
            'sell_price': 'ಮಾರಾಟ ಬೆಲೆ',
            'unit': 'ಘಟಕ',
            'profit_gain': 'ಲಾಭ',
            'status': 'ಸ್ಥಿತಿ'
        }
    },
    'pa': {
        'name': '🇮🇳 ਪੰਜਾਬੀ (Punjabi)',
        'app_title': 'ਸ਼ੋਪੋ ਰੋਬੋ - AI ਦੁਕਾਨ ਸਹਾਇਕ',
        'welcome_msg': 'ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ! ਮੈਂ ਤੁਹਾਡਾ ਸ਼ੋਪੋ ਰੋਬੋ ਹਾਂ। ਤੁਹਾਡੀ ਦੁਕਾਨ ਦਾ AI ਸਾਥੀ।',
        'tabs': {
            'inventory': '📦 ਸਟਾਕ ਸੂਚੀ',
            'voice': '🎙️ AI ਵੌਇਸ',
            'barcode': '📷 ਬਾਰਕੋਡ ਸਕੈਨਰ',
            'market': '📈 ਮੰਡੀ ਦੇ ਭਾਅ',
            'calculator': '🧮 ਮੁਨਾਫਾ ਕੈਲਕੁਲੇਟਰ',
            'settings': '⚙️ ਸੈਟਿੰਗਾਂ'
        },
        'stats': {
            'stock_value': 'ਕੁੱਲ ਸਟਾਕ ਮੁੱਲ',
            'items_count': 'ਕੁੱਲ ਆਈਟਮਾਂ',
            'monthly_profit': 'ਮਹੀਨਾਵਾਰ ਮੁਨਾਫਾ',
            'low_stock': 'ਘੱਟ ਸਟਾਕ ਚੇਤਾਵਨੀ'
        },
        'buttons': {
            'add_item': '+ ਨਵੀਂ ਆਈਟਮ ਸ਼ਾਮਲ ਕਰੋ',
            'start_mic': '🎙️ ਬੋਲ ਕੇ ਦੱਸੋ',
            'stop_mic': '⏹️ ਰੋਕੋ',
            'scan_barcode': '📷 ਬਾਰਕੋਡ ਸਕੈਨ ਕਰੋ',
            'calculate': '🧮 ਗਣਨਾ ਕਰੋ',
            'save': '💾 ਸੇਵ ਕਰੋ'
        },
        'labels': {
            'item_name': 'ਆਈਟਮ ਦਾ ਨਾਮ',
            'category': 'ਸ਼੍ਰੇਣੀ',
            'quantity': 'ਉਪਲਬਧ ਸਟਾਕ',
            'expiry': 'ਮਿਆਦ ਪੁੱਗਣ ਦੀ ਮਿਤੀ',
            'buy_price': 'ਖਰੀਦ ਮੁੱਲ',
            'sell_price': 'ਵੇਚ ਮੁੱਲ',
            'unit': 'ਇਕਾਈ',
            'profit_gain': 'ਮੁਨਾਫਾ',
            'status': 'ਸਥਿਤੀ'
        }
    }
}

DEFAULT_LANG = 'hi'

def get_text(lang_code: str, path: str, default: str = "") -> str:
    """Retrieve localized string with fallback to English."""
    lang = LANGUAGES.get(lang_code, LANGUAGES['en'])
    keys = path.split('.')
    val = lang
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            # Fallback to English
            fallback = LANGUAGES['en']
            for fk in keys:
                if isinstance(fallback, dict) and fk in fallback:
                    fallback = fallback[fk]
                else:
                    return default or path
            return str(fallback)
    return str(val)
