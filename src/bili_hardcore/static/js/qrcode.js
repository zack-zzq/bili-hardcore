/**
 * qrcode.js — 二维码生成模块
 *
 * 使用后端 API 生成二维码图片，避免依赖外部服务。
 * 支持下载为 PNG。
 */
const QRGenerator = {
    _blobUrl: null,

    /**
     * 在指定容器中生成二维码
     * @param {string} containerId - 容器元素 ID
     * @param {string} data - 二维码数据
     * @param {number} size - 二维码尺寸
     */
    async generate(containerId, data, size = 256) {
        const container = document.getElementById(containerId);
        if (!container) return;
        container.innerHTML = '<p style="color: var(--text-muted); padding: 40px;">二维码加载中...</p>';

        // 释放旧的 blob URL
        if (this._blobUrl) {
            URL.revokeObjectURL(this._blobUrl);
            this._blobUrl = null;
        }

        const token = Auth.getToken();
        const qrUrl = `/api/tasks/qrcode?data=${encodeURIComponent(data)}`;

        try {
            const resp = await fetch(qrUrl, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

            const blob = await resp.blob();
            this._blobUrl = URL.createObjectURL(blob);

            // 创建 img 并等待加载完成
            const img = new Image();
            img.id = 'qr-image';
            img.alt = '登录二维码';
            img.style.maxWidth = size + 'px';
            img.style.maxHeight = size + 'px';
            img.style.display = 'block';

            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = reject;
                img.src = this._blobUrl;
            });

            container.innerHTML = '';
            container.appendChild(img);
        } catch (e) {
            console.error('二维码生成失败:', e);
            container.innerHTML = `<p style="color: var(--text-secondary); word-break: break-all; font-size: 0.85rem; padding: 20px;">二维码加载失败<br><a href="${data}" target="_blank" style="color: var(--accent);">点击此处手动登录</a></p>`;
        }
    },

    /**
     * 下载当前二维码为 PNG 图片
     */
    download() {
        const img = document.getElementById('qr-image');
        if (!img || !img.src) return;

        const canvas = document.createElement('canvas');
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0);

        const link = document.createElement('a');
        link.download = 'bili-hardcore-qrcode.png';
        link.href = canvas.toDataURL('image/png');
        link.click();
    },
};
