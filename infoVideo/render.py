#!/usr/bin/env python3
"""
Remotion HTML5 Manga Video Renderer
Render HTML5 16:9 animation template to WebM video using Playwright and FFmpeg.
"""

import os
import sys
import json
import time
import shutil
import argparse
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def find_ffmpeg():
    # Check standard PATH
    path = shutil.which("ffmpeg")
    if path:
        return path
    # Check known local paths on Windows
    common_paths = [
        r"D:\PhanMem\ffmpeg\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"
    ]
    for p in common_paths:
        if os.path.exists(p):
            return p
    return None

def parse_args():
    parser = argparse.ArgumentParser(description="Render HTML5 Remotion Manga Template to WebM")
    parser.add_argument("--config", default="config.json", help="Path to config.json file (default: config.json)")
    parser.add_argument("--output", default="output.webm", help="Output WebM file path (default: output.webm)")
    parser.add_argument("--fps", type=int, default=None, help="Video framerate (default: from config.json or 30)")
    parser.add_argument("--mode", choices=["frame", "realtime"], default="frame", help="Render mode: frame (exact frame-by-frame) or realtime (default: frame)")
    parser.add_argument("--bitrate", default="4M", help="Video bitrate for VP9 encoding (default: 4M)")
    parser.add_argument("--interactive", action="store_true", help="Prompt to edit key parameters before rendering")
    return parser.parse_args()

def interactive_prompt(cfg):
    print("\n--- NHAP THONG SO VIDEO (Nhan Enter de giu nguyen mac dinh) ---")
    s1 = cfg.get("scene1", {})
    cm = s1.get("comic", {})
    ch = s1.get("channel", {})

    new_title = input(f"Ten truyen [{cm.get('title', '')}]: ").strip()
    if new_title:
        cm["title"] = new_title

    new_chap = input(f"Tap truyen [{cm.get('chapter', '')}]: ").strip()
    if new_chap:
        cm["chapter"] = new_chap

    new_syn = input(f"Gioi thieu ngan [{cm.get('synopsis', '')[:40]}...]: ").strip()
    if new_syn:
        cm["synopsis"] = new_syn

    new_ch_name = input(f"Ten kenh [{ch.get('name', '')}]: ").strip()
    if new_ch_name:
        ch["name"] = new_ch_name

    s2 = cfg.get("scene2", {})
    s2_cur = "Y" if s2.get("enabled", True) else "N"
    new_s2 = input(f"Bat Canh 2 - Binh luan? (Y/N) [{s2_cur}]: ").strip().upper()
    if new_s2 in ["Y", "N"]:
        s2["enabled"] = (new_s2 == "Y")

    s4 = cfg.get("scene4", {})
    s4_cur = "Y" if s4.get("enabled", True) else "N"
    new_s4 = input(f"Bat Canh 4 - Chu y / Thong bao? (Y/N) [{s4_cur}]: ").strip().upper()
    if new_s4 in ["Y", "N"]:
        s4["enabled"] = (new_s4 == "Y")

    print("----------------------------------------------------------------\n")
    return cfg

