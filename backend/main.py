from fastapi import FastAPI, UploadFile, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import shutil
import uuid
import os
import traceback

from backend.render import render_video

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "backend/uploads"
OUTPUT_DIR = "backend/outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================================================
# STATIC FILES
# =========================================================

app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")

app.mount("/static", StaticFiles(directory="frontend"), name="static")

jobs = {}

# =========================================================
# FRONTEND WEBSITE
# =========================================================

@app.get("/")
def homepage():
    return FileResponse("frontend/index.html")


@app.get("/app.js")
def app_js():
    return FileResponse("frontend/app.js")


# =========================================================
# RENDER JOB
# =========================================================

def run_render_job(
    job_id,
    audio_path,
    bg_path,
    output_path,
    video_format,
    lyric_language
):
    try:

        jobs[job_id]["status"] = "transcribing"

        render_video(
            audio_path,
            bg_path,
            output_path,
            video_format,
            lyric_language
        )

        jobs[job_id]["status"] = "done"

        jobs[job_id]["video_url"] = (
            f"/outputs/{job_id}.mp4"
        )

    except Exception as e:

        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)

        print(traceback.format_exc())


# =========================================================
# GENERATE ENDPOINT
# =========================================================

@app.post("/generate")
async def generate(
    background_tasks: BackgroundTasks,
    audio: UploadFile,
    background: UploadFile,
    video_format: str = Form("youtube"),
    lyric_language: str = Form("auto")
):

    job_id = str(uuid.uuid4())

    audio_path = f"{UPLOAD_DIR}/{job_id}.mp3"
    bg_path = f"{UPLOAD_DIR}/{job_id}.jpg"

    output_path = f"{OUTPUT_DIR}/{job_id}.mp4"

    with open(audio_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    with open(bg_path, "wb") as f:
        shutil.copyfileobj(background.file, f)

    jobs[job_id] = {
        "status": "queued",
        "video_url": None,
        "error": None
    }

    background_tasks.add_task(
        run_render_job,
        job_id,
        audio_path,
        bg_path,
        output_path,
        video_format,
        lyric_language
    )

    return {
        "job_id": job_id
    }


# =========================================================
# STATUS ENDPOINT
# =========================================================

@app.get("/status/{job_id}")
def status(job_id: str):

    if job_id not in jobs:

        return {
            "status": "not_found"
        }

    return jobs[job_id]