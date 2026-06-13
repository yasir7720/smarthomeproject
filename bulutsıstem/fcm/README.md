# Firebase Cloud Messaging (FCM)

Push bildirim için Firebase service account dosyasını buraya koyun:

```
bulutsıstem/fcm/service-account.json
```

Sonra `.env` veya `docker-compose.yml` içinde:

```
FCM_ENABLED=true
FCM_CREDENTIALS_PATH=/app/fcm/service-account.json
```

Mobil uygulama için gerçek Firebase projesi:

```bash
cd mobile
dart pub global activate flutterfire_cli
flutterfire configure
```

Bu komut `lib/firebase_options.dart` ve `android/app/google-services.json` dosyalarını günceller.
