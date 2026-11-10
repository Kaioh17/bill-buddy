from fastapi import FastAPI

from app.routers import health

app = FastAPI(title="Bill Buddy API")
app.include_router(health.router)
