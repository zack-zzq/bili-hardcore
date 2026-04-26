/**
 * task.js — 任务管理模块
 */
const TaskUI = {
    _currentTaskId: null,
    _selectedCategories: new Set(),

    /** 获取任务列表 */
    async fetchTasks() {
        try {
            const resp = await Auth.apiFetch('/api/tasks');
            if (resp.ok) {
                const data = await resp.json();
                return data.tasks || [];
            }
        } catch (e) {
            console.error('获取任务列表失败:', e);
        }
        return [];
    },

    /** 创建新任务 */
    async createTask() {
        try {
            const resp = await Auth.apiFetch('/api/tasks', { method: 'POST', body: {} });
            if (resp.ok) {
                const data = await resp.json();
                await this.refreshTaskList();
                this.selectTask(data.task_id);
                return data.task_id;
            }
        } catch (e) {
            console.error('创建任务失败:', e);
        }
        return null;
    },

    /** 删除任务 */
    async deleteTask(taskId) {
        try {
            await Auth.apiFetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
            if (this._currentTaskId === taskId) {
                this._currentTaskId = null;
                this.showWelcome();
            }
            await this.refreshTaskList();
        } catch (e) {
            console.error('删除任务失败:', e);
        }
    },

    /** 刷新任务列表 UI */
    async refreshTaskList() {
        const tasks = await this.fetchTasks();
        const list = document.getElementById('task-list');
        const count = document.getElementById('task-count');
        const empty = document.getElementById('empty-state');

        count.textContent = tasks.length;

        if (tasks.length === 0) {
            list.innerHTML = '';
            list.appendChild(empty);
            empty.style.display = 'block';
            return;
        }

        empty.style.display = 'none';
        list.innerHTML = '';
        tasks.forEach(t => {
            const item = document.createElement('div');
            item.className = `task-item${t.id === this._currentTaskId ? ' active' : ''}`;
            item.dataset.taskId = t.id;
            item.innerHTML = `
                <div class="task-item-header">
                    <span class="task-item-id">#${t.id}</span>
                    <span class="task-item-time">${this._formatTime(t.created_at)}</span>
                </div>
                <div class="task-item-body">
                    <span class="task-item-user">${t.bili_username || '等待登录...'}</span>
                    <span class="badge ${this._stateBadgeClass(t.state)}">${this._stateLabel(t.state)}</span>
                </div>
            `;
            item.addEventListener('click', () => this.selectTask(t.id));
            list.appendChild(item);
        });
    },

    /** 选中任务 */
    async selectTask(taskId) {
        // 断开旧连接
        if (this._currentTaskId) {
            WS.disconnect(this._currentTaskId);
        }

        this._currentTaskId = taskId;
        this._selectedCategories.clear();

        // 更新侧边栏高亮
        document.querySelectorAll('.task-item').forEach(el => {
            el.classList.toggle('active', el.dataset.taskId === taskId);
        });

        // 显示任务面板
        document.getElementById('welcome-panel').style.display = 'none';
        const panel = document.getElementById('task-panel');
        panel.style.display = 'flex';

        // 加载任务详情
        try {
            const resp = await Auth.apiFetch(`/api/tasks/${taskId}`);
            if (resp.ok) {
                const data = await resp.json();
                this._renderTaskDetail(data.task, data.logs);
            }
        } catch (e) {
            console.error('加载任务详情失败:', e);
        }

        // 连接 WebSocket
        WS.connect(taskId, (msg) => this._handleWSMessage(taskId, msg));
    },

    showWelcome() {
        document.getElementById('welcome-panel').style.display = 'flex';
        document.getElementById('task-panel').style.display = 'none';
    },

    /** 渲染任务详情 */
    _renderTaskDetail(task, logs) {
        document.getElementById('task-title').textContent = `任务 #${task.id}`;
        this._updateBadge(task.state);
        this._updateProgress(task.current_question, task.total_questions);
        document.getElementById('task-score').textContent = task.score;

        const userBadge = document.getElementById('task-user-badge');
        if (task.bili_username) {
            userBadge.textContent = task.bili_username;
            userBadge.style.display = 'inline';
        } else {
            userBadge.style.display = 'none';
        }

        // 根据状态显示交互区域
        this._updateInteraction(task.state);

        // 渲染日志
        const logContainer = document.getElementById('log-container');
        logContainer.innerHTML = '';
        if (logs && logs.length > 0) {
            logs.forEach(l => this._appendLog(l.timestamp, l.level, l.message));
        } else {
            logContainer.innerHTML = '<div class="log-empty">等待任务开始...</div>';
        }
    },

    _updateBadge(state) {
        const badge = document.getElementById('task-state-badge');
        badge.textContent = this._stateLabel(state);
        badge.className = `badge ${this._stateBadgeClass(state)}`;
    },

    _updateProgress(current, total) {
        document.getElementById('task-progress').textContent = `${current}/${total}`;
        const pct = total > 0 ? (current / total) * 100 : 0;
        document.getElementById('task-progress-bar').style.width = `${pct}%`;
    },

    _updateInteraction(state) {
        const qr = document.getElementById('qr-section');
        const cat = document.getElementById('category-section');
        const cap = document.getElementById('captcha-section');

        qr.style.display = state === 'qr_login' ? 'block' : 'none';
        cat.style.display = state === 'selecting_category' ? 'block' : 'none';
        cap.style.display = state === 'captcha_manual' ? 'block' : 'none';
    },

    /** 处理 WebSocket 消息 */
    _handleWSMessage(taskId, msg) {
        if (taskId !== this._currentTaskId) return;

        switch (msg.type) {
            case 'log':
                this._appendLog(msg.data.timestamp, msg.data.level, msg.data.message);
                break;

            case 'qr_code':
                this._updateInteraction('qr_login');
                this._updateBadge('qr_login');
                QRGenerator.generate('qr-canvas-container', msg.data.url, 240);
                break;

            case 'qr_scanned':
                document.getElementById('qr-section').style.display = 'none';
                break;

            case 'categories':
                this._updateInteraction('selecting_category');
                this._updateBadge('selecting_category');
                this._renderCategories(msg.data);
                break;

            case 'captcha':
                this._updateInteraction('captcha_manual');
                this._updateBadge('captcha_manual');
                this._showCaptcha(msg.data);
                break;

            case 'captcha_result':
                document.getElementById('captcha-section').style.display = 'none';
                break;

            case 'status_change':
                this._updateBadge(msg.data.state);
                this._updateInteraction(msg.data.state);
                this.refreshTaskList();
                break;

            case 'question':
                this._updateProgress(msg.data.num, 100);
                break;

            case 'answer':
                document.getElementById('task-score').textContent = msg.data.score;
                this._updateProgress(msg.data.num, 100);
                break;

            case 'result':
                this.refreshTaskList();
                break;
        }
    },

    _appendLog(timestamp, level, message) {
        const container = document.getElementById('log-container');
        // 移除空状态
        const empty = container.querySelector('.log-empty');
        if (empty) empty.remove();

        const line = document.createElement('div');
        line.className = 'log-line';
        const t = timestamp ? new Date(timestamp).toLocaleTimeString('zh-CN') : '';
        line.innerHTML = `<span class="log-time">${t}</span><span class="log-level ${level}">${level}</span><span class="log-msg">${this._escapeHtml(message)}</span>`;
        container.appendChild(line);
        container.scrollTop = container.scrollHeight;
    },

    _renderCategories(categories) {
        const grid = document.getElementById('category-grid');
        grid.innerHTML = '';
        this._selectedCategories.clear();
        categories.forEach(c => {
            const chip = document.createElement('div');
            chip.className = 'category-chip';
            chip.textContent = c.name;
            chip.dataset.id = c.id;
            chip.addEventListener('click', () => {
                if (this._selectedCategories.has(String(c.id))) {
                    this._selectedCategories.delete(String(c.id));
                    chip.classList.remove('selected');
                } else if (this._selectedCategories.size < 3) {
                    this._selectedCategories.add(String(c.id));
                    chip.classList.add('selected');
                }
            });
            grid.appendChild(chip);
        });
    },

    async submitCategory() {
        if (this._selectedCategories.size === 0) return;
        const ids = Array.from(this._selectedCategories).join(',');
        try {
            await Auth.apiFetch(`/api/tasks/${this._currentTaskId}/category`, {
                method: 'POST',
                body: { ids },
            });
        } catch (e) {
            console.error('提交分类失败:', e);
        }
    },

    _showCaptcha(data) {
        const img = document.getElementById('captcha-image');
        if (data.image_base64) {
            img.src = `data:image/png;base64,${data.image_base64}`;
        } else if (data.url) {
            img.src = data.url;
        }
        document.getElementById('captcha-input').value = '';
        document.getElementById('captcha-input').focus();
    },

    async submitCaptcha() {
        const input = document.getElementById('captcha-input');
        const code = input.value.trim();
        if (!code) return;
        try {
            await Auth.apiFetch(`/api/tasks/${this._currentTaskId}/captcha`, {
                method: 'POST',
                body: { code },
            });
        } catch (e) {
            console.error('提交验证码失败:', e);
        }
    },

    _stateLabel(state) {
        const map = {
            pending: '等待中', qr_login: '扫码登录', selecting_category: '选择分类',
            captcha: '验证码', captcha_manual: '输入验证码', answering: '答题中',
            completed: '已完成', failed: '失败', cancelled: '已取消',
        };
        return map[state] || state;
    },

    _stateBadgeClass(state) {
        const map = {
            completed: 'badge-success', failed: 'badge-error', cancelled: 'badge-error',
            answering: 'badge-info', qr_login: 'badge-warning', captcha: 'badge-warning',
            captcha_manual: 'badge-warning', selecting_category: 'badge-warning',
        };
        return map[state] || '';
    },

    _formatTime(iso) {
        if (!iso) return '';
        try {
            return new Date(iso).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
        } catch { return iso; }
    },

    _escapeHtml(text) {
        const d = document.createElement('div');
        d.textContent = text;
        return d.innerHTML;
    },

    init() {
        document.getElementById('category-submit-btn')?.addEventListener('click', () => this.submitCategory());
        document.getElementById('captcha-submit-btn')?.addEventListener('click', () => this.submitCaptcha());
        document.getElementById('captcha-input')?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.submitCaptcha();
        });
        document.getElementById('qr-download-btn')?.addEventListener('click', () => QRGenerator.download());
        document.getElementById('log-clear-btn')?.addEventListener('click', () => {
            document.getElementById('log-container').innerHTML = '<div class="log-empty">日志已清空</div>';
        });
    },
};
