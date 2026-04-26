/**
 * app.js — 主应用入口
 */
(async function () {
    'use strict';

    const loginPage = document.getElementById('login-page');
    const mainPage = document.getElementById('main-page');
    const loginForm = document.getElementById('login-form');
    const loginError = document.getElementById('login-error');

    // ==================== 路由 / 认证检查 ====================
    async function checkAuth() {
        if (Auth.isLoggedIn() && await Auth.verify()) {
            showMain();
        } else {
            Auth.clearToken();
            showLogin();
        }
    }

    function showLogin() {
        loginPage.classList.add('active');
        mainPage.classList.remove('active');
    }

    function showMain() {
        loginPage.classList.remove('active');
        mainPage.classList.add('active');
        initMain();
    }

    // ==================== 登录 ====================
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        loginError.textContent = '';
        const btn = document.getElementById('login-btn');
        btn.disabled = true;

        try {
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            await Auth.login(username, password);
            showMain();
        } catch (err) {
            loginError.textContent = err.message;
        } finally {
            btn.disabled = false;
        }
    });

    // ==================== 主界面初始化 ====================
    let _inited = false;
    function initMain() {
        if (_inited) return;
        _inited = true;

        Settings.init();
        TaskUI.init();

        document.getElementById('new-task-btn').addEventListener('click', () => TaskUI.createTask());
        document.getElementById('logout-btn').addEventListener('click', () => Auth.logout());

        // 初始加载任务列表
        TaskUI.refreshTaskList();

        // 定期刷新任务列表
        setInterval(() => TaskUI.refreshTaskList(), 15000);
    }

    // ==================== 启动 ====================
    await checkAuth();
})();
