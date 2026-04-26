/**
 * settings.js — 设置管理模块
 */
const Settings = {
    _models: [],

    async load() {
        try {
            const resp = await Auth.apiFetch('/api/settings');
            if (resp.ok) return await resp.json();
        } catch (e) {
            console.error('加载设置失败:', e);
        }
        return { answer_model_id: '', captcha_model_id: '' };
    },

    async save(answerModelId, captchaModelId) {
        const resp = await Auth.apiFetch('/api/settings', {
            method: 'PUT',
            body: { answer_model_id: answerModelId, captcha_model_id: captchaModelId },
        });
        return resp.ok;
    },

    async fetchModels() {
        try {
            const resp = await Auth.apiFetch('/api/settings/models');
            if (resp.ok) {
                const data = await resp.json();
                this._models = data.models || [];
                return this._models;
            }
        } catch (e) {
            console.error('获取模型列表失败:', e);
        }
        return [];
    },

    populateSelects(models, currentAnswer, currentCaptcha) {
        const answerSel = document.getElementById('answer-model-select');
        const captchaSel = document.getElementById('captcha-model-select');
        if (!answerSel || !captchaSel) return;

        // 答题模型
        answerSel.innerHTML = '<option value="">-- 请选择模型 --</option>';
        models.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.id;
            opt.textContent = m.id;
            if (m.id === currentAnswer) opt.selected = true;
            answerSel.appendChild(opt);
        });

        // 验证码识别模型
        captchaSel.innerHTML = '<option value="">-- 不使用AI识别 --</option>';
        models.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m.id;
            opt.textContent = m.id;
            if (m.id === currentCaptcha) opt.selected = true;
            captchaSel.appendChild(opt);
        });
    },

    async openModal() {
        const modal = document.getElementById('settings-modal');
        modal.style.display = 'flex';

        const settings = await this.load();
        const models = await this.fetchModels();
        this.populateSelects(models, settings.answer_model_id, settings.captcha_model_id);
    },

    closeModal() {
        document.getElementById('settings-modal').style.display = 'none';
    },

    async saveFromModal() {
        const answerSel = document.getElementById('answer-model-select');
        const captchaSel = document.getElementById('captcha-model-select');
        const ok = await this.save(answerSel.value, captchaSel.value);
        if (ok) {
            this.closeModal();
        }
    },

    init() {
        document.getElementById('settings-btn')?.addEventListener('click', () => this.openModal());
        document.getElementById('settings-close-btn')?.addEventListener('click', () => this.closeModal());
        document.getElementById('settings-save-btn')?.addEventListener('click', () => this.saveFromModal());
        document.getElementById('refresh-models-btn')?.addEventListener('click', async () => {
            const settings = await this.load();
            const models = await this.fetchModels();
            this.populateSelects(models, settings.answer_model_id, settings.captcha_model_id);
        });
        // 点击遮罩关闭
        document.getElementById('settings-modal')?.addEventListener('click', (e) => {
            if (e.target.id === 'settings-modal') this.closeModal();
        });
    },
};
