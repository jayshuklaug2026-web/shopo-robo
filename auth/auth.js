/**
 * Shopo Robo — Auth Flow Controller
 * ====================================
 * Handles all registration, OTP, login, forgot-password,
 * and shop-setup flows.
 *
 * Session tokens are stored in localStorage.
 * API calls go to /api/auth/* on the same origin.
 */

// ── API Base ──
const API = '/api/auth';

// ── Registration state (held in memory, not exposed) ──
const regState = {
    fullName: '',
    email: '',
    mobile: '',
    otpVerified: false,
};

// ── Forgot password state ──
const forgotState = {
    mobile: '',
    otpVerified: false,
};

// ── Timer references ──
let otpCountdownTimer = null;
let forgotCountdownTimer = null;

// ════════════════════════════════════════════
// SCREEN NAVIGATION
// ════════════════════════════════════════════

const REGISTRATION_SCREENS = ['register', 'otp', 'password', 'shop-setup'];
const PROGRESS_STEPS = { 'register': 1, 'otp': 2, 'password': 3, 'shop-setup': 4 };

function navigateTo(screenId) {
    // Hide all screens
    document.querySelectorAll('.auth-screen').forEach(s => s.classList.remove('active'));

    // Show target screen
    const target = document.getElementById(`screen-${screenId}`);
    if (target) target.classList.add('active');

    // Handle progress bar
    const progressBar = document.getElementById('progressBar');
    if (REGISTRATION_SCREENS.includes(screenId)) {
        progressBar.style.display = 'block';
        updateProgress(PROGRESS_STEPS[screenId]);
        // Add top padding to avoid overlap with fixed progress bar
        target.style.paddingTop = '100px';
    } else {
        progressBar.style.display = 'none';
        if (target) target.style.paddingTop = '';
    }

    // Scroll to top
    window.scrollTo(0, 0);
}

function updateProgress(activeStep) {
    document.querySelectorAll('.progress-step').forEach(step => {
        const n = parseInt(step.dataset.step);
        step.classList.remove('active', 'completed');
        if (n < activeStep) step.classList.add('completed');
        else if (n === activeStep) step.classList.add('active');
    });

    document.querySelectorAll('.progress-line').forEach(line => {
        const n = parseInt(line.dataset.line);
        line.classList.toggle('completed', n < activeStep);
    });
}

// ════════════════════════════════════════════
// SESSION MANAGEMENT
// ════════════════════════════════════════════

function getToken() {
    return localStorage.getItem('shopo_auth_token');
}

function setToken(token) {
    localStorage.setItem('shopo_auth_token', token);
}

function setUser(user) {
    localStorage.setItem('shopo_user', JSON.stringify(user));
}

function getUser() {
    try {
        return JSON.parse(localStorage.getItem('shopo_user'));
    } catch { return null; }
}

function clearSession() {
    localStorage.removeItem('shopo_auth_token');
    localStorage.removeItem('shopo_user');
}

// ════════════════════════════════════════════
// API HELPER
// ════════════════════════════════════════════

async function apiCall(endpoint, method = 'GET', body = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' },
    };

    const token = getToken();
    if (token) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }

    if (body) {
        options.body = JSON.stringify(body);
    }

    try {
        const response = await fetch(`${API}${endpoint}`, options);
        const data = await response.json();
        return { ok: response.ok, status: response.status, ...data };
    } catch (err) {
        console.error('API Error:', err);
        return {
            ok: false,
            success: false,
            message: 'Cannot connect to server. Please check your connection.',
        };
    }
}

// ════════════════════════════════════════════
// TOAST NOTIFICATIONS
// ════════════════════════════════════════════

function showToast(message, type = 'info', duration = 4000) {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        info: 'fa-info-circle',
        warning: 'fa-exclamation-triangle',
    };

    toast.innerHTML = `<i class="fas ${icons[type] || icons.info}"></i><span>${message}</span>`;
    container.appendChild(toast);

    toast.addEventListener('click', () => toast.remove());

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(40px)';
        toast.style.transition = 'all 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ════════════════════════════════════════════
