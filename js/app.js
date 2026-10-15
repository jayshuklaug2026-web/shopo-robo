/**
 * Shopo Robo - Main Application Controller
 * Connects UI views, sidebar navigation, modals, event listeners, and voice actions.
 */

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Initialize GPS Weather, Supabase and Store Data
    if (window.WeatherGPS) WeatherGPS.init();
    SupabaseManager.init();
    await StoreData.init();

    // 2. Initialize Jarvis AI & Charts
    JarvisEngine.init();
    ChartsManager.init();

    // 3. Render Dashboard and Views
    renderAllViews();

    // 4. Bind Global Event Handlers
    bindEventHandlers();
});

// Render everything across the app
function renderAllViews() {
    renderAuthHeader();
    renderStats();
    checkZeroInventoryState();
    renderCurrentStockTable();
    renderPnLCard();
    renderTopItems();
    renderMarketTrends();
    renderAlerts();
    renderKhataView();
    renderInventoryView();
    renderMarketTrendsView();
    renderStoreSetupView();
    ChartsManager.renderDashboardPnL();
}

// Render dynamic authentication status in header
function renderAuthHeader() {
    const container = document.getElementById('authHeaderContainer');
    if (!container) return;

    if (SupabaseManager.currentUser) {
        const u = SupabaseManager.currentUser;
        container.innerHTML = `
            <div class="user-profile-btn" style="padding: 4px 10px; cursor: default;">
                <img src="${u.photoURL}" style="width: 28px; height: 28px; border-radius: 50%;" alt="User">
                <div style="text-align: left; margin-left: 6px;">
                    <span class="user-name-text" style="font-size: 12px; display: block;">${u.displayName}</span>
                    <small style="display: block; font-size: 10px; color: #64748B;">${u.email}</small>
                </div>
                <button onclick="handleLogout(event)" title="Logout" style="background: none; border: none; color: #EF4444; margin-left: 10px; cursor: pointer; font-size: 13px;">
                    <i class="fa-solid fa-right-from-bracket"></i>
                </button>
            </div>
        `;
    } else {
        container.innerHTML = `
            <button class="btn-primary-lime" onclick="openLoginModal()" style="padding: 6px 14px; font-size: 13px;">
                <i class="fa-brands fa-google"></i> Login with Gmail
            </button>
        `;
    }
}

// Check if store has 0 inventory and toggle zero-state onboarding
function checkZeroInventoryState() {
    const card = document.getElementById('zeroInventoryOnboardingCard');
    const welcomeTitle = document.getElementById('dashboardWelcomeTitle');
    const welcomeSubtitle = document.getElementById('dashboardWelcomeSubtitle');

    const u = SupabaseManager.currentUser;
    const ownerName = u ? u.displayName : StoreData.settings.ownerName;

    if (welcomeTitle) {
        welcomeTitle.innerText = `Welcome Back, ${ownerName}!`;
    }

    if (card) {
        if (StoreData.inventory.length === 0) {
            card.style.display = 'block';
            if (welcomeSubtitle) {
                welcomeSubtitle.innerText = 'Aapki inventory abhi 0 hai. Type karne ki zaroorat nahi hai — bas mic se Jarvis ko batayein!';
            }
        } else {
            card.style.display = 'none';
            if (welcomeSubtitle) {
                welcomeSubtitle.innerText = 'Your AI Assistant is always here to manage your store.';
            }
        }
    }
}

// 1. Render Top Metric Cards & AI Health Status
function renderStats() {
    const s = StoreData.stats;
    const cur = StoreData.settings.currency || '₹';

    const stockValEl = document.getElementById('statStockVal');
    const itemsCountEl = document.getElementById('statItemsCount');
    const todaySalesEl = document.getElementById('statTodaySales');
    const monthProfitEl = document.getElementById('statMonthProfit');

    if (stockValEl) stockValEl.innerText = `${cur} ${Number(s.totalStockValue).toLocaleString('en-IN')}`;
    if (itemsCountEl) itemsCountEl.innerText = s.totalItemsCount;
    if (todaySalesEl) todaySalesEl.innerText = `${cur} ${Number(s.todaysSales).toLocaleString('en-IN')}`;
    if (monthProfitEl) monthProfitEl.innerText = `${cur} ${Number(s.monthlyProfit).toLocaleString('en-IN')}`;

    // Dynamic AI Status Panel
    const aiStatusEl = document.getElementById('aiHealthStatusText');
    if (aiStatusEl) {
        aiStatusEl.innerText = s.aiStatusText;
        aiStatusEl.style.color = s.aiStatusColor;
    }

    // Reports View Figures
    const repRev = document.getElementById('reportRevenueVal');
    const repCogs = document.getElementById('reportCogsVal');
    const repProf = document.getElementById('reportProfitVal');
    if (repRev) repRev.innerText = `${cur} ${Number(s.monthlySales).toLocaleString('en-IN')}`;
    if (repCogs) repCogs.innerText = `${cur} ${Number(s.monthlyExpenses).toLocaleString('en-IN')}`;
    if (repProf) repProf.innerText = `${cur} ${Number(s.monthlyProfit).toLocaleString('en-IN')}`;
}

