# BulutSistem

Çok kullanıcılı akıllı ev ve IP kamera platformu.

## Bileşenler

| Servis | Port | Görev |
|--------|------|-------|
| **API** | 8000 | Auth, tenant, kamera, cihaz, otomasyon, algılama, tünel |
| **Adminer** | 8085 | Veritabanı tarayıcı |
| **PostgreSQL** | 5433 | Veritabanı |
| **go2rtc** | 1984 | Canlı yayın proxy |
| **Frigate** | 5000 | Kişi algılama (AI) |
| **Mosquitto** | 1884 | MQTT (kimlik doğrulamalı) |
| **mobile/** | — | Flutter uygulama |

## Başlatma

```bash
cd bulutsıstem
docker-compose up -d --build
```

- API: http://localhost:8000/docs
- Adminer: http://localhost:8085
- Frigate: http://localhost:5000

## Güvenlik Özellikleri

### MQTT Kimlik Doğrulama
- Her tenant'ın kendi `mqtt_username` / `mqtt_password` değeri var
- Mosquitto ACL: tenant sadece `t/{tenant_id}/#` okuyabilir
- Servis hesabı (`bulut_service`) API bridge için
- Frigate hesabı (`bulut_frigate`) sadece `frigate/#` yazar

Mobil uygulama MQTT'ye tenant kimlik bilgileriyle bağlanır.

### FCM Push Bildirim
Kişi algılandığında uygulama kapalıyken bile bildirim gönderir.

Kurulum: [fcm/README.md](fcm/README.md)

```
FCM_ENABLED=true
# fcm/service-account.json dosyasını ekle
docker-compose up -d --build
```

Mobil: `flutterfire configure` ile Firebase projesini bağla.

### Edge Agent Tüneli
Ev dışından kamera erişimi için edge agent outbound WebSocket tüneli açar.

```bash
cd edge-agent && cp config.example.yaml config.yaml
# edge_agent_key ve phone_ip ayarla, tunnel.enabled: true
pip install -r requirements.txt && python agent.py
```

## Kişi Algılama Akışı

```
Kamera → (tünel) → go2rtc → Frigate (person) → MQTT frigate/{key}/person
    → API bridge → t/{tenant}/cameras/{id}/person
    → Mobil MQTT alarm + FCM push
```

## Mobil Uygulama

```bash
cd mobile && flutter pub get && flutter run
```

- **MQTT Host:** PC'nin yerel IP'si (telefon) veya `localhost` (emülatör: `10.0.2.2`)
- MQTT kullanıcı/şifre API'den otomatik alınır

## API Özeti

- `POST /auth/register` — Kayıt
- `POST /auth/push-token` — FCM token kaydı
- `GET /tenants/{id}/mqtt-credentials` — MQTT kimlik bilgisi
- `GET /tenants/{id}/edge/tunnel/status` — Tünel durumu
- `WS /edge/tunnel/ws` — Edge agent tüneli (X-Agent-Key)
- `GET /tenants/{id}/detections` — Algılama geçmişi

## Plan Limitleri

| Plan | Kamera | Cihaz |
|------|--------|-------|
| free | 3 | 10 |
| pro | 20 | 50 |

## Ortam Değişkenleri

`.env.example` dosyasına bakın. Önemli olanlar:

| Değişken | Varsayılan | Açıklama |
|----------|------------|----------|
| `MQTT_SERVICE_PASSWORD` | dev_service_mqtt_secret | API MQTT hesabı |
| `TUNNEL_INTERNAL_KEY` | dev_tunnel_internal_key | Dahili tünel anahtarı |
| `FCM_ENABLED` | false | Push bildirim |
