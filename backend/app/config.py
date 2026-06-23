import os
from typing import List

class Settings:
    # Service Environment
    ENV: str = os.getenv("ENV", "development")
    
    # Network Bind Settings (Render uses $PORT)
    HOST: str = os.getenv("HOST", "127.0.0.1" if ENV == "development" else "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # CORS Security Configuration
    # Defaults to wildcard * only for local dev convenience, but parses comma-separated ALLOWED_ORIGINS env var
    _raw_origins: str = os.getenv("ALLOWED_ORIGINS", "*")
    
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        if not self._raw_origins:
            return ["*"]
        return [origin.strip() for origin in self._raw_origins.split(",") if origin.strip()]

settings = Settings()
