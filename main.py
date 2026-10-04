#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main entrypoint for YouTube Video Processing & Upload Pipeline.
Run with CLI flags or interactive mode.
"""

import argparse
import os
import sys

try:
    from oauth2client.tools import argparser as oauth2client_argparser
except ImportError:
    oauth2client_argparser = argparse.ArgumentParser(add_help=False)

from core import Pipeline, PipelineConfig, VALID_PRIVACY_STATUSES


def prompt_config() -> PipelineConfig:
    def ask(label: str, default: str = "") -> str:
        suffix = f" [{default}]" if default else ""
        val = input(f"{label}{suffix}: ").strip()
        return val or default

    print("\n=== NHAP THONG TIN PIPELINE ===\n")
    name = ask("Ten du an (name)")
    title_pattern = ask("Mau tieu de (title_pattern, dung {index})", "Tap {index} | " + name)
    description = ask("Mo ta video (description, co the dung {index})")
    playlist_url = ask("Link/ID playlist (bo trong neu khong co)") or None
    tags = ask("Tags (cach nhau boi dau phay)")
    category_id = ask("Category ID", "22")
    privacy_status = ask("Privacy status (public/private/unlisted)", "unlisted")
    start_index = int(ask("Start index", "1"))

    audios_dir = ask("Thu muc chua file audio (audios_dir)")
    video_file = ask("File video nen se lap lai (video_file)")
    info_video = ask("File video gioi thieu (info_video, bo trong neu khong co)") or None

    background_music = ask("File nhac nen (background_music, bo trong neu khong co)") or None
    bg_music_volume = ask("Am luong nhac nen (0.0-1.0 hoac vd -18dB)", "0.2") if background_music else "0.2"

    output_dir = ask("Thu muc luu output (output_dir)", "./output")
    client_secrets_file = ask("File client_secrets.json", "client_secrets.json")
    token_file = ask("File token se luu (token_file)", "token.json")
    noauth_local_webserver = ask(
        "Dang nhap kieu headless, khong mo trinh duyet tren may nay? "
        "(y/n - chon y neu chay tren Colab/server)",
        "y",
    ).lower().startswith("y")

    return PipelineConfig(
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
        info_video=info_video,
        background_music=background_music,
        bg_music_volume=bg_music_volume,
        output_dir=output_dir,
        client_secrets_file=client_secrets_file,
        token_file=token_file,
        noauth_local_webserver=noauth_local_webserver,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="YouTube audio->video upload pipeline",
        parents=[oauth2client_argparser],
    )
    p.add_argument("--interactive", action="store_true", help="Nhap thong tin qua cau hoi (input)")

    p.add_argument("--name")
    p.add_argument("--title-pattern")
    p.add_argument("--description", default="")
    p.add_argument("--playlist-url")
    p.add_argument("--tags", default="")
    p.add_argument("--category-id", default="22")
    p.add_argument("--privacy-status", choices=VALID_PRIVACY_STATUSES, default="unlisted")
    p.add_argument("--start-index", type=int, default=1)

    p.add_argument("--audios-dir")
    p.add_argument("--video-file")
    p.add_argument("--info-video")

    p.add_argument("--background-music")
    p.add_argument("--bg-music-volume", default="0.2")

    p.add_argument("--output-dir", default="./output")
    p.add_argument("--client-secrets-file", default="client_secrets.json")
    p.add_argument("--token-file", default="token.json")

    p.add_argument("--delete-final-video-after-upload", action="store_true")
    p.add_argument("--keep-master-audio", action="store_true")
    return p


def config_from_args(args: argparse.Namespace) -> PipelineConfig:
    return PipelineConfig(
        name=args.name,
        title_pattern=args.title_pattern,
        description=args.description,
        playlist_url=args.playlist_url,
        tags=args.tags,
        category_id=args.category_id,
        privacy_status=args.privacy_status,
        start_index=args.start_index,
        audios_dir=args.audios_dir,
        video_file=args.video_file,
        info_video=args.info_video,
        background_music=args.background_music,
        bg_music_volume=args.bg_music_volume,
        output_dir=args.output_dir,
        client_secrets_file=args.client_secrets_file,
        token_file=args.token_file,
        noauth_local_webserver=getattr(args, "noauth_local_webserver", False),
        auth_host_name=getattr(args, "auth_host_name", "localhost"),
        auth_host_port=getattr(args, "auth_host_port", [8080, 8090]),
        delete_final_video_after_upload=args.delete_final_video_after_upload,
        keep_master_audio=args.keep_master_audio,
    )


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.interactive or not args.name:
        config = prompt_config()
    else:
        config = config_from_args(args)

    if not config.audios_dir or not os.path.isdir(config.audios_dir):
        sys.exit(f"audios_dir khong hop le: {config.audios_dir}")
    if not config.video_file or not os.path.exists(config.video_file):
        sys.exit(f"video_file khong hop le: {config.video_file}")

    pipeline = Pipeline(config)
    pipeline.run()


if __name__ == "__main__":
    main()