// LOADING OVERLAY
// ════════════════════════════════════════════

function showLoading() {
    document.getElementById('loadingOverlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

function setButtonLoading(btnId, loading) {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    btn.disabled = loading;
    if (loading) {
        btn.dataset.originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Please wait...';
    } else if (btn.dataset.originalText) {
        btn.innerHTML = btn.dataset.originalText;
    }
}

// ════════════════════════════════════════════
// REGISTRATION — Step 1: Details
// ════════════════════════════════════════════

async function handleRegister(e) {
    e.preventDefault();

    const fullName = document.getElementById('regName').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const mobile = document.getElementById('regMobile').value.trim();

    if (!fullName || fullName.length < 2) {
        showToast('Please enter your full name.', 'error');
        return;
    }
    if (!email) {
        showToast('Please enter your email address.', 'error');
        return;
    }
    if (!mobile || !/^[6-9]\d{9}$/.test(mobile)) {
        showToast('Please enter a valid 10-digit Indian mobile number.', 'error');
        return;
    }

    setButtonLoading('btnRegister', true);

    // Check for duplicates
    const checkResult = await apiCall('/register/check', 'POST', {
        full_name: fullName,
        email: email,
        mobile: mobile,
    });

    if (!checkResult.success) {
        showToast(checkResult.message, 'error');
        setButtonLoading('btnRegister', false);
        return;
    }

    // Store registration state
    regState.fullName = fullName;
    regState.email = email;
    regState.mobile = mobile;
    regState.otpVerified = false;

    // Send OTP
    const otpResult = await apiCall('/otp/send', 'POST', {
        mobile: mobile,
        purpose: 'registration',
    });

    setButtonLoading('btnRegister', false);

    if (!otpResult.success) {
        showToast(otpResult.message, 'error');
        return;
    }

    // Show OTP screen
    document.getElementById('otpMobileDisplay').textContent = `+91 ${mobile.slice(0,5)} ${mobile.slice(5)}`;

    // Handle mock mode banner
    if (otpResult.mock_otp) {
        document.getElementById('mockBanner').style.display = 'flex';
        document.getElementById('mockOtpCode').textContent = otpResult.mock_otp;
    } else {
        document.getElementById('mockBanner').style.display = 'none';
    }

    showToast(otpResult.message, otpResult.mock_otp ? 'warning' : 'success');
    navigateTo('otp');
    startOtpCountdown(otpResult.resend_after || 30);
    focusFirstOtpBox();
}

// ════════════════════════════════════════════
// REGISTRATION — Step 2: OTP Verification
// ════════════════════════════════════════════

function getOtpValue() {
    const boxes = document.querySelectorAll('#screen-otp .otp-box');
    return Array.from(boxes).map(b => b.value).join('');
}

function focusFirstOtpBox() {
    const first = document.querySelector('#screen-otp .otp-box[data-index="0"]');
    if (first) setTimeout(() => first.focus(), 100);
}

function clearOtpBoxes(selector = '#screen-otp .otp-box') {
    document.querySelectorAll(selector).forEach(b => {
        b.value = '';
        b.classList.remove('filled', 'error');
    });
}

async function handleOtpVerify(e) {
    e.preventDefault();

    const otp = getOtpValue();
    if (otp.length !== 6) {
        showToast('Please enter all 6 digits of the OTP.', 'error');
        document.querySelectorAll('#screen-otp .otp-box').forEach(b => b.classList.add('error'));
        return;
    }

    setButtonLoading('btnVerifyOtp', true);

    const result = await apiCall('/otp/verify', 'POST', {
        mobile: regState.mobile,
        otp: otp,
        purpose: 'registration',
    });

    setButtonLoading('btnVerifyOtp', false);

    if (result.success) {
        regState.otpVerified = true;
        showToast('Mobile number verified! ✓', 'success');
        navigateTo('password');
        document.getElementById('newPassword').focus();
    } else {
        showToast(result.message, 'error');
        document.querySelectorAll('#screen-otp .otp-box').forEach(b => b.classList.add('error'));
        setTimeout(() => {
            clearOtpBoxes('#screen-otp .otp-box');
            focusFirstOtpBox();
        }, 600);
    }
}

async function handleResendOtp() {
    setButtonLoading('btnResendOtp', true);
    const result = await apiCall('/otp/send', 'POST', {
        mobile: regState.mobile,
        purpose: 'registration',
    });
    setButtonLoading('btnResendOtp', false);

    if (result.success) {
        showToast(result.message, result.mock_otp ? 'warning' : 'success');
        if (result.mock_otp) {
            document.getElementById('mockOtpCode').textContent = result.mock_otp;
        }
        clearOtpBoxes('#screen-otp .otp-box');
        startOtpCountdown(result.resend_after || 30);
    } else {
        showToast(result.message, 'error');
    }
}

function startOtpCountdown(seconds) {
    clearInterval(otpCountdownTimer);
    const timerEl = document.getElementById('otpTimer');
    const countdownEl = document.getElementById('otpCountdown');
    const resendBtn = document.getElementById('btnResendOtp');

    timerEl.style.display = 'block';
    resendBtn.style.display = 'none';

    let remaining = seconds;
    countdownEl.textContent = remaining;

    otpCountdownTimer = setInterval(() => {
        remaining--;
        countdownEl.textContent = remaining;

        if (remaining <= 0) {
            clearInterval(otpCountdownTimer);
            timerEl.style.display = 'none';
            resendBtn.style.display = 'inline-flex';
        }
    }, 1000);
}

// ════════════════════════════════════════════
// REGISTRATION — Step 3: Password
// ════════════════════════════════════════════

async function handleSetPassword(e) {
    e.preventDefault();

    const password = document.getElementById('newPassword').value;
    const confirm = document.getElementById('confirmPassword').value;

    if (!validatePasswordUI(password)) {
        showToast('Please meet all password requirements.', 'error');
        return;
    }

    if (password !== confirm) {
        document.getElementById('confirmError').style.display = 'block';
        showToast('Passwords do not match.', 'error');
        return;
    }
    document.getElementById('confirmError').style.display = 'none';

    setButtonLoading('btnSetPassword', true);

    const result = await apiCall('/register/complete', 'POST', {
        full_name: regState.fullName,
        email: regState.email,
        mobile: regState.mobile,
        password: password,
        confirm_password: confirm,
    });

    setButtonLoading('btnSetPassword', false);

    if (result.success) {
        // Save session
        setToken(result.data.token);
        setUser(result.data.user);

        // Trigger Animated Account Creation Celebration (Prompt Section 4)
        const successUserEl = document.getElementById('successUserName');
        if (successUserEl) successUserEl.textContent = result.data.user.full_name;
        startAccountCreationCelebration(result.data.user);
    } else {
        showToast(result.message, 'error');
    }
}

// Password validation UI
function validatePasswordUI(password) {
    const rules = {
        length: password.length >= 8,
        upper: /[A-Z]/.test(password),
        digit: /[0-9]/.test(password),
    };

    // Update rule indicators
    ['length', 'upper', 'digit'].forEach(rule => {
        const el = document.getElementById(`rule-${rule}`);
        if (el) el.classList.toggle('pass', rules[rule]);
    });

    // Strength bar
    const passed = Object.values(rules).filter(Boolean).length;
    const fill = document.getElementById('pwStrengthFill');
    const label = document.getElementById('pwStrengthLabel');

    const levels = [
        { pct: 0,   color: 'transparent', text: '' },
        { pct: 33,  color: '#EF4444',     text: 'Weak' },
        { pct: 66,  color: '#F59E0B',     text: 'Medium' },
        { pct: 100, color: '#22C55E',     text: 'Strong' },
    ];

    const level = levels[passed];
    fill.style.width = level.pct + '%';
    fill.style.background = level.color;
    label.textContent = level.text;
    label.style.color = level.color;

    return rules.length && rules.upper && rules.digit;
}

// ════════════════════════════════════════════
// CONFETTI EFFECT
// ════════════════════════════════════════════

function triggerConfetti() {
    const container = document.getElementById('confettiContainer');
    container.innerHTML = '';
    const colors = ['#84CC16', '#22C55E', '#F59E0B', '#3B82F6', '#EF4444', '#A855F7'];

    for (let i = 0; i < 24; i++) {
        const piece = document.createElement('div');
        piece.className = 'confetti-piece';
        piece.style.left = (Math.random() * 180 + 10) + 'px';
        piece.style.top = '20px';
        piece.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
        piece.style.animationDelay = (Math.random() * 0.5) + 's';
        piece.style.animationDuration = (1 + Math.random() * 1) + 's';
        piece.style.transform = `rotate(${Math.random() * 360}deg)`;
        container.appendChild(piece);
    }
}

// ════════════════════════════════════════════
// LOGIN
// ════════════════════════════════════════════

async function handleLogin(e) {
    e.preventDefault();

    const identifier = document.getElementById('loginId').value.trim();
    const password = document.getElementById('loginPassword').value;

    if (!identifier) {
        showToast('Please enter your email or mobile number.', 'error');
        return;
    }
    if (!password) {
        showToast('Please enter your password.', 'error');
        return;
    }

    setButtonLoading('btnLogin', true);

    const result = await apiCall('/login', 'POST', {
        identifier: identifier,
        password: password,
    });

    setButtonLoading('btnLogin', false);

    if (result.success) {
        setToken(result.data.token);
        setUser(result.data.user);
        showToast(result.message, 'success');

        // Redirect based on shop setup status
        if (result.data.user.is_shop_setup_complete) {
            // Go to main app
            setTimeout(() => { window.location.href = '/app/'; }, 800);
        } else {
            // Needs shop setup
            navigateTo('shop-setup');
        }
    } else {
        showToast(result.message, 'error');
    }
}

// ════════════════════════════════════════════
// FORGOT PASSWORD
// ════════════════════════════════════════════

async function handleForgotSendOtp(e) {
    e.preventDefault();

    const mobile = document.getElementById('forgotMobile').value.trim();
    if (!mobile || !/^[6-9]\d{9}$/.test(mobile)) {
        showToast('Please enter a valid 10-digit mobile number.', 'error');
        return;
    }

    forgotState.mobile = mobile;
    setButtonLoading('btnForgotSendOtp', true);

    const result = await apiCall('/otp/send', 'POST', {
        mobile: mobile,
        purpose: 'forgot_password',
    });

    setButtonLoading('btnForgotSendOtp', false);

    if (result.success) {
        document.getElementById('forgotOtpMobileDisplay').textContent = `+91 ${mobile.slice(0,5)} ${mobile.slice(5)}`;

        if (result.mock_otp) {
            document.getElementById('forgotMockBanner').style.display = 'flex';
            document.getElementById('forgotMockOtpCode').textContent = result.mock_otp;
        } else {
            document.getElementById('forgotMockBanner').style.display = 'none';
        }

        showToast(result.message, result.mock_otp ? 'warning' : 'success');
        document.getElementById('forgotStep1').style.display = 'none';
        document.getElementById('forgotStep2').style.display = 'block';
        startForgotOtpCountdown(result.resend_after || 30);

        const first = document.querySelector('.forgot-otp-box[data-index="0"]');
        if (first) setTimeout(() => first.focus(), 100);
    } else {
        showToast(result.message, 'error');
    }
}

async function handleForgotVerifyOtp(e) {
    e.preventDefault();

    const boxes = document.querySelectorAll('.forgot-otp-box');
    const otp = Array.from(boxes).map(b => b.value).join('');

    if (otp.length !== 6) {
        showToast('Please enter all 6 digits.', 'error');
        boxes.forEach(b => b.classList.add('error'));
        return;
    }

    setButtonLoading('btnForgotVerifyOtp', true);

    const result = await apiCall('/otp/verify', 'POST', {
        mobile: forgotState.mobile,
        otp: otp,
        purpose: 'forgot_password',
    });

    setButtonLoading('btnForgotVerifyOtp', false);

    if (result.success) {
        forgotState.otpVerified = true;
        showToast('Verified! Set your new password.', 'success');
        document.getElementById('forgotStep2').style.display = 'none';
        document.getElementById('forgotStep3').style.display = 'block';
        document.getElementById('forgotNewPassword').focus();
    } else {
        showToast(result.message, 'error');
        boxes.forEach(b => b.classList.add('error'));
        setTimeout(() => {
            boxes.forEach(b => { b.value = ''; b.classList.remove('filled', 'error'); });
            const first = document.querySelector('.forgot-otp-box[data-index="0"]');
            if (first) first.focus();
        }, 600);
    }
}

async function handleForgotResetPassword(e) {
    e.preventDefault();

    const password = document.getElementById('forgotNewPassword').value;
    const confirm = document.getElementById('forgotConfirmPassword').value;

    if (password.length < 8) {
        showToast('Password must be at least 8 characters.', 'error');
        return;
    }
    if (password !== confirm) {
        showToast('Passwords do not match.', 'error');
        return;
    }

    setButtonLoading('btnForgotReset', true);

    const result = await apiCall('/forgot-password/reset', 'POST', {
        mobile: forgotState.mobile,
        password: password,
        confirm_password: confirm,
    });

    setButtonLoading('btnForgotReset', false);

    if (result.success) {
        showToast(result.message, 'success');
        // Reset forgot UI
        document.getElementById('forgotStep1').style.display = 'block';
        document.getElementById('forgotStep2').style.display = 'none';
        document.getElementById('forgotStep3').style.display = 'none';
        forgotState.mobile = '';
        forgotState.otpVerified = false;
        // Go to login
        setTimeout(() => navigateTo('login'), 1000);
    } else {
        showToast(result.message, 'error');
    }
}

async function handleForgotResendOtp() {
    const result = await apiCall('/otp/send', 'POST', {
        mobile: forgotState.mobile,
        purpose: 'forgot_password',
    });

    if (result.success) {
        showToast(result.message, result.mock_otp ? 'warning' : 'success');
        if (result.mock_otp) {
            document.getElementById('forgotMockOtpCode').textContent = result.mock_otp;
        }
        clearOtpBoxes('.forgot-otp-box');
        startForgotOtpCountdown(result.resend_after || 30);
    } else {
        showToast(result.message, 'error');
    }
}

function startForgotOtpCountdown(seconds) {
    clearInterval(forgotCountdownTimer);
    const timerEl = document.getElementById('forgotOtpTimer');
    const countdownEl = document.getElementById('forgotOtpCountdown');
    const resendBtn = document.getElementById('btnForgotResend');

    timerEl.style.display = 'block';
    resendBtn.style.display = 'none';

    let remaining = seconds;
    countdownEl.textContent = remaining;

    forgotCountdownTimer = setInterval(() => {
        remaining--;
        countdownEl.textContent = remaining;
        if (remaining <= 0) {
            clearInterval(forgotCountdownTimer);
            timerEl.style.display = 'none';
            resendBtn.style.display = 'inline-flex';
        }
    }, 1000);
}

// ════════════════════════════════════════════
// SHOP SETUP
// ════════════════════════════════════════════

async function handleShopSetup(e) {
    e.preventDefault();

    const shopName = document.getElementById('shopName').value.trim();
    const shopType = document.querySelector('input[name="shopType"]:checked')?.value || '';
    const shopAddress = document.getElementById('shopAddress').value.trim();

    if (!shopName) {
        showToast('Please enter your shop name.', 'error');
        return;
    }

    setButtonLoading('btnShopSetup', true);

    const result = await apiCall('/shop/setup', 'POST', {
        shop_name: shopName,
        shop_type: shopType,
        shop_address: shopAddress,
    });

    setButtonLoading('btnShopSetup', false);

    if (result.success) {
        const user = getUser();
        if (user) {
            user.is_shop_setup_complete = true;
            user.shop_name = shopName;
            user.shop_type = shopType;
            setUser(user);
        }
        showToast('Shop setup complete! 🎉', 'success');
        setTimeout(() => { window.location.href = '/app/'; }, 1000);
    } else {
        showToast(result.message, 'error');
    }
}

function skipShopSetup() {
    showToast('You can set up your shop later from Settings.', 'info');
    setTimeout(() => { window.location.href = '/app/'; }, 800);
}

// ════════════════════════════════════════════
// PASSWORD TOGGLE
// ════════════════════════════════════════════

function togglePassword(inputId, btn) {
    const input = document.getElementById(inputId);
    const icon = btn.querySelector('i');
    if (input.type === 'password') {
        input.type = 'text';
        icon.className = 'fas fa-eye-slash';
    } else {
        input.type = 'password';
        icon.className = 'fas fa-eye';
    }
}

// ════════════════════════════════════════════
// OTP BOX AUTO-ADVANCE
// ════════════════════════════════════════════

function setupOtpBoxes(containerSelector) {
    const boxes = document.querySelectorAll(`${containerSelector} .otp-box`);
    boxes.forEach((box, i) => {
        box.addEventListener('input', (e) => {
            const val = e.target.value.replace(/[^0-9]/g, '');
            e.target.value = val.slice(0, 1);

            if (val && i < boxes.length - 1) {
                boxes[i + 1].focus();
            }
            box.classList.toggle('filled', !!val);
            box.classList.remove('error');
        });

        box.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' && !box.value && i > 0) {
                boxes[i - 1].focus();
                boxes[i - 1].value = '';
                boxes[i - 1].classList.remove('filled');
            }
        });

        box.addEventListener('paste', (e) => {
            e.preventDefault();
            const pasted = (e.clipboardData.getData('text') || '').replace(/[^0-9]/g, '').slice(0, 6);
            pasted.split('').forEach((digit, j) => {
                if (boxes[j]) {
                    boxes[j].value = digit;
                    boxes[j].classList.add('filled');
                }
            });
            const nextEmpty = Array.from(boxes).findIndex(b => !b.value);
            if (nextEmpty >= 0) boxes[nextEmpty].focus();
            else boxes[boxes.length - 1].focus();
        });
    });
}

