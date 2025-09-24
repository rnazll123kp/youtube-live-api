from fastapi import FastAPI
from pydantic import BaseModel
import yt_dlp
import subprocess
import os

app = FastAPI()

# Directory to store temporary files
TMP_DIR = "/tmp/youtube_clips"
os.makedirs(TMP_DIR, exist_ok=True)

class VideoRequest(BaseModel):
    videoUrl: str
    lang: str = "en"

class ClipRequest(BaseModel):
    videoUrl: str
    start: str
    end: str
    outputName: str

@app.post("/download-subtitle")
def download_subtitle(req: VideoRequest):
    """Download subtitles only from YouTube video."""
    output_file = os.path.join(TMP_DIR, "video.%(ext)s")
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": [req.lang],
        "outtmpl": output_file
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([req.videoUrl])

    subtitle_file = os.path.join(TMP_DIR, f"video.{req.lang}.vtt")
    if not os.path.exists(subtitle_file):
        return {"error": "Subtitle not found."}

    return {
        "subtitleUrl": subtitle_file,
        "videoUrl": req.videoUrl
    }

@app.post("/download-clip")
def download_clip(req: ClipRequest):
    """Download a specific highlight clip from YouTube video."""
    clip_path = os.path.join(TMP_DIR, req.outputName)
    section = f"*{req.start}-{req.end}"

    cmd = [
        "yt-dlp",
        req.videoUrl,
        "--download-sections", section,
        "-o", clip_path
    ]
    subprocess.run(cmd, check=True)
    return {"clipPath": clip_path}

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
    subprocess.run(cmd, check=True)
    return {"finalClipPath": final_clip}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
