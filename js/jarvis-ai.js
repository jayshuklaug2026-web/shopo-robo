/**
 * Shopo Robo - Jarvis AI Engine with India All Language Voice Pack
 * Supports:
 * - 🇮🇳 Hindi (hi-IN)
 * - 🇮🇳 English - India (en-IN)
 * - 🇮🇳 Tamil (ta-IN)
 * - 🇮🇳 Telugu (te-IN)
 * - 🇮🇳 Bengali (bn-IN)
 * - 🇮🇳 Marathi (mr-IN)
 * - 🇮🇳 Gujarati (gu-IN)
 * - 🇮🇳 Kannada (kn-IN)
 * - 🇮🇳 Malayalam (ml-IN)
 * - 🇮🇳 Punjabi (pa-IN)
 *
 * Integrated with the Autonomous AI Agent Model:
 * - Real-time stock health analysis (Critical / Low Stock / Optimal)
 * - Restock operations (Restock +50 units)
 * - Real wholesale commodity pricing
 * - Multi-lingual Text-to-Speech & Speech-to-Text
 */

class JarvisAI {
    constructor() {
        this.isListening = false;
        this.isSpeaking = false;
        this.voiceEnabled = true;
        this.recognition = null;
        this.synthesis = window.speechSynthesis;
        this.audioCtx = null;
        this.currentLang = 'hi-IN'; // Default Hindi / Indian English
        this.voicesList = [];

        // Supported Indian Languages Map
        this.languagePacks = {
            'hi-IN': { name: 'हिन्दी (Hindi)', code: 'hi-IN', greeting: 'नमस्ते शॉप ओनर! मैं आपका एआई असिस्टेंट जार्विस हूँ। मैं आपकी दुकान कैसे संभालूँ?' },
            'en-IN': { name: 'English (India)', code: 'en-IN', greeting: 'Hello Shop Owner! I am your AI assistant Jarvis. How can I manage your store today?' },
            'ta-IN': { name: 'தமிழ் (Tamil)', code: 'ta-IN', greeting: 'வணக்கம் கடை உரிமையாளரே! நான் உங்கள் AI உதவியாளர் ஜார்விஸ். நான் உங்களுக்கு எவ்வாறு உதவ முடியும்?' },
            'te-IN': { name: 'తెలుగు (Telugu)', code: 'te-IN', greeting: 'నమస్కారం షాప్ యజమాని! నేను మీ AI అసిస్టెంట్ జార్విస్. నేను మీకు ఎలా సహాయం చేయగలను?' },
            'bn-IN': { name: 'বাংলা (Bengali)', code: 'bn-IN', greeting: 'নমস্কার দোকানদার মশাই! আমি আপনার AI সহকারী জার্ভিস। আজ আপনাকে কীভাবে সাহায্য করতে পারি?' },
            'mr-IN': { name: 'मराठी (Marathi)', code: 'mr-IN', greeting: 'नमस्कार दुकानदार शेठ! मी आपला AI सहाय्यक जार्व्हिस आहे. मी आज आपल्याला कशी मदत करू?' },
            'gu-IN': { name: 'ગુજરાતી (Gujarati)', code: 'gu-IN', greeting: 'નમસ્તે દુકાનદાર ભાઈ! હું તમારો AI સહાયક જાર્વિસ છું. હું આજે તમને કેવી રીતે મદદ કરી શકું?' },
            'kn-IN': { name: 'ಕನ್ನಡ (Kannada)', code: 'kn-IN', greeting: 'ನಮಸ್ಕಾರ ಅಂಗಡಿ ಮಾಲೀಕರೇ! ನಾನು ನಿಮ್ಮ AI ಸಹಾಯಕ ಜಾರ್ವಿಸ್. ನಾನು ನಿಮಗೆ ಹೇಗೆ ಸಹಾಯ ಮಾಡಲಿ?' },
            'ml-IN': { name: 'മലയാളം (Malayalam)', code: 'ml-IN', greeting: 'നമസ്കാരം കടയുടമ! ഞാൻ നിങ്ങളുടെ AI സഹായിയായ ജാർവിസ് ആണ്. ഞാൻ നിങ്ങളെ എങ്ങനെ സഹായിക്കണം?' },
            'pa-IN': { name: 'ਪੰਜਾਬੀ (Punjabi)', code: 'pa-IN', greeting: 'ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ ਦੁਕਾਨਦਾਰ ਜੀ! ਮੈਂ ਤੁਹਾਡਾ AI ਸਹਾਇਕ ਜਾਰਵਿਸ ਹਾਂ। ਮੈਂ ਤੁਹਾਡੀ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?' }
        };
    }