// ════════════════════════════════════════════
// PASSWORD STRENGTH LIVE CHECK
// ════════════════════════════════════════════

function setupPasswordStrength() {
    const pwInput = document.getElementById('newPassword');
    if (pwInput) {
        pwInput.addEventListener('input', () => {
            validatePasswordUI(pwInput.value);
        });
    }
}

// ════════════════════════════════════════════
// AUTO-SESSION CHECK ON LOAD
// ════════════════════════════════════════════

async function checkExistingSession() {
    const token = getToken();
    if (!token) return;

    try {
        const result = await apiCall('/session', 'GET');
        if (result.success && result.data?.user) {
            const user = result.data.user;
            setUser(user);

            if (user.is_shop_setup_complete) {
                window.location.href = '/app/';
            } else {
                navigateTo('shop-setup');
            }
        } else {
            // Invalid session — clear and show welcome
            clearSession();
        }
    } catch {
        // Server not reachable — clear session
        clearSession();
    }
}

// ════════════════════════════════════════════
// INITIALISATION
// ════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    // Setup OTP box auto-advance for both registration and forgot password
    setupOtpBoxes('#screen-otp');
    setupOtpBoxes('#forgotStep2');

    // Auto-fill development OTP when developer clicks the mock banner
    const mockBanner = document.getElementById('mockBanner');
    if (mockBanner) {
        mockBanner.addEventListener('click', () => {
            const code = document.getElementById('mockOtpCode')?.textContent?.trim() || '123456';
            const boxes = document.querySelectorAll('#screen-otp .otp-box');
            code.split('').forEach((d, i) => {
                if (boxes[i]) {
                    boxes[i].value = d;
                    boxes[i].classList.add('filled');
                    boxes[i].classList.remove('error');
                }
            });
            if (boxes[boxes.length - 1]) boxes[boxes.length - 1].focus();
        });
    }

    const forgotMockBanner = document.getElementById('forgotMockBanner');
    if (forgotMockBanner) {
        forgotMockBanner.addEventListener('click', () => {
            const code = document.getElementById('forgotMockOtpCode')?.textContent?.trim() || '123456';
            const boxes = document.querySelectorAll('.forgot-otp-box');
            code.split('').forEach((d, i) => {
                if (boxes[i]) {
                    boxes[i].value = d;
                    boxes[i].classList.add('filled');
                    boxes[i].classList.remove('error');
                }
            });
            if (boxes[boxes.length - 1]) boxes[boxes.length - 1].focus();
        });
    }

    // Setup password strength indicator
    setupPasswordStrength();

    // Check if user already has a valid session
    checkExistingSession();
});


