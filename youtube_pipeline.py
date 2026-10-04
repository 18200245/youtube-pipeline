#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
youtube_pipeline.py
===================
Wrapper tuong thich nguoc (backward compatibility).
Moi chuc nang chinh da duoc module hoa trong thu muc `core/`.
File nay giu nguyen de dam bao cac script hoac notebook cu van import va chay binh thuong.
"""

from core import (
    AudioGroup,
    AudioProcessor,
    Pipeline,
    PipelineConfig,
    SafeDict,
    VideoProcessor,
    YouTubeUploader,
    compute_groups,
    extract_playlist_id,
    ffprobe_json,
    format_hms,
    get_authenticated_service,
    get_duration,
    get_video_stream_params,
    natural_sort_key,
    run_cmd,
    safe_remove,
    setup_logger,
)
from core.constants import (
    MAX_GROUP_SECONDS,
    MAX_UPLOAD_RETRIES,
    MISSING_CLIENT_SECRETS_MESSAGE,
    RETRIABLE_EXCEPTIONS,
    RETRIABLE_STATUS_CODES,
    VALID_PRIVACY_STATUSES,
    VIDEO_ENCODER_MAP,
    YOUTUBE_API_SERVICE_NAME,
    YOUTUBE_API_VERSION,
    YOUTUBE_UPLOAD_SCOPE,
)
from main import (
    build_arg_parser,
    config_from_args,
    main,
    prompt_config,
)

# Alias de dam bao tuong thich ten private cu neu co script goi toi
_safe_remove = safe_remove

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
    "format_hms",
    "_safe_remove",
    "safe_remove",
    "prompt_config",
    "build_arg_parser",
    "config_from_args",
    "main",
    "YOUTUBE_UPLOAD_SCOPE",
    "YOUTUBE_API_SERVICE_NAME",
    "YOUTUBE_API_VERSION",
    "VALID_PRIVACY_STATUSES",
    "MAX_GROUP_SECONDS",
    "RETRIABLE_STATUS_CODES",
    "RETRIABLE_EXCEPTIONS",
    "MAX_UPLOAD_RETRIES",
    "VIDEO_ENCODER_MAP",
    "MISSING_CLIENT_SECRETS_MESSAGE",
]

if __name__ == "__main__":
    main()
