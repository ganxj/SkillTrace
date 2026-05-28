import 'package:flutter/material.dart';

import '../models/learning_models.dart';
import '../services/api_client.dart';
import 'learning_session_screen.dart';
import 'widgets.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key, required this.api});

  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    return ScreenFrame(
      title: '今天学什么',
      subtitle: '先看讲解，再做选择题。每次只推进一个小知识点。',
      child: LoadingOrError<List<ReviewItem>>(
        future: api.getNextReview(),
        builder: (context, items) {
          if (items.isEmpty) {
            return const ErrorCard(message: '暂无学习建议，请先在课程页选择章节。');
          }
          final primary = items.first;
          return Column(
            children: [
              SkillCard(
                skill: primary.skill,
                reason: primary.reason,
                actionLabel: '开始学习',
                onTap: () => _openSession(context, primary.skill),
              ),
              const SizedBox(height: 10),
              ...items.skip(1).map(
                    (item) => SkillCard(
                      skill: item.skill,
                      reason: item.reason,
                      actionLabel: '学习',
                      onTap: () => _openSession(context, item.skill),
                    ),
                  ),
            ],
          );
        },
      ),
    );
  }

  void _openSession(BuildContext context, Skill skill) {
    Navigator.of(context).push(
      MaterialPageRoute(
          builder: (_) => LearningSessionScreen(api: api, skill: skill)),
    );
  }
}