    init() {
        this.speechBubble = document.getElementById('jarvisSpeechBubble');
        this.statusEl = document.getElementById('jarvisStatusText');
        this.micBtn = document.getElementById('jarvisMicBtn');
        this.chatContainer = document.getElementById('jarvisChatHistory');
        this.waveformCanvasLeft = document.getElementById('waveformCanvasLeft');
        this.waveformCanvasRight = document.getElementById('waveformCanvasRight');

        if (this.waveformCanvasLeft && this.waveformCanvasRight) {
            this.waveformCtxLeft = this.waveformCanvasLeft.getContext('2d');
            this.waveformCtxRight = this.waveformCanvasRight.getContext('2d');
            this.startWaveformAnimation();
        }

        // Initialize Speech Recognition with Indian Language
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRecognition) {
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            this.recognition.lang = this.currentLang;

            this.recognition.onstart = () => {
                this.isListening = true;
                this.updateUIStatus('Listening...', 'listening');
                this.playSound('start');
            };

            this.recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                console.log(`🗣️ Jarvis heard (${this.currentLang}):`, transcript);
                this.addUserMessage(transcript);
                this.processCommand(transcript);
            };

            this.recognition.onerror = (event) => {
                this.isListening = false;
                this.updateUIStatus('Ready', 'ready');
            };

