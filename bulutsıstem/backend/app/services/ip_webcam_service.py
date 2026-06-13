import re

import httpx

from app.models.camera import CameraProtocol, CameraSourceKind

IP_WEBCAM_DEFAULT_PORT = 8080
IP_WEBCAM_PATH = "/video"


def build_ip_webcam_url(phone_ip: str, port: int = IP_WEBCAM_DEFAULT_PORT) -> str:
    ip = phone_ip.strip()
    if ip.startswith("http://") or ip.startswith("https://"):
        return ip.rstrip("/") if ip.endswith("/video") else f"{ip.rstrip('/')}{IP_WEBCAM_PATH}"
    return f"http://{ip}:{port}{IP_WEBCAM_PATH}"


def parse_ip_webcam_url(stream_url: str) -> tuple[str, int] | None:
    match = re.match(r"^https?://([^:/]+):?(\d+)?/video/?$", stream_url.strip())
    if not match:
        return None
    host = match.group(1)
    port = int(match.group(2) or IP_WEBCAM_DEFAULT_PORT)
    return host, port


async def probe_ip_webcam(stream_url: str) -> tuple[bool, str]:
    """IP Webcam uygulamasının MJPEG endpoint'ini test eder."""
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            response = await client.get(stream_url, headers={"User-Agent": "BulutSistem/1.0"})
            if response.status_code != 200:
                return False, f"IP Webcam yanıt vermedi: HTTP {response.status_code}"
            content_type = response.headers.get("content-type", "")
            if "multipart" in content_type or "jpeg" in content_type or "mjpeg" in content_type:
                return True, "IP Webcam yayını aktif"
            if len(response.content) > 100:
                return True, "IP Webcam endpoint erişilebilir"
            return False, "IP Webcam'den görüntü verisi alınamadı"
    except httpx.HTTPError as exc:
        return False, (
            f"IP Webcam'e ulaşılamıyor: {exc}. "
            "Telefon ve sunucu aynı WiFi'de mi? IP Webcam uygulaması açık mı?"
        )


def ip_webcam_go2rtc_source(stream_url: str) -> str:
    """go2rtc için IP Webcam MJPEG kaynağı."""
    return stream_url