// Helper to get SVG product icon
function getProductIconSVG(type) {
    switch (type) {
        case 'sugar':
            return `<div class="prod-icon-box bg-lime-soft"><i class="fa-solid fa-bowl-rice text-lime"></i></div>`;
        case 'rice':
            return `<div class="prod-icon-box bg-amber-soft"><i class="fa-solid fa-wheat-awn text-amber"></i></div>`;
        case 'flour':
            return `<div class="prod-icon-box bg-lime-soft"><i class="fa-solid fa-wheat-awn-circle-exclamation text-lime"></i></div>`;
        case 'oil':
            return `<div class="prod-icon-box bg-amber-soft"><i class="fa-solid fa-bottle-droplet text-amber"></i></div>`;
        default:
            return `<div class="prod-icon-box bg-lime-soft"><i class="fa-solid fa-box-open text-lime"></i></div>`;
    }
}

// 2. Render Current Stock Levels (Integrated with User's AI Health Model)
function renderCurrentStockTable() {
    const tbody = document.getElementById('currentStockTableBody');
    if (!tbody) return;

    tbody.innerHTML = '';
    StoreData.inventory.forEach(item => {
        const tr = document.createElement('tr');
        tr.className = 'stock-row';

        const statusClass = item.status === 'Critical' 
            ? 'status-critical' 
            : (item.status === 'Low Stock' ? 'status-low' : 'status-optimal');

        const qty = item.quantity !== undefined ? item.quantity : item.stock;
        const price = item.price !== undefined ? item.price : item.sellPrice;

        tr.innerHTML = `
            <td class="item-name-cell">
                ${getProductIconSVG(item.icon)}
                <div class="item-text-info">
                    <span class="item-name">${item.name}</span>
                    <small class="text-xs text-slate-500" style="display: block;">₹ ${price} / ${item.unit || 'unit'}</small>
                </div>
            </td>
            <td class="item-qty-cell font-medium">${qty} ${item.unit || 'pcs'}</td>
            <td class="item-status-cell">
                <span class="status-badge ${statusClass}">${item.status}</span>
            </td>
            <td style="text-align: right;">
                <button class="action-btn restock-btn" onclick="handleRestockBtn(${item.id})">
                    <i class="fa-solid fa-plus"></i> Restock
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// 3. Render P&L Card Metrics
function renderPnLCard() {
    const cur = StoreData.settings.currency || '₹';
    const s = StoreData.stats;

    const salesVal = document.getElementById('pnlSalesVal');
    const expVal = document.getElementById('pnlExpensesVal');
    const profitVal = document.getElementById('pnlProfitVal');

    if (salesVal) salesVal.innerText = `${cur} ${Number(s.monthlySales).toLocaleString('en-IN')}`;
    if (expVal) expVal.innerText = `${cur} ${Number(s.monthlyExpenses).toLocaleString('en-IN')}`;
    if (profitVal) profitVal.innerText = `${cur} ${Number(s.monthlyProfit).toLocaleString('en-IN')}`;
}

// 4. Render Top Items (Best Selling vs Loss Making Tabs)
let currentTopItemsTab = 'best';

function switchTabTopItems(tab) {
    currentTopItemsTab = tab;
    const btnBest = document.getElementById('tabBestSelling');
    const btnLoss = document.getElementById('tabLossMaking');

    if (btnBest && btnLoss) {
        if (tab === 'best') {
            btnBest.classList.add('active');
            btnLoss.classList.remove('active');
        } else {
            btnBest.classList.remove('active');
            btnLoss.classList.add('active');
        }
    }
    renderTopItems();
}

function renderTopItems() {
    const listEl = document.getElementById('topItemsList');
    if (!listEl) return;

    listEl.innerHTML = '';

    if (currentTopItemsTab === 'best') {
        StoreData.bestSelling.forEach(item => {
            const li = document.createElement('div');
            li.className = 'top-item-row';
            li.innerHTML = `
                <div class="top-item-left">
                    <span class="rank-badge">${item.rank}</span>
                    <span class="top-item-name">${item.name}</span>
                </div>
                <div class="top-item-right">
                    <span class="top-item-sold">${item.soldQty}</span>
                    <span class="top-item-revenue text-lime-dark font-semibold">${item.revenue}</span>
                    <i class="fa-solid fa-chevron-right text-muted-chevron"></i>
                </div>
            `;
            listEl.appendChild(li);
        });
    } else {
        StoreData.lossMakingItems.forEach(item => {
            const li = document.createElement('div');
            li.className = 'top-item-row loss-row';
            li.innerHTML = `
                <div class="top-item-left">
                    <span class="rank-badge rank-badge-loss">${item.rank}</span>
                    <div>
                        <span class="top-item-name font-semibold">${item.name}</span>
                        <div class="text-xs text-muted-loss">${item.reason}</div>
                    </div>
                </div>
                <div class="top-item-right">
                    <span class="top-item-sold">${item.soldQty}</span>
                    <span class="top-item-loss text-red font-semibold">${item.lossAmount}</span>
                    <i class="fa-solid fa-chevron-right text-muted-chevron"></i>
                </div>
            `;
            listEl.appendChild(li);
        });
    }
}

// 5. Render Real Category Market Trends (Live Category Benchmarks)
function renderMarketTrends() {
    const container = document.getElementById('marketTrendsList');
    if (!container) return;

    container.innerHTML = '';
    const trends = StoreData.getActiveCategoryTrends();

    trends.slice(0, 5).forEach(trend => {
        const row = document.createElement('div');
        row.className = 'market-trend-row';

        const isUp = trend.changePct > 0;
        const trendClass = isUp ? 'trend-up' : (trend.changePct < 0 ? 'trend-down' : 'trend-neutral');
        const arrow = isUp ? '▲ +' : (trend.changePct < 0 ? '▼ ' : '• ');

        row.innerHTML = `
            <div class="market-item-left">
                <div class="prod-icon-box bg-lime-soft"><i class="fa-solid fa-chart-line text-lime"></i></div>
                <div>
                    <h5 class="market-item-name">${trend.name}</h5>
                    <span class="market-item-sub"><span class="font-semibold text-slate-800">₹ ${trend.currentPrice}/${trend.unit}</span> | <small class="text-xs text-slate-500">${trend.symbol}</small></span>
                </div>
            </div>
            <div class="market-item-right">
                <span class="trend-badge ${trendClass}">${arrow}${Math.abs(trend.changePct)}%</span>
            </div>
        `;
        container.appendChild(row);
    });
}

// 6. Render AI Alerts List
function renderAlerts() {
    const listEl = document.getElementById('aiAlertsList');
    if (!listEl) return;

    listEl.innerHTML = '';
    if (!StoreData.alerts || StoreData.alerts.length === 0) {
        listEl.innerHTML = `<div style="font-size: 13px; color: #64748B; padding: 10px 0;">No critical alerts. Inventory operations are running smoothly.</div>`;
        return;
    }

    StoreData.alerts.slice(0, 4).forEach(alert => {
        const div = document.createElement('div');
        div.className = `ai-alert-card severity-${alert.type}`;
        div.innerHTML = `
            <div class="alert-icon-wrapper"><i class="fa-solid ${alert.icon}"></i></div>
            <div class="alert-content">
                <div class="alert-text">${alert.text}</div>
            </div>
            <span class="alert-time">${alert.time}</span>
        `;
        listEl.appendChild(div);
    });
}

// 7. Render Full Inventory View
function renderInventoryView() {
    const tbody = document.getElementById('fullInventoryTableBody');
    if (!tbody) return;

    tbody.innerHTML = '';
    if (!StoreData.inventory || StoreData.inventory.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 36px; color: #64748B;">
                    <i class="fa-solid fa-boxes-stacked" style="font-size: 32px; color: var(--lime-500); display: block; margin-bottom: 10px;"></i>
                    Inventory abhi khali hai (0 items). Upar mic button dabaiye aur Jarvis ko bataiye!
                </td>
            </tr>
        `;
        return;
    }

    StoreData.inventory.forEach(item => {
        const tr = document.createElement('tr');
        const qty = item.quantity !== undefined ? item.quantity : item.stock || 0;
        const buy = item.buyPrice || 0;
        const sell = item.price !== undefined ? item.price : item.sellPrice || 0;
        const marginAmt = sell - buy;
        const marginPct = buy > 0 ? ((marginAmt / buy) * 100).toFixed(1) : '0.0';
        const marginClass = marginAmt >= 0 ? 'text-lime-dark font-semibold' : 'text-red font-semibold';

        const statusClass = item.status === 'Critical' 
            ? 'status-critical' 
            : (item.status === 'Low Stock' ? 'status-low' : 'status-optimal');

        tr.innerHTML = `
            <td class="item-name-cell">
                ${getProductIconSVG(item.icon)}
                <div class="item-text-info">
                    <span class="item-name">${item.name}</span>
                    <small class="text-xs text-slate-500" style="display: block;">Unit: ${item.unit || 'pcs'}</small>
                </div>
            </td>
            <td><span class="category-pill">${item.category || 'General'}</span></td>
            <td class="font-bold">${qty} ${item.unit || 'pcs'}</td>
            <td>₹ ${buy.toFixed(2)}</td>
            <td class="font-semibold">₹ ${sell.toFixed(2)}</td>
            <td class="${marginClass}">+₹ ${marginAmt.toFixed(2)} (${marginPct}%)</td>
            <td><span class="status-badge ${statusClass}">${item.status}</span></td>
            <td>
                <div style="display: flex; gap: 6px; align-items: center;">
                    <button class="action-btn restock-btn" onclick="handleRestockBtn(${item.id})" title="Autonomous +50 Restock">
                        <i class="fa-solid fa-plus"></i> Restock
                    </button>
                    <button class="action-btn" onclick="openStockModal(${item.id}, 'add')" title="Add Stock" style="padding: 4px 8px; font-size: 11px;">
                        In
                    </button>
                    <button class="action-btn" onclick="openStockModal(${item.id}, 'sale')" title="Record Sale" style="padding: 4px 8px; font-size: 11px;">
                        Sale
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// Restock Button Action Handler
function handleRestockBtn(id) {
    const res = StoreData.handleRestock(id);
    if (res.success) {
        showToast(res.message, 'success');
        renderAllViews();
        JarvisEngine.showBotResponse(`📦 Restocked 50 units for ${res.item.name}. Stock is now ${res.item.quantity} ${res.item.unit || 'units'} (${res.item.status}).`);
    } else {
        showToast('Item not found', 'warning');
    }
}

// 8. Render Market Trends Full View (Real Category Mandi & Stock Market Feed)
function renderMarketTrendsView() {
    const grid = document.getElementById('marketTrendsCardsGrid');
    if (!grid) return;

    grid.innerHTML = '';
    const trends = StoreData.getActiveCategoryTrends();

    trends.forEach(trend => {
        const card = document.createElement('div');
        card.className = 'market-detail-card';

        const isUp = trend.changePct > 0;
        const trendClass = isUp ? 'trend-up' : 'trend-down';
        const arrow = isUp ? '▲' : '▼';

        card.innerHTML = `
            <div class="mdc-header">
                <div>
                    <h4 class="font-bold text-lg text-slate-900">${trend.name}</h4>
                    <span class="text-xs text-slate-500 font-semibold">${trend.symbol} • Live Wholesale Mandi Benchmark</span>
                </div>
                <span class="trend-badge ${trendClass}">${arrow} ${trend.changePct}%</span>
            </div>
            <div class="mdc-body mt-3">
                <div class="price-stat-row">
                    <span>Wholesale Spot Rate:</span>
                    <strong class="text-lg text-slate-900">₹ ${trend.currentPrice} / ${trend.unit}</strong>
                </div>
                <div class="price-stat-row" style="font-size: 11px; color: #64748B;">
                    <span>Day Range:</span>
                    <span>Low: ₹${trend.low} - High: ₹${trend.high}</span>
                </div>
                <div class="ai-suggestion-box mt-2">
                    <i class="fa-solid fa-wand-magic-sparkles text-lime-dark"></i>
                    <span><strong>AI Signal: ${trend.signal}</strong>. Wholesale rate is ${isUp ? `up by ${trend.changePct}%. Adjust retail markup accordingly.` : `down by ${Math.abs(trend.changePct)}%. Optimal reorder timing.`}</span>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

// 9. Render Store Setup Templates
function renderStoreSetupView() {
    const currentType = StoreData.settings.shopType;
    const currentName = StoreData.settings.shopName;

    const setupCurrentBadge = document.getElementById('setupCurrentShopType');
    if (setupCurrentBadge) setupCurrentBadge.innerText = currentType;
}

// View Switching
function switchView(viewName) {
    const views = document.querySelectorAll('.app-view');
    views.forEach(v => v.classList.remove('active-view'));

    const target = document.getElementById(`view-${viewName}`);
    if (target) target.classList.add('active-view');

    const navItems = document.querySelectorAll('.nav-link');
    navItems.forEach(n => {
        if (n.getAttribute('data-view') === viewName) {
            n.classList.add('active');
        } else {
            n.classList.remove('active');
        }
    });

    if (viewName === 'sales') {
        setTimeout(() => ChartsManager.renderDetailedSalesChart(), 100);
    }
}

// Event Listeners Binding
function bindEventHandlers() {
    // Navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const view = link.getAttribute('data-view');
            if (view) switchView(view);
        });
    });

    // Mic Buttons
    const micBtn = document.getElementById('jarvisMicBtn');
    if (micBtn) {
        micBtn.addEventListener('click', () => JarvisEngine.toggleListening());
    }

    const topMicBtn = document.getElementById('topMicBtn');
    if (topMicBtn) {
        topMicBtn.addEventListener('click', () => JarvisEngine.toggleListening());
    }

    // Voice shortcut chips
    document.querySelectorAll('.voice-chip-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const cmd = btn.getAttribute('data-command') || btn.innerText.replace(/[^\w\s\?]/gi, '').trim();
            JarvisEngine.addUserMessage(cmd);
            JarvisEngine.processCommand(cmd);
        });
    });

    // Chat form submit
    const chatForm = document.getElementById('jarvisChatForm');
    const chatInput = document.getElementById('jarvisTextInput');
    if (chatForm && chatInput) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const text = chatInput.value.trim();
            if (text) {
                chatInput.value = '';
                JarvisEngine.addUserMessage(text);
                JarvisEngine.processCommand(text);
            }
        });
    }

    // Voice Sound Toggle
    const soundToggle = document.getElementById('toggleVoiceAudio');
    if (soundToggle) {
        soundToggle.addEventListener('click', () => {
            JarvisEngine.voiceEnabled = !JarvisEngine.voiceEnabled;
            soundToggle.innerHTML = JarvisEngine.voiceEnabled 
                ? '<i class="fa-solid fa-volume-high"></i>' 
                : '<i class="fa-solid fa-volume-xmark text-red"></i>';
            showToast(JarvisEngine.voiceEnabled ? 'Jarvis voice speech unmuted' : 'Jarvis voice speech muted');
        });
    }

    // Top Items Tabs
    const tabBest = document.getElementById('tabBestSelling');
    const tabLoss = document.getElementById('tabLossMaking');
    if (tabBest) tabBest.addEventListener('click', () => switchTabTopItems('best'));
    if (tabLoss) tabLoss.addEventListener('click', () => switchTabTopItems('loss'));

    // Supabase Connect Form
    const supabaseForm = document.getElementById('supabaseConfigForm');
    if (supabaseForm) {
        const urlInput = document.getElementById('sbUrlInput');
        const keyInput = document.getElementById('sbKeyInput');

        if (urlInput && SupabaseManager.config.url) urlInput.value = SupabaseManager.config.url;
        if (keyInput && SupabaseManager.config.anonKey) keyInput.value = SupabaseManager.config.anonKey;

        supabaseForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const url = urlInput.value.trim();
            const key = keyInput.value.trim();
            const res = SupabaseManager.connect(url, key);
            if (res.success) {
                showToast('Connected to Supabase Cloud Database!');
                updateSupabaseStatusBadge(true);
            } else {
                showToast(res.message, 'error');
            }
        });
    }

    // Quick Shop Type apply cards
    document.querySelectorAll('.btn-apply-shoptype').forEach(btn => {
        btn.addEventListener('click', () => {
            const type = btn.getAttribute('data-type');
            const res = StoreData.applyShopType(type);
            renderAllViews();
            showToast(`Shop type changed to ${res.name}!`);
            JarvisEngine.showBotResponse(`I have reconfigured your store inventory for ${res.name}. All product categories, units, and market baselines have been updated.`);
        });
    });

    // Search Inventory
    const invSearch = document.getElementById('inventorySearchInput');
    if (invSearch) {
        invSearch.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            const rows = document.querySelectorAll('#fullInventoryTableBody tr');
            rows.forEach(r => {
                const text = r.innerText.toLowerCase();
                r.style.display = text.includes(query) ? '' : 'none';
            });
        });
    }
}

