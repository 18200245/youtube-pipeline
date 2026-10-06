from .audio import AudioGroup, AudioProcessor, compute_groups, natural_sort_key
from .config import PipelineConfig, SafeDict, extract_playlist_id
from .constants import (
    MAX_GROUP_SECONDS,
    VALID_PRIVACY_STATUSES,
    VIDEO_ENCODER_MAP,
    YOUTUBE_API_SERVICE_NAME,
    YOUTUBE_API_VERSION,
    YOUTUBE_UPLOAD_SCOPE,
)
from .utils import (
    ffprobe_json,
    format_hms,
    get_duration,
    get_video_stream_params,
    has_audio_stream,
    run_cmd,
    safe_remove,
    setup_logger,
)
from .video import VideoProcessor

try:
    from .auth import get_authenticated_service
    from .uploader import YouTubeUploader
    from .pipeline import Pipeline
except ImportError:
    get_authenticated_service = None
    YouTubeUploader = None
    Pipeline = None

__all__ = [
    "PipelineConfig",
    "SafeDict",
    "extract_playlist_id",
    "Pipeline",
    "AudioProcessor",
    "AudioGroup",
    "compute_groups",
    "natural_sort_key",
    "VideoProcessor",
    "YouTubeUploader",
    "get_authenticated_service",
    "setup_logger",
    "run_cmd",
    "ffprobe_json",
    "get_duration",
    "get_video_stream_params",
    "has_audio_stream",
    "format_hms",
    "safe_remove",
    "YOUTUBE_UPLOAD_SCOPE",
    "YOUTUBE_API_SERVICE_NAME",
    "YOUTUBE_API_VERSION",
    "VALID_PRIVACY_STATUSES",
    "MAX_GROUP_SECONDS",
    "VIDEO_ENCODER_MAP",
]
