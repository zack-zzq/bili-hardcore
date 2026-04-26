/**
 * websocket.js — WebSocket 连接管理
 */
const WS = {
    _connections: {},

    connect(taskId, onMessage) {
        this.disconnect(taskId);
        const proto = location.protocol === 'https:' ? 'wss' : 'ws';
        const token = Auth.getToken();
        const url = `${proto}://${location.host}/ws/task/${taskId}?token=${encodeURIComponent(token)}`;
        const ws = new WebSocket(url);

        ws.onopen = () => console.log(`[WS] Connected to task ${taskId}`);
        ws.onmessage = (e) => {
            try {
                const msg = JSON.parse(e.data);
                onMessage(msg);
            } catch (err) {
                console.error('[WS] Parse error:', err);
            }
        };
        ws.onclose = (e) => {
            console.log(`[WS] Disconnected from task ${taskId}:`, e.code);
            // 自动重连（非正常关闭且任务仍活跃）
            if (e.code !== 1000 && e.code !== 4001 && e.code !== 4004) {
                setTimeout(() => {
                    if (this._connections[taskId] === ws) {
                        console.log(`[WS] Reconnecting to task ${taskId}...`);
                        this.connect(taskId, onMessage);
                    }
                }, 3000);
            }
        };
        ws.onerror = (err) => console.error('[WS] Error:', err);

        this._connections[taskId] = ws;
        return ws;
    },

    disconnect(taskId) {
        const ws = this._connections[taskId];
        if (ws) {
            ws.close(1000);
            delete this._connections[taskId];
        }
    },

    disconnectAll() {
        Object.keys(this._connections).forEach(id => this.disconnect(id));
    },
};
