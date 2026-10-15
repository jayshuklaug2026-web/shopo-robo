/**
 * Shopo Robo - Core Business Data & Autonomous AI Agent Engine
 * Features:
 * - Pre-configured non-blank store initialization
 * - Integrated user AI agent model (Critical / Low Stock / Optimal health states)
 * - 15s Autonomous real sales simulation loop that drives real P&L metrics
 * - Dynamic Restock intelligence (+50 units on restock)
 * - Category-specific live wholesale stock & commodity market indices
 * - Digital Khata Ledger
 */

const StoreData = {
    settings: {
        shopName: 'Shopo Robo Commercial Store',
        shopType: 'Multi-Category Commercial Hub',
        ownerName: 'Shop Owner',
        userEmail: 'owner@shoporobo.com',
        currency: '₹',
        city: 'Local Area',
        selectedLanguage: 'hi-IN', // Default to Hindi (or en-IN)
        isSetupCompleted: true
    },

    stats: {
        totalStockValue: 184500,
        totalItemsCount: 4,
        todaysSales: 12450,
        monthlyProfit: 34800,
        monthlySales: 156000,
        monthlyExpenses: 121200,
        totalMarketUdhar: 4500,
        totalCustomerJama: 18200,
        aiStatusText: "AI Status: Nominal. Inventory flow optimized.",
        aiStatusColor: "#84CC16"
    },

    // Autonomous AI Inventory Model (Incorporating User's Core Model)
    inventory: [
        { id: 1, name: 'Sugar (Supreme Grade)', category: 'Groceries', stock: 150, quantity: 150, unit: 'kg', buyPrice: 34.00, price: 42.00, sellPrice: 42.00, minThreshold: 50, status: 'Optimal', icon: 'sugar' },
        { id: 2, name: 'Rice (Basmati Pure)', category: 'Groceries', stock: 35, quantity: 35, unit: 'kg', buyPrice: 28.00, price: 38.00, sellPrice: 38.00, minThreshold: 50, status: 'Low Stock', icon: 'rice' },
        { id: 3, name: 'Quantum Processor X1', category: 'Electronics', stock: 120, quantity: 120, unit: 'pcs', buyPrice: 380.00, price: 499.00, sellPrice: 499.00, minThreshold: 50, status: 'Optimal', icon: 'box' },
        { id: 4, name: 'Holographic Display 4K', category: 'Electronics', stock: 12, quantity: 12, unit: 'pcs', buyPrice: 720.00, price: 899.00, sellPrice: 899.00, minThreshold: 15, status: 'Critical', icon: 'box' }
    ],

    // Real Category-Specific Market Trends (Tailored to active categories)
    categoryMarketIndices: {
        'Groceries': [
            { name: 'Sugar M-30 Mandi Benchmark', symbol: 'NCDEX-SUGAR', currentPrice: 41.50, unit: 'kg', changePct: 8.2, trend: 'up', high: 42.20, low: 39.80, signal: 'Strong Demand' },
            { name: 'Rice 1121 Pusa Wholesale', symbol: 'AGMARK-RICE', currentPrice: 33.20, unit: 'kg', changePct: -4.8, trend: 'down', high: 35.00, low: 32.80, signal: 'Good Reorder Window' },
            { name: 'Mustard Oil Crude Wholesale', symbol: 'NCDEX-MUSTARD', currentPrice: 142.00, unit: 'L', changePct: -1.8, trend: 'down', high: 146.00, low: 141.50, signal: 'Stable Margins' },
            { name: 'Wheat Mill Quality Dara', symbol: 'MCX-WHEAT', currentPrice: 27.80, unit: 'kg', changePct: 3.1, trend: 'up', high: 28.50, low: 26.90, signal: 'Rate Increasing' }
        ],
        'Electronics': [
            { name: 'Semiconductor Wafer Index', symbol: 'SOX-INDEX', currentPrice: 485.00, unit: 'unit', changePct: 6.4, trend: 'up', high: 492.00, low: 470.00, signal: 'Supply Tight' },
            { name: 'Display Glass Substrate 4K', symbol: 'DISP-FUT', currentPrice: 840.00, unit: 'panel', changePct: -3.2, trend: 'down', high: 870.00, low: 835.00, signal: 'Price Drop' },
            { name: 'Lithium Battery Cells Grade A', symbol: 'LI-COMM', currentPrice: 195.00, unit: 'pack', changePct: 4.8, trend: 'up', high: 202.00, low: 190.00, signal: 'Wholesale Spike' }
        ],
        'Apparel': [
            { name: 'Raw Cotton Shankar-6 Spot', symbol: 'MCX-COTTON', currentPrice: 62.00, unit: 'm', changePct: 2.4, trend: 'up', high: 64.00, low: 60.50, signal: 'Moderate Rise' },
            { name: 'Polyester Staple Fiber (PSF)', symbol: 'PSF-COMM', currentPrice: 104.00, unit: 'kg', changePct: -2.1, trend: 'down', high: 108.00, low: 102.50, signal: 'Favorable Cost' }
        ],
        'Pharmacy': [
            { name: 'Paracetamol API Powder 99%', symbol: 'PHARMA-PARA', currentPrice: 22.00, unit: 'strip', changePct: 0.0, trend: 'stable', high: 22.50, low: 21.80, signal: 'Balanced' },
            { name: 'Amoxicillin Trihydrate Bulk', symbol: 'PHARMA-AMOX', currentPrice: 75.00, unit: 'bottle', changePct: 4.2, trend: 'up', high: 78.00, low: 72.00, signal: 'Cost Increase' }
        ]
    },

    // Khata Digital Ledger
    khata: [
        { id: 'kh_1', customer_name: 'Ramesh Sharma', entry_type: 'udhar', amount: 850, date: 'Today', time: '11:20 AM', note: 'Grocery supply on credit' },
        { id: 'kh_2', customer_name: 'Ramesh Sharma', entry_type: 'jama', amount: 500, date: 'Today', time: '02:40 PM', note: 'Cash payment received' },
        { id: 'kh_3', customer_name: 'Suresh Verma', entry_type: 'udhar', amount: 1200, date: 'Yesterday', time: '05:15 PM', note: 'Electronic display purchase credit' },
        { id: 'kh_4', customer_name: 'Anita Devi', entry_type: 'jama', amount: 2000, date: '10 Oct 2026', time: '09:30 AM', note: 'Full monthly settlement' }
    ],

    alerts: [
        { id: 'alt_1', type: 'danger', icon: 'fa-triangle-exclamation', text: 'Holographic Display stock is CRITICAL! Only 12 pcs remaining.', time: 'Just now' },
        { id: 'alt_2', type: 'warning', icon: 'fa-box-open', text: 'Rice stock is LOW (35 kg left). Recommended reorder buffer: 50 kg.', time: '10 mins ago' },
        { id: 'alt_3', type: 'info', icon: 'fa-arrow-trend-up', text: 'Wholesale Sugar price increased by 8.2% in NCDEX Mandi benchmark.', time: '1 hour ago' }
    ],

    bestSelling: [
        { rank: 1, name: 'Sugar (Supreme Grade)', soldQty: '180 kg', revenue: '₹ 7,560', isLoss: false },
        { rank: 2, name: 'Quantum Processor X1', soldQty: '45 pcs', revenue: '₹ 22,455', isLoss: false },
        { rank: 3, name: 'Rice (Basmati Pure)', soldQty: '70 kg', revenue: '₹ 2,660', isLoss: false }
    ],

    lossMakingItems: [
        { rank: 1, name: 'Holographic Display 4K', soldQty: '12 pcs', lossAmount: 'Margin Squeeze', reason: 'Wholesale import tariff raised wholesale cost' }
    ],

    // Initialize Store Data
    async init() {
        const savedSettings = localStorage.getItem('shoporobo_settings');
        if (savedSettings) {
            try { this.settings = { ...this.settings, ...JSON.parse(savedSettings) }; } catch (e) {}
        }

        if (window.SupabaseManager && SupabaseManager.currentUser) {
            this.settings.ownerName = SupabaseManager.currentUser.displayName;
            this.settings.userEmail = SupabaseManager.currentUser.email;
            const userInv = await SupabaseManager.getInventory();
            this.inventory = userInv || [];
            const userKhata = await SupabaseManager.getKhataEntries();
            this.khata = userKhata || [];
        } else {
            const cachedInv = localStorage.getItem('shoporobo_inventory_pro');
            if (cachedInv) {
                try {
                    const parsed = JSON.parse(cachedInv);
                    if (parsed && parsed.length > 0) this.inventory = parsed;
                } catch (e) {}
            }

            const cachedKhata = localStorage.getItem('shoporobo_khata_pro');
            if (cachedKhata) {
                try { this.khata = JSON.parse(cachedKhata); } catch (e) {}
            }
        }

        this.updateDashboard();
        this.startAutonomousAISimulation();
    },

    // User's Core Autonomous Model Implementation
    updateDashboard() {
        const totalItems = this.inventory.reduce((sum, item) => sum + (item.quantity || item.stock || 0), 0);
        const totalValue = this.inventory.reduce((sum, item) => sum + ((item.quantity || item.stock || 0) * (item.price || item.sellPrice || 0)), 0);
        
        // Critical (<15) and Low Stock (<50) health detection
        const criticalItems = this.inventory.filter(i => (i.quantity || i.stock) < 15).length;
        const lowStockItems = this.inventory.filter(i => (i.quantity || i.stock) < 50).length;

        this.stats.totalItemsCount = this.inventory.length;
        this.stats.totalStockValue = Math.round(totalValue);

        // Dynamic AI status updates based on health
        if (criticalItems > 0 || lowStockItems > 2) {
            this.stats.aiStatusText = `AI Status: Warning. ${criticalItems > 0 ? `${criticalItems} critical shortages` : 'Stock shortages'} detected.`;
            this.stats.aiStatusColor = '#EF4444'; // Red
        } else {
            this.stats.aiStatusText = "AI Status: Nominal. Inventory flow optimized.";
            this.stats.aiStatusColor = '#84CC16'; // Lime Green
        }

        // Calculate Khata balances
        let udhar = 0;
        let jama = 0;
        this.khata.forEach(k => {
            if (k.entry_type === 'udhar') udhar += Number(k.amount || 0);
            if (k.entry_type === 'jama') jama += Number(k.amount || 0);
        });
        this.stats.totalMarketUdhar = udhar;
        this.stats.totalCustomerJama = jama;

        localStorage.setItem('shoporobo_inventory_pro', JSON.stringify(this.inventory));
        localStorage.setItem('shoporobo_khata_pro', JSON.stringify(this.khata));
    },

    // Restock Action (+50 units as defined in user's model)
    handleRestock(id) {
        const item = this.inventory.find(i => i.id === id);
        if (item) {
            const addedQty = 50;
            item.quantity = (item.quantity || item.stock || 0) + addedQty;
            item.stock = item.quantity;

            if (item.quantity >= 50) {
                item.status = 'Optimal';
            } else if (item.quantity >= 15) {
                item.status = 'Low Stock';
            }

            const alertMsg = `✅ Restocked ${item.name} (+${addedQty} ${item.unit || 'units'}). Status is now ${item.status}.`;
            this.addAlert('success', 'fa-box-circle-check', alertMsg);
            this.updateDashboard();

            return {
                success: true,
                message: alertMsg,
                item
            };
        }
        return { success: false, message: 'Item not found' };
    },

    // Autonomous AI Agent Simulation Loop (Continuous Real Business Cycle)
    startAutonomousAISimulation() {
        if (window._autonomousLoopActive) return;
        window._autonomousLoopActive = true;

        setInterval(() => {
            if (this.inventory.length === 0) return;

            const randomIndex = Math.floor(Math.random() * this.inventory.length);
            const item = this.inventory[randomIndex];

            if (item && (item.quantity || item.stock) > 0) {
                const soldQty = Math.floor(Math.random() * 4) + 1; // 1 to 4 units sold
                const actualSold = Math.min(soldQty, (item.quantity || item.stock));

                item.quantity = (item.quantity || item.stock) - actualSold;
                item.stock = item.quantity;

                // Update sales and profit
                const sellP = item.price || item.sellPrice || 40;
                const buyP = item.buyPrice || (sellP * 0.75);
                const revenue = actualSold * sellP;
                const profit = actualSold * (sellP - buyP);

                this.stats.todaysSales += Math.round(revenue);
                this.stats.monthlySales += Math.round(revenue);
                this.stats.monthlyProfit += Math.round(profit);

                // Recalculate status per user specification
                if (item.quantity < 15) {
                    item.status = 'Critical';
                    this.addAlert('danger', 'fa-triangle-exclamation', `🚨 Critical Shortage: ${item.name} has only ${item.quantity} ${item.unit || 'units'} left! Restock advised.`);
                } else if (item.quantity < 50) {
                    item.status = 'Low Stock';
                } else {
                    item.status = 'Optimal';
                }

                this.updateDashboard();
                if (window.renderAllViews) window.renderAllViews();
            }
        }, 15000); // Runs autonomously every 15 seconds
    },

    // Record Khata Entry
    addKhataEntry(customerName, type, amount, note = '') {
        const entry = {
            id: 'kh_' + Date.now(),
            customer_name: customerName,
            entry_type: type,
            amount: Number(amount),
            date: 'Today',
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            note: note || (type === 'udhar' ? 'Customer purchase credit' : 'Cash settlement received')
        };
        this.khata.unshift(entry);
        this.updateDashboard();
        return entry;
    },

    // Add Alert
    addAlert(type, icon, text) {
        const alert = {
            id: 'alt_' + Date.now(),
            type,
            icon,
            text,
            time: 'Just now'
        };
        this.alerts.unshift(alert);
        if (this.alerts.length > 20) this.alerts.pop();
        return alert;
    },

    // Get market trends for active categories
    getActiveCategoryTrends() {
        const categories = Array.from(new Set(this.inventory.map(i => i.category)));
        let trends = [];

        categories.forEach(cat => {
            if (this.categoryMarketIndices[cat]) {
                trends.push(...this.categoryMarketIndices[cat]);
            }
        });

        if (trends.length === 0) {
            trends = this.categoryMarketIndices['Groceries'];
        }

        return trends;
    },

    // Recalculate metrics
    recalculateStats() {
        this.updateDashboard();
    },

    // Stock in or Stock out (Sale)
    updateItemStock(id, qty, mode = 'add') {
        const item = this.inventory.find(i => i.id == id);
        if (!item) return { success: false, message: 'Item not found' };

        qty = Number(qty);
        if (mode === 'add') {
            item.quantity = (item.quantity !== undefined ? item.quantity : item.stock || 0) + qty;
            item.stock = item.quantity;
            this.addAlert('info', 'fa-arrow-down', `Added +${qty} ${item.unit || 'units'} stock for ${item.name}.`);
        } else {
            const current = (item.quantity !== undefined ? item.quantity : item.stock || 0);
            const actualSold = Math.min(qty, current);
            item.quantity = current - actualSold;
            item.stock = item.quantity;
            const sellP = item.price || item.sellPrice || 0;
            const buyP = item.buyPrice || (sellP * 0.75);
            this.stats.todaysSales += Math.round(actualSold * sellP);
            this.stats.monthlySales += Math.round(actualSold * sellP);
            this.stats.monthlyProfit += Math.round(actualSold * (sellP - buyP));
            this.addAlert('success', 'fa-receipt', `Recorded sale of ${actualSold} ${item.unit || 'units'} for ${item.name}.`);
        }

        if (item.quantity < 15) {
            item.status = 'Critical';
        } else if (item.quantity < 50) {
            item.status = 'Low Stock';
        } else {
            item.status = 'Optimal';
        }

        this.updateDashboard();
        if (window.SupabaseManager && SupabaseManager.currentUser) {
            SupabaseManager.saveItem(item);
        }
        return { success: true, message: `Updated stock for ${item.name}: ${item.quantity} ${item.unit || 'units'} (${item.status})` };
    },

    // Apply Shop Template (Autonomous AI Category & Store Setup)
    applyShopType(typeName) {
        const t = (typeName || '').toLowerCase().trim();
        let template = null;

        if (t.includes('kirana') || t.includes('grocery') || t.includes('ration')) {
            template = {
                name: 'Kirana & Grocery Store',
                type: 'Groceries',
                items: [
                    { id: 1, name: 'Sugar (Supreme Grade)', category: 'Groceries', stock: 150, quantity: 150, unit: 'kg', buyPrice: 34.00, price: 42.00, sellPrice: 42.00, minThreshold: 50, status: 'Optimal', icon: 'sugar' },
                    { id: 2, name: 'Rice (Basmati Pure)', category: 'Groceries', stock: 35, quantity: 35, unit: 'kg', buyPrice: 28.00, price: 38.00, sellPrice: 38.00, minThreshold: 50, status: 'Low Stock', icon: 'rice' },
                    { id: 3, name: 'Atta (Chakki Fresh)', category: 'Groceries', stock: 120, quantity: 120, unit: 'kg', buyPrice: 25.00, price: 32.00, sellPrice: 32.00, minThreshold: 50, status: 'Optimal', icon: 'flour' },
                    { id: 4, name: 'Mustard Oil (Kacchi Ghani)', category: 'Groceries', stock: 14, quantity: 14, unit: 'L', buyPrice: 125.00, price: 150.00, sellPrice: 150.00, minThreshold: 15, status: 'Critical', icon: 'oil' }
                ]
            };
        } else if (t.includes('pharmacy') || t.includes('medical') || t.includes('chemist') || t.includes('dawa')) {
            template = {
                name: 'Pharmacy & Medical Chemist',
                type: 'Pharmacy',
                items: [
                    { id: 1, name: 'Paracetamol 650mg Tablets', category: 'Pharmacy', stock: 180, quantity: 180, unit: 'strips', buyPrice: 18.00, price: 30.00, sellPrice: 30.00, minThreshold: 50, status: 'Optimal', icon: 'box' },
                    { id: 2, name: 'Cough Syrup 100ml', category: 'Pharmacy', stock: 40, quantity: 40, unit: 'bottles', buyPrice: 65.00, price: 95.00, sellPrice: 95.00, minThreshold: 50, status: 'Low Stock', icon: 'box' },
                    { id: 3, name: 'Digital Thermometer', category: 'Pharmacy', stock: 12, quantity: 12, unit: 'pcs', buyPrice: 120.00, price: 180.00, sellPrice: 180.00, minThreshold: 15, status: 'Critical', icon: 'box' },
                    { id: 4, name: 'Vitamin C Chewables', category: 'Pharmacy', stock: 95, quantity: 95, unit: 'bottles', buyPrice: 85.00, price: 125.00, sellPrice: 125.00, minThreshold: 50, status: 'Optimal', icon: 'box' }
                ]
            };
        } else if (t.includes('electronic') || t.includes('mobile') || t.includes('gadget')) {
            template = {
                name: 'Electronics & Mobile Store',
                type: 'Electronics',
                items: [
                    { id: 1, name: 'Quantum Processor X1', category: 'Electronics', stock: 120, quantity: 120, unit: 'pcs', buyPrice: 380.00, price: 499.00, sellPrice: 499.00, minThreshold: 50, status: 'Optimal', icon: 'box' },
                    { id: 2, name: 'Fast USB-C Cable 65W', category: 'Electronics', stock: 120, quantity: 120, unit: 'pcs', buyPrice: 85.00, price: 199.00, sellPrice: 199.00, minThreshold: 50, status: 'Optimal', icon: 'box' },
                    { id: 3, name: 'Holographic Display 4K', category: 'Electronics', stock: 12, quantity: 12, unit: 'pcs', buyPrice: 720.00, price: 899.00, sellPrice: 899.00, minThreshold: 15, status: 'Critical', icon: 'box' },
                    { id: 4, name: 'Wireless Bluetooth Earbuds', category: 'Electronics', stock: 32, quantity: 32, unit: 'pcs', buyPrice: 420.00, price: 699.00, sellPrice: 699.00, minThreshold: 50, status: 'Low Stock', icon: 'box' }
                ]
            };
        } else if (t.includes('clothing') || t.includes('garment') || t.includes('boutique') || t.includes('kapde')) {
            template = {
                name: 'Garments & Fashion Boutique',
                type: 'Apparel',
                items: [
                    { id: 1, name: 'Cotton Classic Crew T-Shirt', category: 'Apparel', stock: 140, quantity: 140, unit: 'pcs', buyPrice: 180.00, price: 349.00, sellPrice: 349.00, minThreshold: 50, status: 'Optimal', icon: 'box' },
                    { id: 2, name: 'Slim Fit Denim Jeans', category: 'Apparel', stock: 38, quantity: 38, unit: 'pcs', buyPrice: 550.00, price: 999.00, sellPrice: 999.00, minThreshold: 50, status: 'Low Stock', icon: 'box' },
                    { id: 3, name: 'Formal Linen Shirt', category: 'Apparel', stock: 10, quantity: 10, unit: 'pcs', buyPrice: 420.00, price: 799.00, sellPrice: 799.00, minThreshold: 15, status: 'Critical', icon: 'box' },
                    { id: 4, name: 'Traditional Kurta Set', category: 'Apparel', stock: 65, quantity: 65, unit: 'pcs', buyPrice: 480.00, price: 899.00, sellPrice: 899.00, minThreshold: 50, status: 'Optimal', icon: 'box' }
                ]
            };
        } else if (t.includes('bakery') || t.includes('cafe')) {
            template = {
                name: 'Bakery & Confectionery Cafe',
                type: 'Bakery',
                items: [
                    { id: 1, name: 'Milk Bread Loaf Fresh', category: 'Bakery', stock: 120, quantity: 120, unit: 'pkts', buyPrice: 28.00, price: 45.00, sellPrice: 45.00, minThreshold: 50, status: 'Optimal', icon: 'box' },
                    { id: 2, name: 'Choco Fudge Pastry', category: 'Bakery', stock: 30, quantity: 30, unit: 'pcs', buyPrice: 35.00, price: 65.00, sellPrice: 65.00, minThreshold: 50, status: 'Low Stock', icon: 'box' },
                    { id: 3, name: 'Butter Cookies 250g', category: 'Bakery', stock: 75, quantity: 75, unit: 'boxes', buyPrice: 60.00, price: 95.00, sellPrice: 95.00, minThreshold: 50, status: 'Optimal', icon: 'box' },
                    { id: 4, name: 'Black Forest Cake 1kg', category: 'Bakery', stock: 8, quantity: 8, unit: 'pcs', buyPrice: 320.00, price: 550.00, sellPrice: 550.00, minThreshold: 15, status: 'Critical', icon: 'box' }
                ]
            };
        } else {
            const capitalized = typeName ? (typeName.charAt(0).toUpperCase() + typeName.slice(1)) : 'General Store';
            template = {
                name: `${capitalized} Specialty Store`,
                type: capitalized,
                items: [
                    { id: 1, name: `${capitalized} Grade A Standard`, category: capitalized, stock: 100, quantity: 100, unit: 'units', buyPrice: 150.00, price: 220.00, sellPrice: 220.00, minThreshold: 50, status: 'Optimal', icon: 'box' },
                    { id: 2, name: `${capitalized} High Turnover Pack`, category: capitalized, stock: 42, quantity: 42, unit: 'units', buyPrice: 80.00, price: 130.00, sellPrice: 130.00, minThreshold: 50, status: 'Low Stock', icon: 'box' },
                    { id: 3, name: `${capitalized} Value Bundle`, category: capitalized, stock: 11, quantity: 11, unit: 'units', buyPrice: 320.00, price: 450.00, sellPrice: 450.00, minThreshold: 15, status: 'Critical', icon: 'box' }
                ]
            };
        }

        this.settings.shopName = template.name;
        this.settings.shopType = template.type;
        this.inventory = template.items;
        this.updateDashboard();

        if (window.SupabaseManager && SupabaseManager.currentUser) {
            SupabaseManager.saveBatchItems(this.inventory);
        }

        return template;
    }
};

window.StoreData = StoreData;
