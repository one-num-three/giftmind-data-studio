# GiftMind 后端 Agent 必读：礼物入库 Skill 与接口

这份文档是部署、维护或排查 GiftMind 后端 Agent 能力前必须阅读的运行契约。目标是让任意 Agent 接收礼物图片、链接和描述后，通过一个稳定接口生成结构化草稿；Agent 不得直接写 SQLite。

## 1. 系统边界

一次入库按以下顺序执行：

1. Agent 先读取用户发送的图片，整理可见名称、颜色、价格、规格和客观描述。
2. Skill 脚本使用团队口令调用 `/api/session/login`，只在内存 CookieJar 保存会话。
3. 脚本把描述、图片、链接和已知字段提交到 `/api/agent/gifts/ingest`。
4. 后端提取网页文字，尝试 PaddleOCR / 视觉模型，再把文字证据交给 DeepSeek。
5. 后端执行商品/活动类型约束、字段校验和精确重复检查。
6. 合格记录写入数据库，默认状态为 `draft`；第一张图片保存为封面。

以下边界不得绕过：

- 不允许 Agent 直接连接或修改 SQLite。
- 不允许为了绕过 409 而改写同一礼物名称。
- AI 推断不能写入 `verifiedAt`，验证状态只由人工维护。
- 用户明确给出的名称、价格、颜色和备注优先于 AI 建议。
- 没有图像处理器时必须返回 `processor: none`，不能假装识别了图片。

## 2. 代码与发布物

核心文件：

- `backend/app/api/routes/agent_ingest.py`：入库、计数、Skill 元数据和下载接口。
- `backend/app/services/assistant_suggestions.py`：DeepSeek 与规则兜底生成字段建议。
- `backend/app/services/image_understanding.py`：OCR 与视觉模型转文字。
- `backend/app/services/gifts.py`：类型化写入、完整度与重复保护。
- `skills/giftmind-gift-ingest/`：后端对外分发的完整 Skill。
- `tests/api/test_agent_ingest.py`：接口契约回归测试。

下载 ZIP 由后端根据仓库内 `skills/giftmind-gift-ingest/` 实时生成。不要在服务器上手工维护另一份 ZIP，否则下载内容会与 Git 版本漂移。

## 3. 环境变量

最少配置：

```dotenv
APP_SECRET=replace-with-a-long-random-value
TEAM_PASSCODE=replace-with-the-team-passcode
DATABASE_URL=sqlite+aiosqlite:///./data/giftmind.sqlite3
DATA_DIR=./data
UPLOAD_DIR=./uploads
BACKUP_DIR=./backups
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-v4-flash
```

图片理解可选配置：

```dotenv
VISION_API_KEY=
VISION_BASE_URL=
VISION_MODEL=
```

也可以安装本地 OCR：

```bash
pip install -e '.[ocr]'
```

`.env`、数据库、上传图片、淘宝 Cookie 和备份目录不得提交 Git。

## 4. Skill 下载接口

Skill 元数据（公开，不包含秘密）：

```http
GET /api/agent/skill
```

返回示例：

```json
{
  "name": "giftmind-gift-ingest",
  "version": "1.0.0",
  "downloadUrl": "https://example.com/api/agent/skill/download",
  "sha256": "...",
  "sizeBytes": 12345
}
```

直接下载链接：

```text
https://<GiftMind 后端域名>/api/agent/skill/download
```

服务器 Agent 安装：

```bash
curl -fL 'https://<GiftMind 后端域名>/api/agent/skill/download' -o /tmp/giftmind-gift-ingest.zip
mkdir -p ~/.codex/skills
unzip -o /tmp/giftmind-gift-ingest.zip -d ~/.codex/skills
python ~/.codex/skills/giftmind-gift-ingest/scripts/ingest_gift.py --help
```

可先对照元数据里的 SHA-256：

```bash
sha256sum /tmp/giftmind-gift-ingest.zip
```

## 5. 入库接口

```http
POST /api/agent/gifts/ingest
Content-Type: multipart/form-data
```

该接口复用现有团队会话。先登录：

```bash
curl -c /tmp/giftmind-cookie.txt \
  -H 'Content-Type: application/json' \
  -d '{"passcode":"<TEAM_PASSCODE>"}' \
  'https://<GiftMind 后端域名>/api/session/login'
```

再提交：

```bash
curl -b /tmp/giftmind-cookie.txt \
  -F 'description=南京主题黄铜书签，标价 69 元' \
  -F 'gift_type_code=auto' \
  -F 'lifecycle_status=draft' \
  -F 'known_fields_json={"canonicalName":"南京主题黄铜书签","productDetails":{"colors":["金色"]}}' \
  -F 'source_urls_json=[]' \
  -F 'images=@/path/to/gift.jpg' \
  'https://<GiftMind 后端域名>/api/agent/gifts/ingest'
```

约束：

- 图片最多 4 张；单张最大 8 MB；仅 JPG、PNG、WebP。
- `gift_type_code` 为 `auto`、`product` 或 `activity`。
- `lifecycle_status` 默认为 `draft`。
- `known_fields_json` 使用 GiftMind camelCase 字段，并覆盖 AI 建议。
- 精确重复返回 HTTP 409 和 `DUPLICATE_GIFT`。
- 信息不足返回 HTTP 422、`INCOMPLETE_GIFT`、缺失问题及字段错误。

## 6. 数量接口

```http
GET /api/agent/gifts/counts
```

该接口需要团队会话，统计所有未删除记录：

```json
{
  "productCount": 84,
  "activityCount": 18,
  "totalCount": 102,
  "byStatus": {"draft": 1, "active": 101, "inactive": 0}
}
```

Skill 脚本可直接查询：

```bash
export GIFTMIND_API_URL='https://<GiftMind 后端域名>'
export GIFTMIND_TEAM_PASSCODE='<TEAM_PASSCODE>'
python ~/.codex/skills/giftmind-gift-ingest/scripts/ingest_gift.py --counts
```

## 7. Nginx 与进程要求

建议至少设置：

```nginx
client_max_body_size 40m;
proxy_read_timeout 240s;
proxy_send_timeout 240s;
```

`/api/` 必须代理到 FastAPI，`/uploads/` 可以由 FastAPI 当前挂载处理或由 Nginx 映射到同一 `UPLOAD_DIR`。部署代码时必须包含 `skills/giftmind-gift-ingest/`，否则下载接口会返回 503。

本次接口不增加数据库表，无需新增 Alembic 迁移。

## 8. 部署后自检

```bash
curl -fsS 'https://<GiftMind 后端域名>/api/health'
curl -fsS 'https://<GiftMind 后端域名>/api/agent/skill'
curl -fL 'https://<GiftMind 后端域名>/api/agent/skill/download' -o /tmp/giftmind-skill.zip
unzip -l /tmp/giftmind-skill.zip
```

仓库验证：

```bash
pytest -q tests/api/test_agent_ingest.py
pytest -q
ruff check backend/app/api/routes/agent_ingest.py tests/api/test_agent_ingest.py backend/app/api/router.py
python ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/giftmind-gift-ingest
```

发布前确认下载 ZIP 中至少包含：

- `giftmind-gift-ingest/SKILL.md`
- `giftmind-gift-ingest/agents/openai.yaml`
- `giftmind-gift-ingest/scripts/ingest_gift.py`
- `giftmind-gift-ingest/references/api-contract.md`
