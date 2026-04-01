# 步骤 09 - Docker 部署（本地/内网）

## 1. 目标

这一步用于把 CaiBao 以容器方式跑起来，并保持数据可持久化。  
当前默认数据库仍是 SQLite，不切换 PostgreSQL。

## 2. 当前部署基线

`docker-compose.yml` 采用以下约定：

1. 服务：`caibao-api`
2. 端口：`8000:8000`
3. 数据库：`DATABASE_URL=sqlite:////data/CaiBao.db`
4. 持久化：`caibao_data:/data`
5. 迁移策略：`APP_ENV=prod` + `DB_LEGACY_INIT_ENABLED=false`，启动前自动执行 `alembic upgrade head`

## 3. 启动与停止

```powershell
docker compose up --build -d
docker compose logs -f caibao-api
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/v1/health"
docker compose down
```

> 提示：如果本机已有 `uvicorn` 占用 `8000`，先停止本机进程再起容器。

## 4. Alembic 迁移（SQLite）

### 4.1 本机执行

```powershell
# 升级到最新
alembic upgrade head

# 回滚一步
alembic downgrade base
```

### 4.2 容器内执行

```powershell
docker compose exec caibao-api alembic upgrade head
docker compose exec caibao-api alembic downgrade base
```

说明：

1. 迁移命令不改变数据库类型，只对当前 SQLite 文件做结构升级/回滚。
2. 生产模式下应用会在启动前自动执行 `upgrade head`，且 schema 非 `head` 会拒绝启动。

### 4.3 历史库一次性对齐（旧库已由 `create_all` 建过表）

如果旧库曾由历史逻辑 `create_all + ALTER` 初始化，建议先做一次 stamp 再升级：

```powershell
# 将历史库标记到当前迁移头（不改数据）
alembic stamp head

# 再执行升级校验（应为 no-op）
alembic upgrade head
```

如果希望分阶段对齐，也可以先标记到基线再升级：

```powershell
alembic stamp 20260330_00
alembic upgrade head
```

## 5. Phase 2 记忆卡本地验收（后端）

### 5.1 创建记忆卡

```powershell
$payload = @{
  team_id = "team_ops"
  user_id = "u_001"
  space_id = "your_space_id"
  title = "默认输出语言"
  content = "以后默认用中文回答。"
  category = "preference"
  status = "active"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/memory/cards" -ContentType "application/json; charset=utf-8" -Body $payload
```

### 5.2 验证列表与空间隔离

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/v1/memory/cards?team_id=team_ops&user_id=u_001&space_id=your_space_id"
```

### 5.3 问答注入记忆

`POST /api/v1/chat/ask` 时默认 `include_memory=true`，应能命中已激活记忆卡。

### 5.4 禁用后不再注入

将该卡状态更新为 `disabled` 后再次 `chat/ask`，应不再注入这条记忆。

## 6. Phase 3 收藏与结论本地验收（后端）

### 6.1 从聊天消息创建收藏

```powershell
$favoritePayload = @{
  team_id = "team_ops"
  user_id = "u_001"
  space_id = "your_space_id"
  conversation_id = "your_conversation_id"
  message_id = "your_message_id"
  title = "可复用回答"
  note = "后续转结论"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/favorites/answers" -ContentType "application/json; charset=utf-8" -Body $favoritePayload
```

### 6.2 查询收藏列表

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/v1/favorites/answers?team_id=team_ops&user_id=u_001&space_id=your_space_id"
```

### 6.3 收藏转记忆卡

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/favorites/answers/your_favorite_id/promote-to-memory" -ContentType "application/json; charset=utf-8" -Body (@{team_id="team_ops";user_id="u_001"} | ConvertTo-Json)
```

### 6.4 收藏转结论并确认归档

```powershell
# 转结论
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/favorites/answers/your_favorite_id/promote-to-conclusion" -ContentType "application/json; charset=utf-8" -Body (@{team_id="team_ops";user_id="u_001"} | ConvertTo-Json)

# 确认结论（应生成 doc_sync_document_id）
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/conclusions/your_conclusion_id/confirm" -ContentType "application/json; charset=utf-8" -Body (@{team_id="team_ops";user_id="u_001"} | ConvertTo-Json)

# 归档结论
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/conclusions/your_conclusion_id/archive" -ContentType "application/json; charset=utf-8" -Body (@{team_id="team_ops";user_id="u_001"} | ConvertTo-Json)
```

## 7. 回滚建议

如果升级后发现问题，优先回滚迁移而不是手工改表：

```powershell
alembic downgrade base
```

然后重启服务并复测健康检查与关键接口。
