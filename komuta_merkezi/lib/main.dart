import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_mjpeg/flutter_mjpeg.dart';
import 'package:flutter_ringtone_player/flutter_ringtone_player.dart';
import 'package:mqtt_client/mqtt_client.dart';
import 'package:mqtt_client/mqtt_server_client.dart';

const String _defaultMqttHost = '100.108.199.127';
const int _defaultMqttPort = 1883;
const String _defaultAlarmTopic = 'frigate/telefon_arka/person';
// SİBER DÜZELTME: Artık iki göz de doğrudan Frigate üzerinden (kutusuz saf yayın) alınıyor
const String _defaultTelefonUrl = 'http://100.108.199.127:5000/api/telefon_arka';
const String _defaultPcUrl = 'http://100.108.199.127:5000/api/pc_kamera';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const KomutaMerkeziApp());
}

class KomutaMerkeziApp extends StatefulWidget {
  const KomutaMerkeziApp({super.key});

  @override
  State<KomutaMerkeziApp> createState() => _KomutaMerkeziAppState();
}

class _KomutaMerkeziAppState extends State<KomutaMerkeziApp> {
  bool isDarkMode = true;

  void toggleTheme(bool value) {
    setState(() => isDarkMode = value);
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Kontrol Paneli',
      debugShowCheckedModeBanner: false,
      themeMode: isDarkMode ? ThemeMode.dark : ThemeMode.light,
      theme: ThemeData(
        brightness: Brightness.light,
        scaffoldBackgroundColor: const Color(0xFFF0F2F5),
        cardColor: Colors.white,
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0D0D12),
        cardColor: const Color(0xFF1A1A24),
        useMaterial3: true,
      ),
      home: DashboardScreen(isDarkMode: isDarkMode, onThemeChanged: toggleTheme),
    );
  }
}

class DashboardScreen extends StatefulWidget {
  final bool isDarkMode;
  final ValueChanged<bool> onThemeChanged;

  const DashboardScreen({super.key, required this.isDarkMode, required this.onThemeChanged});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  // MQTT İstemcisi
  MqttServerClient? mqttClient;
  StreamSubscription<List<MqttReceivedMessage<MqttMessage>>>? mqttSubscription;
  bool isMqttConnected = false;
  List<String> sistemLoglari = [];

  // Güvenlik alarmı (Frigate kişi algılama)
  bool alarmAktif = true;
  bool kisiAlgilandi = false;
  bool alarmCaliyor = false;
  final TextEditingController alarmTopicController = TextEditingController(text: _defaultAlarmTopic);
  String alarmTopic = _defaultAlarmTopic;

  // Cihaz Durumları ve Arayüz Değişkenleri
  bool salonLamba = false;
  bool salonTvPriz = false;
  bool yatakOdasiLamba = false;
  bool mutfakPriz = false;
  
  final TextEditingController mqttHostController = TextEditingController(text: _defaultMqttHost);
  final TextEditingController mqttPortController = TextEditingController(text: _defaultMqttPort.toString());
  final TextEditingController telefonUrlController = TextEditingController(text: _defaultTelefonUrl);
  final TextEditingController pcUrlController = TextEditingController(text: _defaultPcUrl);
  
  String mqttHost = _defaultMqttHost;
  int mqttPort = _defaultMqttPort;
  String telefonUrl = _defaultTelefonUrl;
  String pcUrl = _defaultPcUrl;

  TimeOfDay ozelBaslangic = const TimeOfDay(hour: 23, minute: 0);
  TimeOfDay ozelBitis = const TimeOfDay(hour: 07, minute: 0);

  Color get anaRenk => widget.isDarkMode ? Colors.cyanAccent : Colors.cyan.shade800;

  @override
  void initState() {
    super.initState();
    _sistemiBaslat();
  }

