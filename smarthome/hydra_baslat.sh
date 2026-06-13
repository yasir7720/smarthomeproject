#!/bin/bash

echo "========================================"
echo "🤖 PROJECT HYDRA AKTİFLEŞTİRİLİYOR..."
echo "========================================"

# Varsa eski takılı kalmış Python ajanlarını temizle
pkill -f tv_ajani.py 2>/dev/null

# Docker Compose ile tüm arka plan sistemlerini (Frigate, n8n, MQTT) kaldır
echo "[1/2] Docker konteynerleri (Mosquitto, n8n, Frigate) kontrol ediliyor..."
sudo docker-compose -f /home/yasir/görüntüproje/smarthome/docker-compose.yml up -d

echo "[2/2] Masaüstü Ajanı (TV Simülasyonu) nöbete başlıyor..."
echo "Sistemi kapatmak için bu ekranda CTRL+C yapabilirsiniz."
echo "========================================"

# Python ajanını bu terminalde çalıştır (Böylece ekrana müdahale edebilir)
python3 /home/yasir/görüntüproje/smarthome/tv_ajani.py
