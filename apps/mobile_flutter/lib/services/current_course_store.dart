import 'package:flutter/services.dart';

class CurrentCourseStore {
  static const _channel = MethodChannel('ai_learning_os/current_course');

  Future<String?> readDomainId() async {
    return _channel.invokeMethod<String>('getCurrentDomainId');
  }

  Future<void> saveDomainId(String domainId) async {
    await _channel.invokeMethod<void>('setCurrentDomainId', domainId);
  }
}
