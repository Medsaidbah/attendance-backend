import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'env.dart';

class Api {
  final Dio _dio = Dio(BaseOptions(
    baseUrl: apiBaseUrl,
    connectTimeout: const Duration(seconds: 8),
  ));
  final _storage = const FlutterSecureStorage();

  Api() {
    _dio.interceptors.add(InterceptorsWrapper(onRequest: (options, handler) async {
      final token = await _storage.read(key: 'token');
      if (token != null) options.headers['Authorization'] = 'Bearer $token';
      handler.next(options);
    }));
  }

  Future<void> login(String username, String password) async {
    final res = await _dio.post('/auth/login', data: {'username': username, 'password': password});
    final token = res.data['access_token'] as String;
    await _storage.write(key: 'token', value: token);
  }

  Future<Map<String, dynamic>> checkPresence({
    required String matricule,
    required double lat,
    required double lon,
    String method = 'manual',
  }) async {
    final res = await _dio.post('/presence/check', data: {
      'matricule': matricule,
      'lat': lat,
      'lon': lon,
      'method': method,
    });
    return Map<String, dynamic>.from(res.data);
  }
}
