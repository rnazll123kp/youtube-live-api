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

# Path to your cookies file
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

# Root endpoint
@app.get("/")
def root():
    return {"message": "YouTube Live API with cookies is running!"}

# Serve subtitles publicly
@app.get("/subtitles/{filename}")
def get_subtitle(filename: str):
    file_path = os.path.join(TMP_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/vtt")
    return {"error": "Subtitle not found"}

# Serve clips publicly
@app.get("/clips/{filename}")
def get_clip(filename: str):
    file_path = os.path.join(TMP_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="video/mp4")
    return {"error": "Clip not found"}

# Download subtitles only (for Gemini)
@app.post("/download-subtitle")
def download_subtitle(req: VideoRequest):
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

@app.post("/download-clip")
def download_clip(req: ClipRequest):
    clip_path = os.path.join(TMP_DIR, req.outputName)

    # yt-dlp requires the "*start-end" format inside quotes
    section = f"*{req.start}-{req.end}"

    cmd = [
    "yt-dlp",
    req.videoUrl,
    "--download-sections", section,
    "-o", clip_path,
    "--cookies", COOKIES_FILE,
    "--remux-video", "mp4",   # <--- force mp4
    "--force-overwrites",     # <--- overwrite if exists
    ]


    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        return {"error": str(e)}

    # Public clip URL for n8n / YouTube upload
    public_url = f"https://youtube-live-api-57jx.onrender.com/clips/{req.outputName}"
    return {"clipUrl": public_url, "outputName": req.outputName}


# Cleanup endpoint (delete all files automatically)
@app.get("/cleanup")
@app.post("/cleanup")
def cleanup_all():
    deleted = []
    for f in os.listdir(TMP_DIR):
        path = os.path.join(TMP_DIR, f)
        if os.path.isfile(path):
            os.remove(path)
            deleted.append(f)
    return {"deleted": deleted, "status": "all cleaned"}


# Start server
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)