  // --- 1. MQTT MOTORU VE LOG SİSTEMİ ---
  Future<void> _sistemiBaslat() async {
    mqttClient?.disconnect();
    mqttClient = MqttServerClient(mqttHost, '');
    mqttClient!.port = mqttPort;
    mqttClient!.logging(on: false);
    mqttClient!.keepAlivePeriod = 20;

    final connMess = MqttConnectMessage().withClientIdentifier('hydra_mobil_komuta').startClean();
    mqttClient!.connectionMessage = connMess;

    try {
      _logEkle("[MQTT] $mqttHost:$mqttPort aranıyor...");
      await mqttClient!.connect();
    } catch (e) {
      _logEkle("[MQTT] Bağlantı Hatası: $e", isError: true);
      mqttClient!.disconnect();
    }

    if (mqttClient!.connectionStatus!.state == MqttConnectionState.connected) {
      setState(() => isMqttConnected = true);
      _logEkle("[MQTT] Bağlantı BAŞARILI. Ajan aktif.");
      _alarmDinleyicisiBaslat();
    } else {
      setState(() => isMqttConnected = false);
      _logEkle("[MQTT] Bağlantı REDDEDİLDİ.", isError: true);
    }
  }

  void _alarmDinleyicisiBaslat() {
    if (mqttClient == null || mqttClient!.connectionStatus?.state != MqttConnectionState.connected) {
      return;
    }
    mqttSubscription?.cancel();
    mqttClient!.subscribe(alarmTopic, MqttQos.atLeastOnce);
    mqttSubscription = mqttClient!.updates?.listen((messages) {
      for (final msg in messages) {
        final topic = msg.topic;
        if (topic != alarmTopic) continue;
        final payload = msg.payload as MqttPublishMessage;
        final text = MqttPublishPayload.bytesToStringAsString(payload.payload.message);
        _kisiiAlgilamaIsle(text);
      }
    });
    _logEkle("[ALARM] Dinleniyor: $alarmTopic");
  }

  void _kisiiAlgilamaIsle(String payload) {
    final sayi = int.tryParse(payload.trim()) ?? 0;
    if (!alarmAktif) return;

    if (sayi > 0 && !kisiAlgilandi) {
      setState(() => kisiAlgilandi = true);
      _logEkle("[ALARM] Kişi algılandı! ($sayi)", isError: true);
      _alarmCal();
    } else if (sayi == 0 && kisiAlgilandi) {
      setState(() => kisiAlgilandi = false);
      _logEkle("[ALARM] Kadraj temiz — alarm durdu.");
      _alarmDurdur();
    }
  }

  Future<void> _alarmCal() async {
    if (alarmCaliyor) return;
    alarmCaliyor = true;
    try {
      await FlutterRingtonePlayer().playAlarm(looping: true, asAlarm: true, volume: 1.0);
    } catch (e) {
      _logEkle("[ALARM] Ses hatası: $e", isError: true);
      alarmCaliyor = false;
    }
  }

  Future<void> _alarmDurdur() async {
    if (!alarmCaliyor) return;
    try {
      await FlutterRingtonePlayer().stop();
    } catch (_) {}
    alarmCaliyor = false;
  }

  void _baglantiyiKaydetVeUygula() {
    setState(() {
      mqttHost = mqttHostController.text.trim();
      mqttPort = int.tryParse(mqttPortController.text.trim()) ?? 1883;
      telefonUrl = telefonUrlController.text.trim();
      pcUrl = pcUrlController.text.trim();
      alarmTopic = alarmTopicController.text.trim();
      isMqttConnected = false;
    });
    _alarmDurdur();
    _sistemiBaslat();
  }

  void _komutGonder(String topic, String mesaj) {
    if (mqttClient == null || mqttClient!.connectionStatus!.state != MqttConnectionState.connected) {
      _logEkle("[MQTT_ERR] Çevrimdışı. Komut iletilemedi.", isError: true);
      return;
    }
    final builder = MqttClientPayloadBuilder();
    builder.addString(mesaj);
    mqttClient!.publishMessage(topic, MqttQos.atLeastOnce, builder.payload!);
    _logEkle("[PUB] $topic -> $mesaj");
  }

  void _logEkle(String mesaj, {bool isError = false}) {
    if (!mounted) return;
    setState(() {
      final saat = "${TimeOfDay.now().hour.toString().padLeft(2, '0')}:${TimeOfDay.now().minute.toString().padLeft(2, '0')}";
      sistemLoglari.insert(0, "> [$saat] $mesaj");
      if (sistemLoglari.length > 50) sistemLoglari.removeLast(); 
    });
  }