// Modal Handlers
let selectedModalItemId = null;
let currentModalMode = 'add';

function openStockModal(itemId, mode = 'add') {
    selectedModalItemId = itemId;
    currentModalMode = mode;
    const item = StoreData.inventory.find(i => i.id === itemId);
    if (!item) return;

    const modal = document.getElementById('stockModal');
    const modalTitle = document.getElementById('stockModalTitle');
    const modalItemName = document.getElementById('stockModalItemName');
    const modalUnit = document.getElementById('stockModalUnit');
    const modalQty = document.getElementById('stockModalQty');

    if (modalTitle) modalTitle.innerText = mode === 'add' ? 'Stock In (Add Stock)' : 'Stock Out (Record Sale)';
    if (modalItemName) modalItemName.innerText = `${item.name} (Current: ${item.stock} ${item.unit})`;
    if (modalUnit) modalUnit.innerText = item.unit;
    if (modalQty) {
        modalQty.value = '';
        modalQty.focus();
    }

    if (modal) modal.classList.add('show-modal');
}

function closeStockModal() {
    const modal = document.getElementById('stockModal');
    if (modal) modal.classList.remove('show-modal');
}

async function confirmStockModal() {
    const modalQty = document.getElementById('stockModalQty');
    const qty = modalQty ? Number(modalQty.value) : 0;

    if (!qty || qty <= 0) {
        showToast('Please enter a valid quantity', 'warning');
        return;
    }

    const res = await StoreData.updateItemStock(selectedModalItemId, qty, currentModalMode);
    closeStockModal();
    renderAllViews();
    showToast(res.message);
    JarvisEngine.showBotResponse(`Updated: ${res.message}`);
}

