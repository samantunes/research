from dotenv import load_dotenv
import logging
from pathlib import Path

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # File handler for general application logs
        logging.FileHandler('logs/app.log'),
        # Stream handler for console output
        logging.StreamHandler()
    ]
)

# Suppress verbose fontTools logging
logging.getLogger('fontTools').setLevel(logging.WARNING)
logging.getLogger('fontTools.subset').setLevel(logging.WARNING)
logging.getLogger('fontTools.ttLib').setLevel(logging.WARNING)

# Create logger instance
logger = logging.getLogger(__name__)

load_dotenv()

from backend.server.app import app as _fastapi_app


class StripBackendPrefixMiddleware:
    """Allows requests both with and without the /backend prefix (HTTP & WebSocket)."""

    def __init__(self, inner_app):
        self.inner_app = inner_app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            path = scope.get("path", "")
            if path == "/backend" or path.startswith("/backend/"):
                scope = dict(scope)
                scope["path"] = path[len("/backend"):] or "/"
                if "raw_path" in scope and scope["raw_path"].startswith(b"/backend"):
                    scope["raw_path"] = scope["raw_path"][len(b"/backend"):] or b"/"
        await self.inner_app(scope, receive, send)


app = StripBackendPrefixMiddleware(_fastapi_app)

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
