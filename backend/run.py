import uvicorn
from app.config import settings

if __name__ == "__main__":
    # Bootstraps Uvicorn with config parameters
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENV == "development"
    )
