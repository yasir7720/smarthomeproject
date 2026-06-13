import paho.mqtt.client as mqtt
import webbrowser
import os
import time

OYUN_PORTALI = "file:///home/yasir/bulut-oyun/index.html"
tv_acik = False

def on_connect(client, userdata, flags, rc):
    print("🎮 Hayalet Ajan Nöbette! Frigate dinleniyor...")
    client.subscribe("frigate/pc_kamera/person")

def on_message(client, userdata, msg):
    global tv_acik
    kisi_sayisi = int(msg.payload.decode())
    
    if kisi_sayisi > 0 and not tv_acik:
        print("🚀 HEDEF TESPİT EDİLDİ! Oyun portalı açılıyor...")
        webbrowser.open_new_tab(OYUN_PORTALI)
        tv_acik = True
        
    elif kisi_sayisi == 0 and tv_acik:
        print("💤 Kadraj boşaldı. RetroCloud sekmesi kapatılıyor...")
        # GÜNCELLENEN FÜZE: Hedefi bul, öne getir ve CTRL+W'yi çak!
        os.system('xdotool search --name "RetroCloud" windowactivate --sync key ctrl+w 2>/dev/null')
        tv_acik = False

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("127.0.0.1", 1883, 60)
client.loop_forever()
