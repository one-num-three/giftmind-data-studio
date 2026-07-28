# GiftMind Data Studio

GiftMind 的数据采集与维护工作台。它为礼物条目、素材、导入导出和数据质量维护提供独立的管理界面，并以 FastAPI 后端和 Vue 3 前端组成一个本地优先的应用。

## 包含内容

- 礼物数据的创建、编辑、筛选、回收与恢复
- 产品、活动及组合礼物的类型化字段
- 导入、导出、备份与审核辅助工具
- 受通行码保护的本地会话
- 可选的 DeepSeek V4 Flash 辅助预填；密钥只保存在服务器 `.env`
- 每条礼物独立的 AI 选品助手会话，支持文字、链接和 JPG/PNG/WebP 图片
- AI 输出按字段审核，可单项填入、忽略或批量采用高可信建议，不会绕过人工直接保存

## 本地启动

后端需要 Python 3.13 或更高版本：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
uvicorn backend.app.main:app --reload
```

在 `.env` 中填写 `DEEPSEEK_API_KEY` 后，AI 助手固定调用
`deepseek-v4-flash`。图片最多 4 张、每张不超过 8MB。

另开一个终端启动前端：

```powershell
Set-Location frontend
npm install
npm run dev
```

前端开发服务器会将 `/api` 请求代理至 `http://127.0.0.1:8000`。健康检查地址为 `http://127.0.0.1:8000/api/health`。

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
