# 濮濄儵顎?09 - Docker 闁劎璁?## 鏉╂瑤绔村銉よ礋娴犫偓娑斿牆鐡ㄩ崷?閸撳秹娼伴幋鎴滄粦閸︺劍婀伴崷鎷屾珓閹风喓骞嗘晶鍐櫡鏉╂劘顢戦張宥呭閿涘矁绻栭柅鍌氭値瀵偓閸欐垵顒熸稊鐘偓?娴间椒绗熸い鍦窗娑撳﹦鍤庨弮鍫曟付鐟曚讲鈧粎骞嗘晶鍐х閼锋番鈧礁褰叉径宥呭煑闁劎璁查垾婵撶礉Docker 鐏忚鲸妲搁張鈧亸蹇撳讲鐞涘本鏌熷鍫涒偓?
婵″倹鐏夌捄瀹犵箖鏉╂瑤绔村銉窗
1. 濮ｅ繐褰撮張鍝勬珤闁€燁洣閹靛浼愮憗鍛贩鐠ф牭绱濈€硅妲楅崙铏瑰箛閳ユ粍鍨滄潻娆掑厴鐠烘垳缍橀柇锝勭瑝閼冲€熺獓閳ユ縿鈧?2. 娴溿倓绮崪灞肩瑐缁炬寧鍨氶張顒勭彯閿涘本甯撻柨娆忔炊闂呬勘鈧?3. 閸氬海鐢婚幍鈺侇啇閸滃矁绺肩粔璁崇窗瀵板牏妫濋懟锔衡偓?
## 閺堫剚顒為張鈧亸蹇曟窗閺?1. `Dockerfile`閿涙艾鐣炬稊澶婄安閻劑鏆呴崓蹇斺偓搴濈疄閺嬪嫬缂撻妴?2. `docker-compose.yml`閿涙矮绔撮弶鈥虫嚒娴犮倕鎯庨崝銊︽箛閸斅扳偓?3. `.dockerignore`閿涙艾鍣虹亸鎴炵€杞扮瑐娑撳鏋冮敍灞惧絹閸楀洦鐎娲偓鐔峰閵?
## 濡€虫健閼卞矁鐭?1. `Dockerfile`
   - 閸╄櫣顢呴梹婊冨剼閿涙瓪python:3.11-slim`
   - 鐎瑰顥婃笟婵婄閿涙瓪pip install -r requirements.txt`
   - 閹风柉绀夋惔鏃傛暏娴狅絿鐖?   - 閸氼垰濮╅崨鎴掓姢閿涙瓪uvicorn app.main:app --host 0.0.0.0 --port 8000`

2. `docker-compose.yml`
   - 閺嗘挳婀剁粩顖氬經 `8000:8000`
   - 闁俺绻?`DATABASE_URL=sqlite:////data/CaiBao.db` 閹稿洤鎮滅€圭懓娅掗幐浣风畽閸栨牞鐭惧?   - 閹稿倽娴囬崡?`caibao_data:/data` 娣囨繆鐦夐柌宥呮儙閸氬孩鏆熼幑顔荤瑝娑撱垹銇?
3. `.dockerignore`
   - 閹烘帡娅?`tests/`閵嗕梗docs/`閵嗕胶绱︾€涙ê鎷伴張顒€婀撮搹姘珯閻滎垰顣?   - 閸戝繐鐨梹婊冨剼閺嬪嫬缂撴担鎾缎濋崪宀冣偓妤佹

## 鏉╂劘顢戦崨鎴掓姢
```powershell
# 閺嬪嫬缂撻獮璺烘倵閸欐澘鎯庨崝?docker compose up --build -d

# 閺屻儳婀呴張宥呭閺冦儱绻?docker compose logs -f caibao-api

# 閸嬨儱鎮嶅Λ鈧弻?Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/api/v1/health"

# 閸嬫粍顒涢張宥呭
docker compose down
```

## 妤犲本鏁归弽鍥у櫙
1. `docker compose up --build -d` 閹存劕濮涢妴?2. `GET /api/v1/health` 鏉╂柨娲?200閵?3. 闁插秴鎯庣€圭懓娅掗崥搴礉閸樺棗褰堕弫鐗堝祦娴犲秴婀敍鍫濆祹閻㈢喐鏅ラ敍澶堚偓?

> Tip: if local `uvicorn` is already running on port `8000`, stop it first before `docker compose up`.
