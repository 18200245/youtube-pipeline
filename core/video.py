import logging
import os
from typing import Optional

from .constants import VIDEO_ENCODER_MAP
from .utils import get_video_stream_params, run_cmd, safe_remove


class VideoProcessor:
    def __init__(self, work_dir: str, logger: logging.Logger):
        self.work_dir = work_dir
        self.logger = logger
        os.makedirs(work_dir, exist_ok=True)

    def build_body(
        self, video_file: str, audio_segment: str, idx: int, duration: Optional[float] = None
    ) -> str:
        """Lap video_file lien tuc, cat theo dung do dai audio_segment,
        khong encode lai video (copy), chi encode audio sang AAC."""
        out_path = os.path.join(self.work_dir, f"_body_{idx:03d}.mp4")
        self.logger.info("Dang ghep video + audio cho group %d...", idx)
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", video_file,
            "-i", audio_segment,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
        ]
        if duration is not None:
            cmd.extend(["-t", f"{max(0.001, float(duration)):.3f}"])
        cmd.extend(["-shortest", out_path])
        run_cmd(cmd, self.logger)
        return out_path

    def convert_intro_to_match(self, info_video: str, target_params: dict, idx: int) -> str:
        """Encode lai video gioi thieu cho khop codec/kich thuoc/audio voi
        video chinh, de co the noi (concat demuxer -c copy) ma khong phai
        encode lai toan bo video dai (body)."""
        encoder = VIDEO_ENCODER_MAP.get(target_params["codec_name"], "libx264")
        out_path = os.path.join(self.work_dir, f"_intro_converted_{idx:03d}.mp4")
        self.logger.info("Dang chuan hoa video gioi thieu (info_video) cho group %d...", idx)
        run_cmd(
            [
                "ffmpeg", "-y", "-i", info_video,
                "-vf", f"scale={target_params['width']}:{target_params['height']},fps={target_params['fps']}",
                "-c:v", encoder, "-pix_fmt", target_params["pix_fmt"],
                "-c:a", "aac",
                "-ar", str(target_params["audio_sample_rate"]),
                "-ac", str(target_params["audio_channels"]),
                "-b:a", "192k",
                out_path,
            ],
            self.logger,
        )
        return out_path

    def concat_intro_and_body(self, intro_path: str, body_path: str, idx: int) -> str:
        concat_list = os.path.join(self.work_dir, f"_concat_video_{idx:03d}.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for p in (intro_path, body_path):
                safe_path = os.path.abspath(p).replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")

        out_path = os.path.join(self.work_dir, f"_final_{idx:03d}.mp4")
        self.logger.info("Dang noi video gioi thieu vao dau group %d...", idx)
        run_cmd(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", out_path],
            self.logger,
        )
        safe_remove(concat_list, self.logger)
        return out_path

    def build_group_video(
        self,
        video_file: str,
        audio_segment: str,
        info_video: Optional[str],
        idx: int,
        duration: Optional[float] = None,
    ) -> str:
        body_path = self.build_body(video_file, audio_segment, idx, duration=duration)

        if not info_video:
            return body_path

        target_params = get_video_stream_params(body_path)
        intro_converted = self.convert_intro_to_match(info_video, target_params, idx)
        final_path = self.concat_intro_and_body(intro_converted, body_path, idx)

        safe_remove(intro_converted, self.logger)
        safe_remove(body_path, self.logger)
        return final_path
