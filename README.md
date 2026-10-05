# YouTube Video Automation & Upload Pipeline

He thong xu ly am thanh, ghep video va tu dong upload len kenh YouTube voi ho tro OAuth 2.0 (chay duoc tren ca may local va Google Colab / Headless Server).

---

## 1. Cau truc thu muc

```text
youtube/
├── core/                       # Package chua logic xu ly loi
│   ├── __init__.py             # Export cac class va ham chinh
│   ├── constants.py            # Hang so he thong va thiet lap YouTube API
│   ├── config.py               # PipelineConfig va SafeDict
│   ├── utils.py                # Tien ich logging, ffmpeg, ffprobe
│   ├── auth.py                 # Dang nhap OAuth 2.0 (local webserver / OOB)
│   ├── audio.py                # Xu ly ghep, chuan hoa, mix nhac nen, chia group
│   ├── video.py                # Tao video loop, can chinh thong so intro, noi video
│   ├── uploader.py             # Resumable upload len YouTube va them vao playlist
│   └── pipeline.py             # Dieu phoi toan bo quy trinh (Pipeline)
├── run_colab.ipynb             # Notebook mau cho Google Colab / Jupyter
├── main.py                     # Entrypoint CLI va che do hoi dap interactive
├── youtube_pipeline.py         # File wrapper tuong thich nguoc voi code cu
├── requirements.txt            # Cac goi Python can thiet
├── .gitignore                  # Loai tru token, secrets, file output va cache
└── README.md                   # Huong dan su dung
```

---

## 2. Cai dat moi truong

### Yeu cau he thong
- Python >= 3.8
- `ffmpeg` va `ffprobe` da duoc cai dat va nam trong PATH.
  - Windows: cai bang `winget install Gyan.FFmpeg` hoac `choco install ffmpeg`.
  - Ubuntu / Debian / Colab: `sudo apt-get install -y ffmpeg`.

### Cai dat thu vien Python
```powershell
pip install -r requirements.txt
```

---

## 3. Huong dan su dung

### A. Chay tren Google Colab / Jupyter Notebook
1. Mo file `run_colab.ipynb`.
2. Chay lan luot cac cell:
   - Cell 1-2: Cai dat dependencies va kiem tra ffmpeg.
   - Cell 3: Upload file `client_secrets.json`.
   - Cell 4: Chinh sua cac thong so du an trong `PipelineConfig` (luu y dat `noauth_local_webserver=True`).
   - Cell 5: Chay pipeline. Mo link xac thuc, copy authorization code dan vao o input cua Colab.

### B. Chay bang dong lenh (CLI)
```powershell
python main.py \
  --name "TruyenKiemHiep" \
  --title-pattern "Tap {index} | Truyen Kiem Hiep Hay" \
  --audios-dir "./data/audios" \
  --video-file "./data/background.mp4" \
  --client-secrets-file "client_secrets.json" \
  --privacy-status "unlisted"
```

### C. Che do tuong tac (Interactive Mode)
Chay lenh sau va nhap tung thong so theo huong dan:
```powershell
python main.py --interactive
```

### D. Su dung nhu mot thu vien trong code Python
```python
from core import Pipeline, PipelineConfig

config = PipelineConfig(
    name="MySeries",
    title_pattern="Tap {index} | Series Name",
    audios_dir="./audios",
    video_file="./background.mp4",
    privacy_status="unlisted",
)

pipeline = Pipeline(config)
uploaded_ids = pipeline.run()
```

### E. Chay tu dong dong bo tu Google Apps Script (run.py)
Lay metadata du an theo `start_index` tu Apps Script va chay tu dong:
```powershell
python run.py \
  --start-index 9 \
  --name "Truyen1" \
  --project-id 9 \
  --output-dir "/tmp/output" \
  --delete-final-video
```

