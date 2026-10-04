import json
import logging
import os
import subprocess
import sys
from typing import Sequence


def setup_logger(log_dir: str, name: str = "yt_pipeline") -> logging.Logger:
    """Tao logger vua in ra console, vua ghi ra file log trong log_dir."""
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "pipeline.log")

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    logger.info("Log duoc ghi tai: %s", log_path)
    return logger


def run_cmd(cmd: Sequence[str], logger: logging.Logger) -> str:
    """Chay 1 lenh shell, log lai va nem loi neu that bai."""
    logger.info("CMD: %s", " ".join(str(c) for c in cmd))
    result = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    if result.returncode != 0:
        logger.error("Lenh that bai (exit=%s):\n%s", result.returncode, result.stdout)
        raise RuntimeError(f"Lenh that bai: {' '.join(str(c) for c in cmd)}")
    return result.stdout


def ffprobe_json(path: str) -> dict:
    out = subprocess.run(
        [
            "ffprobe", "-v", "error", "-print_format", "json",
            "-show_format", "-show_streams", path,
        ],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True,
    )
    return json.loads(out.stdout)


def get_duration(path: str) -> float:
    info = ffprobe_json(path)
    return float(info["format"]["duration"])


def get_video_stream_params(path: str) -> dict:
    """Lay cac thong so quan trong cua stream video/audio dau tien, dung de
    encode lai info_video cho khop voi video nen."""
    info = ffprobe_json(path)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    fps = v.get("avg_frame_rate") or v.get("r_frame_rate") or "30/1"
    return {
        "width": int(v["width"]),
        "height": int(v["height"]),
        "codec_name": v.get("codec_name", "h264"),
        "pix_fmt": v.get("pix_fmt", "yuv420p"),
        "fps": fps,
        "audio_sample_rate": int(a["sample_rate"]) if a and a.get("sample_rate") else 44100,
        "audio_channels": int(a["channels"]) if a and a.get("channels") else 2,
    }


def format_hms(seconds: float) -> str:
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def safe_remove(path: str, logger: logging.Logger) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
            logger.info("Da xoa file tam: %s", path)
    except OSError as exc:
        logger.warning("Khong xoa duoc %s: %s", path, exc)
