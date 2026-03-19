import os
from fastapi import FastAPI
from app.config import settings

app = FastAPI(
    title=settings.APP_TITLE,
    debug=settings.DEBUG,
)


@app.get("/")
def root():
    return {
        "message": "Hello from Cloud Run!",
        "environment": settings.ENV,
    }


@app.get("/health")
def health():
    return {"status": "healthy", "environment": settings.ENV}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
