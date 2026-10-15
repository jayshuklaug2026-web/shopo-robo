/**
 * Shopo Robo - Supabase Database Client & Multi-User Gmail Auth Manager
 * Supports:
 * - Google / Gmail Authentication (Supabase Auth & Local OAuth simulator)
 * - User-isolated Inventory & Khata Ledger
 * - Offline-first fallback to LocalStorage per Gmail account
 */

const SupabaseManager = {
    client: null,
    isConnected: false,
    currentUser: null,
    config: {
        url: '',
        anonKey: ''
    },

    // Initialize Supabase and user session
    init() {
        const savedUrl = localStorage.getItem('shoporobo_supabase_url');
        const savedKey = localStorage.getItem('shoporobo_supabase_key');

        if (savedUrl && savedKey) {
            this.config.url = savedUrl;
            this.config.anonKey = savedKey;
            this.connect(savedUrl, savedKey);
        }

        // Restore logged in Gmail session
        const savedUser = localStorage.getItem('shoporobo_current_user');
        if (savedUser) {
            try {
                this.currentUser = JSON.parse(savedUser);
            } catch (e) {
                this.currentUser = null;
            }
        }
    },

    // Connect to Supabase project
    connect(url, anonKey) {
        try {
            if (window.supabase && typeof window.supabase.createClient === 'function') {
                this.client = window.supabase.createClient(url, anonKey);
                this.isConnected = true;
                this.config.url = url;
                this.config.anonKey = anonKey;
                localStorage.setItem('shoporobo_supabase_url', url);
                localStorage.setItem('shoporobo_supabase_key', anonKey);
                console.log('✅ Supabase client active!');
                return { success: true, message: 'Connected to Supabase cloud successfully!' };
            } else {
                throw new Error('Supabase JS client library not loaded.');
            }
        } catch (err) {
            console.warn('Supabase connection warning:', err.message);
            this.isConnected = false;
            return { success: false, message: err.message };
        }
    },

    // Google / Gmail Login
    async loginWithGmail(email, displayName = 'Shop Owner') {
        const cleanEmail = email.toLowerCase().trim();
        const user = {
            email: cleanEmail,
            displayName: displayName || cleanEmail.split('@')[0],
            photoURL: `https://api.dicebear.com/7.x/bottts/svg?seed=${cleanEmail}&backgroundColor=ecfccb`,
            loggedInAt: new Date().toISOString()
        };

        this.currentUser = user;
        localStorage.setItem('shoporobo_current_user', JSON.stringify(user));

        // If real Supabase client is active, attempt Supabase Auth OAuth if requested
        if (this.isConnected && this.client && window.location.protocol.startsWith('http')) {
            try {
                // Background sync profile
                await this.client.from('shop_settings').upsert({
                    user_email: cleanEmail,
                    owner_name: user.displayName,
                    updated_at: new Date().toISOString()
                }, { onConflict: 'user_email' });
            } catch (e) {
                console.debug('Supabase user profile upsert notice:', e.message);
            }
        }

        return user;
    },

    // Logout
    logout() {
        this.currentUser = null;
        localStorage.removeItem('shoporobo_current_user');
        if (this.isConnected && this.client) {
            try { this.client.auth.signOut(); } catch (e) {}
        }
    },

    // Get Storage Key scoped to current logged-in user
    getUserStorageKey(prefix) {
        const email = this.currentUser ? this.currentUser.email : 'guest';
        return `shoporobo_${prefix}_${email}`;
    },

    // Fetch Inventory for current user
    async getInventory() {
        if (!this.currentUser) return [];

        if (this.isConnected && this.client) {
            try {
                const { data, error } = await this.client
                    .from('inventory')
                    .select('*')
                    .eq('user_email', this.currentUser.email)
                    .order('name', { ascending: true });
                if (!error && data) return data;
            } catch (err) {
                console.warn('Supabase fetch inventory warning:', err);
            }
        }

        const local = localStorage.getItem(this.getUserStorageKey('inventory'));
        return local ? JSON.parse(local) : [];
    },

    // Save or update an item
    async saveItem(item) {
        if (!this.currentUser) return [];

        const items = (await this.getInventory()) || [];
        const existingIdx = items.findIndex(i => i.id === item.id || (i.name && item.name && i.name.toLowerCase() === item.name.toLowerCase()));
        
        if (existingIdx >= 0) {
            items[existingIdx] = { ...items[existingIdx], ...item, updated_at: new Date().toISOString() };
        } else {
            if (!item.id) item.id = 'item_' + Date.now();
            item.user_email = this.currentUser.email;
            item.created_at = new Date().toISOString();
            items.push(item);
        }
        localStorage.setItem(this.getUserStorageKey('inventory'), JSON.stringify(items));

        if (this.isConnected && this.client) {
            try {
                await this.client.from('inventory').upsert({
                    ...item,
                    user_email: this.currentUser.email
                });
            } catch (err) {
                console.warn('Supabase item upsert err:', err);
            }
        }

        return items;
    },

    // Save batch of items
    async saveBatchItems(newItems) {
        if (!this.currentUser) return [];
        localStorage.setItem(this.getUserStorageKey('inventory'), JSON.stringify(newItems));

        if (this.isConnected && this.client) {
            try {
                const rows = newItems.map(i => ({
                    ...i,
                    user_email: this.currentUser.email
                }));
                await this.client.from('inventory').upsert(rows);
            } catch (e) {
                console.warn('Supabase batch upsert warning:', e);
            }
        }
        return newItems;
    },

    // Khata (Digital Ledger) methods
    async getKhataEntries() {
        if (!this.currentUser) return [];

        if (this.isConnected && this.client) {
            try {
                const { data, error } = await this.client
                    .from('khata_entries')
                    .select('*')
                    .eq('user_email', this.currentUser.email)
                    .order('created_at', { ascending: false });
                if (!error && data) return data;
            } catch (e) {}
        }

        const local = localStorage.getItem(this.getUserStorageKey('khata'));
        return local ? JSON.parse(local) : [];
    },

    async addKhataEntry(entry) {
        if (!this.currentUser) return null;

        const entries = await this.getKhataEntries();
        const newEntry = {
            id: 'khata_' + Date.now(),
            user_email: this.currentUser.email,
            date: new Date().toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }),
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            created_at: new Date().toISOString(),
            ...entry
        };

        entries.unshift(newEntry);
        localStorage.setItem(this.getUserStorageKey('khata'), JSON.stringify(entries));

        if (this.isConnected && this.client) {
            try {
                await this.client.from('khata_entries').insert(newEntry);
            } catch (e) {
                console.warn('Supabase khata insert warning:', e);
            }
        }

        return newEntry;
    }
};

window.SupabaseManager = SupabaseManager;
