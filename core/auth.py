import logging
import os
from types import SimpleNamespace
from typing import List, Optional

try:
    import httplib2
    from oauth2client.client import flow_from_clientsecrets
    from oauth2client.file import Storage
    from oauth2client.tools import run_flow
    from googleapiclient.discovery import build
except ImportError:  # pragma: no cover
    print(
        "Thieu thu vien Google API. Hay chay:\n"
        "  pip install oauth2client google-api-python-client httplib2"
    )
    raise

from .constants import (
    MISSING_CLIENT_SECRETS_MESSAGE,
    YOUTUBE_API_SERVICE_NAME,
    YOUTUBE_API_VERSION,
    YOUTUBE_UPLOAD_SCOPE,
)

httplib2.RETRIES = 1


def get_authenticated_service(
    client_secrets_file: str,
    token_file: str,
    logger: logging.Logger,
    noauth_local_webserver: bool = False,
    auth_host_name: str = "localhost",
    auth_host_port: Optional[List[int]] = None,
):
    """
    Dang nhap YouTube dung oauth2client.
    - noauth_local_webserver=True: Che do OOB flow, phu hop Colab/server/SSH.
    - noauth_local_webserver=False: Mo trinh duyet + local webserver.
    """
    if not os.path.exists(client_secrets_file):
        logger.error(MISSING_CLIENT_SECRETS_MESSAGE)
        raise FileNotFoundError(
            f"Khong tim thay file client_secrets tai '{client_secrets_file}'."
        )

    flow = flow_from_clientsecrets(
        client_secrets_file,
        scope=" ".join(YOUTUBE_UPLOAD_SCOPE),
        message=MISSING_CLIENT_SECRETS_MESSAGE,
    )

    storage = Storage(token_file)
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        if noauth_local_webserver:
            print("\n" + "=" * 70)
            print("DANG NHAP YOUTUBE (--noauth_local_webserver, khong dung localhost)")
            print("=" * 70)
            print(
                "Ban se thay 1 link duoc in ra ben duoi. Mo link do tren trinh\n"
                "duyet bat ky, dang nhap tai khoan YouTube muon dung de upload,\n"
                "bam 'Cho phep'. Google se hien THANG mot MA XAC THUC ngay tren\n"
                "trang (khong chuyen huong di dau ca) - copy ma do va dan vao\n"
                "khi terminal hoi 'Enter verification code'.\n"
            )
        else:
            logger.info(
                "Dang mo trinh duyet + local webserver de dang nhap "
                "(dung noauth_local_webserver=True neu may nay khong co "
                "trinh duyet, vd Colab/server)..."
            )

        flags = SimpleNamespace(
            noauth_local_webserver=noauth_local_webserver,
            logging_level="ERROR",
            auth_host_name=auth_host_name,
            auth_host_port=auth_host_port or [8080, 8090],
        )

        try:
            credentials = run_flow(flow, storage, flags)
        except Exception as exc:  # noqa: BLE001
            if noauth_local_webserver:
                raise RuntimeError(
                    f"Dang nhap that bai: {exc}\n"
                    "Neu Google bao loi kieu 'invalid_request' hoac 'OAuth client "
                    "is not compliant', co nghia la client_secrets.json cua ban "
                    "khong con duoc phep dung OOB flow (Google da han che tu "
                    "2022 cho cac OAuth client tao moi). Hay thu tao lai OAuth "
                    "client hoac chay khong co --noauth_local_webserver tren may "
                    "co trinh duyet."
                ) from exc
            raise

        logger.info("Dang nhap thanh cong. Da luu token vao %s", token_file)
    else:
        logger.info("Tim thay token co san tai %s, dang su dung lai.", token_file)

    return build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)