            this.recognition.onend = () => {
                this.isListening = false;
                if (!this.isSpeaking) this.updateUIStatus('Ready', 'ready');
            };
        }

        // Load Synthesis Voices
        if (this.synthesis) {
            const populateVoices = () => {
                this.voicesList = this.synthesis.getVoices();
            };
            populateVoices();
            if (this.synthesis.onvoiceschanged !== undefined) {
                this.synthesis.onvoiceschanged = populateVoices;
            }
        }
    }

    // Switch Language Dynamically
    setLanguage(langCode) {
        if (this.languagePacks[langCode]) {
            this.currentLang = langCode;
            if (this.recognition) this.recognition.lang = langCode;
            StoreData.settings.selectedLanguage = langCode;

            const pack = this.languagePacks[langCode];
            const notice = `🇮🇳 Language switched to ${pack.name}`;
            this.showBotResponse(pack.greeting);
            if (window.showToast) window.showToast(notice);
            console.log(`🌐 Jarvis active language: ${pack.name} (${langCode})`);
        }
    }

    // Audio SFX using Web Audio API
    playSound(type = 'start') {
        try {
            if (!this.audioCtx) {
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                if (AudioContext) this.audioCtx = new AudioContext();
            }
            if (!this.audioCtx) return;
            if (this.audioCtx.state === 'suspended') this.audioCtx.resume();

            const osc = this.audioCtx.createOscillator();
            const gain = this.audioCtx.createGain();
            osc.connect(gain);
            gain.connect(this.audioCtx.destination);
            const now = this.audioCtx.currentTime;

            if (type === 'start') {
                osc.type = 'sine';
                osc.frequency.setValueAtTime(520, now);
                osc.frequency.exponentialRampToValueAtTime(880, now + 0.15);
                gain.gain.setValueAtTime(0.12, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
                osc.start(now);
                osc.stop(now + 0.25);
            } else if (type === 'reply') {
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(440, now);
                osc.frequency.setValueAtTime(660, now + 0.08);
                osc.frequency.setValueAtTime(880, now + 0.16);
                gain.gain.setValueAtTime(0.15, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
                osc.start(now);
                osc.stop(now + 0.3);
            }
        } catch (e) {}
    }

    // Toggle Listening
    toggleListening() {
        if (!this.recognition) {
            alert('Speech Recognition is not supported by your current browser. You can still type your command to Jarvis!');
            return;
        }

        if (this.isListening) {
            this.recognition.stop();
            this.isListening = false;
            this.updateUIStatus('Ready', 'ready');
        } else {
            try {
                if (this.isSpeaking && this.synthesis) {
                    this.synthesis.cancel();
                    this.isSpeaking = false;
                }
                this.recognition.lang = this.currentLang;
                this.recognition.start();
            } catch (err) {
                this.recognition.stop();
            }
        }
    }

    // Update UI Status
    updateUIStatus(text, state) {
        if (this.statusEl) this.statusEl.innerText = text;
        if (this.micBtn) {
            this.micBtn.classList.remove('listening', 'speaking');
            if (state === 'listening') this.micBtn.classList.add('listening');
            if (state === 'speaking') this.micBtn.classList.add('speaking');
        }
    }

    // Add User Message to Transcript
    addUserMessage(text) {
        if (!this.chatContainer) return;
        const msg = document.createElement('div');
        msg.className = 'chat-msg user-msg';
        msg.innerHTML = `<div class="msg-bubble"><span class="user-text">${this.escapeHTML(text)}</span></div>`;
        this.chatContainer.appendChild(msg);
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    }

    // Show Bot Response & Vocalize
    showBotResponse(text) {
        if (this.speechBubble) this.speechBubble.innerHTML = text;

        if (this.chatContainer) {
            const msg = document.createElement('div');
            msg.className = 'chat-msg bot-msg';
            msg.innerHTML = `
                <div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>
                <div class="msg-bubble"><span class="bot-text">${text}</span></div>
            `;
            this.chatContainer.appendChild(msg);
            this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
        }

        this.speak(text);
    }

    // Text to Speech in the Selected Indian Language
    speak(text) {
        if (!this.voiceEnabled || !this.synthesis) return;

        const cleanText = text.replace(/<[^>]*>?/gm, '').replace(/₹/g, 'Rupees ').replace(/%/g, ' percent ');
        this.synthesis.cancel();

        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = this.currentLang;

        // Find best matching voice for current Indian language
        const prefix = this.currentLang.split('-')[0];
        const matchVoice = this.voicesList.find(v => v.lang === this.currentLang || v.lang.startsWith(prefix));
        if (matchVoice) utterance.voice = matchVoice;

        utterance.rate = 1.0;
        utterance.pitch = 1.02;

        utterance.onstart = () => {
            this.isSpeaking = true;
            this.updateUIStatus('Jarvis Speaking...', 'speaking');
            this.playSound('reply');
        };

        utterance.onend = () => {
            this.isSpeaking = false;
            this.updateUIStatus('Ready', 'ready');
        };

        utterance.onerror = () => {
            this.isSpeaking = false;
            this.updateUIStatus('Ready', 'ready');
        };

        this.synthesis.speak(utterance);
    }

    // Audio Waveform Visualizer
    startWaveformAnimation() {
        if (!this.waveformCanvasLeft || !this.waveformCanvasRight) return;
        const leftCanvas = this.waveformCanvasLeft;
        const rightCanvas = this.waveformCanvasRight;
        const leftCtx = this.waveformCtxLeft;
        const rightCtx = this.waveformCtxRight;

        let phase = 0;

        const drawBars = (canvas, ctx, reverse = false) => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            const w = canvas.width;
            const h = canvas.height;
            const cy = h / 2;

            const active = this.isListening || this.isSpeaking;
            const bars = 8;
            const barWidth = 4;
            const spacing = (w - (bars * barWidth)) / (bars - 1);

            for (let i = 0; i < bars; i++) {
                let height = 6;
                const idx = reverse ? (bars - 1 - i) : i;
                if (active) {
                    const wave = Math.sin(phase + idx * 0.6);
                    height = Math.max(5, Math.abs(wave) * 16 + (Math.random() * 4));
                }

                const x = i * (barWidth + spacing);
                const y = cy - height / 2;

                ctx.fillStyle = active ? '#84CC16' : '#E2E8F0';
                ctx.beginPath();
                if (ctx.roundRect) ctx.roundRect(x, y, barWidth, height, 2);
                else ctx.rect(x, y, barWidth, height);
                ctx.fill();
            }
        };

        const draw = () => {
            drawBars(leftCanvas, leftCtx, false);
            drawBars(rightCanvas, rightCtx, true);
            const active = this.isListening || this.isSpeaking;
            phase += active ? 0.25 : 0.05;
            this.animFrameId = requestAnimationFrame(draw);
        };

        draw();
    }

    // Process Spoken Query Across Indian Languages
    async processCommand(rawText) {
        const query = rawText.toLowerCase().trim();
        console.log('🤖 Jarvis processing command:', query);

        // 1. Restock Action (User's Model: handleRestock +50 units)
        if (query.includes('restock') || query.includes('reorder') || query.includes('bhar') || query.includes('maal') || query.includes('chadhaye')) {
            const item = StoreData.inventory.find(i => query.includes(i.name.toLowerCase()) || i.name.toLowerCase().includes('sugar') && query.includes('cheeni') || i.name.toLowerCase().includes('rice') && query.includes('chawal') || i.name.toLowerCase().includes('display') && query.includes('display') || i.name.toLowerCase().includes('processor') && query.includes('processor'));

            if (item) {
                const res = StoreData.handleRestock(item.id);
                this.showBotResponse(`📦 AI Restocked: ${item.name} has been replenished (+50 units). Stock is now ${item.quantity} (${item.status}).`);
                if (window.renderAllViews) window.renderAllViews();
                return;
            } else {
                // Restock first low stock or critical item
                const critical = StoreData.inventory.find(i => i.status === 'Critical' || i.status === 'Low Stock');
                if (critical) {
                    StoreData.handleRestock(critical.id);
                    this.showBotResponse(`📦 Autonomous Restock executed for ${critical.name} (+50 units). Status is now Optimal.`);
                    if (window.renderAllViews) window.renderAllViews();
                    return;
                }
            }
        }

        // 2. Health & Critical Items Check
        if (query.includes('critical') || query.includes('khatam') || query.includes('shortage') || query.includes('low stock') || query.includes('kam hai')) {
            const criticals = StoreData.inventory.filter(i => (i.quantity || i.stock) < 15);
            const low = StoreData.inventory.filter(i => (i.quantity || i.stock) < 50);

            if (criticals.length > 0) {
                const names = criticals.map(c => `${c.name} (${c.quantity} ${c.unit || 'left'})`).join(', ');
                this.showBotResponse(`⚠️ Critical Shortage Warning! Items below 15 units: ${names}. Jarvis recommends immediate restocking.`);
            } else if (low.length > 0) {
                const names = low.map(l => `${l.name} (${l.quantity} ${l.unit || 'left'})`).join(', ');
                this.showBotResponse(`🟡 Low Stock Alert: ${names} are under 50 units. Restock advised soon.`);
            } else {
                this.showBotResponse(`✅ AI Status: Nominal. All inventory stock levels are optimal above 50 units.`);
            }
            if (window.switchView) window.switchView('inventory');
            return;
        }

        // 3. Khata (Udhar & Jama) Voice Transactions
        if (query.includes('udhar') || query.includes('jama') || query.includes('khata') || query.includes('bahi') || query.includes('credit') || query.includes('debit')) {
            const numbers = query.match(/\d+/g);
            const amount = numbers ? parseInt(numbers[0]) : null;

            if (amount !== null) {
                const isJama = query.includes('jama') || query.includes('diya') || query.includes('received') || query.includes('paid');
                const type = isJama ? 'jama' : 'udhar';

                // Extract customer name
                let name = 'Customer';
                const words = rawText.split(/\s+/);
                for (let i = 0; i < words.length; i++) {
                    const w = words[i].toLowerCase();
                    if (['ka', 'ke', 'ne', 'se', 'for', 'from'].includes(w) && i > 0 && isNaN(words[i-1])) {
                        name = words[i-1];
                        break;
                    }
                }

                StoreData.addKhataEntry(name, type, amount);
                const reply = type === 'udhar'
                    ? `📕 Khata Alert: ${name} ke account me ₹ ${amount} udhar likh diya gaya hai.`
                    : `📗 Khata Alert: ${name} se ₹ ${amount} jama prapt hua aur ledger update ho gaya!`;

                this.showBotResponse(reply);
                if (window.renderAllViews) window.renderAllViews();
                if (window.switchView) window.switchView('khata');
                return;
            } else {
                const reply = `📖 Dukandar Khata Summary: Total Market Udhar ₹ ${StoreData.stats.totalMarketUdhar.toLocaleString('en-IN')}, aur Total Jama prapt ₹ ${StoreData.stats.totalCustomerJama.toLocaleString('en-IN')} hai.`;
                this.showBotResponse(reply);
                if (window.switchView) window.switchView('khata');
                return;
            }
        }

        // 4. Category Stock & Wholesale Mandi Market Price Trend
        if (query.includes('market') || query.includes('mandi') || query.includes('price') || query.includes('trend') || query.includes('bhav') || query.includes('rate')) {
            const trends = StoreData.getActiveCategoryTrends();
            const summary = trends.slice(0, 3).map(t => `${t.name}: ₹${t.currentPrice}/${t.unit} (${t.changePct > 0 ? '+' : ''}${t.changePct}%)`).join(' | ');
            this.showBotResponse(`📈 Real Category Wholesale Trends: ${summary}. Jarvis signal: ${trends[0].signal}.`);
            if (window.switchView) window.switchView('market');
            return;
        }

        // 5. Profit & Sales Queries
        if (query.includes('profit') || query.includes('sale') || query.includes('revenue') || query.includes('kamai') || query.includes('faida')) {
            const s = StoreData.stats;
            this.showBotResponse(`💰 Financial Status: Today's Sales ₹ ${s.todaysSales.toLocaleString('en-IN')}, Monthly Revenue ₹ ${s.monthlySales.toLocaleString('en-IN')}, and Net Profit ₹ ${s.monthlyProfit.toLocaleString('en-IN')}. Operating health is strong!`);
            if (window.switchView) window.switchView('sales');
            return;
        }

        // 6. Reports Month End Query
        if (query.includes('report') || query.includes('pdf') || query.includes('audit')) {
            this.showBotResponse(`📑 Notice: Aapki official store audit report month end par PDF format me available hogi. Aap abhi pre-audit preview download kar sakte hain.`);
            if (window.switchView) window.switchView('reports');
            return;
        }

        // Default Intelligent Fallback in Active Indian Language
        const reply = `Maine aapka instruction suna: "${rawText}". Main aapki dukan ka live stock, critical shortage alerts, category market rates, aur Khata ledger manage kar raha hu. Mujhe batayein kya karna hai!`;
        this.showBotResponse(reply);
    }

    escapeHTML(str) {
        return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }
}

window.JarvisEngine = new JarvisAI();
