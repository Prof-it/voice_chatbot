import uvicorn
from api import create_app

app, _ = create_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001, log_level="info")
