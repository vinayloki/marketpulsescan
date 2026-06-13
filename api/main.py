from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import scanner, watchlists, alerts

app = FastAPI(title="MarketPulse India API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scanner.router, prefix="/api/scanner", tags=["scanner"])
app.include_router(watchlists.router, prefix="/api/watchlists", tags=["watchlists"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])

@app.get("/")
def read_root():
    return {"message": "Welcome to MarketPulse API"}
