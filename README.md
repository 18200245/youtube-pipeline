# YouTube Video Automation & Upload Pipeline

He thong xu ly am thanh TTS, render video gioi thieu truyen Remotion Manga HTML5, ghep video gameplay nen, can chinh am thanh va tu dong upload len kenh YouTube voi OAuth 2.0 (ho tro chay tren may local, Google Colab va Kaggle).

---

## 1. Cau truc thu muc

```text
youtube/
├── core/                       # Package chua logic xu ly chinh
│   ├── __init__.py             # Export cac class va ham
│   ├── constants.py            # Hang so he thong va thiet lap YouTube API
│   ├── config.py               # PipelineConfig va SafeDict
│   ├── utils.py                # Logging, ffmpeg, ffprobe, kiem tra audio stream
│   ├── auth.py                 # Dang nhap OAuth 2.0 (local webserver / OOB)
│   ├── audio.py                # Xu ly ghep, chuan hoa, mix nhac nen, chia group
│   ├── video.py                # Render comic intro, chuan hoa clip, ghep concat
│   ├── uploader.py             # Resumable upload len YouTube va them vao playlist
│   └── pipeline.py             # Dieu phoi toan bo quy trinh (Pipeline)
├── infoVideo/                  # Tool render video gioi thieu truyen Manga HTML5
│   ├── index.html              # Template giao dien studio 16:9
│   ├── app.js                  # Engine dieu khien frame va timeline animation
│   ├── style.css               # Phong cach manga, khung truyen, speedlines
│   ├── config.json             # File cau hinh noi dung truyen, kenh, donate
│   ├── render.py               # Script xuat video WebM bang Playwright & FFmpeg
│   └── assets/                 # Anh bia, avatar, ma QR
├── main.py                     # Entrypoint CLI va che do hoi dap interactive
├── run.py                      # Chay tu dong lay metadata tu Google Apps Script
├── youtube_pipeline.py         # File wrapper tuong thich nguoc
├── requirements.txt            # Danh sach thu vien Python
└── README.md                   # Huong dan su dung
```

---

## 2. Quy trinh ghep video (Video Concat Workflow)

Moi video xuat ra duoc ghep noi theo thu tu chuan:

```text
[1. Intro Video] -> [2. Video Gioi Thieu Truyen] -> [3. Video TTS Chinh] -> [4. Outro Video]
```

- **Video TTS Chinh (Body)**: Lap video nen (`video_file`) theo tong thoi luong audio TTS da mix nhac nen (neu co).
- **Video Gioi Thieu Truyen (Comic Info)**: Render tu file JSON cau hinh bang `infoVideo/render.py` (khong co am thanh goc).
- **Chuan hoa (Re-encode to match)**: Cac clip Intro, Video gioi thieu va Outro deu duoc tu dong encode lai de khop 100% thong so voi video TTS chinh (`codec`, `do phan giai`, `fps`, `pix_fmt`, `audio sample rate`, `channels`).
- **Xu ly am thanh cho clip khong tieng**: Tu dong long nhac nen (`background_music` voi `bg_music_volume`) hoac chen audio im lang (`silent audio`), dam bao FFmpeg concat demuxer (`-c copy`) khong loi va khong lam mat am thanh video chinh.

---

## 3. Cai dat moi truong

### Yeu cau he thong
- Python >= 3.8
- `ffmpeg` va `ffprobe` trong PATH.
  - Windows: `winget install Gyan.FFmpeg` hoac `choco install ffmpeg`
  - Ubuntu / Debian / Colab / Kaggle: `sudo apt-get install -y ffmpeg`

### Cai dat thu vien Python
```powershell
pip install -r requirements.txt
playwright install chromium
# Tren Linux / Kaggle / Colab neu thieu thu vien he thong (libatk-1.0.so.0...):
playwright install-deps chromium
```

---

## 4. Cac tham so cau hinh (PipelineConfig)

| Tham so | Kieu du lieu | Mac dinh | Mo ta |
| :--- | :--- | :--- | :--- |
| `name` | str | Bat buoc | Ten bo truyen / du an |
| `title_pattern` | str | Bat buoc | Mau tieu de video, vi du: `Tap {index} \| {name}` |
| `audios_dir` | str | Bat buoc | Thu muc chua cac file audio chapter |
| `video_file` | str | Bat buoc | File video nen (gameplay loop) |
| `intro_enable` | bool | `True` | Bat/tat ghep video intro |
| `intro_video` | str \| None | `None` | Duong dan file video intro |
| `comic_info_enable` | bool | `True` | Bat/tat render video gioi thieu truyen |
| `comic_json` | str \| None | `infoVideo/config.json` | Duong dan file JSON cau hinh cho `render.py` |
| `comic_render_mode` | str | `"frame"` | Che do render: `frame` (chuan frame) hoac `realtime` |
| `outro_enable` | bool | `True` | Bat/tat ghep video outro |
| `outro_video` | str \| None | `None` | Duong dan file video outro |
| `background_music` | str \| None | `None` | File nhac nen chay duoi audio doc truyen |
| `bg_music_volume` | str | `"0.2"` | Am luong nhac nen (`0.2` hoac `-18dB`) |
| `output_dir` | str | `"./output"` | Thu muc luu video xuat ra |
| `client_secrets_file`| str | `"client_secrets.json"` | File OAuth 2.0 Client tu Google Cloud |
| `token_file` | str | `"token.json"` | File token luu phien dang nhap |
| `privacy_status` | str | `"unlisted"` | Che do rieng tu: `public`, `private`, `unlisted` |

---

## 5. Huong dan su dung

### A. Chay dong lenh (CLI) qua `main.py`
```powershell
python main.py `
  --name "GoblinChuyenSinh" `
  --title-pattern "Tap {index} | Chuyen Sinh Thanh Goblin" `
  --audios-dir "./chapters" `
  --video-file "./background.mp4" `
  --intro-enable `
  --intro-video "./intro.mp4" `
  --comic-info-enable `
  --comic-json "./infoVideo/config.json" `
  --outro-enable `
  --outro-video "./outro.mp4" `
  --background-music "./bg_music.mp3" `
  --bg-music-volume "0.2" `
  --client-secrets-file "client_secrets.json" `
  --privacy-status "unlisted"
```

### B. Che do tuong tac (Interactive Mode)
```powershell
python main.py --interactive
```

### C. Chay tu dong lay metadata tu Google Apps Script (`run.py`)
Tu dong lay metadata tu Web App theo index:
```powershell
python run.py `
  --start-index 1 `
  --name "GoblinChuyenSinh" `
  --project-id 9 `
  --output-dir "/tmp/output" `
  --intro-video "./intro.mp4" `
  --outro-video "./outro.mp4" `
  --comic-json "./infoVideo/config.json" `
  --delete-final-video
```

### D. Su dung truc tiep trong Python Code
```python
from core import Pipeline, PipelineConfig

config = PipelineConfig(
    name="GoblinChuyenSinh",
    title_pattern="Tap {index} | Chuyen Sinh Thanh Goblin",
    audios_dir="./chapters",
    video_file="./background.mp4",
    intro_enable=True,
    intro_video="./intro.mp4",
    comic_info_enable=True,
    comic_json="./infoVideo/config.json",
    outro_enable=True,
    outro_video="./outro.mp4",
    background_music="./bg_music.mp3",
    bg_music_volume="0.2",
    privacy_status="unlisted",
)

pipeline = Pipeline(config)
uploaded_ids = pipeline.run()
```
