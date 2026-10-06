"""
Constants used across the YouTube pipeline.
"""

YOUTUBE_UPLOAD_SCOPE = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

MAX_GROUP_SECONDS = 12 * 3600  # 12 hours - hard limit per group

AUDIO_SAMPLE_RATE = 24000
AUDIO_CHANNELS = 1

RETRIABLE_STATUS_CODES = (500, 502, 503, 504)
RETRIABLE_EXCEPTIONS = (IOError, ConnectionError)
MAX_UPLOAD_RETRIES = 10

VIDEO_ENCODER_MAP = {
    "h264": "libx264",
    "hevc": "libx265",
    "h265": "libx265",
    "vp9": "libvpx-vp9",
    "vp8": "libvpx",
    "mpeg4": "mpeg4",
    "av1": "libaom-av1",
}

MISSING_CLIENT_SECRETS_MESSAGE = """
CANH BAO: Chua cau hinh OAuth 2.0

Khong tim thay file client_secrets tai duong dan da chi dinh.
Hay tai file OAuth client (loai "TVs and Limited Input devices" hoac
"Desktop app") tu Google Cloud Console:
    https://console.cloud.google.com/
va dat dung ten/duong dan da khai bao trong cau hinh.

Chi tiet dinh dang file client_secrets.json:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
"""
