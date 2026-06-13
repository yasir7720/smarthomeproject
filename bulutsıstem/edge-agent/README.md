# BulutSistem Edge Agent

Ev içi kameraları buluta bağlar. Farklı ağdaki kullanıcılar için **WebSocket tüneli** ile kamera yayını sağlar.

## Kurulum

```bash
cd edge-agent
cp config.example.yaml config.yaml
pip install -r requirements.txt
```

`config.yaml` içine Adminer veya `GET /tenants/{id}/edge/info` ile aldığınız `edge_agent_key` değerini yazın.

## Çalıştırma

```bash
# Tünel + heartbeat (sürekli)
python agent.py

# Tek seferlik kayıt (tünel olmadan)
python agent.py --once
```

## Tünel nasıl çalışır?

```
Telefon IP Webcam (ev WiFi)
    ↓
Edge Agent (evdeki PC / Raspberry Pi)
    ↓ WebSocket tünel
BulutSistem API → go2rtc → Frigate → Alarm
```

`tunnel.enabled: true` olduğunda agent buluta outbound WebSocket açar. Bulut, kameraya doğrudan erişemediğinde yayını tünel üzerinden çeker.

## Yapılandırma

| Alan | Açıklama |
|------|----------|
| `api_url` | BulutSistem API, örn. `http://192.168.1.10:8000/api/v1` |
| `edge_agent_key` | Tenant edge anahtarı |
| `ip_webcam.phone_ip` | Telefonun yerel IP'si |
| `tunnel.enabled` | `true` = tünel aktif |
