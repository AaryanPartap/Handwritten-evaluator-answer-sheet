import sys
from pathlib import Path

# Add project root to sys.path
root_path = Path(__file__).resolve().parent
sys.path.insert(0, str(root_path))

from frontend.app import app
from frontend.config import frontend_config

if __name__ == "__main__":
    print(f"Starting Flask Frontend on http://127.0.0.1:{frontend_config.FRONTEND_PORT}")
    print(f"Connecting to FastAPI Backend at {frontend_config.BACKEND_URL}")
    app.run(
        host="127.0.0.1",
        port=frontend_config.FRONTEND_PORT,
        debug=True
    )
