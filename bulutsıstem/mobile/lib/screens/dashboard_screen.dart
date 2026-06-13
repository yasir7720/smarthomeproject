import 'package:flutter/material.dart';
import 'package:flutter_mjpeg/flutter_mjpeg.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../services/api_service.dart';
import '../services/mqtt_alarm_service.dart';
import '../services/push_service.dart';
import 'login_screen.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key, required this.token, required this.apiBase});

  final String token;
  final String apiBase;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  late ApiService api;
  String? tenantId;
  List<dynamic> cameras = [];
  List<dynamic> devices = [];
  List<dynamic> detections = [];
  Map<String, String> streamUrls = {};
  List<String> logs = [];
  bool loading = true;
  String? error;
  final MqttAlarmService mqttAlarm = MqttAlarmService();
  bool mqttAlarmConnected = false;
  final _mqttHost = TextEditingController(text: 'localhost');

  final _camName = TextEditingController(text: 'Telefon Kamerası');
  final _camUrl = TextEditingController(text: 'rtsp://192.168.1.50:554/stream');
  final _phoneIp = TextEditingController(text: '192.168.1.105');
  final _phonePort = TextEditingController(text: '8080');

  @override
  void initState() {
    super.initState();
    api = ApiService(baseUrl: widget.apiBase, token: widget.token);
    _mqttHost.text = Uri.parse(widget.apiBase).host;
    mqttAlarm.onLog = (msg) => _log(msg);
    mqttAlarm.onStateChanged = () {
      if (mounted) setState(() {});
    };
    _load();
  }

  @override
  void dispose() {
    mqttAlarm.disconnect();
    _mqttHost.dispose();
    super.dispose();
  }

  void _log(String msg) {
    setState(() => logs.insert(0, msg));
  }

  Future<void> _load() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final tenants = await api.listTenants();
      if (tenants.isEmpty) throw Exception('Ev bulunamadı');
      tenantId = tenants.first['id'] as String;
      cameras = await api.listCameras(tenantId!);
      devices = await api.listDevices(tenantId!);
      detections = await api.listDetections(tenantId!);
      await PushService.init(api);
      await _mqttAlarmBaglan();
      streamUrls.clear();
      for (final cam in cameras) {
        final tokenData = await api.getStreamToken(tenantId!, cam['id'] as String);
        streamUrls[cam['id'] as String] = tokenData['mjpeg_url'] as String;
      }
      _log('Veriler yüklendi');
    } catch (e) {
      error = e.toString();
    } finally {
      if (mounted) setState(() => loading = false);
    }
  }

  Future<void> _addCamera() async {
    if (tenantId == null) return;
    try {
      await api.addCamera(tenantId!, name: _camName.text.trim(), streamUrl: _camUrl.text.trim());
      _log('Kamera eklendi');
      await _load();
    } catch (e) {
      _log('Hata: $e');
    }
  }

  Future<void> _addIpWebcam() async {
    if (tenantId == null) return;
    try {
      final result = await api.addIpWebcam(
        tenantId!,
        phoneIp: _phoneIp.text.trim(),
        name: _camName.text.trim().isEmpty ? 'Telefon Kamerası' : _camName.text.trim(),
        port: int.tryParse(_phonePort.text.trim()) ?? 8080,
      );
      _log('IP Webcam: ${result['status']} — ${result['status_message']}');
      await _load();
    } catch (e) {
      _log('IP Webcam hata: $e');
    }
  }

  Future<void> _deleteCamera(String cameraId, String cameraName) async {
    if (tenantId == null) return;
    final onay = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Kamerayı Sil'),
        content: Text('"$cameraName" kaldırılsın mı?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('İptal')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Colors.red),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Sil'),
          ),
        ],
      ),
    );
    if (onay != true) return;
    try {
      await api.deleteCamera(tenantId!, cameraId);
      _log('Kamera silindi: $cameraName');
      await _load();
    } catch (e) {
      _log('Silme hatası: $e');
    }
  }

  Future<void> _mqttAlarmBaglan() async {
    if (tenantId == null) return;
    try {
      final creds = await api.getMqttCredentials(tenantId!);
      final host = _mqttHost.text.trim().isNotEmpty ? _mqttHost.text.trim() : creds['host'] as String;
      final port = creds['port'] as int;
      await mqttAlarm.connect(
        host: host,
        port: port,
        tenantId: tenantId!,
        username: creds['username'] as String,
        password: creds['password'] as String,
      );
      if (mounted) setState(() => mqttAlarmConnected = true);
      _log('MQTT alarm bağlantısı aktif ($host:$port)');
    } catch (e) {
      if (mounted) setState(() => mqttAlarmConnected = false);
      _log('MQTT alarm hatası: $e');
    }
  }

  Future<void> _toggleDevice(String deviceId, bool value) async {
    if (tenantId == null) return;
    try {
      await api.deviceCommand(tenantId!, deviceId, value);
      _log('Cihaz komutu gönderildi');
      await _load();
    } catch (e) {
      _log('Hata: $e');
    }
  }

  Future<void> _logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('token');
    if (!mounted) return;
    Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const LoginScreen()));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('BulutSistem'),
        actions: [
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
          IconButton(onPressed: _logout, icon: const Icon(Icons.logout)),
        ],
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : error != null
              ? Center(child: Text(error!, style: const TextStyle(color: Colors.red)))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      _section('Canlı Kameralar', [
                        if (cameras.isEmpty)
                          const Text('Henüz kamera yok')
                        else
                          ...cameras.map((cam) {
                            final id = cam['id'] as String;
                            final url = streamUrls[id];
                            final name = cam['name'] as String;
                            return Card(
                              child: Padding(
                                padding: const EdgeInsets.all(12),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Expanded(
                                          child: Text(name, style: const TextStyle(fontWeight: FontWeight.bold)),
                                        ),
                                        IconButton(
                                          tooltip: 'Kamerayı sil',
                                          icon: const Icon(Icons.delete_outline, color: Colors.redAccent),
                                          onPressed: () => _deleteCamera(id, name),
                                        ),
                                      ],
                                    ),
                                    Text('${cam['status']} — ${cam['status_message'] ?? ''}',
                                        style: const TextStyle(fontSize: 12)),
                                    const SizedBox(height: 8),
                                    if (url != null)
                                      AspectRatio(
                                        aspectRatio: 16 / 9,
                                        child: ClipRRect(
                                          borderRadius: BorderRadius.circular(8),
                                          child: Mjpeg(
                                            isLive: true,
                                            stream: url,
                                            error: (context, error, stack) =>
                                                const Center(child: Icon(Icons.videocam_off, color: Colors.red)),
                                          ),
                                        ),
                                      ),
                                  ],
                                ),
                              ),
                            );
                          }),
                        const SizedBox(height: 8),
                        const Text(
                          'IP Webcam (telefon uygulaması)',
                          style: TextStyle(fontWeight: FontWeight.w600),
                        ),
                        const Text(
                          'IP Webcam uygulamasını aç → sunucuyu başlat → telefon IP\'sini gir',
                          style: TextStyle(fontSize: 12, color: Colors.grey),
                        ),
                        const SizedBox(height: 8),
                        TextField(
                          controller: _camName,
                          decoration: const InputDecoration(labelText: 'Kamera adı', border: OutlineInputBorder()),
                        ),
                        const SizedBox(height: 8),
                        Row(
                          children: [
                            Expanded(
                              flex: 2,
                              child: TextField(
                                controller: _phoneIp,
                                decoration: const InputDecoration(
                                  labelText: 'Telefon IP',
                                  hintText: '192.168.1.105',
                                  border: OutlineInputBorder(),
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Expanded(
                              child: TextField(
                                controller: _phonePort,
                                keyboardType: TextInputType.number,
                                decoration: const InputDecoration(
                                  labelText: 'Port',
                                  border: OutlineInputBorder(),
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 8),
                        FilledButton.icon(
                          onPressed: _addIpWebcam,
                          icon: const Icon(Icons.smartphone),
                          label: const Text('IP Webcam Ekle'),
                        ),
                        const Divider(height: 24),
                        const Text('Manuel stream URL (RTSP/MJPEG)', style: TextStyle(fontWeight: FontWeight.w600)),
                        const SizedBox(height: 8),
                        TextField(
                          controller: _camUrl,
                          decoration: const InputDecoration(labelText: 'Stream URL', border: OutlineInputBorder()),
                        ),
                        const SizedBox(height: 8),
                        OutlinedButton(onPressed: _addCamera, child: const Text('Manuel Kamera Ekle')),
                      ]),
                      _section('Güvenlik Alarmı', [
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: mqttAlarm.personDetected
                                ? Colors.red.withValues(alpha: 0.15)
                                : Colors.green.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                              color: mqttAlarm.personDetected ? Colors.redAccent : Colors.green,
                            ),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                mqttAlarm.personDetected ? Icons.warning_amber : Icons.verified_user,
                                color: mqttAlarm.personDetected ? Colors.redAccent : Colors.green,
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  mqttAlarm.personDetected
                                      ? (mqttAlarm.alarmPlaying ? 'KİŞİ ALGILANDI — ALARM!' : 'Kişi algılandı')
                                      : (mqttAlarmConnected ? 'Güvenli — izleniyor' : 'MQTT bağlı değil'),
                                  style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    color: mqttAlarm.personDetected ? Colors.redAccent : Colors.green,
                                    fontSize: 12,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 8),
                        TextField(
                          controller: _mqttHost,
                          decoration: const InputDecoration(
                            labelText: 'MQTT Host (PC IP)',
                            hintText: '192.168.1.10 veya localhost',
                            border: OutlineInputBorder(),
                          ),
                        ),
                        const SizedBox(height: 8),
                        SwitchListTile(
                          title: const Text('Kişi algılanınca alarm çal'),
                          value: mqttAlarm.alarmEnabled,
                          onChanged: (v) async {
                            setState(() => mqttAlarm.alarmEnabled = v);
                            if (!v) await mqttAlarm.stopAlarm();
                          },
                        ),
                        if (mqttAlarm.alarmPlaying)
                          OutlinedButton.icon(
                            onPressed: () => mqttAlarm.stopAlarm(),
                            icon: const Icon(Icons.volume_off, color: Colors.redAccent),
                            label: const Text('Alarmı Sustur'),
                          ),
                        if (detections.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          const Text('Son algılamalar:', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 12)),
                          ...detections.take(5).map((d) => Text(
                                '${d['created_at']} — kişi: ${d['count']}',
                                style: const TextStyle(fontSize: 11, fontFamily: 'monospace'),
                              )),
                        ],
                      ]),
                      _section('Cihazlar', [
                        ...devices.map((d) => SwitchListTile(
                              title: Text('${d['room']} — ${d['name']}'),
                              subtitle: Text(d['mqtt_topic'] as String),
                              value: d['is_on'] as bool,
                              onChanged: (v) => _toggleDevice(d['id'] as String, v),
                            )),
                      ]),
                      _section('Otomasyon', [
                        ElevatedButton.icon(
                          onPressed: tenantId == null ? null : () async {
                            await api.scenarioHome(tenantId!);
                            _log('Eve dönüş tetiklendi');
                          },
                          icon: const Icon(Icons.home),
                          label: const Text('Eve Dönüş'),
                        ),
                        ElevatedButton.icon(
                          onPressed: tenantId == null ? null : () async {
                            await api.scenarioAway(tenantId!);
                            _log('Evden çıkış tetiklendi');
                          },
                          icon: const Icon(Icons.shield),
                          label: const Text('Evden Çıkış'),
                        ),
                        ElevatedButton.icon(
                          onPressed: tenantId == null ? null : () async {
                            await api.scenarioSchedule(tenantId!, '23:00:00', '07:00:00');
                            _log('Zaman penceresi kuruldu');
                          },
                          icon: const Icon(Icons.schedule),
                          label: const Text('Zaman Penceresi (23-07)'),
                        ),
                      ]),
                      _section('Loglar', [
                        ...logs.map((l) => Text(l, style: const TextStyle(fontFamily: 'monospace', fontSize: 12))),
                      ]),
                    ],
                  ),
                ),
    );
  }

  Widget _section(String title, List<Widget> children) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            ...children,
          ],
        ),
      ),
    );
  }
}
