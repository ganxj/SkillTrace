import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/learning_models.dart';

class ApiClient {
  ApiClient({
    this.baseUrl = 'http://localhost:8000/api/v1',
    this.userId = 'demo-user',
  });

  final String baseUrl;
  final String userId;

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        'X-User-Id': userId,
      };

  Future<List<ReviewItem>> getNextReview() async {
    final data = await _getList('/review/next?limit=5');
    return data.map((item) => ReviewItem.fromJson(item)).toList();
  }

  Future<List<Skill>> getSkills() async {
    final data = await _getList('/skills?domain_slug=quant_v1');
    return data.map((item) => Skill.fromJson(item)).toList();
  }

  Future<List<LearnerState>> getLearnerState() async {
    final data = await _getList('/learner/state');
    return data.map((item) => LearnerState.fromJson(item)).toList();
  }

  Future<String> createSession({required Skill skill, String mode = 'learn'}) async {
    final data = await _post('/sessions', {
      'skill_id': skill.id,
      'mode': mode,
      'duration_minutes': skill.estimatedMinutes,
      'goal': '碎片化学习：${skill.title}',
    });
    return data['id'] as String;
  }

  Future<void> submitEvidence({
    required Skill skill,
    required String? sessionId,
    required String evidenceType,
    required double score,
    required String response,
  }) async {
    await _post('/evidence', {
      'skill_id': skill.id,
      'session_id': sessionId,
      'evidence_type': evidenceType,
      'score': score,
      'prompt': '请用自己的话解释：${skill.title}',
      'response': response,
      'feedback': score >= 0.7 ? '解释清晰，进入下一轮复习。' : '还需要补强概念边界。',
    });
  }

  Future<TutorReply> sendTutorMessage({
    required String message,
    String? skillId,
    String mode = 'coach',
  }) async {
    final data = await _post('/tutor/messages', {
      'message': message,
      'skill_id': skillId,
      'mode': mode,
    });
    return TutorReply.fromJson(data);
  }

  Future<List<Map<String, dynamic>>> _getList(String path) async {
    final response = await http.get(Uri.parse('$baseUrl$path'), headers: _headers);
    _ensureOk(response);
    return (jsonDecode(utf8.decode(response.bodyBytes)) as List<dynamic>)
        .cast<Map<String, dynamic>>();
  }

  Future<Map<String, dynamic>> _post(String path, Map<String, dynamic> payload) async {
    final response = await http.post(
      Uri.parse('$baseUrl$path'),
      headers: _headers,
      body: jsonEncode(payload),
    );
    _ensureOk(response);
    return jsonDecode(utf8.decode(response.bodyBytes)) as Map<String, dynamic>;
  }

  void _ensureOk(http.Response response) {
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('API ${response.request?.url} failed: ${response.statusCode} ${response.body}');
    }
  }
}

