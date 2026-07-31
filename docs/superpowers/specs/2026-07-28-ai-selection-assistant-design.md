# GiftMind AI 选品助手完整设计

## 目标

在礼物录入页增加默认收起的右侧“AI 选品助手”。每条新建或编辑中的礼物拥有独立、可恢复的聊天会话。采集同学可以发送文字、公开网页链接和最多 4 张图片；系统提取网页资料，对图片执行 OCR 或可配置的视觉理解，再调用 DeepSeek V4 Flash 返回可逐字段审核的建议补丁。

AI 永远不直接保存礼物。只有人工点击“应用”“应用全部”或“只应用高置信度”后，建议才写入当前前端表单；礼物仍需使用原有保存按钮进入数据库。

## 方案选择

### 采用：后端持久化会话

- 新建礼物生成稳定 `draft_id`，后端按它创建或恢复线程。
- 保存礼物后将线程绑定到 `gift_id`。
- 消息、资料来源、建议、已应用字段和已忽略字段均可恢复。
- 刷新页面或稍后返回时不会丢失上下文。

### 不采用：浏览器临时会话

实现最少，但刷新即丢失，无法满足“每个礼物独立上下文并可继续”的目标。

### 暂不采用：通用 Agent/工具调用框架

它适合多工具自治任务，但当前只有网页提取和结构化识别，加入框架会增加部署、调试和数据边界复杂度。

## 数据模型

### `ai_threads`

- `id`: UUID
- `draft_id`: 前端草稿 UUID，唯一索引
- `gift_id`: 可空，保存后绑定礼物
- `status`: `active` 或 `archived`
- `created_at`, `updated_at`

### `ai_messages`

- `id`: UUID
- `thread_id`: 外键
- `role`: `user` 或 `assistant`
- `content`: 对话正文
- `attachments_json`: 图片附件元数据，单轮最多 4 张
- `source_refs_json`: 链接提取结果引用
- `created_at`

### `ai_suggestion_runs`

- `id`: UUID
- `thread_id`: 外键
- `assistant_message_id`: 外键
- `patch_json`: 字段建议数组
- `confidence`: 本轮整体置信度
- `source_refs_json`: 来源摘要
- `applied_fields`: 已应用路径数组
- `ignored_fields`: 已忽略路径数组
- `created_at`, `updated_at`

迁移版本为 `0002_ai_assistant_threads`，不改动既有礼物表结构。

## API

### 创建或恢复线程

`POST /api/ai/threads`

```json
{
  "draftId": "uuid",
  "giftId": null
}
```

同一个 `draftId` 重复请求返回同一线程。

### 读取线程

`GET /api/ai/threads/{thread_id}`

返回按时间排序的消息和最近建议轮次。

### 发送消息

`POST /api/ai/threads/{thread_id}/messages`

```json
{
  "content": "这是一张南京博物院黄铜书签，链接 https://example.com/item",
  "giftTypeCode": "product",
  "currentValues": {},
  "imageAttachments": []
}
```

服务端执行：

1. 保存用户消息。
2. 从正文识别最多 3 个 URL。
3. 仅抓取公开 HTTP/HTTPS 页面；10 秒超时、最多 3 次重定向、正文最多 1MB。
4. 提取标题、描述、可见正文、价格线索和 JSON-LD 产品信息。
5. 对最多 4 张图片调用本机 PaddleOCR；如配置了兼容接口，则同时生成视觉描述。
6. 将 OCR 文本和视觉描述存为来源引用。DeepSeek 只接收这些文本，不直接接收图片。
7. 将当前线程最近 12 条消息、提取结果和当前表单值交给 DeepSeek V4 Flash。
8. 保存助手消息与结构化建议轮次。
9. 返回完整的新消息、待确认问题与建议补丁。

链接抓取失败不会让整轮对话失败；助手会标记该来源无法读取，并继续处理文字。

### 记录审核结果

`PATCH /api/ai/suggestion-runs/{run_id}`

```json
{
  "appliedFields": ["priceMin", "productDetails.materials"],
  "ignoredFields": ["tags"]
}
```

### 保存后绑定礼物

`PATCH /api/ai/threads/{thread_id}/bind`

```json
{ "giftId": "uuid" }
```

绑定前校验礼物存在。

## 建议补丁格式

每个字段独立返回：

```json
{
  "path": "productDetails.materials",
  "label": "材质",
  "value": ["黄铜"],
  "confidence": 0.91,
  "sourceRefs": ["用户描述", "https://example.com/item"],
  "status": "pending"
}
```

覆盖字段：

