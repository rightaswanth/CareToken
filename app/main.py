from fastapi import FastAPI
from app.core.config import settings
from app.middleware.log_middleware import LogMiddleware

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(LogMiddleware)

@app.get("/")
async def root():
    return {"message": "Welcome to CareToken API"}

from app.api.api import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)