  // --- 2. N8N KİŞİSEL ZAMAN PENCERESİ ---
  void _kisiselZamanPenceresiAc() {
    showDialog(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return AlertDialog(
              backgroundColor: widget.isDarkMode ? const Color(0xFF1A1A24) : Colors.white,
              title: Row(
                children: [
                  Icon(Icons.schedule, color: widget.isDarkMode ? Colors.orangeAccent : Colors.orange.shade800),
                  const SizedBox(width: 10),
                  Text("Kişisel Zaman Tercihi", style: TextStyle(color: widget.isDarkMode ? Colors.orangeAccent : Colors.orange.shade800, fontSize: 18)),
                ],
              ),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text("Belirtilen saatler arasında tüm güç kesilecek ve otomasyon devreye girecektir.", style: TextStyle(color: widget.isDarkMode ? Colors.white70 : Colors.black87, fontSize: 13), textAlign: TextAlign.center),
                  const SizedBox(height: 20),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      InkWell(
                        onTap: () async {
                          final secilen = await showTimePicker(context: context, initialTime: ozelBaslangic);
                          if (secilen != null) setDialogState(() => ozelBaslangic = secilen);
                        },
                        child: _buildSaatKutusu("Gücü Kes", ozelBaslangic.format(context), widget.isDarkMode ? Colors.redAccent : Colors.red.shade700),
                      ),
                      const Icon(Icons.arrow_forward_ios, color: Colors.grey, size: 16),
                      InkWell(
                        onTap: () async {
                          final secilen = await showTimePicker(context: context, initialTime: ozelBitis);
                          if (secilen != null) setDialogState(() => ozelBitis = secilen);
                        },
                        child: _buildSaatKutusu("Gücü Ver", ozelBitis.format(context), widget.isDarkMode ? Colors.greenAccent : Colors.green.shade700),
                      ),
                    ],
                  ),
                ],
              ),
              actions: [
                TextButton(onPressed: () => Navigator.pop(context), child: const Text("İPTAL", style: TextStyle(color: Colors.grey))),
                ElevatedButton(
                  style: ElevatedButton.styleFrom(backgroundColor: widget.isDarkMode ? Colors.orangeAccent : Colors.orange.shade700, foregroundColor: widget.isDarkMode ? Colors.black : Colors.white),
                  onPressed: () {
                    _komutGonder("ev/otomasyon/zaman", '{"baslangic": "${ozelBaslangic.hour.toString().padLeft(2, '0')}:${ozelBaslangic.minute.toString().padLeft(2, '0')}:00", "bitis": "${ozelBitis.hour.toString().padLeft(2, '0')}:${ozelBitis.minute.toString().padLeft(2, '0')}:00"}');
                    Navigator.pop(context);
                  },
                  child: const Text("ZAMANI KUR"),
                ),
              ],
            );
          }
        );
      },
    );
  }

  Widget _buildSaatKutusu(String baslik, String saat, Color renk) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: widget.isDarkMode ? Colors.black45 : Colors.grey.shade100, borderRadius: BorderRadius.circular(8), border: Border.all(color: renk.withOpacity(0.5))),
      child: Column(
        children: [
          Text(baslik, style: TextStyle(color: renk, fontSize: 10, fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          Text(saat, style: TextStyle(color: widget.isDarkMode ? Colors.white : Colors.black87, fontSize: 18, fontWeight: FontWeight.bold)),
        ],
      ),
    );
  }

  // --- 3. ANA ARAYÜZ (TÜM PANELLER) ---
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('KONTROL PANELİ', style: TextStyle(letterSpacing: 2.0, color: anaRenk, fontWeight: FontWeight.bold)),
            const SizedBox(width: 10),
            Icon(Icons.circle, size: 12, color: isMqttConnected ? Colors.greenAccent : Colors.redAccent),
          ],
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
      ),
      body: ListView(
        padding: const EdgeInsets.all(12.0),
        children: [
          
          // ARKA PLAN YAYIN DURUMU YERİNE SİSTEM DURUMU
          Container(
            padding: const EdgeInsets.all(12),
            margin: const EdgeInsets.only(bottom: 16),
            decoration: BoxDecoration(color: Colors.green.withOpacity(0.1), borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.green)),
            child: const Row(
              children: [
                Icon(Icons.rocket_launch, color: Colors.green),
                SizedBox(width: 10),
                Expanded(child: Text("Sistem Jilet Gibi: Yükler Frigate'e Devredildi.", style: TextStyle(color: Colors.green, fontWeight: FontWeight.bold, fontSize: 12))),
              ],
            ),
          ),

          // 1. KART: PROFİL VE AYARLAR
          _buildSiberKart(
            baslik: "PROFİL & BAĞLANTI AYARLARI",
            ikon: Icons.person,
            icerik: Column(
              children: [
                Row(
                  children: [
                    Expanded(child: TextField(controller: mqttHostController, decoration: _siberInputGorev("MQTT IP", Icons.link))),
                    const SizedBox(width: 12),
                    Expanded(child: TextField(controller: mqttPortController, keyboardType: TextInputType.number, decoration: _siberInputGorev("Port", Icons.electrical_services))),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(child: TextField(controller: telefonUrlController, decoration: _siberInputGorev("Telefon URL (Frigate)", Icons.smartphone))),
                    const SizedBox(width: 12),
                    Expanded(child: TextField(controller: pcUrlController, decoration: _siberInputGorev("Sunucu URL (Frigate)", Icons.computer))),
                  ],
                ),
                const SizedBox(height: 12),
                Container(
                  decoration: BoxDecoration(color: widget.isDarkMode ? Colors.black26 : Colors.grey.shade100, border: Border.all(color: anaRenk.withOpacity(0.3)), borderRadius: BorderRadius.circular(8)),
                  child: SwitchListTile(title: Text("Karanlık Tema", style: TextStyle(fontSize: 14, color: widget.isDarkMode ? Colors.white : Colors.black87)), secondary: Icon(widget.isDarkMode ? Icons.dark_mode : Icons.light_mode, color: anaRenk), activeColor: anaRenk, value: widget.isDarkMode, onChanged: widget.onThemeChanged),
                ),
                const SizedBox(height: 12),
                ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(backgroundColor: anaRenk, foregroundColor: widget.isDarkMode ? Colors.black : Colors.white, minimumSize: const Size(double.infinity, 45), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
                  onPressed: _baglantiyiKaydetVeUygula,
                  icon: const Icon(Icons.save),
                  label: const Text("KAYDET VE UYGULA", style: TextStyle(fontWeight: FontWeight.bold)),
                ),
              ],
            ),
          ),

          // 2. KART: CANLI GÖRÜNTÜ (FRIGATE ÇİFT GÖZ)
          _buildSiberKart(
            baslik: "CANLI GÖRÜNTÜ",
            ikon: Icons.visibility,
            icerik: Row(
              children: [
                // --- SOL: TELEFON KAMERASI (FRIGATE YAYINI) ---
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: Container(
                      decoration: BoxDecoration(border: Border.all(color: anaRenk.withOpacity(0.5))),
                      child: AspectRatio(
                        aspectRatio: 16 / 9,
                        child: Mjpeg(
                          isLive: true,
                          error: (context, error, stack) => const Center(child: Icon(Icons.broken_image, color: Colors.redAccent)),
                          stream: telefonUrl,
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                // --- SAĞ: PC KAMERASI (FRIGATE YAYINI) ---
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: Container(
                      decoration: BoxDecoration(border: Border.all(color: anaRenk.withOpacity(0.5))),
                      child: AspectRatio(
                        aspectRatio: 16 / 9,
                        child: Mjpeg(
                          isLive: true,
                          error: (context, error, stack) => const Center(child: Icon(Icons.broken_image, color: Colors.redAccent)),
                          stream: pcUrl,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),

          // 3. KART: GÜVENLİK ALARMI (TELEFON KAMERASI)
          _buildSiberKart(
            baslik: "GÜVENLİK ALARMI — TELEFON KAMERASI",
            ikon: Icons.notifications_active,
            icerik: Column(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: kisiAlgilandi ? Colors.red.withOpacity(0.15) : Colors.green.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: kisiAlgilandi ? Colors.redAccent : Colors.green),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        kisiAlgilandi ? Icons.warning_amber_rounded : Icons.verified_user,
                        color: kisiAlgilandi ? Colors.redAccent : Colors.green,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          kisiAlgilandi
                              ? (alarmCaliyor ? "KİŞİ ALGILANDI — ALARM ÇALIYOR!" : "Kişi algılandı")
                              : "Güvenli — hareket yok",
                          style: TextStyle(
                            color: kisiAlgilandi ? Colors.redAccent : Colors.green,
                            fontWeight: FontWeight.bold,
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: alarmTopicController,
                  decoration: _siberInputGorev("Frigate MQTT Topic", Icons.sensors),
                ),
                const SizedBox(height: 8),
                SwitchListTile(
                  title: Text("Alarm açık", style: TextStyle(fontSize: 14, color: widget.isDarkMode ? Colors.white : Colors.black87)),
                  subtitle: const Text("Frigate kişi algılayınca telefon alarmı çalar", style: TextStyle(fontSize: 11)),
                  value: alarmAktif,
                  activeColor: anaRenk,
                  onChanged: (val) async {
                    setState(() => alarmAktif = val);
                    if (!val) {
                      setState(() => kisiAlgilandi = false);
                      await _alarmDurdur();
                      _logEkle("[ALARM] Kullanıcı tarafından kapatıldı.");
                    } else {
                      _logEkle("[ALARM] Aktif.");
                    }
                  },
                ),
                if (alarmCaliyor)
                  OutlinedButton.icon(
                    onPressed: _alarmDurdur,
                    icon: const Icon(Icons.volume_off, color: Colors.redAccent),
                    label: const Text("Alarmı Sustur", style: TextStyle(color: Colors.redAccent)),
                  ),
              ],
            ),
          ),

          // 4. KART: DONANIM KONTROL
          _buildSiberKart(
            baslik: "DONANIM KONTROL",
            ikon: Icons.power,
            icerik: Column(
              children: [
                ExpansionTile(
                  title: Text("Salon", style: TextStyle(color: widget.isDarkMode ? Colors.white : Colors.black87)),
                  leading: Icon(Icons.weekend, color: anaRenk, size: 20),
                  iconColor: anaRenk,
                  collapsedIconColor: Colors.grey,
                  children: [
                    _buildCihazAnahtari("Ana Lamba", salonLamba, (val) { setState(() => salonLamba = val); _komutGonder('ev/salon/lamba', val ? '{"durum":"acik"}' : '{"durum":"kapali"}'); }),
                    _buildCihazAnahtari("TV Priz", salonTvPriz, (val) { setState(() => salonTvPriz = val); _komutGonder('ev/salon/tv', val ? '{"durum":"acik"}' : '{"durum":"kapali"}'); }),
                  ],
                ),
                ExpansionTile(
                  title: Text("Yatak Odası", style: TextStyle(color: widget.isDarkMode ? Colors.white : Colors.black87)),
                  leading: Icon(Icons.bed, color: anaRenk, size: 20),
                  iconColor: anaRenk,
                  collapsedIconColor: Colors.grey,
                  children: [
                    _buildCihazAnahtari("Tavan Lambası", yatakOdasiLamba, (val) { setState(() => yatakOdasiLamba = val); _komutGonder('ev/yatakodasi/lamba', val ? '{"durum":"acik"}' : '{"durum":"kapali"}'); }),
                  ],
                ),
                ExpansionTile(
                  title: Text("Mutfak", style: TextStyle(color: widget.isDarkMode ? Colors.white : Colors.black87)),
                  leading: Icon(Icons.kitchen, color: anaRenk, size: 20),
                  iconColor: anaRenk,
                  collapsedIconColor: Colors.grey,
                  children: [
                    _buildCihazAnahtari("Kahve Makinesi", mutfakPriz, (val) { setState(() => mutfakPriz = val); _komutGonder('ev/mutfak/priz', val ? '{"durum":"acik"}' : '{"durum":"kapali"}'); }),
                  ],
                ),
              ],
            ),
          ),

          // 4. KART: N8N OTOMASYON
          _buildSiberKart(
            baslik: "N8N OTOMASYON",
            ikon: Icons.hub_outlined,
            icerik: Column(
              children: [
                _buildGucButonu(metin: "Eve Dönüş (Tüm Gücü Ver)", ikon: Icons.home, renk: widget.isDarkMode ? Colors.greenAccent : Colors.green.shade700, onPressed: () => _komutGonder('ev/senaryo/evedonus', '{"tetikleyici":"aktif"}')),
                const SizedBox(height: 12),
                _buildGucButonu(metin: "Evden Çıkış (Tüm Gücü Kes)", ikon: Icons.shield, renk: widget.isDarkMode ? Colors.redAccent : Colors.red.shade700, onPressed: () => _komutGonder('ev/senaryo/evdencikis', '{"tetikleyici":"aktif"}')),
                const SizedBox(height: 12),
                _buildGucButonu(metin: "Kişisel Zaman Tercihi", ikon: Icons.schedule, renk: widget.isDarkMode ? Colors.orangeAccent : Colors.orange.shade700, onPressed: _kisiselZamanPenceresiAc),
              ],
            ),
          ),

          // 5. KART: SİSTEM LOGLARI
          _buildSiberKart(
            baslik: "SİSTEM LOGLARI",
            ikon: Icons.terminal,
            icerik: Container(
              height: 150,
              width: double.infinity,
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(color: Colors.black, borderRadius: BorderRadius.circular(8)),
              child: SingleChildScrollView(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: sistemLoglari.map((logStr) {
                    final isErr = logStr.contains("[MQTT_ERR]") || logStr.contains("Exception") || logStr.contains("REDDEDİLDİ");
                    return Text(logStr, style: TextStyle(color: isErr ? Colors.redAccent : Colors.greenAccent, fontFamily: 'monospace', fontSize: 12));
                  }).toList(),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // --- YARDIMCI WIDGET'LAR ---
  InputDecoration _siberInputGorev(String etiket, IconData ikon) {
    return InputDecoration(
      labelText: etiket, labelStyle: TextStyle(color: widget.isDarkMode ? Colors.grey : Colors.black54, fontSize: 12), prefixIcon: Icon(ikon, color: anaRenk, size: 18), filled: true, fillColor: widget.isDarkMode ? Colors.black26 : Colors.grey.shade100, enabledBorder: OutlineInputBorder(borderSide: BorderSide(color: anaRenk.withOpacity(0.3))), focusedBorder: OutlineInputBorder(borderSide: BorderSide(color: anaRenk)), contentPadding: const EdgeInsets.symmetric(vertical: 0, horizontal: 10),
    );
  }

  Widget _buildGucButonu({required String metin, required IconData ikon, required Color renk, required VoidCallback onPressed}) {
    return ElevatedButton(
      style: ElevatedButton.styleFrom(backgroundColor: widget.isDarkMode ? Colors.black45 : Colors.grey.shade100, foregroundColor: renk, side: BorderSide(color: renk.withOpacity(0.5)), minimumSize: const Size(double.infinity, 45), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)), elevation: 0),
      onPressed: onPressed, child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [Icon(ikon, size: 20), const SizedBox(width: 10), Text(metin, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14))]),
    );
  }

  Widget _buildCihazAnahtari(String isim, bool durum, ValueChanged<bool> onChange) {
    return SwitchListTile(title: Text(isim, style: TextStyle(fontSize: 13, color: widget.isDarkMode ? Colors.white : Colors.black87)), activeColor: anaRenk, value: durum, onChanged: onChange, dense: true, contentPadding: const EdgeInsets.symmetric(horizontal: 32.0));
  }

  Widget _buildSiberKart({required String baslik, required IconData ikon, required Widget icerik}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(color: Theme.of(context).cardColor, borderRadius: BorderRadius.circular(16), border: Border.all(color: anaRenk.withOpacity(0.3), width: 1)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch, mainAxisSize: MainAxisSize.min,
        children: [
          Container(padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 12), decoration: BoxDecoration(color: widget.isDarkMode ? Colors.black38 : Colors.grey.shade200, borderRadius: const BorderRadius.only(topLeft: Radius.circular(16), topRight: Radius.circular(16))), child: Row(children: [Icon(ikon, size: 16, color: anaRenk), const SizedBox(width: 8), Text(baslik, style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: widget.isDarkMode ? Colors.white70 : Colors.black87))])),
          Padding(padding: const EdgeInsets.all(16.0), child: icerik),
        ],
      ),
    );
  }

  @override
  void dispose() {
    mqttSubscription?.cancel();
    _alarmDurdur();
    mqttClient?.disconnect();
    alarmTopicController.dispose();
    super.dispose();
  }
}