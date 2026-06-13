# Komuta Merkezi

Flutter tabanli MQTT kontrol paneli ve kamera izleme uygulamasi.

## Ozellikler

- MQTT broker baglantisi ve komut gonderimi
- Oda bazli cihaz kontrolu
- Senaryo tetikleme (eve donus, evden cikis, zaman penceresi)
- MJPEG kamera yayini izleme

## Konfigurasyon

Uygulama varsayilan baglanti bilgilerini derleme zamani degiskenlerinden alir:

- `MQTT_HOST` (varsayilan: `127.0.0.1`)
- `MQTT_PORT` (varsayilan: `1883`)
- `CAMERA_URL` (varsayilan: `http://127.0.0.1:8080/video`)

Ornek calistirma:

```bash
flutter run \
  --dart-define=MQTT_HOST=192.168.1.20 \
  --dart-define=MQTT_PORT=1883 \
  --dart-define=CAMERA_URL=http://192.168.1.50:8080/video
```

## Platform Notlari

- Android icin internet izni `AndroidManifest.xml` icinde aktif.
- iOS tarafinda HTTP medya akisi icin `NSAllowsArbitraryLoadsInMedia` acik.
  Uretimde HTTPS kullanmaniz tavsiye edilir.

## Gelistirme

```bash
flutter pub get
flutter analyze
flutter test
```
