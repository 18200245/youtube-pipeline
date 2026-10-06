import logging
import os
import sys
from typing import List, Optional

from .constants import VIDEO_ENCODER_MAP
from .utils import get_duration, get_video_stream_params, has_audio_stream, run_cmd, safe_remove


class VideoProcessor:
    def __init__(self, work_dir: str, logger: logging.Logger):
        self.work_dir = work_dir
        self.logger = logger
        os.makedirs(work_dir, exist_ok=True)

    def render_comic_video(
        self,
        config_json: str,
        out_path: Optional[str] = None,
        mode: str = "frame",
    ) -> str:
        """Tao video gioi thieu truyen bang HTML5 Remotion Manga renderer (render.py)."""
        if not out_path:
            out_path = os.path.join(self.work_dir, "_comic_intro.webm")

        # Tim duong dan toi render.py trong thu muc infoVideo
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        render_script = os.path.join(project_root, "infoVideo", "render.py")
        if not os.path.exists(render_script):
            raise FileNotFoundError(f"Khong tim thay script render tai {render_script}")

        self.logger.info("Dang render video gioi thieu truyen tu config: %s (mode=%s)...", config_json, mode)
        cmd = [
            sys.executable,
            render_script,
            "--config",
            os.path.abspath(config_json),
            "--output",
            os.path.abspath(out_path),
            "--mode",
            mode,
        ]
        run_cmd(cmd, self.logger)

        if not os.path.exists(out_path):
            raise RuntimeError(f"Render video gioi thieu that bai, khong tim thay file: {out_path}")

        self.logger.info("Render video gioi thieu thanh cong: %s", out_path)
        return out_path

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
            "-c:a", "aac", "-b:a", "128k",
            "-ar", "24000", "-ac", "1",
        ]
        if duration is not None:
            cmd.extend(["-t", f"{max(0.001, float(duration)):.3f}"])
        cmd.extend(["-shortest", out_path])
        run_cmd(cmd, self.logger)
        return out_path

    def convert_clip_to_match(
        self,
        clip_path: str,
        target_params: dict,
        out_path: str,
        bg_music: Optional[str] = None,
        bg_volume: str = "0.2",
    ) -> str:
        """Encode lai clip video de khop 100% codec, do phan giai, fps, pix_fmt
        va audio (AAC, 24000Hz, mono) voi video chinh (body), dam bao
        co the concat (-c copy) khong loi va khong bi mat tieng."""
        encoder = VIDEO_ENCODER_MAP.get(target_params["codec_name"], "libx264")
        v_filter = f"[0:v]scale={target_params['width']}:{target_params['height']},fps={target_params['fps']}[v]"
        audio_sr = target_params.get("audio_sample_rate") or 24000
        audio_ch = target_params.get("audio_channels") or 1
        has_audio = has_audio_stream(clip_path)
        clip_dur = max(0.1, get_duration(clip_path))

        self.logger.info(
            "Chuan hoa video '%s' (duration=%.2fs, has_audio=%s, 24000Hz mono) khop voi video chinh...",
            os.path.basename(clip_path),
            clip_dur,
            has_audio,
        )

        if has_audio:
            # Video da co audio: chuyen sang AAC 24000Hz mono
            filter_complex = f"{v_filter};[0:a]aformat=sample_rates=24000:channel_layouts=mono[a]"
            cmd = [
                "ffmpeg", "-y",
                "-i", clip_path,
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "[a]",
                "-c:v", encoder, "-pix_fmt", target_params["pix_fmt"],
                "-c:a", "aac", "-b:a", "128k",
                "-ar", "24000", "-ac", "1",
                "-t", f"{clip_dur:.3f}",
                out_path,
            ]
        elif bg_music and os.path.exists(bg_music):
            # Video khong co audio: long nhac nen 24000Hz mono gioi han dung thoi luong video
            self.logger.info("Long nhac nen cho clip '%s' (24000Hz mono)...", os.path.basename(clip_path))
            filter_complex = (
                f"{v_filter};"
                f"[1:a]atrim=0:{clip_dur:.3f},volume={bg_volume},aformat=sample_rates=24000:channel_layouts=mono[a]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", clip_path,
                "-stream_loop", "-1", "-i", bg_music,
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "[a]",
                "-c:v", encoder, "-pix_fmt", target_params["pix_fmt"],
                "-c:a", "aac", "-b:a", "128k",
                "-ar", "24000", "-ac", "1",
                "-t", f"{clip_dur:.3f}",
                out_path,
            ]
        else:
            # Video khong co audio va khong co nhac nen: tao luong silent audio 24000Hz mono
            filter_complex = (
                f"{v_filter};"
                f"anullsrc=channel_layout=mono:sample_rate=24000,atrim=0:{clip_dur:.3f}[a]"
            )
            cmd = [
                "ffmpeg", "-y",
                "-i", clip_path,
                "-filter_complex", filter_complex,
                "-map", "[v]", "-map", "[a]",
                "-c:v", encoder, "-pix_fmt", target_params["pix_fmt"],
                "-c:a", "aac", "-b:a", "128k",
                "-ar", "24000", "-ac", "1",
                "-t", f"{clip_dur:.3f}",
                out_path,
            ]

        run_cmd(cmd, self.logger)
        return out_path

    def convert_intro_to_match(
        self,
        info_video: str,
        target_params: dict,
        idx: int,
        bg_music: Optional[str] = None,
        bg_volume: str = "0.2",
    ) -> str:
        """Ham tuong thich nguoc de chuan hoa video intro."""
        out_path = os.path.join(self.work_dir, f"_intro_converted_{idx:03d}.mp4")
        return self.convert_clip_to_match(info_video, target_params, out_path, bg_music, bg_volume)

    def concat_videos(self, video_paths: List[str], out_path: str) -> str:
        """Ghep danh sach cac video theo dung thu tu su dung concat demuxer (-c copy)."""
        concat_list = os.path.join(self.work_dir, f"_concat_list_{os.path.basename(out_path)}.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for p in video_paths:
                safe_path = os.path.abspath(p).replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")

        self.logger.info("Dang concat %d video thanh %s...", len(video_paths), out_path)
        run_cmd(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", out_path],
            self.logger,
        )
        safe_remove(concat_list, self.logger)
        return out_path

    def concat_intro_and_body(self, intro_path: str, body_path: str, idx: int) -> str:
        """Ham tuong thich nguoc de ghep intro va body."""
        out_path = os.path.join(self.work_dir, f"_final_{idx:03d}.mp4")
        return self.concat_videos([intro_path, body_path], out_path)

    def build_group_video(
        self,
        video_file: str,
        audio_segment: str,
        idx: int = 0,
        duration: Optional[float] = None,
        intro_video: Optional[str] = None,
        comic_video: Optional[str] = None,
        outro_video: Optional[str] = None,
        bg_music: Optional[str] = None,
        bg_volume: str = "0.2",
        info_video: Optional[str] = None,
    ) -> str:
        """Xay dung video hoan chinh cho mot group bao gom:
        [Intro] -> [Video gioi thieu truyen] -> [Body TTS] -> [Outro]."""
        # Ho tro goi theo thu tu tham so cu: build_group_video(video_file, audio_segment, info_video, idx, duration)
        if isinstance(idx, str) or (idx is None and isinstance(duration, int)):
            actual_info_video = idx
            actual_idx = duration if isinstance(duration, int) else 0
            actual_duration = intro_video if isinstance(intro_video, (int, float)) else None
            intro_video = actual_info_video
            idx = actual_idx
            duration = actual_duration

        if not intro_video and info_video:
            intro_video = info_video

        body_path = self.build_body(video_file, audio_segment, idx, duration=duration)

        # Kiem tra xem co can ghep them video nao khong
        has_intro = bool(intro_video and os.path.exists(intro_video))
        has_comic = bool(comic_video and os.path.exists(comic_video))
        has_outro = bool(outro_video and os.path.exists(outro_video))

        if not (has_intro or has_comic or has_outro):
            return body_path

        target_params = get_video_stream_params(body_path)
        clips_to_concat: List[str] = []
        temp_clips_to_clean: List[str] = []

        # 1. Intro video (neu bat va ton tai)
        if has_intro:
            intro_conv = os.path.join(self.work_dir, f"_intro_conv_{idx:03d}.mp4")
            self.convert_clip_to_match(intro_video, target_params, intro_conv, bg_music, bg_volume)
            clips_to_concat.append(intro_conv)
            temp_clips_to_clean.append(intro_conv)

        # 2. Video gioi thieu truyen (tu render.py)
        if has_comic:
            comic_conv = os.path.join(self.work_dir, f"_comic_conv_{idx:03d}.mp4")
            self.convert_clip_to_match(comic_video, target_params, comic_conv, bg_music, bg_volume)
            clips_to_concat.append(comic_conv)
            temp_clips_to_clean.append(comic_conv)

        # 3. Video TTS chinh (body)
        clips_to_concat.append(body_path)
        temp_clips_to_clean.append(body_path)

        # 4. Outro video (neu bat va ton tai)
        if has_outro:
            outro_conv = os.path.join(self.work_dir, f"_outro_conv_{idx:03d}.mp4")
            self.convert_clip_to_match(outro_video, target_params, outro_conv, bg_music, bg_volume)
            clips_to_concat.append(outro_conv)
            temp_clips_to_clean.append(outro_conv)

        final_path = os.path.join(self.work_dir, f"_final_{idx:03d}.mp4")
        self.concat_videos(clips_to_concat, final_path)

        # Don dep cac clip tam sau khi da ghep xong
        for temp_clip in temp_clips_to_clean:
            safe_remove(temp_clip, self.logger)

        return final_path
