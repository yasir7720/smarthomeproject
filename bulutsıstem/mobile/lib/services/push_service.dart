import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_ringtone_player/flutter_ringtone_player.dart';

import '../firebase_options.dart';
import 'api_service.dart';

final FlutterLocalNotificationsPlugin _localNotifications = FlutterLocalNotificationsPlugin();

@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  if (message.data['type'] == 'person_detected') {
    await FlutterRingtonePlayer().playAlarm(looping: true, asAlarm: true, volume: 1.0);
  }
}

class PushService {
  static bool initialized = false;

  static Future<void> init(ApiService api) async {
    if (initialized) return;
    try {
      await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
      FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);

      await _localNotifications.initialize(
        const InitializationSettings(
          android: AndroidInitializationSettings('@mipmap/ic_launcher'),
        ),
      );

      final messaging = FirebaseMessaging.instance;
      await messaging.requestPermission(alert: true, badge: true, sound: true);

      final token = await messaging.getToken();
      if (token != null) {
        await api.registerPushToken(token);
        debugPrint('FCM token kaydedildi');
      }

      FirebaseMessaging.onMessage.listen((message) async {
        final title = message.notification?.title ?? 'Güvenlik Alarmı';
        final body = message.notification?.body ?? 'Kişi algılandı';
        await _localNotifications.show(
          DateTime.now().millisecondsSinceEpoch ~/ 1000,
          title,
          body,
          const NotificationDetails(
            android: AndroidNotificationDetails(
              'security_alarm',
              'Güvenlik Alarmı',
              importance: Importance.max,
              priority: Priority.high,
            ),
          ),
        );
        if (message.data['type'] == 'person_detected') {
          await FlutterRingtonePlayer().playAlarm(looping: true, asAlarm: true, volume: 1.0);
        }
      });

      messaging.onTokenRefresh.listen((token) async {
        await api.registerPushToken(token);
      });

      initialized = true;
    } catch (e) {
      debugPrint('FCM başlatılamadı (google-services.json / firebase_options gerekli): $e');
    }
  }
}
