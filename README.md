# Bili-Hardcore

B 站硬核会员自动答题工具 —— WebUI 版，利用 LLM 大模型实现智能答题。

## ✨ 特性

- 🌐 **WebUI 界面** — 现代化深色主题，实时日志推送
- 🤖 **OpenAI Compatible** — 支持任何兼容 OpenAI API 的模型服务（硅基流动、火山引擎、阿里云等）
- 📱 **优雅二维码** — 前端渲染，支持下载为图片
- 🔐 **AI 验证码识别** — 自动识别图形验证码，失败时回退到人工输入
- 🔄 **并行任务** — 同时运行多个答题任务，独立管理
- 🐳 **Docker 部署** — 一键启动，支持 docker-compose
- 🔒 **身份认证** — JWT 令牌认证，保护 WebUI 访问

## 🚀 快速开始 (Docker)

### 1. 创建 `docker-compose.yml`

```yaml
services:
  bili-hardcore:
    image: ghcr.io/karben233/bili-hardcore:latest
    container_name: bili-hardcore
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      - OPENAI_BASE_URL=https://api.siliconflow.cn/v1
      - OPENAI_API_KEY=your-api-key-here
      - AUTH_USERNAME=admin
      - AUTH_PASSWORD=your-password
      - JWT_SECRET=change-me-in-production
    volumes:
      - bili-data:/app/data

volumes:
  bili-data:
```

### 2. 启动

```bash
docker compose up -d
```

### 3. 访问

打开浏览器访问 `http://localhost:8080`，使用配置的用户名密码登录。

## ⚙️ 环境变量

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `OPENAI_BASE_URL` | ✅ | - | OpenAI Compatible API 基础 URL |
| `OPENAI_API_KEY` | ✅ | - | API 密钥 |
| `AUTH_USERNAME` | ❌ | `admin` | WebUI 登录用户名 |
| `AUTH_PASSWORD` | ❌ | `admin` | WebUI 登录密码 |
| `JWT_SECRET` | ❌ | 内置默认值 | JWT 签名密钥（生产环境务必修改） |
| `APP_PORT` | ❌ | `8080` | 服务端口 |

### API 提供商配置示例

| 提供商 | `OPENAI_BASE_URL` |
|--------|-------------------|
| 硅基流动 | `https://api.siliconflow.cn/v1` |
| 火山引擎 | `https://ark.cn-beijing.volces.com/api/v3` |
| 阿里云百炼 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| DeepSeek | `https://api.deepseek.com/v1` |

## 📖 使用流程

1. 登录 WebUI
2. 在 **设置** 中选择答题模型和验证码识别模型
3. 点击 **新建任务** 开始
4. 使用哔哩哔哩 APP 扫码登录
5. 选择答题分类
6. 验证码自动识别（或手动输入）
7. AI 自动答题，实时查看进度和日志

## 🛠️ 本地开发

### 前置要求
- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

### 安装 & 运行

```bash
# 克隆项目
git clone https://github.com/Karben233/bili-hardcore.git
cd bili-hardcore

# 安装依赖
uv sync

# 设置环境变量
export OPENAI_BASE_URL=https://api.siliconflow.cn/v1
export OPENAI_API_KEY=your-key

# 运行
uv run bili-hardcore
```

## 使用前须知

- 程序仅在服务端调用 B 站 API 和 LLM API，不会上传您的登录信息和 API Key
- 请确保您的 B 站账号已满 6 级，根据 B 站规则，6 级用户才可以进行硬核会员试炼
- 硬核会员试炼每天有 3 次答题机会，达到限制后需要 24 小时后才能重新答题
- 不建议使用思考模型，思维链过长可能导致超时请求失败
- 请合理使用，遵守 B 站相关规则

## 📜 License

[MIT](LICENSE)
