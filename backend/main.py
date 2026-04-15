from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import subprocess
import os
import sys

app = FastAPI(title="MeetScribe Backend")

# Allow CORS since our frontend is hosted separately on Netlify
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow Netlify domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class JoinRequest(BaseModel):
    url: str

@app.post("/api/bot/start")
def start_bot(req: JoinRequest):
    try:
        # Spawn the playwright script in the background so it doesn't block FastAPI
        # We pass the URL as sys.argv[1]
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        
        # Popen spawns it completely asynchronously from the project root
        subprocess.Popen([sys.executable, "check_meet.py", req.url], cwd=project_root)
        
        return {"status": "success", "message": f"Bot deployed to {req.url}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/transcripts")
def get_transcript():
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "transcripts", "meeting_transcript.txt"))
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"status": "success", "content": content}
    return {"status": "not_found", "content": ""}

@app.get("/api/summaries")
def get_summary():
    file_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "transcripts", "meeting_summary.txt"))
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"status": "success", "content": content}
    return {"status": "not_found", "content": ""}

# Optional: Serve a vanilla frontend locally for testing
# app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
