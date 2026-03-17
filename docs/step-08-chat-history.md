# 步骤 08 - 聊天记录（Chat History）
## 这一步为什么存在
前面我们已经有问答与工具动作，但还没有“可追踪性”。
企业系统里必须能回放：谁问了什么、系统怎么回答、触发了什么动作。

如果跳过这一步，线上出现错误时无法审计与复盘，也无法做后续会话上下文能力。

## 本步最小目标
1. 所有聊天入口自动落库：
   - `POST /api/v1/chat/echo`
   - `POST /api/v1/chat/ask`
   - `POST /api/v1/chat/action`
2. 增加历史查询接口：
   - `GET /api/v1/chat/history`

## 模块职责
1. `app/models/chat_history.py`
   - 定义聊天记录表结构。
2. `app/services/chat_history_service.py`
   - 负责写入记录和查询记录。
3. `app/api/routes/chat.py`
   - 在每个聊天入口执行成功后调用记录服务。
   - 提供 `chat/history` 查询入口。
4. `app/schemas/chat.py`
   - 定义历史记录响应结构（返回给前端/客户端）。

## 调用流程
1. 用户调用 `echo/ask/action`。
2. 业务逻辑返回结果。
3. 路由调用 `ChatHistoryService.record_message(...)` 写入数据库。
4. 后续调用 `GET /chat/history` 可按团队/用户查看最近记录。

## 为什么把记录放在路由层
- 路由层最清楚“本次请求 + 本次响应”的完整结构。
- 服务层专注业务逻辑，路由层负责协议与审计拼装。
- 这样职责更清晰，后续扩展也更稳。

## 缺失后果（企业视角）
1. 无法审计：不知道谁触发过哪些动作。
2. 无法复盘：问题出现时拿不到上下文。
3. 无法演进：后续做会话记忆、质量分析会很困难。
