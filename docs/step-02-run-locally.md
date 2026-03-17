# 濠殿喗绺块崕鐢割敁?02 - 闂佸搫鐗滈崜娆忥耿鐎涙ɑ浜ら柟閭﹀灱閺€鑺ヮ殽閻愭彃顣抽柟顔硷功閹叉挳鏁愰崱妯活啋婵炶揪绲鹃幐鑽ょ矈閿斿墽鐭?
## 1. 闁诲海鎳撻ˇ鎶剿?Python 3.11闂佹寧绋戝﹢绛皀dows闂?
1. 婵炲濮存鎼佹偩閼测晝纾鹃柟瀛樼矌閻熸捇寮堕悙鑸殿棄闁伙絻鍔庨幉?Python 3.11闂?2. 闁诲海鎳撻ˇ鎶剿夋繝鍐╀氦闁搞儮鏂侀弻銈呪槈閹垮啫骞栭悗锝傚亾闂?`Add Python to PATH`闂?3. 闂?PowerShell 婵炴垶鎼╅崣鍐偘濞嗘垶瀚氬〒姘功缁?
```powershell
python --version
```

## 2. 闂佸憡甯楃粙鎴犵磽閹剧粯鎯炴慨姗嗗幖閻濐垶鏌ｅ搴＄仩妞?
```powershell
python -m venv .CaiBao
.\.CaiBao\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3. 闂佸憡鍑归崹鐗堟叏?API 闂佸搫鐗嗙粔瀛樻叏?
```powershell
uvicorn app.main:app --reload --port 8000
```

## 4. 婵°倗濮撮惌渚€鎯佹径鎰闁靛鍎辩紞鎾绘煥濞戞ɑ鎭璷werShell 闂佺绻掗崢褔顢欓幇鏉跨婵炲棙鍔楅妴濠囨煥?
### 4.1 闂佺顑冮崕閬嶅箖瀹ュ憘娑㈠焵椤掑嫬钃?
```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/v1/health"
```

### 4.2 闂佸憡甯楃粙鎴犵磽閹捐鐐婇柕蹇嬪€栬

```powershell
$team = @{ team_id = "team_ops"; name = "Operations Team"; description = "MVP default team" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/teams" -ContentType "application/json" -Body $team
```

### 4.3 闂佸憡甯楃粙鎴犵磽閹剧粯鍋ㄩ柕濠忕畱閻?
```powershell
$user = @{ user_id = "u_001"; team_id = "team_ops"; display_name = "Alice"; role = "owner" } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/users" -ContentType "application/json" -Body $user
```

### 4.4 闁诲海鏁搁崢褔宕ｉ崱娑樻闁搞儯鍔婇埀?
```powershell
$doc = @{
  team_id = "team_ops"
  source_name = "ops-guide.md"
  content_type = "md"
  content = "# Ops Guide`n`nAlways check alerts first. Escalate incidents quickly."
} | ConvertTo-Json

$imported = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/documents/import" -ContentType "application/json" -Body $doc
$document_id = $imported.document_id
```

### 4.5 闂佸搫鍊稿ú锕傚Υ閸岀偛绀嗛柛銉戝啰鈧?
```powershell
$chunkPayload = @{ team_id = "team_ops"; max_chars = 120; overlap = 20 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/documents/$document_id/chunk" -ContentType "application/json" -Body $chunkPayload
```

### 4.6 閻庣偣鍊涘▍锝夋偟濞戙垹瑙﹂柟杈剧畱濞呫倗绱掓笟鍨仼缂?
```powershell
$indexPayload = @{ team_id = "team_ops"; document_id = $document_id } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/retrieval/index" -ContentType "application/json" -Body $indexPayload
```

### 4.7 TopK 濠碘槅鍋€閸嬫挾绱?
```powershell
$searchPayload = @{ team_id = "team_ops"; query = "alerts"; top_k = 3; document_id = $document_id } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/retrieval/search" -ContentType "application/json" -Body $searchPayload
```

### 4.8 RAG 闂傚倸鍋嗛崰姘舵偤閻斿吋鏅柛褍娼漚t/ask闂?
```powershell
$askPayload = @{
  user_id = "u_001"
  team_id = "team_ops"
  question = "闂佸憡鍨煎▍锝夌嵁閸ヮ剙宸濆┑鐘叉媼閸斿懘鏌涘顒佹崳妞ゆ垵娲︾粙澶愬焵椤掆偓椤垽濡烽…鎴炵煑闂佺顑嗛惌顔惧垝閸喓鈻曢柛顐墰閸?
  top_k = 3
  document_id = $document_id
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/chat/ask" -ContentType "application/json" -Body $askPayload
```

## 5. 闂佹椿浜為崰搴ㄦ偪?LLM闂佹寧绋戦悧鍡氥亹閺屻儲鐒诲鑸电〒缁€?
婵帗绋掗…鍫ヮ敇?`LLM_PROVIDER=mock`闂佹寧绋戞總鏃傜箔婢跺鐟规繝闈涳功椤╊偄顭块懜鐢靛⒌闁稿孩鎸冲闈涱吋閸涱収娼抽梺?
婵犵鈧啿鈧綊鎮樻径瀣闁绘ü璀﹀ú锝夋煙閹帒鍔ゆ繝鈧敍鍕ㄥ亾閸︻厼浠﹂懚鈺呮煕閵娿儺鍎滅紒杈ㄧ箘閹风姴鐣￠悧鍫ｅ惈 `.env` 闁荤姳绀佹晶浠嬫偪閸℃稒鏅?
```env
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=<YOUR_LLM_API_KEY>
LLM_MODEL=gpt-4.1-mini
```

## 6. 闂傚倸鍟幊鎾活敋閻楀牏顩烽柨婵嗘川閸ㄥ啿顪冮妶鍛儓缂?
1. `app/api/routes/chat.py`
2. `app/services/rag_chat_service.py`
3. `app/services/retrieval_service.py`
4. `app/services/llm_service.py`
## 7. 婵炴垶鎼╅崢浠嬪几閸愨晝鈻曢弶鍫氭櫇閸ㄦ娊鏌熼悜妯虹瑲闁绘搫绻濋弫宥夊捶椤хerShell闂?
婵犵鈧啿鈧綊鎮?`chat/ask` 闂佹眹鍔岀€氼亪鎳欓幋锕€妫橀柛銉墯閿涙牕螞閻楀煶鎴﹀垂閵娧呴┏闁哄啠鍋撴い銏犵Ч瀵即宕滆娴犳盯鏌?`????` / 婵炴垶妫佹禍顒勬偉濠婂牊鏅€光偓閸曘劌浜炬慨姗嗗墰閸╂鏌￠崟闈涚仯缂侇喗鎸剧划鈺咁敍濠婂懏銇濋梺娲诲枙濡炴帞绮径鎰強?UTF-8闂?
闂佺绻愰悧濠冩櫠閻ｅ本鍋樼€光偓鐎ｎ剛鐛?
```powershell
chcp 65001
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
```

闂佸憡鍔曠粔鍫曞极?UTF-8 闂佸搫瀚ù鐑藉灳濮椻偓瀹曪綁骞嬮敂鐟颁壕濞达絿鐡旈崵鐐存叏閻熸澘浜扮紒?
```powershell
$json = $askPayload | ConvertTo-Json -Depth 6
$bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/chat/ask" -ContentType "application/json; charset=utf-8" -Body $bytes
```
## 8. Tool plugin action call (Step 07)
Create an incident:

```powershell
$actionPayload = @{
  user_id = "u_001"
  team_id = "team_ops"
  action = "create_incident"
  arguments = @{
    title = "Database CPU usage above threshold"
    severity = "P1"
  }
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/chat/action" -ContentType "application/json; charset=utf-8" -Body $actionPayload
```

List recent documents:

```powershell
$listPayload = @{
  user_id = "u_001"
  team_id = "team_ops"
  action = "list_recent_documents"
  arguments = @{ limit = 3 }
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/api/v1/chat/action" -ContentType "application/json; charset=utf-8" -Body $listPayload
```

## 9. Chat history (Step 08)
Read recent history records by team:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/v1/chat/history?team_id=team_ops&limit=10"
```

Read recent history records by team + user:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/v1/chat/history?team_id=team_ops&user_id=u_001&limit=10"
```

## 10. Docker deploy (Step 09)
Build and run:

```powershell
docker compose up --build -d
```

View logs:

```powershell
docker compose logs -f caibao-api
```

Check health:

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/v1/health"
```

Stop:

```powershell
docker compose down
```

> Tip: if local `uvicorn` is already running on port `8000`, stop it first before starting Docker.
