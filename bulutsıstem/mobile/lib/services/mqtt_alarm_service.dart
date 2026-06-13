import 'dart:async';

import 'package:flutter_ringtone_player/flutter_ringtone_player.dart';
import 'package:mqtt_client/mqtt_client.dart';
import 'package:mqtt_client/mqtt_server_client.dart';

class MqttAlarmService {
  MqttServerClient? _client;
  StreamSubscription? _subscription;
  bool alarmEnabled = true;
  bool personDetected = false;
  bool alarmPlaying = false;
  void Function(String message)? onLog;
  void Function()? onStateChanged;

  Future<void> connect({
    required String host,
    required int port,
    required String tenantId,
    required String username,
    required String password,
  }) async {
    await disconnect();
    _client = MqttServerClient(host, '');
    _client!.port = port;
    _client!.keepAlivePeriod = 20;
    _client!.logging(on: false);
    _client!.connectionMessage = MqttConnectMessage()
        .withClientIdentifier('bulutsistem_alarm_$tenantId')
        .authenticateAs(username, password)
        .startClean();

    await _client!.connect();
    if (_client!.connectionStatus?.state != MqttConnectionState.connected) {
      throw Exception('MQTT bağlantısı kurulamadı');
    }

    final topic = 't/$tenantId/cameras/+/person';
    _client!.subscribe(topic, MqttQos.atLeastOnce);
    _log('Alarm dinleyici: $topic (kimlik doğrulamalı)');

    _subscription = _client!.updates?.listen((messages) {
      for (final msg in messages) {
        final payload = msg.payload as MqttPublishMessage;
        final text = MqttPublishPayload.bytesToStringAsString(payload.payload.message);
        _handlePerson(text);
      }
    });
  }

  void _handlePerson(String payload) {
    if (!alarmEnabled) return;
    final count = int.tryParse(payload.trim()) ?? 0;
    if (count > 0 && !personDetected) {
      personDetected = true;
      onStateChanged?.call();
      _log('Kişi algılandı! Alarm çalıyor...');
      _playAlarm();
    } else if (count == 0 && personDetected) {
      personDetected = false;
      onStateChanged?.call();
      _log('Kadraj temiz — alarm durdu.');
      stopAlarm();
    }
  }

  Future<void> _playAlarm() async {
    if (alarmPlaying) return;
    alarmPlaying = true;
    onStateChanged?.call();
    try {
      await FlutterRingtonePlayer().playAlarm(looping: true, asAlarm: true, volume: 1.0);
    } catch (e) {
      _log('Alarm ses hatası: $e');
      alarmPlaying = false;
    }
  }

  Future<void> stopAlarm() async {
    if (!alarmPlaying) return;
    try {
      await FlutterRingtonePlayer().stop();
    } catch (_) {}
    alarmPlaying = false;
    onStateChanged?.call();
  }

  Future<void> disconnect() async {
    await _subscription?.cancel();
    _subscription = null;
    _client?.disconnect();
    _client = null;
    await stopAlarm();
    personDetected = false;
  }

  void _log(String msg) => onLog?.call(msg);
}