function promptJarvisForItem(itemName) {
    const query = `Check stock for ${itemName}`;
    JarvisEngine.addUserMessage(query);
    JarvisEngine.processCommand(query);
}

// Add New Item Modal
function openAddItemModal() {
    const modal = document.getElementById('addItemModal');
    if (modal) modal.classList.add('show-modal');
}

function closeAddItemModal() {
    const modal = document.getElementById('addItemModal');
    if (modal) modal.classList.remove('show-modal');
}

async function handleAddNewItem(e) {
    e.preventDefault();
    const name = document.getElementById('newItemName').value.trim();
    const category = document.getElementById('newItemCategory').value.trim() || 'General';
    const stock = Number(document.getElementById('newItemStock').value) || 0;
    const unit = document.getElementById('newItemUnit').value.trim() || 'pcs';
    const buyPrice = Number(document.getElementById('newItemBuyPrice').value) || 0;
    const sellPrice = Number(document.getElementById('newItemSellPrice').value) || 0;
    const minThreshold = Number(document.getElementById('newItemMinThreshold').value) || 15;

    if (!name) {
        showToast('Item name is required', 'warning');
        return;
    }

    const newItem = {
        id: Date.now(),
        name,
        category,
        stock,
        quantity: stock,
        unit,
        minThreshold,
        buyPrice,
        price: sellPrice,
        sellPrice,
        marketPrice: sellPrice,
        marketChange: 0,
        status: stock < 15 ? 'Critical' : (stock < 50 ? 'Low Stock' : 'Optimal'),
        isLossMaking: sellPrice < buyPrice,
        icon: 'box'
    };

    StoreData.inventory.push(newItem);
    await SupabaseManager.saveItem(newItem);
    StoreData.recalculateStats();

    closeAddItemModal();
    renderAllViews();
    showToast(`Added ${name} to inventory!`);
    JarvisEngine.showBotResponse(`Added ${name} with ${stock} ${unit} to your inventory. Status: ${newItem.status}.`);
}

