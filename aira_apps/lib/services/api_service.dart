import 'dart:convert';
import 'package:http/http.dart' as http;

class ApiService {
  static const String baseUrl =
      "https://7lp30gph-5000.asse.devtunnels.ms/"; // nanti ganti dengan backend Flask kamu

  static Future<String> getAnswer(String question) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/ask'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'question': question}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['answer'] ??
            "Maaf, saya tidak menemukan informasi tersebut.";
      } else {
        return "Terjadi kesalahan pada server.";
      }
    } catch (e) {
      return "Gagal terhubung ke server.";
    }
  }
}
