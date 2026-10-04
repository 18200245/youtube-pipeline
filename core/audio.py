import glob
import logging
import math
import os
import re
from dataclasses import dataclass
from typing import List, Optional

from .constants import MAX_GROUP_SECONDS
from .utils import run_cmd, safe_remove


def natural_sort_key(path: str):
    """Tach so de sap xep tu nhien: chapter_2 truoc chapter_10, chapter_0001 truoc chapter_0002."""
    filename = os.path.basename(path)
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", filename)]


@dataclass
class AudioGroup:
    index_in_run: int    # thu tu 0-based trong lan chay nay
    start: float
    duration: float


def compute_groups(total_duration: float, max_seconds: float = MAX_GROUP_SECONDS) -> List[AudioGroup]:
    """Chia total_duration thanh N group, moi group < max_seconds, chia
    DEU nhau (vd 13h -> 2 group ~6.5h/group, khong phai 12h + 1h)."""
    if total_duration <= max_seconds:
        n_groups = 1
    else:
        n_groups = math.ceil(total_duration / max_seconds)

    group_duration = total_duration / n_groups
    groups: List[AudioGroup] = []
    start = 0.0
    for i in range(n_groups):
        if i == n_groups - 1:
            dur = total_duration - start  # group cuoi lay het phan con lai (tranh lech do lam tron)
        else:
            dur = group_duration
        groups.append(AudioGroup(index_in_run=i, start=start, duration=dur))
        start += dur
    return groups


class AudioProcessor:
    def __init__(self, work_dir: str, logger: logging.Logger):
        self.work_dir = work_dir
        self.logger = logger
        os.makedirs(work_dir, exist_ok=True)

    def list_audio_files(self, audios_dir: str) -> List[str]:
        exts = ("*.wav", "*.mp3", "*.m4a", "*.aac", "*.flac", "*.ogg")
        all_files: List[str] = []
        for ext in exts:
            all_files.extend(glob.glob(os.path.join(audios_dir, ext)))

        # Loai bo cac file tam, file rac tu TTS hoac qua trinh xu ly truoc do
        ignored_prefixes = ("temp_", "_norm_", "_merged", "_clean", "_master", "_segment", "single_output")
        valid_files = [
            f for f in all_files
            if not os.path.basename(f).lower().startswith(ignored_prefixes)
        ]

        # Neu co file theo mau chapter_*, uu tien loc lay cac file chapter_*
        chapter_files = [
            f for f in valid_files
            if os.path.basename(f).lower().startswith("chapter_")
        ]
        selected_files = chapter_files if chapter_files else valid_files

        # Sap xep theo thu tu so tu nhien (natural sort)
        files = sorted(selected_files, key=natural_sort_key)

        if not files:
            raise RuntimeError(f"Khong tim thay file audio hop le nao trong '{audios_dir}'")
        self.logger.info("Tim thay %d file audio trong '%s'", len(files), audios_dir)
        for f in files:
            self.logger.info("  - %s", os.path.basename(f))
        return files

    def normalize(self, audio_files: List[str]) -> List[str]:
        """Dua tat ca file audio ve cung 1 dinh dang (wav pcm_s16le, 24000Hz,
        stereo) de co the noi (concat demuxer + copy) an toan."""
        normalized = []
        for i, src in enumerate(audio_files):
            dst = os.path.join(self.work_dir, f"_norm_{i:04d}.wav")
            run_cmd(
                [
                    "ffmpeg", "-y", "-i", src,
                    "-ar", "24000", "-ac", "2", "-c:a", "pcm_s16le",
                    dst,
                ],
                self.logger,
            )
            normalized.append(dst)
        return normalized

    def concat(self, normalized_files: List[str]) -> str:
        concat_list = os.path.join(self.work_dir, "_concat_audio.txt")
        with open(concat_list, "w", encoding="utf-8") as f:
            for wav in normalized_files:
                safe_path = os.path.abspath(wav).replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")

        merged = os.path.join(self.work_dir, "_merged.wav")
        self.logger.info("Dang ghep %d file audio...", len(normalized_files))
        run_cmd(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", merged],
            self.logger,
        )
        return merged

    def mix_background(self, speech_audio: str, bg_music: Optional[str], bg_volume: str) -> str:
        if not bg_music:
            self.logger.info("Khong co nhac nen, bo qua buoc tron nhac.")
            return speech_audio

        self.logger.info("Dang ghep nhac nen (volume=%s)...", bg_volume)
        master = os.path.join(self.work_dir, "_master_audio.wav")
        run_cmd(
            [
                "ffmpeg", "-y",
                "-i", speech_audio,
                "-stream_loop", "-1", "-i", bg_music,
                "-filter_complex",
                f"[1:a]volume={bg_volume}[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2:normalize=0",
                "-c:a", "pcm_s16le",
                master,
            ],
            self.logger,
        )
        return master

    def build_master_audio(self, audios_dir: str, bg_music: Optional[str], bg_volume: str) -> str:
        files = self.list_audio_files(audios_dir)
        normalized = self.normalize(files)
        merged = self.concat(normalized)
        master = self.mix_background(merged, bg_music, bg_volume)

        # don temp trung gian (giu lai file master cuoi cung)
        for f in normalized:
            safe_remove(f, self.logger)
        safe_remove(os.path.join(self.work_dir, "_concat_audio.txt"), self.logger)
        if merged != master:
            safe_remove(merged, self.logger)
        return master

    def extract_segment(self, master_audio: str, start: float, duration: float, idx: int) -> str:
        seg_path = os.path.join(self.work_dir, f"_segment_{idx:03d}.wav")
        run_cmd(
            [
                "ffmpeg", "-y", "-i", master_audio,
                "-ss", f"{start:.3f}", "-t", f"{duration:.3f}",
                "-c", "copy", seg_path,
            ],
            self.logger,
        )
        return seg_path
