import os
import re
from dataclasses import dataclass, field
from typing import List, Optional


class SafeDict(dict):
    """Dict dung cho str.format_map: giu nguyen {key} neu key khong ton tai,
    thay vi nem KeyError."""

    def __missing__(self, key):
        return "{" + key + "}"


def extract_playlist_id(playlist_url_or_id: str) -> str:
    """Nhan mot link playlist YouTube hoac 1 ID va tra ve ID."""
    playlist_url_or_id = playlist_url_or_id.strip()
    match = re.search(r"[?&]list=([a-zA-Z0-9_-]+)", playlist_url_or_id)
    if match:
        return match.group(1)
    return playlist_url_or_id


@dataclass
class PipelineConfig:
    # --- Thong tin chung ---
    name: str                          # ten du an, dung de dat ten thu muc tam
    title_pattern: str                 # vd: "Tap {index} | abcd"
    description: str = ""              # co the dung {index}, {name}, {group}, {total_groups}
    playlist_url: Optional[str] = None # link hoac ID playlist YouTube
    tags: str = ""                     # cac tag, cach nhau boi dau phay
    category_id: str = "22"
    privacy_status: str = "unlisted"   # public | private | unlisted
    start_index: int = 1

    # --- Nguon du lieu ---
    audios_dir: str = ""               # thu muc chua cac file audio
    video_file: str = ""               # 1 file video nen de lap lai
    intro_video: Optional[str] = None  # file video intro
    intro_enable: bool = True          # bat/tat video intro
    outro_video: Optional[str] = None  # file video outro
    outro_enable: bool = True          # bat/tat video outro
    comic_json: Optional[str] = None   # duong dan file json gioi thieu truyen (render.py)
    comic_info_enable: bool = True     # bat/tat video gioi thieu truyen tu render.py
    comic_render_mode: str = "frame"   # che do render cua render.py: "frame" hoac "realtime"
    info_video: Optional[str] = None   # alias cu tuong thich nguoc
    rerender: bool = False             # True = encode lai 1 lan khi ghep (bo qua build_body/copy)
    rerender_preset: str = "fastest"   # fastest | balanced | quality

    # --- Nhac nen ---
    background_music: Optional[str] = None
    bg_music_volume: str = "0.2"       # he so tuyen tinh (vd 0.2) hoac dang dB (vd "-18dB")

    # --- Output / thu muc lam viec ---
    output_dir: str = "./output"
    work_dir: Optional[str] = None     # thu muc tam; mac dinh = output_dir/_tmp_<name>

    # --- OAuth ---
    client_secrets_file: str = "client_secrets.json"
    token_file: str = "token.json"
    noauth_local_webserver: bool = False   # True = dang nhap khong dung localhost (OOB, dan code thu cong),
                                            # False = tu mo trinh duyet + local webserver (chi dung khi
                                            # chay tren may co giao dien, KHONG dung tren Colab/server)
    auth_host_name: str = "localhost"
    auth_host_port: Optional[List[int]] = field(default_factory=lambda: [8080, 8090])

    # --- Don dep ---
    delete_final_video_after_upload: bool = False  # xoa luon video hoan chinh sau khi upload thanh cong
    keep_master_audio: bool = False                # giu lai file audio tong da ghep va mix nhac nen

    def playlist_id(self) -> Optional[str]:
        return extract_playlist_id(self.playlist_url) if self.playlist_url else None

    def tag_list(self) -> Optional[List[str]]:
        if not self.tags:
            return None
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    def resolved_work_dir(self) -> str:
        if self.work_dir:
            return self.work_dir
        return os.path.join(self.output_dir, f"_tmp_{self.name}")

    def resolved_intro_video(self) -> Optional[str]:
        if not self.intro_enable:
            return None
        if self.intro_video:
            return self.intro_video
        if self.info_video and not self.info_video.strip().endswith(".json"):
            return self.info_video
        return None

    def resolved_outro_video(self) -> Optional[str]:
        if not self.outro_enable:
            return None
        return self.outro_video

    def resolved_comic_json(self) -> Optional[str]:
        if not self.comic_info_enable:
            return None
        if self.comic_json:
            return self.comic_json
        if self.info_video and self.info_video.strip().endswith(".json"):
            return self.info_video
        # Fallback to infoVideo/config.json if it exists
        default_json = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "infoVideo", "config.json")
        if os.path.exists(default_json):
            return default_json
        return None

