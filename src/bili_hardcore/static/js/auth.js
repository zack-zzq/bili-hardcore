/**
 * auth.js — 认证模块
 */
const Auth = {
    TOKEN_KEY: 'bili_hardcore_token',

    getToken() {
        return localStorage.getItem(this.TOKEN_KEY);
    },

    setToken(token) {
        localStorage.setItem(this.TOKEN_KEY, token);
    },

    clearToken() {
        localStorage.removeItem(this.TOKEN_KEY);
    },

    isLoggedIn() {
        return !!this.getToken();
    },

    async login(username, password) {
        const resp = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password }),
        });
        if (!resp.ok) {
            const data = await resp.json().catch(() => ({}));
            throw new Error(data.detail || '登录失败');
        }
        const data = await resp.json();
        this.setToken(data.access_token);
        return data;
    },

    async verify() {
        const token = this.getToken();
        if (!token) return false;
        try {
            const resp = await fetch('/api/auth/verify', {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            return resp.ok;
        } catch {
            return false;
        }
    },

    /** 带认证头的 fetch 封装 */
    async apiFetch(url, options = {}) {
        const token = this.getToken();
        const headers = { ...options.headers };
        if (token) headers['Authorization'] = `Bearer ${token}`;
        if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
            options.body = JSON.stringify(options.body);
        }
        const resp = await fetch(url, { ...options, headers });
        if (resp.status === 401) {
            this.clearToken();
            window.location.reload();
            throw new Error('认证已过期');
        }
        return resp;
    },

    logout() {
        this.clearToken();
        window.location.reload();
    },
};