// Toast notification helper
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `shopo-toast toast-${type}`;
    toast.innerHTML = `<i class="fa-solid fa-circle-check"></i> <span>${message}</span>`;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add('visible'), 10);
    setTimeout(() => {
        toast.classList.remove('visible');
        setTimeout(() => toast.remove(), 300);
    }, 3200);
}

function updateSupabaseStatusBadge(connected) {
    const badge = document.getElementById('supabaseStatusBadge');
    if (badge) {
        badge.innerHTML = connected 
            ? `<span class="badge-connected"><i class="fa-solid fa-circle-check"></i> Supabase Connected</span>`
            : `<span class="badge-offline"><i class="fa-solid fa-cloud"></i> Local Storage (Offline Mode)</span>`;
    }
}

// Custom shop generator handler
function handleCustomShopGeneration() {
    const input = document.getElementById('customShopInput');
    const query = input ? input.value.trim() : '';

    if (!query) {
        showToast('Please type or speak your store type (e.g. Hardware, Footwear, Bakery)', 'warning');
        return;
    }

    const template = StoreData.applyShopType(query);
    if (input) input.value = '';
    renderAllViews();
    showToast(`Store initialized as ${template.name}!`);
    JarvisEngine.showBotResponse(`I have configured your entire store inventory for ${template.name}. I've set up relevant categories, standard units, wholesale buy rates, and profit margin targets!`);
}

