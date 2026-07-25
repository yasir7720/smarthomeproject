Smart Home Project

Smart Home Project; akıllı ev cihazlarının kontrolünü, IP kamera takibini, kişi algılamayı ve otomasyon senaryolarını tek bir sistem altında toplamayı amaçlayan bir IoT projesidir.

Proje; Flutter mobil uygulaması, Python tabanlı servisler, MQTT haberleşmesi, kamera analiz bileşenleri ve Docker tabanlı altyapıdan oluşmaktadır.

🚧 Proje durumu: Aktif geliştirme aşamasındadır. Bazı özellikler deneysel olabilir ve üretim ortamı için ek güvenlik yapılandırmaları gerektirir.

Temel Özellikler

Oda ve cihaz bazlı akıllı ev kontrolü

MQTT üzerinden cihazlara komut gönderme

IP kamera ve canlı yayın görüntüleme

Frigate ile kişi algılama

Algılama olaylarının mobil uygulamaya aktarılması

FCM üzerinden anlık bildirim gönderimi

Eve dönüş ve evden çıkış gibi otomasyon senaryoları

Uzak ağdaki kameralara edge agent tüneli üzerinden erişim

Kullanıcı ve ev bazlı ayrılmış sistem yapısı

Proje Yapısı

smarthomeproject/
├── bulutsıstem/       # Güncel çok kullanıcılı platform ve mobil uygulama
├── komuta_merkezi/    # İlk Flutter tabanlı MQTT kontrol uygulaması
├── smarthome/         # Yerel ve deneysel Docker akıllı ev altyapısı
└── .claude/           # Geliştirme yardımcı dosyaları

bulutsıstem/

Projenin güncel ana platformudur. Backend, Flutter mobil uygulaması, MQTT altyapısı, kamera servisleri ve edge agent bileşenlerini içerir.

komuta_merkezi/

MQTT ile cihaz kontrolü, senaryo tetikleme ve MJPEG kamera görüntüleme özelliklerine sahip ilk Flutter istemcisidir.

smarthome/

Mosquitto, n8n ve Frigate servislerinden oluşan yerel geliştirme ve otomasyon ortamıdır.

Kullanılan Teknolojiler

Flutter ve Dart

Python

Docker Compose

PostgreSQL

Mosquitto MQTT

Frigate

go2rtc

n8n

Firebase Cloud Messaging

WebSocket

Genel Çalışma Akışı

Kamera
  ↓
go2rtc
  ↓
Frigate kişi algılama
  ↓
MQTT olay mesajı
  ↓
Backend API
  ↓
Flutter uygulaması ve FCM bildirimi

Cihaz kontrol akışı ise mobil uygulamadan gönderilen komutların API veya MQTT üzerinden ilgili akıllı ev cihazına iletilmesiyle çalışır.

Kurulum

Gereksinimler

Docker ve Docker Compose

Flutter SDK

Python 3

Git

Ana sistemi başlatma

git clone https://github.com/yasir7720/smarthomeproject.git
cd smarthomeproject/bulutsıstem
cp .env.example .env
docker compose up -d --build

Başlatılan temel servisler:

Servis

Port

Görev

API

8000

Kimlik doğrulama, cihaz, kamera ve otomasyon işlemleri

Adminer

8085

Veritabanı yönetimi

PostgreSQL

5433

Ana veritabanı

Frigate

5000

Kamera ve kişi algılama

go2rtc

1984

Canlı yayın aktarımı

Mosquitto

1884

MQTT haberleşmesi

Mobil uygulamayı çalıştırma

cd bulutsıstem/mobile
flutter pub get
flutter run

Yerel Deneysel Altyapı

Daha sade yerel sistemi çalıştırmak için:

cd smarthome
docker compose up -d

Bu yapı varsayılan olarak şu servisleri çalıştırır:

MQTT: localhost:1883

n8n: localhost:5678

Frigate: localhost:5000

Güvenlik Notları

.env dosyaları, API anahtarları ve servis hesabı dosyaları repoya eklenmemelidir.

Varsayılan geliştirme şifreleri üretim ortamında kullanılmamalıdır.

İnternet üzerinden erişim sağlanacaksa TLS, güçlü MQTT kimlik doğrulaması ve erişim kuralları etkinleştirilmelidir.

Yerel deneysel altyapıdaki anonim MQTT erişimi yalnızca geliştirme amacıyla kullanılmalıdır.

Geliştirme Durumu

Proje işlevsel prototipler ve güncel platform bileşenleri içermektedir. Ancak yayınlanabilir bir ürün hâline gelmeden önce test kapsamının artırılması, güvenlik ayarlarının sertleştirilmesi ve eski istemcilerle güncel platformun sadeleştirilmesi planlanmaktadır.

Planlanan Geliştirmeler

Otomatik test kapsamının artırılması

Mobil arayüzün geliştirilmesi

Kamera ve cihaz kurulum sürecinin kolaylaştırılması

TLS ve gelişmiş erişim kontrolü

Loglama ve hata izleme altyapısı

Kararlı sürüm ve kurulum belgeleri

Lisans

Bu proje için henüz açık kaynak lisansı belirlenmemiştir.
