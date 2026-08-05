# GiftMind Data Studio

GiftMind 的数据采集与维护工作台。它为礼物条目、素材、导入导出和数据质量维护提供独立的管理界面，并以 FastAPI 后端和 Vue 3 前端组成一个本地优先的应用。

## 包含内容

- 礼物数据的创建、编辑、筛选、回收与恢复
- 产品、活动及组合礼物的类型化字段
- 导入、导出、备份与审核辅助工具
- 受通行码保护的本地会话
- 可选的 DeepSeek V4 Flash 辅助预填；密钥只保存在服务器 `.env`
- 每条礼物独立的 AI 选品助手会话，支持文字、链接和 JPG/PNG/WebP 图片
- 淘宝/天猫商品链接由服务器端 Playwright 读取标题、说明、价格和页面文字；不下载商品图片，也不要求采集员提供淘宝账号密码
- 工具页可打开服务器上的淘宝登录画面，人工完成一次登录后将会话状态保存到 `data/private/`，后续提取自动复用
- AI 输出按字段审核，可单项填入、忽略或批量采用高可信建议，不会绕过人工直接保存
- 面向 GiftMind H5 的本地策划 API：目录硬过滤、AI 生成、单件替换、信件与仪式专项重写
- 可下载的 `giftmind-gift-ingest` Agent Skill：图片/链接分析、一键草稿入库与商品/活动数量查询

## 本地启动

后端需要 Python 3.11 或更高版本：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
python -m playwright install chromium
uvicorn backend.app.main:app --reload
```

在 `.env` 中填写 `DEEPSEEK_API_KEY` 后，AI 助手固定调用
`deepseek-v4-flash`。图片最多 4 张、每张不超过 8MB。

图片不会直接交给 DeepSeek。服务器会先尝试 PaddleOCR：

```powershell
pip install -e ".[ocr]"
```

如果还要识别没有文字的普通商品图片，可在 `.env` 配置一个兼容
OpenAI 图片消息格式的视觉模型：

```dotenv
VISION_API_KEY=
VISION_BASE_URL=
VISION_MODEL=
```

OCR 文字和视觉描述会作为资料来源交给 DeepSeek 做结构化字段判断；
没有配置图片处理器时，助手会明确提示图片未能识别，不会假装看懂。

### 淘宝链接文字提取

服务器需要安装 Playwright 的 Chromium 运行时：

```bash
pip install -e .
python -m playwright install --with-deps chromium
```

也可以在 `.env` 中关闭浏览器提取：

```dotenv
PLAYWRIGHT_ENABLED=false
PLAYWRIGHT_TIMEOUT_MS=20000
```

关闭后，淘宝链接会回退到普通 HTTP 页面提取，动态商品页可能只能拿到很少的文字。

工具页的淘宝登录是服务器浏览器的截图与操作面板：采集员点击登录框后，可以通过输入框发送文字、点击或拖动验证控件。账号密码不会写入 GiftMind 数据库，只有 Playwright 的登录状态文件留在服务器 `data/private/`；该文件等同于登录凭证，不能提交 Git 或发给他人。

另开一个终端启动前端：

```powershell
Set-Location frontend
npm install
npm run dev
```

前端开发服务器会将 `/api` 请求代理至 `http://127.0.0.1:8000`。健康检查地址为 `http://127.0.0.1:8000/api/health`。

## 接入 GiftMind H5

先在 H5 仓库导出 101 条演示礼物，再导入本地数据库：

```powershell
# giftmind-h5
npm run catalog:export

# giftmind-data-studio；默认导入为 draft
python -m backend.scripts.import_h5_seed ..\giftmind-h5\data\giftmind-seed-catalog.json

# 本地全链路演示可直接启用；重复执行会跳过同名同类型条目
python -m backend.scripts.import_h5_seed ..\giftmind-h5\data\giftmind-seed-catalog.json --status active
```

H5 使用的接口前缀为 `/api/h5`。`GET /api/h5/status` 可查看 DeepSeek 配置和 active 礼物数量。没有配置 `DEEPSEEK_API_KEY` 时，生成与专项修改会保留规则兜底，不会阻断本地流程。

## 后端 Agent 与 Skill

部署或维护 Agent 入库能力前，请先阅读 [`docs/BACKEND-AGENT-SKILL.md`](docs/BACKEND-AGENT-SKILL.md)。后端启动后，访问 `GET /api/agent/skill` 可取得 Skill 元数据和绝对下载地址，也可以直接下载：

```text
http://127.0.0.1:8000/api/agent/skill/download
```

## 验证

```powershell
pytest
Set-Location frontend
npm run typecheck
npm test
npm run build
```

## 本地数据

`.env`、`data/`、`uploads/`、备份文件和依赖目录均不会提交到 Git。请在迁移或清理本地文件前单独备份这些目录。