// Render Khata (Digital Ledger) View
function renderKhataView() {
    const tbody = document.getElementById('khataTableBody');
    const totalUdharEl = document.getElementById('khataTotalUdhar');
    const totalJamaEl = document.getElementById('khataTotalJama');
    const totalCustEl = document.getElementById('khataTotalCustomers');

    const cur = StoreData.settings.currency || '₹';
    if (totalUdharEl) totalUdharEl.innerText = `${cur} ${Number(StoreData.stats.totalMarketUdhar || 0).toLocaleString('en-IN')}`;
    if (totalJamaEl) totalJamaEl.innerText = `${cur} ${Number(StoreData.stats.totalCustomerJama || 0).toLocaleString('en-IN')}`;

    const uniqueCustomers = new Set(StoreData.khata.map(k => k.customer_name));
    if (totalCustEl) totalCustEl.innerText = uniqueCustomers.size;

    if (!tbody) return;
    tbody.innerHTML = '';

    if (StoreData.khata.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" style="text-align: center; padding: 30px; color: #64748B;">
                    <i class="fa-solid fa-book-open" style="font-size: 28px; color: var(--lime-500); display: block; margin-bottom: 8px;"></i>
                    Khata ledger abhi khali hai. Mic dabayein aur boliye: <em>"Ramesh ka 500 rupaye udhar likho"</em>
                </td>
            </tr>
        `;
        return;
    }

    StoreData.khata.forEach(k => {
        const tr = document.createElement('tr');
        const isUdhar = k.entry_type === 'udhar';
        const badgeClass = isUdhar ? 'badge-udhar' : 'badge-jama';
        const typeText = isUdhar ? '🔴 Udhar (Debit)' : '🟢 Jama (Credit)';
        const amountColor = isUdhar ? 'text-red font-bold' : 'text-lime-dark font-bold';

        tr.innerHTML = `
            <td class="font-semibold"><i class="fa-solid fa-user text-slate-400" style="margin-right: 6px;"></i> ${k.customer_name}</td>
            <td class="text-sm text-slate-500">${k.date} ${k.time || ''}</td>
            <td><span class="status-badge ${badgeClass}">${typeText}</span></td>
            <td class="${amountColor}">₹ ${Number(k.amount).toLocaleString('en-IN')}</td>
            <td class="text-sm text-slate-600">${k.note || 'Recorded by Jarvis AI'}</td>
        `;
        tbody.appendChild(tr);
    });
}

// Gmail Login Modal Handlers
function openLoginModal() {
    const modal = document.getElementById('loginModal');
    if (modal) modal.classList.add('show-modal');
}

function closeLoginModal() {
    const modal = document.getElementById('loginModal');
    if (modal) modal.classList.remove('show-modal');
}

async function performGmailLogin(email, displayName) {
    await SupabaseManager.loginWithGmail(email, displayName);
    await StoreData.init();
    closeLoginModal();
    renderAllViews();
    showToast(`Logged in as ${email}`);
    JarvisEngine.showBotResponse(`Namaste ${displayName}! Aapka account login ho gaya hai. Aapki inventory abhi 0 hai. Koi typing ki zaroorat nahi hai — bas mic dabaiye aur apne dukan ke items bol kar batayein, main sab chadhata hu!`);
}

async function handleCustomGmailSubmit(e) {
    e.preventDefault();
    const email = document.getElementById('customUserEmailInput').value.trim();
    const name = document.getElementById('customUserNameInput').value.trim() || email.split('@')[0];
    if (email) {
        await performGmailLogin(email, name);
    }
}

function handleLogout(e) {
    if (e) e.stopPropagation();
    SupabaseManager.logout();
    StoreData.inventory = [];
    StoreData.khata = [];
    StoreData.recalculateStats();
    renderAllViews();
    showToast('Logged out successfully');
    openLoginModal();
}

// Download Pre-Audit Month-End PDF Report
function downloadPreAuditPDF() {
    const s = StoreData.stats;
    const cur = StoreData.settings.currency || '₹';
    const now = new Date();
    const dateStr = now.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    const monthName = now.toLocaleString('en-IN', { month: 'long', year: 'numeric' });
    const owner = (SupabaseManager.currentUser && SupabaseManager.currentUser.displayName) || StoreData.settings.ownerName || 'Dukandar';
    const email = (SupabaseManager.currentUser && SupabaseManager.currentUser.email) || StoreData.settings.userEmail;

    // Build printable HTML document for Month-End Audit
    const printWindow = window.open('', '_blank');
    if (!printWindow) {
        showToast('Please allow popups in your browser to print/download the Month-End PDF Report', 'warning');
        return;
    }

    let itemsRows = '';
    StoreData.inventory.forEach((item, idx) => {
        const qty = item.quantity !== undefined ? item.quantity : item.stock || 0;
        const buy = item.buyPrice || 0;
        const sell = item.price !== undefined ? item.price : item.sellPrice || 0;
        const totalVal = qty * sell;
        itemsRows += `
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid #E2E8F0;">${idx + 1}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #E2E8F0; font-weight: 600;">${item.name}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #E2E8F0;">${item.category || 'General'}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #E2E8F0; text-align: center;">${qty} ${item.unit || 'units'}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #E2E8F0; text-align: right;">₹${buy.toFixed(2)}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #E2E8F0; text-align: right;">₹${sell.toFixed(2)}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #E2E8F0; text-align: right; font-weight: 600;">₹${totalVal.toLocaleString('en-IN')}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #E2E8F0; text-align: center;">
                    <span style="display: inline-block; padding: 2px 8px; border-radius: 9999px; font-size: 11px; font-weight: bold; background: ${item.status === 'Critical' ? '#FEE2E2; color: #991B1B;' : (item.status === 'Low Stock' ? '#FEF3C7; color: #92400E;' : '#DCFCE7; color: #166534;')}">
                        ${item.status}
                    </span>
                </td>
            </tr>
        `;
    });

    let khataRows = '';
    StoreData.khata.forEach((k, idx) => {
        khataRows += `
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid #E2E8F0;">${idx + 1}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #E2E8F0; font-weight: 600;">${k.customer_name}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #E2E8F0;">${k.date} ${k.time || ''}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #E2E8F0; text-transform: uppercase; font-weight: bold; color: ${k.entry_type === 'udhar' ? '#DC2626' : '#16A34A'};">${k.entry_type}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #E2E8F0; text-align: right; font-weight: 700;">₹${Number(k.amount).toLocaleString('en-IN')}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid #E2E8F0; font-size: 12px; color: #64748B;">${k.note || '-'}</td>
            </tr>
        `;
    });

    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Shopo Robo - Month-End Commercial Audit Report (${monthName})</title>
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 40px; color: #0F172A; }
                .header { border-bottom: 3px solid #84CC16; padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-end; }
                .title { font-size: 26px; font-weight: 800; color: #0F172A; margin: 0; }
                .title span { color: #84CC16; }
                .subtitle { font-size: 13px; color: #64748B; margin-top: 4px; }
                .summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 24px; }
                .stat-box { background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px; }
                .stat-box h4 { margin: 0; font-size: 11px; text-transform: uppercase; color: #64748B; }
                .stat-box .val { font-size: 18px; font-weight: 800; color: #0F172A; margin-top: 4px; }
                .section-title { font-size: 16px; font-weight: 700; margin: 24px 0 10px 0; color: #1E293B; border-bottom: 1px solid #E2E8F0; padding-bottom: 6px; }
                table { width: 100%; border-collapse: collapse; font-size: 12px; margin-bottom: 20px; }
                th { background: #F1F5F9; padding: 8px 12px; text-align: left; font-weight: 700; color: #475569; }
                .footer { margin-top: 40px; font-size: 11px; color: #94A3B8; text-align: center; border-top: 1px solid #E2E8F0; padding-top: 16px; }
                @media print {
                    .no-print { display: none; }
                }
            </style>
        </head>
        <body>
            <div class="no-print" style="margin-bottom: 20px; display: flex; gap: 10px;">
                <button onclick="window.print()" style="background: #84CC16; color: #0F172A; font-weight: 700; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer;">
                    🖨️ Print / Save as PDF
                </button>
                <button onclick="window.close()" style="background: #F1F5F9; border: 1px solid #CBD5E1; padding: 10px 20px; border-radius: 6px; cursor: pointer;">
                    Close Window
                </button>
            </div>

            <div class="header">
                <div>
                    <h1 class="title">Shopo <span>Robo</span> Inventory Store</h1>
                    <div class="subtitle">Official Commercial Month-End Audit & Tax Ledger</div>
                    <div class="subtitle">Store: <strong>${StoreData.settings.shopName}</strong> | Owner: <strong>${owner}</strong> (${email})</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-weight: 700; font-size: 14px;">Audit Period: ${monthName}</div>
                    <div style="font-size: 12px; color: #64748B;">Generated: ${dateStr}</div>
                </div>
            </div>

            <div class="summary-grid">
                <div class="stat-box">
                    <h4>Total Stock Valuation</h4>
                    <div class="val">₹ ${Number(s.totalStockValue).toLocaleString('en-IN')}</div>
                </div>
                <div class="stat-box">
                    <h4>Monthly Sales Revenue</h4>
                    <div class="val">₹ ${Number(s.monthlySales).toLocaleString('en-IN')}</div>
                </div>
                <div class="stat-box">
                    <h4>Net Monthly Profit</h4>
                    <div class="val" style="color: #16A34A;">₹ ${Number(s.monthlyProfit).toLocaleString('en-IN')}</div>
                </div>
                <div class="stat-box">
                    <h4>Market Udhar (Receivables)</h4>
                    <div class="val" style="color: #DC2626;">₹ ${Number(s.totalMarketUdhar).toLocaleString('en-IN')}</div>
                </div>
            </div>

            <div class="section-title">📦 Inventory Physical & Valuation Ledger</div>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Item Description</th>
                        <th>Category</th>
                        <th style="text-align: center;">Stock Qty</th>
                        <th style="text-align: right;">Wholesale Buy</th>
                        <th style="text-align: right;">Retail Sell</th>
                        <th style="text-align: right;">Total Value</th>
                        <th style="text-align: center;">AI Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${itemsRows}
                </tbody>
            </table>

            <div class="section-title">📖 Dukandar Digital Khata (Customer Ledger)</div>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Customer Name</th>
                        <th>Date & Time</th>
                        <th>Entry Type</th>
                        <th style="text-align: right;">Amount (₹)</th>
                        <th>Remarks</th>
                    </tr>
                </thead>
                <tbody>
                    ${khataRows}
                </tbody>
            </table>

            <div class="footer">
                This document is autonomously certified by <strong>Shopo Robo Jarvis AI Assistant</strong> for official commercial and audit compliance. Notice: Official cycle finalized at month end.
            </div>
        </body>
        </html>
    `);
    printWindow.document.close();
    showToast('Month-End PDF Report generated! Click Print / Save as PDF in the report window.', 'success');
}

