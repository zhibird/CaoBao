# CaiBao

这是一个面向新手、从零开始的最小版项目。目标不是一次做成“大而全”的系统，而是先做出一个能跑通的 MVP（CaiBao），再一层层补能力。

## 技术栈

1. 后端
   1. Python 3.11（见 `Dockerfile`）
   2. FastAPI（Web 框架）
   3. Uvicorn（ASGI Server）
   4. Pydantic Settings（配置管理：`.env` / 环境变量）
2. 数据库
   1. SQLAlchemy 2.x（ORM）
   2. SQLite（默认：文件库，Docker 下默认落在挂载卷 `/data/CaiBao.db`）
3. 测试与调用
   1. Pytest（测试框架）
   2. HTTPX（HTTP Client，用于测试/接口调用）
4. 部署
   1. Docker（容器化，见 `Dockerfile`）
   2. Docker Compose（本地/服务器一键拉起，见 `docker-compose.yml`）
5. LLM 接入（可选）
   1. 通过环境变量 `LLM_PROVIDER` / `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` 切换
   2. 默认 `LLM_PROVIDER=mock`，也可对接 OpenAI 兼容接口（默认 `LLM_BASE_URL=https://api.openai.com/v1`）

## 1. 最小版能力

1. 用户 / 团队配置
2. 聊天入口
3. 文档导入
4. 文档切分
5. 向量索引与检索
6. RAG 问答
7. 工具插件（后续）
8. 聊天记录（后续）
9. Docker 部署（后续）

## 2. 当前完成

1. `/api/v1/teams`、`/api/v1/users` 配置管理
2. `/api/v1/conversations` 会话创建/列表/删除
3. `/api/v1/documents/import` 文档导入
4. `/api/v1/documents/{id}/chunk` 文档切分
5. `/api/v1/retrieval/index` 向量索引
6. `/api/v1/retrieval/search` TopK 检索
7. `/api/v1/chat/ask` 问答（默认对话；有索引时自动走 RAG）
8. 会话级文档/历史隔离（`conversation_id` 贯穿链路）

## 3. 下一步

1. 在 `chat/ask` 中加入更严格的引用/来源格式
2. 接入 1-2 个工具插件
3. 保存聊天记录并做 Docker 部署

## 4. 学习文档

1. `docs/step-01-module-map.md`
2. `docs/step-02-run-locally.md`
3. `docs/step-03-team-user-config.md`
4. `docs/step-04-document-import.md`
5. `docs/step-04-chunking.md`
6. `docs/step-05-retrieval-index-search.md`
7. `docs/step-05-rag-chat.md`

## 5. 个人版产品设计（会话隔离 + 跨会话上下文）

为满足“小豆包”形态，本项目后续产品方向调整为：**默认会话隔离，显式跨会话桥接**。

### 5.1 核心原则

1. 默认只使用当前会话上下文（不跨会话读历史全文）
2. 上传文件默认仅当前会话可用（不做全局共享）
3. 跨会话能力通过“记忆卡片 / 资料库”显式开启
4. 所有跨会话来源在回答中可解释、可关闭、可删除

### 5.2 三层上下文模型

1. 会话层（Session Scope）
   1. 当前会话消息、临时文件、草稿
   2. 强隔离，不跨会话自动读取
2. 记忆层（Memory Scope）
   1. 用户偏好、长期目标、关键约束
   2. 通过“记住这条”写入，可随时删除
3. 知识层（Library Scope）
   1. 用户主动发布到资料库的内容
   2. 可在多个会话复用检索

### 5.3 当前状态与后续演进

1. 当前实现仍以 `team/user` 为基础模型
2. 下一步将按个人版改造为 `account + conversation` 主模型
3. 会补充会话级文件隔离、会话/消息删除接口、跨会话上下文开关

详细实现细节见：

- `design/personal-edition-architecture.md`

## 6. 更新日志（changelogs）

1. 目录：根目录 `changelogs/`
2. 文件名：按版本号命名（如 `0.2.0.md`）
3. 内容规范：
   1. 使用中文撰写
   2. 文末附“具体代码文件改动”清单
4. 当前版本：`0.2.0`
5. 最新日志：`changelogs/0.2.0.md`
