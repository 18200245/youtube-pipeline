import logging
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from .utils import get_duration


@dataclass
class SubtitleEntry:
    start: float  # seconds
    end: float    # seconds
    text: str


def parse_timestamp_seconds(ts: str) -> float:
    """Chuyen doi chuoi thoi gian SRT/VTT/ASS sang giay."""
    ts = ts.strip().replace(",", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    return float(ts)


def format_ass_time(seconds: float) -> str:
    """Dinh dang giay sang chuoi thoi gian ASS: H:MM:SS.cc"""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 0
        s += 1
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def parse_srt(content: str) -> List[SubtitleEntry]:
    """Phan tich cu phap SRT sang danh sach SubtitleEntry."""
    entries: List[SubtitleEntry] = []
    blocks = re.split(r"\r?\n\r?\n", content.strip())
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        # Dong 0 co the la so thu tu (1, 2, 3...) hoac dong timecode
        time_line_idx = 1 if len(lines) > 1 and "-->" in lines[1] else (0 if "-->" in lines[0] else -1)
        if time_line_idx == -1:
            continue
        time_match = re.search(r"(\d+:\d+:\d+[\.,]\d+)\s*-->\s*(\d+:\d+:\d+[\.,]\d+)", lines[time_line_idx])
        if not time_match:
            continue
        start_sec = parse_timestamp_seconds(time_match.group(1))
        end_sec = parse_timestamp_seconds(time_match.group(2))
        text = "\\N".join(lines[time_line_idx + 1:])
        if text and end_sec > start_sec:
            entries.append(SubtitleEntry(start=start_sec, end=end_sec, text=text))
    return entries


def parse_vtt(content: str) -> List[SubtitleEntry]:
    """Phan tich cu phap WebVTT sang danh sach SubtitleEntry."""
    entries: List[SubtitleEntry] = []
    # Bo qua header WEBVTT
    content = re.sub(r"^WEBVTT[^\n]*\n", "", content.strip())
    blocks = re.split(r"\r?\n\r?\n", content)
    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        time_line_idx = -1
        for i, l in enumerate(lines[:2]):
            if "-->" in l:
                time_line_idx = i
                break
        if time_line_idx == -1:
            continue
        time_match = re.search(r"((?:\d+:)?\d+:\d+[\.,]\d+)\s*-->\s*((?:\d+:)?\d+:\d+[\.,]\d+)", lines[time_line_idx])
        if not time_match:
            continue
        start_sec = parse_timestamp_seconds(time_match.group(1))
        end_sec = parse_timestamp_seconds(time_match.group(2))
        text = "\\N".join(lines[time_line_idx + 1:])
        if text and end_sec > start_sec:
            entries.append(SubtitleEntry(start=start_sec, end=end_sec, text=text))
    return entries


def parse_ass(content: str) -> List[SubtitleEntry]:
    """Phan tich cu phap ASS sang danh sach SubtitleEntry."""
    entries: List[SubtitleEntry] = []
    lines = content.splitlines()
    in_events = False
    for line in lines:
        line = line.strip()
        if line.lower() == "[events]":
            in_events = True
            continue
        if in_events and line.startswith("[") and line.endswith("]"):
            break
        if in_events and line.startswith("Dialogue:"):
            parts = line[len("Dialogue:"):].split(",", 9)
            if len(parts) >= 10:
                start_sec = parse_timestamp_seconds(parts[1])
                end_sec = parse_timestamp_seconds(parts[2])
                raw_text = parts[9]
                # Loai bo override tags {\...} neu co
                clean_text = re.sub(r"\{[^\}]*\}", "", raw_text).strip()
                if clean_text and end_sec > start_sec:
                    entries.append(SubtitleEntry(start=start_sec, end=end_sec, text=clean_text))
    return entries


def parse_subtitle_file(file_path: str) -> List[SubtitleEntry]:
    """Doc va tu dong phan tich noi dung file phu de."""
    with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        content = f.read()

    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".srt":
        return parse_srt(content)
    elif ext == ".vtt":
        return parse_vtt(content)
    elif ext in (".ass", ".ssa"):
        return parse_ass(content)
    else:
        # Thu lan luot cac parser
        if "[Events]" in content:
            return parse_ass(content)
        elif "-->" in content:
            if "WEBVTT" in content:
                return parse_vtt(content)
            return parse_srt(content)
    return []


def generate_ass_content(
    entries: List[SubtitleEntry],
    width: int = 1920,
    height: int = 1080,
    font_name: str = "Bee Leave",
    font_size: Optional[int] = None,
) -> str:
    """Tao noi dung file ASS voi style Hop den (Opaque box) dong nhat theo yeu cau.

    Style mo phong chinh xac:
    - Font: Bee Leave (Bold)
    - Mau chu: Trang (&H00FFFFFF)
    - Mau hop nen: Den xam trong suot nhe (&H30222222) voi BorderStyle=3 (Opaque box)
    - Dem hop (Outline padding): ti le theo chieu cao video
    - Can le: Giua duoi (Alignment=2)
    """
    scale = height / 1080.0
    actual_font_size = font_size if font_size is not None else int(round(48 * scale))
    box_padding = max(4, int(round(16 * scale)))
    margin_v = max(10, int(round(65 * scale)))
    margin_lr = max(10, int(round(30 * scale)))

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{actual_font_size},&H00FFFFFF,&H000000FF,&H00000000,&H30222222,-1,0,0,0,100,100,0,0,3,{box_padding},0,2,{margin_lr},{margin_lr},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    dialogues: List[str] = []
    for entry in entries:
        start_str = format_ass_time(entry.start)
        end_str = format_ass_time(entry.end)
        dialogues.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{entry.text}")

    return header + "\n".join(dialogues) + "\n"


class SubtitleProcessor:
    def __init__(self, work_dir: str, logger: logging.Logger):
        self.work_dir = work_dir
        self.logger = logger
        os.makedirs(work_dir, exist_ok=True)

    def find_matching_subtitles(
        self, audio_files: List[str], subtitles_dir: Optional[str] = None
    ) -> Dict[str, Optional[str]]:
        """Tim file phu de khop ten voi tung file audio trong thu muc."""
        sub_map: Dict[str, Optional[str]] = {}
        for af in audio_files:
            base = os.path.splitext(af)[0]
            search_dir = subtitles_dir if subtitles_dir and os.path.isdir(subtitles_dir) else os.path.dirname(af)
            base_name = os.path.splitext(os.path.basename(af))[0]
            matched = None
            for ext in (".srt", ".ass", ".ssa", ".vtt"):
                candidate = os.path.join(search_dir, base_name + ext)
                if os.path.exists(candidate):
                    matched = candidate
                    break
            sub_map[af] = matched
        return sub_map

    def build_master_subtitles(
        self,
        audio_files: List[str],
        subtitles_dir: Optional[str] = None,
        single_subtitle_file: Optional[str] = None,
    ) -> List[SubtitleEntry]:
        """Tong hop phu de cua tat ca cac chapter thanh timeline duy nhat khop voi master audio."""
        if single_subtitle_file and os.path.exists(single_subtitle_file):
            self.logger.info("Su dung file phu de don le: %s", single_subtitle_file)
            return parse_subtitle_file(single_subtitle_file)

        # Kiem tra xem trong subtitles_dir co file phu de don khong
        if subtitles_dir and os.path.isdir(subtitles_dir):
            for candidate_name in ("subtitles.srt", "subtitle.srt", "full.srt", "master.srt"):
                candidate_path = os.path.join(subtitles_dir, candidate_name)
                if os.path.exists(candidate_path):
                    self.logger.info("Tim thay file phu de tong trong thu muc: %s", candidate_path)
                    return parse_subtitle_file(candidate_path)

        # Tim file phu de tuong ung tung chapter
        sub_map = self.find_matching_subtitles(audio_files, subtitles_dir)
        matched_count = sum(1 for p in sub_map.values() if p)
        if matched_count == 0:
            self.logger.info("Khong tim thay file phu de nao cho cac file audio.")
            return []

        self.logger.info("Tim thay %d / %d file phu de tuong ung cac chapter.", matched_count, len(audio_files))

        all_entries: List[SubtitleEntry] = []
        current_offset = 0.0

        for af in audio_files:
            dur = get_duration(af)
            sub_path = sub_map.get(af)
            if sub_path and os.path.exists(sub_path):
                self.logger.info("  - Ghep sub: %s (offset=%.2fs)", os.path.basename(sub_path), current_offset)
                entries = parse_subtitle_file(sub_path)
                for entry in entries:
                    all_entries.append(
                        SubtitleEntry(
                            start=entry.start + current_offset,
                            end=entry.end + current_offset,
                            text=entry.text,
                        )
                    )
            else:
                self.logger.debug("  - Khong co sub cho: %s (duration=%.2fs)", os.path.basename(af), dur)
            current_offset += dur

        # Sap xep theo thoi gian bat dau
        all_entries.sort(key=lambda e: e.start)

        # Khang va cham (anti-collision): triet tieu overlap thoi gian lam sub nhay vi tri
        for i in range(len(all_entries) - 1):
            if all_entries[i].end > all_entries[i + 1].start:
                all_entries[i].end = all_entries[i + 1].start
        return all_entries

    def slice_group_subtitles(
        self,
        master_entries: List[SubtitleEntry],
        start: float,
        duration: float,
        idx: int,
        width: int = 1920,
        height: int = 1080,
        font_name: str = "Bee Leave",
        font_size: Optional[int] = None,
    ) -> Optional[str]:
        """Trich xuat va tao file ASS cho mot group video voi timeline dich chuyen ve 0."""
        if not master_entries:
            return None

        group_end = start + duration
        group_entries: List[SubtitleEntry] = []

        for entry in master_entries:
            # Bo qua neu entry nam hoan toan ngoai khoang [start, group_end]
            if entry.end <= start or entry.start >= group_end:
                continue

            # Crop va shift timestamp
            shifted_start = max(0.0, entry.start - start)
            shifted_end = min(duration, entry.end - start)
            if shifted_end > shifted_start:
                group_entries.append(
                    SubtitleEntry(
                        start=shifted_start,
                        end=shifted_end,
                        text=entry.text,
                    )
                )

        if not group_entries:
            self.logger.info("Group %d khong co phu de nao trong khoang thoi gian nay.", idx)
            return None

        group_entries.sort(key=lambda e: e.start)
        # Khang va cham (anti-collision): triet tieu overlap thoi gian lam sub nhay vi tri
        for i in range(len(group_entries) - 1):
            if group_entries[i].end > group_entries[i + 1].start:
                group_entries[i].end = group_entries[i + 1].start

        out_path = os.path.join(self.work_dir, f"_sub_group_{idx:03d}.ass")
        ass_content = generate_ass_content(
            group_entries,
            width=width,
            height=height,
            font_name=font_name,
            font_size=font_size,
        )
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(ass_content)

        self.logger.info(
            "Da tao file phu de group %d (%d cau): %s", idx, len(group_entries), out_path
        )
        return out_path
