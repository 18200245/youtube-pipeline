import logging
import time
from typing import List, Optional

try:
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
except ImportError:  # pragma: no cover
    raise

from .constants import (
    MAX_UPLOAD_RETRIES,
    RETRIABLE_EXCEPTIONS,
    RETRIABLE_STATUS_CODES,
)


class YouTubeUploader:
    def __init__(self, youtube, logger: logging.Logger):
        self.youtube = youtube
        self.logger = logger

    def upload_video(
        self,
        file_path: str,
        title: str,
        description: str,
        tags: Optional[List[str]],
        category_id: str,
        privacy_status: str,
    ) -> str:
        body = dict(
            snippet=dict(
                title=title,
                description=description,
                tags=tags,
                categoryId=category_id,
            ),
            status=dict(privacyStatus=privacy_status),
        )

        self.logger.info("Bat dau upload: '%s' (%s)", title, file_path)
        insert_request = self.youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True),
        )
        video_id = self._resumable_upload(insert_request)
        self.logger.info("Upload thanh cong. Video ID = %s", video_id)
        return video_id

    def _resumable_upload(self, insert_request) -> str:
        response = None
        error = None
        retry = 0
        while response is None:
            try:
                status, response = insert_request.next_chunk()
                if status:
                    self.logger.info("  ... da upload %d%%", int(status.progress() * 100))
                if response:
                    if "id" in response:
                        return response["id"]
                    raise RuntimeError(f"Upload that bai voi phan hoi khong xac dinh: {response}")
            except HttpError as e:
                if e.resp.status in RETRIABLE_STATUS_CODES:
                    error = f"Loi HTTP {e.resp.status} (co the thu lai): {e.content}"
                else:
                    raise
            except RETRIABLE_EXCEPTIONS as e:
                error = f"Loi co the thu lai: {e}"

            if error:
                self.logger.warning(error)
                retry += 1
                if retry > MAX_UPLOAD_RETRIES:
                    raise RuntimeError("Da vuot qua so lan thu lai upload cho phep.")
                sleep_seconds = min(2 ** retry, 60)
                self.logger.info("Ngu %ss roi thu lai...", sleep_seconds)
                time.sleep(sleep_seconds)
                error = None
        raise RuntimeError("Upload ket thuc bat thuong.")

    def add_to_playlist(self, video_id: str, playlist_id: str) -> None:
        try:
            self.youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id},
                    }
                },
            ).execute()
            self.logger.info("Da them video %s vao playlist %s", video_id, playlist_id)
        except HttpError as e:
            self.logger.error("Khong the them video vao playlist: %s", e)
