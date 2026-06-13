#!/bin/sh
set -e
echo "Mosquitto: MQTT kimlik dosyası bekleniyor..."
while [ ! -s /mosquitto/credentials/passwd ]; do
  sleep 2
done
echo "Mosquitto: kimlik doğrulama aktif, broker başlıyor."
exec /usr/sbin/mosquitto -c /mosquitto/config/mosquitto.conf
