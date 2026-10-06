#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run.py
======
Tu dong lay metadata tu Google Apps Script va chay pipeline YouTube.
Cac tham so chinh:
  --start-index: Thu tu tap (index) bat dau
  --name: Ten du an / series
  --project-id: ID du an TTS tren Google Drive
  --output-dir: Thu muc luu video output (mac dinh: /tmp/output)
  --delete-final-video / --no-delete-final-video: Xoa video sau khi upload thanh cong (mac dinh: True)
  --keep-audio: Giu lai master audio sau khi xu ly (mac dinh: False)
"""

import argparse
import sys
from typing import List, Optional
import requests

DEFAULT_WEB_APP_URL = (
    "https://script.google.com/macros/s/"
    "AKfycbx6Lmkc-ul-ZosgAOBdCyQ5XIGOZBcfFqB-D-XowMAyDQIsdTuFIFIFjWKWtS4gMG_quw/exec"
)


def fetch_rendered_info(web_app_url: str, start_index: int) -> dict:
    """Goi API Google Apps Script de lay thong tin video render theo index."""
    resp = requests.get(
        web_app_url,
        params={"action": "get_rendered", "index": start_index},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") != "success" or "data" not in data:
        raise RuntimeError(
            f"Lay metadata that bai tu Apps Script cho index={start_index}: {data}"
        )
    return data["data"]


def run_pipeline(
    start_index: int,
    name: str,
    project_id: str | int,
    output_dir: str = "/tmp/output",
    delete_final_video: bool = True,
    keep_audio: bool = False,
    audios_dir: Optional[str] = None,
    client_secrets_file: str = "client_secrets.json",
    token_file: str = "token.json",
    noauth_local_webserver: bool = True,
    web_app_url: str = DEFAULT_WEB_APP_URL,
    intro_enable: bool = True,
    outro_enable: bool = True,
    intro_video: Optional[str] = None,
    outro_video: Optional[str] = None,
    comic_json: Optional[str] = None,
    comic_info_enable: bool = True,
    comic_render_mode: str = "frame",
) -> List[str]:
    """Lay metadata tu Web App va thuc thi Pipeline."""
    print(f"Dang lay thong tin render tu Web App voi index={start_index}...")
    video_info = fetch_rendered_info(web_app_url, start_index)

    if not audios_dir:
        audios_dir = f"/kaggle/working/VoiceVNZeroTTS/projects/{project_id}/chapters"

    video_file = video_info.get("game_path", "")
    title_pattern = video_info.get("title", f"Tap {start_index} | {name}")
    description = video_info.get("description", "")
    playlist_url = video_info.get("playlist_url") or None
    tags = video_info.get("tags", "")
    category_id = str(video_info.get("category_id", "22"))
    privacy_status = video_info.get("privacy_status", "unlisted")

    bg_music_path = video_info.get("background_music") or None
    bg_music_volume = str(video_info.get("bg_music_volume", "0.2"))

    # Lay them cac thong tin intro/outro/comic neu chua truyen tu command line
    if intro_video is None:
        intro_video = video_info.get("intro_video") or video_info.get("info_video") or None
    if outro_video is None:
        outro_video = video_info.get("outro_video") or None
    if comic_json is None:
        comic_json = video_info.get("comic_json") or video_info.get("info_json") or None

    if "intro_enable" in video_info and isinstance(video_info["intro_enable"], bool):
        intro_enable = video_info["intro_enable"]
    if "outro_enable" in video_info and isinstance(video_info["outro_enable"], bool):
        outro_enable = video_info["outro_enable"]

    try:
        sample_title = title_pattern.format(index=start_index)
    except Exception:
        sample_title = title_pattern

    print(f"Da lay cau hinh thanh cong. Tieu de mau: '{sample_title}'")

    from core import Pipeline, PipelineConfig

    config = PipelineConfig(
        name=name,
        title_pattern=title_pattern,
        description=description,
        playlist_url=playlist_url,
        tags=tags,
        category_id=category_id,
        privacy_status=privacy_status,
        start_index=start_index,
        audios_dir=audios_dir,
        video_file=video_file,
        intro_video=intro_video,
        intro_enable=intro_enable,
        outro_video=outro_video,
        outro_enable=outro_enable,
        comic_json=comic_json,
        comic_info_enable=comic_info_enable,
        comic_render_mode=comic_render_mode,
        background_music=bg_music_path,
        bg_music_volume=bg_music_volume,
        output_dir=output_dir,
        client_secrets_file=client_secrets_file,
        token_file=token_file,
        noauth_local_webserver=noauth_local_webserver,
        delete_final_video_after_upload=delete_final_video,
        keep_master_audio=keep_audio,
    )

    pipeline = Pipeline(config)
    video_ids = pipeline.run()

    print("\nCac video da upload:")
    for vid in video_ids:
        print(f"  https://youtu.be/{vid}")

    return video_ids


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Chay YouTube Video Automation Pipeline lay metadata tu Web App"
    )
    parser.add_argument(
        "--start-index",
        type=int,
        required=True,
        help="Thu tu tap (index) bat dau",
    )
    parser.add_argument(
        "--name",
        type=str,
        required=True,
        help="Ten du an / bo truyen",
    )
    parser.add_argument(
        "--project-id",
        type=str,
        required=True,
        help="ID du an TTS tren Google Drive (vd: 9)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/tmp/output",
        help="Thu muc luu video ket qua (mac dinh: /tmp/output)",
    )
    parser.add_argument(
        "--delete-final-video",
        action="store_true",
        default=True,
        help="Xoa file video cuoi cung sau khi upload thanh cong (mac dinh: True)",
    )
    parser.add_argument(
        "--no-delete-final-video",
        action="store_false",
        dest="delete_final_video",
        help="Giu lai file video cuoi cung sau khi upload",
    )
    parser.add_argument(
        "--keep-audio",
        action="store_true",
        default=False,
        help="Giu lai file master audio sau khi hoan tat (mac dinh: False)",
    )

    # Tham so intro / outro / video gioi thieu truyen
    parser.add_argument(
        "--intro-enable",
        action="store_true",
        default=True,
        help="Bat video intro (mac dinh: True)",
    )
    parser.add_argument(
        "--no-intro-enable",
        action="store_false",
        dest="intro_enable",
        help="Tat video intro",
    )
    parser.add_argument(
        "--outro-enable",
        action="store_true",
        default=True,
        help="Bat video outro (mac dinh: True)",
    )
    parser.add_argument(
        "--no-outro-enable",
        action="store_false",
        dest="outro_enable",
        help="Tat video outro",
    )
    parser.add_argument(
        "--intro-video",
        type=str,
        default=None,
        help="Duong dan file video intro",
    )
    parser.add_argument(
        "--outro-video",
        type=str,
        default=None,
        help="Duong dan file video outro",
    )
    parser.add_argument(
        "--comic-json",
        type=str,
        default=None,
        help="Duong dan file JSON truyen de render video gioi thieu (dung render.py)",
    )
    parser.add_argument(
        "--comic-info-enable",
        action="store_true",
        default=True,
        help="Bat video gioi thieu truyen tu render.py (mac dinh: True)",
    )
    parser.add_argument(
        "--no-comic-info",
        action="store_false",
        dest="comic_info_enable",
        help="Tat video gioi thieu truyen tu render.py",
    )
    parser.add_argument(
        "--comic-render-mode",
        choices=["frame", "realtime"],
        default="frame",
        help="Che do render video gioi thieu truyen: frame hoac realtime (mac dinh: frame)",
    )

    # Cac tham so tuy chon bo sung
    parser.add_argument(
        "--audios-dir",
        type=str,
        default=None,
        help="Ghi de thu muc audio (mac dinh dung project_id)",
    )
    parser.add_argument(
        "--client-secrets-file",
        type=str,
        default="client_secrets.json",
        help="File OAuth client_secrets.json (mac dinh: client_secrets.json)",
    )
    parser.add_argument(
        "--token-file",
        type=str,
        default="token.json",
        help="File OAuth token.json (mac dinh: token.json)",
    )
    parser.add_argument(
        "--web-app-url",
        type=str,
        default=DEFAULT_WEB_APP_URL,
        help="URL Google Apps Script API",
    )
    parser.add_argument(
        "--local-webserver",
        action="store_false",
        dest="noauth_local_webserver",
        default=True,
        help="Mo trinh duyet local thay vi dung OOB headless (cho may co man hinh)",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        run_pipeline(
            start_index=args.start_index,
            name=args.name,
            project_id=args.project_id,
            output_dir=args.output_dir,
            delete_final_video=args.delete_final_video,
            keep_audio=args.keep_audio,
            audios_dir=args.audios_dir,
            client_secrets_file=args.client_secrets_file,
            token_file=args.token_file,
            noauth_local_webserver=args.noauth_local_webserver,
            web_app_url=args.web_app_url,
            intro_enable=args.intro_enable,
            outro_enable=args.outro_enable,
            intro_video=args.intro_video,
            outro_video=args.outro_video,
            comic_json=args.comic_json,
            comic_info_enable=args.comic_info_enable,
            comic_render_mode=args.comic_render_mode,
        )
    except Exception as exc:
        print(f"\n[LOI] {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