// Global functions for inline HTML calls
window.renderAllViews = renderAllViews;
window.switchView = switchView;
window.switchTabTopItems = switchTabTopItems;
window.renderAlerts = renderAlerts;
window.renderInventoryView = renderInventoryView;
window.handleRestockBtn = handleRestockBtn;
window.downloadPreAuditPDF = downloadPreAuditPDF;
window.openStockModal = openStockModal;
window.closeStockModal = closeStockModal;
window.confirmStockModal = confirmStockModal;
window.promptJarvisForItem = promptJarvisForItem;
window.openAddItemModal = openAddItemModal;
window.closeAddItemModal = closeAddItemModal;
window.handleAddNewItem = handleAddNewItem;
window.handleCustomShopGeneration = handleCustomShopGeneration;
window.openLoginModal = openLoginModal;
window.closeLoginModal = closeLoginModal;
window.performGmailLogin = performGmailLogin;
window.handleCustomGmailSubmit = handleCustomGmailSubmit;
window.handleLogout = handleLogout;
window.showToast = showToast;

// PWA Installation & Permanent Chrome App Handlers
let deferredPrompt = null;
window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    const installBtn = document.getElementById('pwaInstallBtn');
    if (installBtn) installBtn.style.display = 'inline-flex';
});

async function installPWA() {
    if (deferredPrompt) {
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        if (outcome === 'accepted') {
            showToast('Shopo Robo installed on Chrome as a permanent app!', 'success');
        }
        deferredPrompt = null;
        const installBtn = document.getElementById('pwaInstallBtn');
        if (installBtn) installBtn.style.display = 'none';
    } else {
        showToast('Click the install icon in Chrome address bar (or Menu > Install Shopo Robo)', 'info');
    }
}
window.installPWA = installPWA;

// Register Service Worker for Offline-First capability
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('./sw.js').then((reg) => {
            console.log('✅ Shopo Robo PWA ServiceWorker active:', reg.scope);
        }).catch((err) => {
            console.log('PWA ServiceWorker notice:', err.message);
        });
    });
}

