import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../services/api_service.dart';
import 'dashboard_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _fullName = TextEditingController();
  final _tenantName = TextEditingController(text: 'Evim');
  final _apiBase = TextEditingController(text: 'http://localhost:8000');
  bool _isRegister = false;
  bool _loading = false;
  String? _error;

  Future<void> _submit() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ApiService(baseUrl: _apiBase.text.trim());
      Map<String, dynamic> result;
      if (_isRegister) {
        result = await api.register(
          email: _email.text.trim(),
          password: _password.text,
          fullName: _fullName.text.trim(),
          tenantName: _tenantName.text.trim(),
        );
      } else {
        result = await api.login(
          email: _email.text.trim(),
          password: _password.text,
        );
      }
      final token = result['access_token'] as String;
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('token', token);
      await prefs.setString('api_base', _apiBase.text.trim());
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => DashboardScreen(token: token, apiBase: _apiBase.text.trim()),
        ),
      );
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Column(
              children: [
                Icon(Icons.cloud, size: 64, color: Colors.cyan.shade400),
                const SizedBox(height: 12),
                Text('BulutSistem', style: Theme.of(context).textTheme.headlineMedium),
                const SizedBox(height: 24),
                TextField(
                  controller: _apiBase,
                  decoration: const InputDecoration(labelText: 'API Adresi', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 12),
                if (_isRegister) ...[
                  TextField(
                    controller: _fullName,
                    decoration: const InputDecoration(labelText: 'Ad Soyad', border: OutlineInputBorder()),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _tenantName,
                    decoration: const InputDecoration(labelText: 'Ev Adı', border: OutlineInputBorder()),
                  ),
                  const SizedBox(height: 12),
                ],
                TextField(
                  controller: _email,
                  decoration: const InputDecoration(labelText: 'E-posta', border: OutlineInputBorder()),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _password,
                  obscureText: true,
                  decoration: const InputDecoration(labelText: 'Şifre', border: OutlineInputBorder()),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(_error!, style: const TextStyle(color: Colors.redAccent)),
                ],
                const SizedBox(height: 20),
                FilledButton(
                  onPressed: _loading ? null : _submit,
                  child: Text(_loading ? 'Bekleyin...' : (_isRegister ? 'Kayıt Ol' : 'Giriş Yap')),
                ),
                TextButton(
                  onPressed: () => setState(() => _isRegister = !_isRegister),
                  child: Text(_isRegister ? 'Zaten hesabım var' : 'Yeni hesap oluştur'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
