from fastapi import FastAPI
from pydantic import BaseModel
import yt_dlp
import subprocess
import os

app = FastAPI()

# Temporary storage directory
TMP_DIR = "/tmp/youtube_clips"
os.makedirs(TMP_DIR, exist_ok=True)

# Path to your cookies file (upload this to Render, next to main.py)
COOKIES_FILE = os.path.join(os.path.dirname(__file__), "cookies.txt")

# Request models
class VideoRequest(BaseModel):
    videoUrl: str
    lang: str = "en"

class ClipRequest(BaseModel):
    videoUrl: str
    start: str
    end: str
    outputName: str

# Root endpoint for testing
@app.get("/")
def root():
    return {"message": "YouTube Live API with cookies is running!"}

# Download subtitles only
@app.post("/download-subtitle")
def download_subtitle(req: VideoRequest):
    """Download subtitles only from YouTube video using cookies."""
    output_file = os.path.join(TMP_DIR, "video.%(ext)s")
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": [req.lang],
        "outtmpl": output_file,
        "cookiefile": COOKIES_FILE,  # <-- use your cookies
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([req.videoUrl])
    except yt_dlp.utils.DownloadError as e:
        return {"error": str(e)}

    subtitle_file = os.path.join(TMP_DIR, f"video.{req.lang}.vtt")
    if not os.path.exists(subtitle_file):
        return {"error": "Subtitle not found."}

    return {"subtitleUrl": subtitle_file, "videoUrl": req.videoUrl}

# Download a specific highlight clip
@app.post("/download-clip")
def download_clip(req: ClipRequest):
    """Download only the required segment of a YouTube video."""
    clip_path = os.path.join(TMP_DIR, req.outputName)
    section = f"*{req.start}-{req.end}"
    cmd = [
        "yt-dlp",
        req.videoUrl,
        "--download-sections", section,
        "-o", clip_path,
        "--cookies", COOKIES_FILE  # <-- use cookies for restricted videos
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        return {"error": str(e)}

    return {"clipPath": clip_path}

# Add subtitles to a clip
@app.post("/add-subtitles")
def add_subtitles(clipPath: str, subtitlePath: str):
    """Embed subtitles into the clip."""
    final_clip = clipPath.replace(".mp4", "_sub.mp4")
    cmd = [
        "ffmpeg",
        "-i", clipPath,
        "-vf", f"subtitles={subtitlePath}",
        final_clip
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        return {"error": str(e)}
    return {"finalClipPath": final_clip}

# Start server (Render uses PORT environment variable)
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
