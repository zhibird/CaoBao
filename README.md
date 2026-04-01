## changelogs

- **v0.1.0**：后端 MVP + 前端基础页面
- **v0.2.0**：会话管理（引入会话 `conversation_id`，实现会话隔离、删除）
- **v0.3.0**：支持会话重命名、消息删除、用户发送的对话消息重新编辑
- **v0.4.0**：完善调用大模型 API 对话能力，支持用户在前端填写 API Key / Base URL 配置模型，并按账号隔离使用
- **v0.5.0**：优化前端界面，新增会话置顶（pin）接口，支持复制与切换模型重生成
  - **v0.5.1**：前端 UI 细节优化
- **v0.6.0**：
  1）AG 检索链路正式支持真实 embedding（非 mock）并可安全重建索引
  2）增真实场景性能评估数据集
- **v0.7.0**：
  1）面向团队暂时调整为面向用户（account），产品初步定位为小豆包
  2）答返回补齐 `mode + sources`，支持前端清晰展示回答模式与来源
  3）页新增场景卡区块，点击后可一键填充提示词模板
  - **v0.7.1**：修复 RAG 链路存在的 bug
- **v0.8.0**：将会话内 RAG 交互从“系统视角的文档范围配置”调整为“用户视角的附件式聊天流”，更符合豆包心智模型
- **v0.9.0**：新增“开发者可用”的管理员账户与独立管理后台，集中管理团队/用户/会话/上传文件
  - **v0.9.1**：隔离测试用数据库，修复测试数据污染主库问题，清理历史脏数据
- **v0.10.0**：新增支持 PDF 与图片上传与解析功能
  - **v0.10.1**：修复附件预览时报错的问题
  - **v0.10.2**：支持将文件拖拽进聊天输入区完成附件上传
  - **v0.10.3**：修正图片附件的调用逻辑（支持多模态）
  - **v0.10.4**：修复模型回复显示不完整的问题
- **v0.11.0**：支持模型输出图片
  - **v0.11.1**：修复模型图片输出的续写污染与远程图片历史失效问题
  - **v0.11.2**：支持点击预览聊天图片，并在预览界面下载图片
- **v0.12.0**：附件上传新增支持 Word / Excel（`docx` / `xlsx`）
  - **v0.12.1**：修复图片附件问答在部分 OpenAI-compatible 提供方返回 400 的问题
  - **v0.12.2**：升级前端UI，优化交互体验
- **v0.13.0**：支持同会话上下文记忆
- **v0.14.0**：新增回答收藏（favorites）与历史结论（conclusions）沉淀能力，支持从收藏转记忆卡/结论

## 部署与迁移（本地/内网）

当前默认部署仍使用 SQLite，不切换到 PostgreSQL：

- `DATABASE_URL=sqlite:////data/CaiBao.db`
- Docker volume 持久化目录：`/data`

### 本地启动

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Alembic 迁移（SQLite）

```powershell
# 升级到最新版本
python -m alembic upgrade head

# 回滚一步
python -m alembic downgrade base
```

### Docker 启动（本地/内网）

```powershell
docker compose up --build -d
docker compose logs -f caibao-api
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/v1/health"
```

### Phase 2 记忆卡链路验收（后端）

1. 创建记忆卡：`POST /api/v1/memory/cards`
2. 查看记忆卡：`GET /api/v1/memory/cards?team_id=...&user_id=...&space_id=...`
3. 发起问答：`POST /api/v1/chat/ask`（默认 `include_memory=true`）
4. 禁用记忆卡后复测：`PATCH /api/v1/memory/cards/{memory_id}` 将 `status=disabled`，确认不再注入

### Phase 3 收藏与结论链路验收（后端）

1. 创建收藏：`POST /api/v1/favorites/answers`
2. 查询收藏：`GET /api/v1/favorites/answers?team_id=...&user_id=...&space_id=...`
3. 收藏转记忆卡：`POST /api/v1/favorites/answers/{favorite_id}/promote-to-memory`
4. 收藏转结论：`POST /api/v1/favorites/answers/{favorite_id}/promote-to-conclusion`
5. 查询结论：`GET /api/v1/conclusions?team_id=...&user_id=...&space_id=...`
6. 结论确认：`POST /api/v1/conclusions/{conclusion_id}/confirm`，并验证 `doc_sync_document_id` 已生成
7. 结论归档：`POST /api/v1/conclusions/{conclusion_id}/archive`