// ════════════════════════════════════════════
// ACCOUNT CREATION CELEBRATION (Section 4)
// ════════════════════════════════════════════

let celebrationVoiceUtterance = null;
let celebrationVoiceTimer = null;

function startAccountCreationCelebration(user) {
    navigateTo('celebration');

    // Generate confetti particles
    generateCelebrationParticles();

    // Voice Dialogue Timed Trigger (after robot arrives and thumbs up pops at ~2.1s)
    if (celebrationVoiceTimer) clearTimeout(celebrationVoiceTimer);
    celebrationVoiceTimer = setTimeout(() => {
        playCelebrationVoice("Congratulations! Your Shopo account is created, Boss!");
    }, 2100);
}

function generateCelebrationParticles() {
    const container = document.getElementById('celebrationConfetti');
    if (!container) return;
    container.innerHTML = '';

    const colors = ['#84CC16', '#16803C', '#22C55E', '#A3E635', '#F59E0B', '#10B981'];
    const particleCount = 42;

    for (let i = 0; i < particleCount; i++) {
        const p = document.createElement('div');
        p.className = 'confetti-particle';
        const color = colors[Math.floor(Math.random() * colors.length)];
        const left = Math.random() * 100;
        const width = 6 + Math.random() * 8;
        const height = 8 + Math.random() * 12;
        const delay = Math.random() * 3.2;
        const duration = 2.8 + Math.random() * 2.2;

        p.style.left = `${left}%`;
        p.style.width = `${width}px`;
        p.style.height = `${height}px`;
        p.style.background = color;
        p.style.animationDelay = `${delay}s`;
        p.style.animationDuration = `${duration}s`;

        container.appendChild(p);
    }
}

