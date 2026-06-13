#!/usr/bin/env python3
"""
BulutSistem Edge Agent

Ev içi kameraları buluta bağlar:
- IP Webcam kaydı
- Heartbeat
- WebSocket tünel (uzak ağdan kamera erişimi)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

import httpx
import yaml

from tunnel import run_tunnel

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_config(path: Path) -> dict:
    if not path.exists():
        print(f"Yapılandırma bulunamadı: {path}")
        print("Örnek: cp config.example.yaml config.yaml")
        sys.exit(1)
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def headers(agent_key: str) -> dict:
    return {"X-Agent-Key": agent_key, "Content-Type": "application/json"}


def heartbeat(client: httpx.Client, api_url: str, agent_key: str, name: str, local_ip: str | None) -> None:
    response = client.post(
        f"{api_url}/edge/heartbeat",
        headers=headers(agent_key),
        json={"agent_name": name, "local_ip": local_ip, "message": "edge-agent aktif"},
    )
    response.raise_for_status()
    print(f"[heartbeat] OK — tenant {response.json().get('tenant_id')}")


def register_ip_webcam(client: httpx.Client, api_url: str, agent_key: str, cfg: dict) -> None:
    cam = cfg.get("ip_webcam", {})
    if not cam.get("enabled", True):
        return
    payload = {
        "name": cam.get("camera_name", "Telefon Kamerası"),
        "phone_ip": cam["phone_ip"],
        "port": cam.get("port", 8080),
    }
    response = client.post(
        f"{api_url}/edge/cameras/ip-webcam",
        headers=headers(agent_key),
        json=payload,
    )
    if response.status_code == 200:
        data = response.json()
        print(f"[kamera] Kayıtlı: {data.get('name')} → {data.get('stream_url')}")
        print(f"[kamera] Durum: {data.get('status')} — {data.get('status_message')}")
    else:
        print(f"[kamera] Hata: {response.status_code} {response.text}")


def heartbeat_loop(api_url: str, agent_key: str, name: str, local_ip: str | None, interval: int) -> None:
    while True:
        time.sleep(interval)
        try:
            with httpx.Client(timeout=20.0) as client:
                heartbeat(client, api_url, agent_key, name, local_ip)
        except Exception as exc:
            print(f"[heartbeat] Hata: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="BulutSistem Edge Agent")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="config.yaml yolu")
    parser.add_argument("--once", action="store_true", help="Tek sefer çalış ve çık (tünel olmadan)")
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    api_url = cfg["api_url"].rstrip("/")
    agent_key = cfg["edge_agent_key"]
    interval = int(cfg.get("heartbeat_seconds", 30))
    agent_name = cfg.get("agent_name", "bulutsistem-edge-agent")
    local_ip = cfg.get("local_ip")
    tunnel_cfg = cfg.get("tunnel", {})
    tunnel_enabled = tunnel_cfg.get("enabled", False)

    print("=" * 50)
    print("BulutSistem Edge Agent")
    print(f"API: {api_url}")
    print(f"Tünel: {'AÇIK' if tunnel_enabled else 'KAPALI'}")
    print("=" * 50)

    with httpx.Client(timeout=20.0) as client:
        register_ip_webcam(client, api_url, agent_key, cfg)
        heartbeat(client, api_url, agent_key, agent_name, local_ip)

    if args.once or not tunnel_enabled:
        if not tunnel_enabled:
            print("Tünel kapalı. config.yaml içinde tunnel.enabled: true yapın.")
        return

    import threading

    threading.Thread(
        target=heartbeat_loop,
        args=(api_url, agent_key, agent_name, local_ip, interval),
        daemon=True,
    ).start()

    asyncio.run(run_tunnel(api_url, agent_key))


if __name__ == "__main__":
    main()
