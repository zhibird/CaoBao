# 步骤 07 - 工具插件（从会说到会做）
## 这一步为什么存在
RAG 只解决“知道什么”，工具插件解决“去做什么”。
企业运营场景里，助手必须能触发动作，比如创建 incident、查询最近文档。

如果跳过这一步，系统就会停留在问答机器人，无法承接真实流程。

## 本步最小目标
1. 增加一个动作入口：`POST /api/v1/chat/action`
2. 接入 2 个工具：
   - `create_incident`
   - `list_recent_documents`

## 模块职责
1. `app/api/routes/chat.py`
   - 负责 HTTP 协议层，接收 `chat/action` 请求并返回响应。
2. `app/services/action_chat_service.py`
   - 负责编排：校验用户归属团队 -> 调用工具执行器 -> 组装响应。
3. `app/services/tool_service.py`
   - 负责具体动作实现（真正执行 create/list）。
4. `app/models/incident.py`
   - 负责把“动作结果”落库，形成可追踪实体。
5. `app/schemas/chat.py`
   - 负责接口 contract，定义动作请求和动作响应字段。

## 调用流程
1. 客户端调用 `POST /api/v1/chat/action`。
2. 路由把 JSON 解析成 `ChatActionRequest`。
3. `ActionChatService.execute(...)` 先校验 `user_id` 是否属于 `team_id`。
4. `ToolService.execute(...)` 根据 `action` 分发到具体工具。
5. 工具执行结果写入数据库或查询数据库。
6. 返回 `ChatActionResponse` 给客户端。

## 工具一：create_incident
请求参数：
- `arguments.title`：事件标题（必填）
- `arguments.severity`：`P1/P2/P3`（默认 `P2`）

执行结果：
- 新增一条 `incidents` 记录
- 返回 `incident_id`、`severity`、`status`

## 工具二：list_recent_documents
请求参数：
- `arguments.limit`：返回条数（1~20，默认 5）

执行结果：
- 返回该团队最近导入的文档简表

## 企业视角下的价值
1. 可执行性：把建议变成动作。
2. 可追踪性：动作有结构化结果。
3. 可扩展性：后续新增工具时，不需要改聊天主流程。