- `canonicalName`
- `giftTypeCode`
- `shortDescription`
- `priceMin`, `priceMax`, `isFree`
- `whyTemplate`
- `recipientTypes`, `occasions`, `interests`, `tags`
- 商品：`genericProductName`, `materials`, `personalizationMethods`, `shippingRequired`
- 活动：`activityCategory`, `serviceRegions`, `durationMinutesMin/Max`, `participantsMin/Max`, `bookingRequired`, `bookingLeadDaysMin/Max`

服务端只允许白名单路径，丢弃未知路径，规范数字、布尔值和字符串数组。置信度限制在 0 到 1。

## 前端交互

### 悬浮助手

- 桌面端固定在右下角，默认收起为“AI 选品助手”按钮。
- 展开后宽 390px、高度不超过视口。
- 移动端展开为底部全宽抽屉。
- 顶部显示当前礼物会话状态，允许关闭但不删除上下文。
- 消息区显示用户输入、助手说明和链接来源。
- 输入区发送文字；正文中的链接自动识别，无需单独输入框。
- 支持一次选择最多 4 张图片，并显示缩略图和识别状态。

### 字段审核

- 建议卡显示字段名、建议值、来源、置信度。
- 每项提供“应用”和“忽略”。
- 顶部提供“应用全部建议”“只应用高置信度建议（≥0.8）”“清除本次建议”。
- “清除”只清除当前建议卡，不删除聊天历史。
- 已应用项提供“撤销”；撤销恢复应用前的字段值。
- 表单字段被 AI 改写后以浅绿色高亮。
- 人工修改该字段后，高亮自动消失。

### 礼物类型

- 新礼物且当前类型专属字段为空时，可直接应用 AI 类型建议。
- 当前类型专属字段已有内容时，沿用现有类型切换确认框。
- 编辑已有礼物时类型保持锁定，AI 类型建议可忽略但不能应用。

## 草稿与线程生命周期

- `WorkbenchState` 增加 `draftId`，`startNew()` 每次生成新的 UUID。
- 同一条未保存草稿恢复时沿用本地保存的 `draftId`。
- `saveDraft()` 成功后保留 `draftId` 并绑定 `giftId`。
- “保存并新建下一条”成功后才生成新 `draftId`，因此新礼物不会继承上一条聊天。
- 编辑既有礼物时使用稳定的 `gift-{gift_id}` draft 标识创建或恢复线程。

## 错误与降级

- 未配置 DeepSeek 时仍创建线程，并使用现有规则建议返回低置信度补丁。
- DeepSeek 超时或返回非法 JSON 时保存一条降级助手消息，不丢用户输入。
- 链接失败以来源状态展示，不阻断文字识别。
- 消息发送期间禁用重复提交。
- 所有错误在悬浮窗内可见，不影响原有表单保存。

## 图片理解架构

DeepSeek V4 Flash 负责结构化文本推理，不直接接收图片。图片先经过独立预处理：

1. 默认可安装 `paddleocr` 可选依赖，在服务器本机执行 OCR。
2. 如需识别画面、材质、包装和使用场景，可配置 OpenAI 兼容视觉接口：
   `VISION_API_KEY`、`VISION_BASE_URL`、`VISION_MODEL`。
3. OCR 文本、视觉描述、处理器名称和错误状态都作为 `source_ref` 保存。
4. 没有配置任何图片处理器时，界面明确显示“图片识别不可用”，不会伪造结果。
5. 聊天图片只作为采集资料；正式礼物图片仍由原有图片区人工选择和排序。

## 主动补问、批量导入与查重

- 每轮分析后最多给出 3 个关键补问，例如预算、对象、场景或活动时长。
- 工具页可一次解析最多 20 个公开链接；每个链接产生独立、待人工审核的草稿建议。
- 批量解析不会直接保存礼物。
- 单条录入继续提供精确和近似重复提示。
- 工具页提供全库近似重复扫描，供人工判断合并，不自动删除数据。

## 验收标准

- 两个不同 `draftId` 的线程消息完全隔离。
- 刷新后同一草稿恢复原线程与消息。
- 文字、可访问链接以及经过 OCR/视觉预处理的图片可生成结构化字段建议。
- 多图片不会直接发送给 DeepSeek。
- 不可访问链接不阻断整轮消息。
- 未知字段路径不会返回前端。
- 单字段应用、忽略、撤销可用。
- 应用全部和高置信度应用可用。
- AI 应用字段高亮，人工修改后高亮消失。
- 保存礼物后线程绑定 `giftId`；新建下一条产生新线程。
- AI 不直接调用礼物保存 API。
- 批量链接可生成独立待审草稿；全库重复扫描可显示近似重复对。
- 后端、前端测试、类型检查和生产构建通过。
