# SmartHome Stack

Bu dizin Docker Compose ile calisan yerel akilli ev altyapisini icerir:

- Mosquitto (MQTT broker)
- n8n (otomasyon)
- Frigate (kamera olay algilama)

## Hizli Baslangic

```bash
docker compose up -d
```

Not: `.env` dosyasi zorunlu degildir. Isterseniz sonradan olusturup
`N8N_ENCRYPTION_KEY` gibi degerleri override edebilirsiniz.

## MQTT Notu

Mevcut kurulumda Mosquitto anonim erisime aciktir (hizli gelistirme modu).
Uretim asamasinda kullanici/parola + TLS'e gecilmesi tavsiye edilir.

## Servisler

- MQTT: `localhost:1883`
- n8n: `http://localhost:5678`
- Frigate: `http://localhost:5000`

## Notlar

- Image etiketleri sabitlenmistir; plansiz `latest` gecislerinden kacinilir.
- `n8n_data` ve benzeri runtime verileri yedeklenmelidir.
- Uretim ortami icin TLS, ACL ve gizli bilgi yonetimi (secret manager) eklenmelidir.

## Yedek Alma

```bash
./scripts/backup.sh
```
