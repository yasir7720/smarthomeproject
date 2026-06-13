import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config.dart';

class ApiService {
  ApiService({String? baseUrl, this.token}) : baseUrl = baseUrl ?? AppConfig.defaultApiBase;

  final String baseUrl;
  String? token;

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    required String fullName,
    required String tenantName,
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/api/v1/auth/register'),
      headers: _headers,
      body: jsonEncode({
        'email': email,
        'password': password,
        'full_name': fullName,
        'tenant_name': tenantName,
      }),
    );
    return _decode(res);
  }

  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/api/v1/auth/login'),
      headers: _headers,
      body: jsonEncode({'email': email, 'password': password}),
    );
    return _decode(res);
  }

  Future<void> registerPushToken(String token, {String platform = 'android'}) async {
    final res = await http.post(
      Uri.parse('$baseUrl/api/v1/auth/push-token'),
      headers: _headers,
      body: jsonEncode({'token': token, 'platform': platform}),
    );
    _decode(res);
  }

  Future<Map<String, dynamic>> getMqttCredentials(String tenantId) async {
    final res = await http.get(
      Uri.parse('$baseUrl/api/v1/tenants/$tenantId/mqtt-credentials'),
      headers: _headers,
    );
    return _decode(res);
  }

  Future<List<dynamic>> listDetections(String tenantId) async {
    final res = await http.get(
      Uri.parse('$baseUrl/api/v1/tenants/$tenantId/detections'),
      headers: _headers,
    );
    return _decode(res) as List<dynamic>;
  }

  Future<List<dynamic>> listTenants() async {
    final res = await http.get(Uri.parse('$baseUrl/api/v1/tenants'), headers: _headers);
    return _decode(res) as List<dynamic>;
  }

  Future<List<dynamic>> listCameras(String tenantId) async {
    final res = await http.get(
      Uri.parse('$baseUrl/api/v1/tenants/$tenantId/cameras'),
      headers: _headers,
    );
    return _decode(res) as List<dynamic>;
  }

  Future<Map<String, dynamic>> addIpWebcam(
    String tenantId, {
    required String phoneIp,
    String name = 'Telefon Kamerası',
    int port = 8080,
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/api/v1/tenants/$tenantId/cameras/ip-webcam'),
      headers: _headers,
      body: jsonEncode({
        'name': name,
        'phone_ip': phoneIp,
        'port': port,
      }),
    );
    return _decode(res);
  }

  Future<Map<String, dynamic>> addCamera(
    String tenantId, {
    required String name,
    required String streamUrl,
    String protocol = 'rtsp',
  }) async {
    final res = await http.post(
      Uri.parse('$baseUrl/api/v1/tenants/$tenantId/cameras'),
      headers: _headers,
      body: jsonEncode({
        'name': name,
        'stream_url': streamUrl,
        'protocol': protocol,
      }),
    );
    return _decode(res);
  }

  Future<void> deleteCamera(String tenantId, String cameraId) async {
    final res = await http.delete(
      Uri.parse('$baseUrl/api/v1/tenants/$tenantId/cameras/$cameraId'),
      headers: _headers,
    );
    if (res.statusCode < 200 || res.statusCode >= 300) {
      _decode(res);
    }
  }

  Future<Map<String, dynamic>> getStreamToken(String tenantId, String cameraId) async {
    final res = await http.post(
      Uri.parse('$baseUrl/api/v1/tenants/$tenantId/cameras/$cameraId/stream-token'),
      headers: _headers,
    );
    return _decode(res);
  }

  Future<List<dynamic>> listDevices(String tenantId) async {
    final res = await http.get(
      Uri.parse('$baseUrl/api/v1/tenants/$tenantId/devices'),
      headers: _headers,
    );
    return _decode(res) as List<dynamic>;
  }

  Future<void> deviceCommand(String tenantId, String deviceId, bool isOn) async {
    final res = await http.post(
      Uri.parse('$baseUrl/api/v1/tenants/$tenantId/devices/$deviceId/command'),
      headers: _headers,
      body: jsonEncode({'is_on': isOn}),
    );
    _decode(res);
  }

  Future<void> scenarioHome(String tenantId) async {
    final res = await http.post(
      Uri.parse('$baseUrl/api/v1/tenants/$tenantId/automations/home'),
      headers: _headers,
    );
    _decode(res);
  }

  Future<void> scenarioAway(String tenantId) async {
    final res = await http.post(
      Uri.parse('$baseUrl/api/v1/tenants/$tenantId/automations/away'),
      headers: _headers,
    );
    _decode(res);
  }

  Future<void> scenarioSchedule(String tenantId, String baslangic, String bitis) async {
    final res = await http.post(
      Uri.parse('$baseUrl/api/v1/tenants/$tenantId/automations/schedule'),
      headers: _headers,
      body: jsonEncode({'baslangic': baslangic, 'bitis': bitis}),
    );
    _decode(res);
  }

  dynamic _decode(http.Response res) {
    final body = res.body.isEmpty ? null : jsonDecode(res.body);
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return body ?? {};
    }
    final detail = body is Map ? (body['detail'] ?? body.toString()) : res.body;
    throw Exception('$detail (HTTP ${res.statusCode})');
  }
}
