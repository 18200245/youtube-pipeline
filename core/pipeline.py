import logging
import os
import shutil
import time
from typing import List

from .audio import AudioProcessor, compute_groups
from .auth import get_authenticated_service
from .config import PipelineConfig, SafeDict
from .constants import MAX_GROUP_SECONDS
from .uploader import YouTubeUploader
from .utils import format_hms, get_duration, safe_remove, setup_logger
from .video import VideoProcessor


class Pipeline:
    def __init__(self, config: PipelineConfig):
        self.cfg = config
        self.work_dir = config.resolved_work_dir()
        os.makedirs(self.cfg.output_dir, exist_ok=True)
        os.makedirs(self.work_dir, exist_ok=True)
        self.logger = setup_logger(self.cfg.output_dir)

    def run(self) -> List[str]:
        cfg = self.cfg
        logger = self.logger
        t0 = time.time()

        logger.info("=" * 70)
        logger.info("BAT DAU PIPELINE: %s", cfg.name)
        logger.info("=" * 70)

        # --- Buoc 0: dang nhap YouTube ---
        youtube = get_authenticated_service(
            cfg.client_secrets_file,
            cfg.token_file,
            logger,
            noauth_local_webserver=cfg.noauth_local_webserver,
            auth_host_name=cfg.auth_host_name,
            auth_host_port=cfg.auth_host_port,
        )
        uploader = YouTubeUploader(youtube, logger)
        playlist_id = cfg.playlist_id()

        # --- Buoc 1: xu ly audio tong ---
        audio_proc = AudioProcessor(self.work_dir, logger)
        master_audio = audio_proc.build_master_audio(
            cfg.audios_dir, cfg.background_music, cfg.bg_music_volume
        )
        total_duration = get_duration(master_audio)
        logger.info("Tong do dai audio: %s (%.1f giay)", format_hms(total_duration), total_duration)

        # --- Buoc 2: chia group ---
        groups = compute_groups(total_duration, MAX_GROUP_SECONDS)
        logger.info("Chia thanh %d group, moi group ~%s", len(groups), format_hms(groups[0].duration))
        for g in groups:
            logger.info(
                "  Group %d: bat dau=%s, do dai=%s",
                g.index_in_run, format_hms(g.start), format_hms(g.duration),
            )

        video_proc = VideoProcessor(self.work_dir, logger)

        # --- Buoc 2.5: Render video gioi thieu truyen bang render.py (neu duoc bat) ---
        comic_video_path = None
        comic_json = cfg.resolved_comic_json()
        if cfg.comic_info_enable and comic_json and os.path.exists(comic_json):
            logger.info("Dang tao video gioi thieu truyen tu file json: %s ...", comic_json)
            comic_video_path = video_proc.render_comic_video(
                config_json=comic_json,
                mode=cfg.comic_render_mode,
            )

        uploaded_video_ids: List[str] = []
        final_paths: List[str] = []

        for g in groups:
            current_index = cfg.start_index + g.index_in_run
            logger.info("-" * 70)
            logger.info("XU LY GROUP %d / %d (index video = %d)", g.index_in_run + 1, len(groups), current_index)
            logger.info("-" * 70)

            # --- Buoc 3: cat audio group + ghep video ---
            segment_audio = audio_proc.extract_segment(master_audio, g.start, g.duration, g.index_in_run)
            group_video = video_proc.build_group_video(
                video_file=cfg.video_file,
                audio_segment=segment_audio,
                idx=g.index_in_run,
                duration=g.duration,
                intro_video=cfg.resolved_intro_video(),
                comic_video=comic_video_path,
                outro_video=cfg.resolved_outro_video(),
                bg_music=cfg.background_music,
                bg_volume=cfg.bg_music_volume,
            )

            final_dest = os.path.join(cfg.output_dir, f"{cfg.name}_tap_{current_index}.mp4")
            shutil.move(group_video, final_dest)
            final_paths.append(final_dest)
            logger.info("Video hoan chinh cho group %d: %s", g.index_in_run, final_dest)

            safe_remove(segment_audio, logger)

            # --- Buoc 4: upload ---
            placeholders = {
                "index": current_index,
                "name": cfg.name,
                "group": g.index_in_run + 1,
                "total_groups": len(groups),
            }
            title = cfg.title_pattern.format_map(SafeDict(placeholders))
            description = cfg.description.format_map(SafeDict(placeholders)) if cfg.description else ""

            video_id = uploader.upload_video(
                final_dest,
                title=title,
                description=description,
                tags=cfg.tag_list(),
                category_id=cfg.category_id,
                privacy_status=cfg.privacy_status,
            )
            uploaded_video_ids.append(video_id)

            if playlist_id:
                uploader.add_to_playlist(video_id, playlist_id)

            # --- Buoc 5: xoa file tam cua group nay ---
            if cfg.delete_final_video_after_upload:
                safe_remove(final_dest, logger)
                final_paths[-1] = f"(da xoa sau upload) {final_dest}"

        # --- don dep chung ---
        if not cfg.keep_master_audio:
            safe_remove(master_audio, logger)
        if comic_video_path:
            safe_remove(comic_video_path, logger)

        try:
            if os.path.isdir(self.work_dir) and not os.listdir(self.work_dir):
                os.rmdir(self.work_dir)
        except OSError:
            pass

        elapsed = time.time() - t0
        logger.info("=" * 70)
        logger.info("HOAN TAT PIPELINE trong %s", format_hms(elapsed))
        logger.info("So video da upload: %d", len(uploaded_video_ids))
        for vid, path in zip(uploaded_video_ids, final_paths):
            logger.info("  - https://youtu.be/%s  <-  %s", vid, path)
        logger.info("=" * 70)

        return uploaded_video_ids
