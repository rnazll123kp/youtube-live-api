from fastapi import FastAPI
from fastapi.responses import FileResponse
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

# Serve subtitles publicly
@app.get("/subtitles/{filename}")
def get_subtitle(filename: str):
    file_path = os.path.join(TMP_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/vtt")
    return {"error": "File not found"}

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
        "cookiefile": COOKIES_FILE,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([req.videoUrl])
    except yt_dlp.utils.DownloadError as e:
        return {"error": str(e)}

    subtitle_file_name = f"video.{req.lang}.vtt"
    subtitle_path = os.path.join(TMP_DIR, subtitle_file_name)
    if not os.path.exists(subtitle_path):
        return {"error": "Subtitle not found."}

    public_url = f"https://youtube-live-api-57jx.onrender.com/subtitles/{subtitle_file_name}"
    return {"subtitleUrl": public_url, "videoUrl": req.videoUrl}

# Download a specific highlight clip (sequential, blocking)
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
        "--cookies", COOKIES_FILE,
    ]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        return {"error": str(e)}

    # Return JSON with final clip path (sequential ready for n8n upload step)
    return {"clipPath": clip_path, "outputName": req.outputName}

# Add subtitles to a clip (optional)
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