def render_frame_mode(page, total_frames, fps, output_path, bitrate, ffmpeg_bin):
    print(f"Khoi tao FFmpeg encoder (libvpx-vp9, {bitrate}, {fps} FPS, khong audio)...")
    cmd = [
        ffmpeg_bin, "-y",
        "-loglevel", "error",
        "-f", "image2pipe",
        "-vcodec", "mjpeg",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libvpx-vp9",
        "-deadline", "realtime",
        "-cpu-used", "4",
        "-b:v", bitrate,
        "-pix_fmt", "yuv420p",
        "-an",
        output_path
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    start_time = time.time()
    bar_width = 30

    try:
        for f in range(total_frames):
            page.evaluate(f"window.seekToFrame({f})")
            frame_bytes = page.screenshot(type="jpeg", quality=95)
            proc.stdin.write(frame_bytes)

            # Progress line
            progress = (f + 1) / total_frames
            filled = int(bar_width * progress)
            bar = "#" * filled + "-" * (bar_width - filled)
            elapsed = time.time() - start_time
            fps_current = (f + 1) / max(elapsed, 0.001)
            eta = (total_frames - (f + 1)) / max(fps_current, 0.001)

            sys.stdout.write(f"\r[{bar}] {int(progress * 100)}% | Frame {f+1}/{total_frames} | {fps_current:.1f} fps | ETA: {int(eta)}s  ")
            sys.stdout.flush()

        sys.stdout.write("\n")
        _, stderr_data = proc.communicate()
    except Exception as e:
        proc.kill()
        raise e

    if proc.returncode != 0:
        err_msg = stderr_data.decode('utf-8', errors='ignore') if stderr_data else "Unknown error"
        raise RuntimeError(f"FFmpeg error (code {proc.returncode}): {err_msg}")

def render_realtime_mode(p, html_url, config_json, total_duration, output_path):
    print(f"Chay che do realtime recording ({total_duration:.1f} giay)...")
    temp_dir = os.path.abspath("./.temp_render")
    os.makedirs(temp_dir, exist_ok=True)

    browser = p.chromium.launch(headless=True, args=["--allow-file-access-from-files"])
    context = browser.new_context(
        record_video_dir=temp_dir,
        record_video_size={"width": 1920, "height": 1080},
        viewport={"width": 1920, "height": 1080}
    )
    page = context.new_page()
    page.goto(f"{html_url}?render=1")
    page.wait_for_function("() => window.remotionReady === true || window.remotionEngine !== undefined")

    if config_json:
        page.evaluate(f"window.loadConfig({json.dumps(config_json)})")

    page.evaluate("() => document.fonts.ready")
    time.sleep(1.0)

    page.evaluate("window.playFromStart()")
    time.sleep(total_duration + 0.5)

    context.close()
    video_path = page.video.path()
    browser.close()

    try:
        with open(video_path, 'rb') as f_src, open(output_path, 'wb') as f_dst:
            shutil.copyfileobj(f_src, f_dst)
    except Exception as e:
        print(f"Luu file video canh bao: {e}")

    # Clean temp dir
    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass

def render_manga_video(
    config_path: str = "config.json",
    output_path: str = "output.webm",
    fps: int = None,
    mode: str = "frame",
    bitrate: str = "4M",
    interactive: bool = False,
) -> str:
    base_dir = Path(__file__).resolve().parent
    index_html = base_dir / "index.html"

    if not index_html.exists():
        raise FileNotFoundError(f"Khong tim thay {index_html}")

    config_p = Path(config_path)
    if not config_p.is_file():
        alt_p = base_dir / config_path
        if alt_p.is_file():
            config_p = alt_p

    # Load configuration
    cfg = {}
    if config_p.exists():
        with open(config_p, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        print(f"Canh bao: Khong tim thay {config_p}, se su dung mac dinh.")

    if interactive:
        cfg = interactive_prompt(cfg)

    render_fps = fps or cfg.get("general", {}).get("fps", 30)

    # Summary
    cm = cfg.get("scene1", {}).get("comic", {})
    ch = cfg.get("scene1", {}).get("channel", {})
    s2_enabled = cfg.get("scene2", {}).get("enabled", True)
    s4_enabled = cfg.get("scene4", {}).get("enabled", True)

    print("==================================================")
    print("      REMOTION MANGA HTML5 VIDEO RENDERER         ")
    print("==================================================")
    print(f"Kenh        : {ch.get('name', 'N/A')}")
    print(f"Ten Truyen  : {cm.get('title', 'N/A')}")
    print(f"Tap         : {cm.get('chapter', 'N/A')}")
    print(f"Canh 2 (BL) : {'Bat' if s2_enabled else 'Tat'}")
    print(f"Canh 4 (CY) : {'Bat' if s4_enabled else 'Tat'}")
    print(f"Che do      : {mode.upper()}")
    print(f"FPS         : {render_fps}")
    print(f"File xuat   : {output_path}")
    print("==================================================")

    ffmpeg_bin = find_ffmpeg()
    if mode == "frame" and not ffmpeg_bin:
        raise RuntimeError(
            "Khong tim thay FFmpeg tren may de render che do frame. "
            "Vui long cai dat FFmpeg hoac chon mode='realtime'."
        )

    html_url = f"file:///{str(index_html).replace(os.sep, '/')}"

    with sync_playwright() as p:
        if mode == "realtime":
            d1 = cfg.get("scene1", {}).get("duration", 5.0)
            d2 = cfg.get("scene2", {}).get("duration", 4.5) if s2_enabled else 0
            d3 = cfg.get("scene3", {}).get("duration", 5.0)
            d4 = cfg.get("scene4", {}).get("duration", 4.0) if s4_enabled else 0
            total_dur = d1 + d2 + d3 + d4
            render_realtime_mode(p, html_url, cfg, total_dur, output_path)
        else:
            browser = p.chromium.launch(headless=True, args=["--allow-file-access-from-files"])
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.goto(f"{html_url}?render=1")
            page.wait_for_function("() => window.remotionReady === true || window.remotionEngine !== undefined")

            if cfg:
                page.evaluate(f"window.loadConfig({json.dumps(cfg)})")

            page.evaluate("() => document.fonts.ready")
            time.sleep(1.0)

            video_cfg = page.evaluate("window.getVideoConfig()")
            total_frames = video_cfg["totalFrames"]
            used_fps = video_cfg.get("fps", render_fps)
            duration_sec = video_cfg["durationInSeconds"]

            print(f"Tong frame: {total_frames} ({duration_sec:.2f} giay)")
            render_frame_mode(page, total_frames, used_fps, output_path, bitrate, ffmpeg_bin)
            browser.close()

    output_abs = os.path.abspath(output_path)
    if os.path.exists(output_abs):
        file_size_mb = os.path.getsize(output_abs) / (1024 * 1024)
        print(f"\nXuat video thanh cong!")
        print(f"Duong dan: {output_abs}")
        print(f"Kich thuoc: {file_size_mb:.2f} MB")
        return output_abs
    else:
        raise RuntimeError("Khong tim thay file output sau khi render.")


def main():
    args = parse_args()
    try:
        render_manga_video(
            config_path=args.config,
            output_path=args.output,
            fps=args.fps,
            mode=args.mode,
            bitrate=args.bitrate,
            interactive=args.interactive,
        )
    except Exception as exc:
        print(f"\n[LOI RENDER] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
