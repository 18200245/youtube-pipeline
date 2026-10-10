import logging
import os
import subprocess
import sys
from typing import List, Optional

from .constants import VIDEO_ENCODER_MAP
from .utils import get_duration, get_video_stream_params, has_audio_stream, run_cmd, safe_remove

# Preset rerender: (nvenc_args, x264_args)
RERENDER_PRESETS = {
    "fastest": (
        ["-preset", "p1", "-tune", "ll", "-rc", "vbr", "-cq", "28", "-b:v", "0", "-bf", "0", "-g", "60"],
        ["-preset", "ultrafast", "-tune", "zerolatency", "-crf", "28", "-g", "60", "-threads", "0"],
    ),
    "balanced": (
        ["-preset", "p4", "-rc", "vbr", "-cq", "23", "-b:v", "0"],
        ["-preset", "veryfast", "-crf", "23", "-threads", "0"],
    ),
    "quality": (
        ["-preset", "p7", "-rc", "vbr", "-cq", "19", "-b:v", "0"],
        ["-preset", "medium", "-crf", "20", "-threads", "0"],
    ),
}

_NVENC_AVAILABLE: Optional[bool] = None


def nvenc_available() -> bool:
    """Kiem tra h264_nvenc co dung duoc khong (cache ket qua)."""
    global _NVENC_AVAILABLE
    if _NVENC_AVAILABLE is not None:
        return _NVENC_AVAILABLE
    try:
        encoders = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        ).stdout
        if "h264_nvenc" not in encoders:
            _NVENC_AVAILABLE = False
        else:
            test = subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-v", "error",
                    "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.1",
                    "-c:v", "h264_nvenc", "-f", "null", "-",
                ],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            _NVENC_AVAILABLE = test.returncode == 0
    except Exception:
        _NVENC_AVAILABLE = False
    return _NVENC_AVAILABLE


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

    def build_group_video_rerender(
        self,
        video_file: str,
        audio_segment: str,
        idx: int,
        duration: Optional[float],
        clips_before: List[str],
        clips_after: List[str],
        bg_music: Optional[str] = None,
        bg_volume: str = "0.2",
        preset: str = "fastest",
    ) -> str:
        """Rerender 1 lan duy nhat: [clips_before] + body(video_file lap + audio_segment)
        + [clips_after] bang concat filter, khong tao file body trung gian."""
        params = get_video_stream_params(video_file)
        W, H, fps = params["width"], params["height"], params["fps"]
        body_dur = float(duration) if duration is not None else get_duration(audio_segment)
        body_dur = max(0.001, body_dur)

        nvenc_args, x264_args = RERENDER_PRESETS.get(preset, RERENDER_PRESETS["fastest"])
        if nvenc_available():
            enc_args = ["-c:v", "h264_nvenc"] + nvenc_args
            self.logger.info("Rerender dung h264_nvenc (preset=%s)", preset)
        else:
            enc_args = ["-c:v", "libx264"] + x264_args
            self.logger.info("Rerender dung libx264 (preset=%s)", preset)

        inputs: List[str] = []
        n_inputs = 0
        filters: List[str] = []
        segs: List[str] = []
        seg_i = 0
        vnorm = f"scale={W}:{H},fps={fps},setsar=1,format=yuv420p"
        anorm = "aformat=sample_rates=24000:channel_layouts=mono"

        def add_clip(path: str) -> None:
            nonlocal n_inputs, seg_i
            vi = n_inputs
            inputs.extend(["-i", path])
            n_inputs += 1
            dur = max(0.1, get_duration(path))
            filters.append(f"[{vi}:v]{vnorm},trim=duration={dur:.3f},setpts=PTS-STARTPTS[v{seg_i}]")
            if has_audio_stream(path):
                filters.append(f"[{vi}:a]{anorm},asetpts=PTS-STARTPTS[a{seg_i}]")
            elif bg_music and os.path.exists(bg_music):
                bi = n_inputs
                inputs.extend(["-stream_loop", "-1", "-i", bg_music])
                n_inputs += 1
                filters.append(
                    f"[{bi}:a]atrim=0:{dur:.3f},volume={bg_volume},{anorm},asetpts=PTS-STARTPTS[a{seg_i}]"
                )
            else:
                filters.append(
                    f"anullsrc=channel_layout=mono:sample_rate=24000,atrim=0:{dur:.3f},asetpts=PTS-STARTPTS[a{seg_i}]"
                )
            segs.append(f"[v{seg_i}][a{seg_i}]")
            seg_i += 1

        for p in clips_before:
            add_clip(p)

        # Body: video lap vo han (cat bang trim) + audio segment
        bv = n_inputs
        inputs.extend(["-stream_loop", "-1", "-i", video_file])
        n_inputs += 1
        ba = n_inputs
        inputs.extend(["-i", audio_segment])
        n_inputs += 1
        filters.append(f"[{bv}:v]{vnorm},trim=duration={body_dur:.3f},setpts=PTS-STARTPTS[v{seg_i}]")
        filters.append(f"[{ba}:a]{anorm},atrim=duration={body_dur:.3f},asetpts=PTS-STARTPTS[a{seg_i}]")
        segs.append(f"[v{seg_i}][a{seg_i}]")
        seg_i += 1

        for p in clips_after:
            add_clip(p)

        filters.append(f"{''.join(segs)}concat=n={len(segs)}:v=1:a=1[v][a]")

        out_path = os.path.join(self.work_dir, f"_final_{idx:03d}.mp4")
        cpu = str(os.cpu_count() or 1)
        cmd = [
            "ffmpeg", "-y", "-filter_complex_threads", cpu, *inputs,
            "-filter_complex", ";".join(filters),
            "-map", "[v]", "-map", "[a]",
            *enc_args,
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ar", "24000", "-ac", "1",
            "-movflags", "+faststart",
            out_path,
        ]
        self.logger.info("Rerender video group %d (%d doan)...", idx, len(segs))
        run_cmd(cmd, self.logger)
        return out_path

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
        rerender: bool = False,
        rerender_preset: str = "fastest",
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

        if rerender:
            before = [
                p for p in (intro_video, comic_video) if p and os.path.exists(p)
            ]
            after = [outro_video] if outro_video and os.path.exists(outro_video) else []
            return self.build_group_video_rerender(
                video_file, audio_segment, idx, duration,
                before, after, bg_music, bg_volume, rerender_preset,
            )

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
