import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'api.dart';

void main() => runApp(const MyApp());

class MyApp extends StatelessWidget {
  const MyApp({super.key});
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Attendance',
      theme: ThemeData(useMaterial3: true, colorSchemeSeed: Colors.indigo),
      home: const LoginPage(),
    );
  }
}

class LoginPage extends StatefulWidget {
  const LoginPage({super.key});
  @override
  State<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends State<LoginPage> {
  final _api = Api();
  final _user = TextEditingController(text: 'admin');
  final _pass = TextEditingController(text: 'admin123');
  bool _loading = false;
  String? _error;

  Future<void> _doLogin() async {
    setState(() { _loading = true; _error = null; });
    try {
      await _api.login(_user.text.trim(), _pass.text);
      if (!mounted) return;
      Navigator.of(context).pushReplacement(MaterialPageRoute(builder: (_) => const PresencePage()));
    } catch (e) {
      setState(() => _error = 'Login failed: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Login')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(children: [
          TextField(controller: _user, decoration: const InputDecoration(labelText: 'Username')),
          TextField(controller: _pass, decoration: const InputDecoration(labelText: 'Password'), obscureText: true),
          const SizedBox(height: 16),
          if (_error != null) Text(_error!, style: const TextStyle(color: Colors.red)),
          const SizedBox(height: 8),
          FilledButton(
            onPressed: _loading ? null : _doLogin,
            child: _loading ? const CircularProgressIndicator() : const Text('Sign in'),
          ),
        ]),
      ),
    );
  }
}

class PresencePage extends StatefulWidget {
  const PresencePage({super.key});
  @override
  State<PresencePage> createState() => _PresencePageState();
}

class _PresencePageState extends State<PresencePage> {
  final _api = Api();
  final _matricule = TextEditingController(text: 'STU001');
  String _result = '';
  bool _loading = false;

  Future<void> _markPresence() async {
    setState(() { _loading = true; _result = ''; });
    try {
      final perm = await Geolocator.requestPermission();
      if (perm == LocationPermission.denied || perm == LocationPermission.deniedForever) {
        setState(() { _result = 'Location permission denied'; _loading = false; });
        return;
      }
      final pos = await Geolocator.getCurrentPosition(desiredAccuracy: LocationAccuracy.high);
      final res = await _api.checkPresence(
        matricule: _matricule.text.trim(),
        lat: pos.latitude,
        lon: pos.longitude,
      );
      setState(() => _result = res.toString());
    } catch (e) {
      setState(() => _result = 'Error: $e');
    } finally {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mark presence')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(children: [
          TextField(controller: _matricule, decoration: const InputDecoration(labelText: 'Matricule')),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _loading ? null : _markPresence,
            child: _loading ? const CircularProgressIndicator() : const Text('Check presence'),
          ),
          const SizedBox(height: 16),
          Expanded(child: SingleChildScrollView(child: Text(_result))),
        ]),
      ),
    );
  }
}
