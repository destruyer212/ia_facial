import 'dart:io';

import 'package:path_provider/path_provider.dart';

import 'api_config.dart';

class ApiPreferences {
  static const _fileName = 'api_base_url.txt';

  static Future<String> load() async {
    try {
      final file = await _file();
      if (await file.exists()) {
        final value = (await file.readAsString()).trim();
        if (value.isNotEmpty) return value;
      }
    } catch (_) {
      // usar valor por defecto
    }
    return kProductionApiBaseUrl;
  }

  static Future<void> save(String url) async {
    final file = await _file();
    await file.writeAsString(url.trim());
  }

  static Future<File> _file() async {
    final dir = await getApplicationDocumentsDirectory();
    return File('${dir.path}/$_fileName');
  }
}