function playCelebrationVoice(sentence) {
    if (!('speechSynthesis' in window)) return;
    try {
        window.speechSynthesis.cancel();
        celebrationVoiceUtterance = new SpeechSynthesisUtterance(sentence);
        celebrationVoiceUtterance.rate = 0.96;
        celebrationVoiceUtterance.pitch = 1.05;
        celebrationVoiceUtterance.lang = 'en-IN';

        celebrationVoiceUtterance.onstart = () => {
            const btn = document.getElementById('speechAudioBtn');
            if (btn) btn.classList.add('playing');
        };
        celebrationVoiceUtterance.onend = () => {
            const btn = document.getElementById('speechAudioBtn');
            if (btn) btn.classList.remove('playing');
        };
        celebrationVoiceUtterance.onerror = () => {
            const btn = document.getElementById('speechAudioBtn');
            if (btn) btn.classList.remove('playing');
        };

        window.speechSynthesis.speak(celebrationVoiceUtterance);
    } catch (e) {
        console.warn('Speech synthesis bypassed:', e);
    }
}

function toggleCelebrationAudio() {
    if ('speechSynthesis' in window && window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
        const btn = document.getElementById('speechAudioBtn');
        if (btn) btn.classList.remove('playing');
    } else {
        playCelebrationVoice("Congratulations! Your Shopo account is created, Boss!");
    }
}

function proceedToShopSetup() {
    if (celebrationVoiceTimer) {
        clearTimeout(celebrationVoiceTimer);
        celebrationVoiceTimer = null;
    }
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
    }
    // Navigate cleanly to the existing Shop Setup screen (Section 4, Step 6)
    navigateTo('shop-setup');
}
