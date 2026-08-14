from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import require_api_key
from app.rate_limit import rate_limit
from app.routers import movies, search, theaters

app = FastAPI(
    title="Filmy API",
    version="0.1.0",
    description="Filmarks スクレイピングAPI（映画・劇場・スケジュール検索）",
)

# 開発用CORS設定: 全オリジン許可（本番では必要に応じて制限すること）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーター登録（認証 + レート制限を全APIエンドポイントに適用。
# /health は依存を付けず、Koyeb のヘルスチェックがキーなしで通るようにする）
_api_dependencies = [Depends(require_api_key), Depends(rate_limit)]
app.include_router(movies.router, dependencies=_api_dependencies)
app.include_router(theaters.router, dependencies=_api_dependencies)
app.include_router(search.router, dependencies=_api_dependencies)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
