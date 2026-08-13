from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# ルーター登録
app.include_router(movies.router)
app.include_router(theaters.router)
app.include_router(search.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
