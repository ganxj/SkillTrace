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
      title: '今天建议学什么',
      subtitle: '每次只推进一个小知识点，保持 5-10 分钟闭环。',
      child: LoadingOrError<List<ReviewItem>>(
        future: api.getNextReview(),
        builder: (context, items) {
          if (items.isEmpty) {
            return const Card(child: Padding(padding: EdgeInsets.all(14), child: Text('暂无学习建议。')));
          }
          final primary = items.first;
          return Column(
            children: [
              SkillCard(
                skill: primary.skill,
                reason: primary.reason,
                onTap: () => _openSession(context, primary.skill),
              ),
              const SizedBox(height: 10),
              ...items.skip(1).map(
                    (item) => SkillCard(
                      skill: item.skill,
                      reason: item.reason,
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
      MaterialPageRoute(builder: (_) => LearningSessionScreen(api: api, skill: skill)),
    );
  }
}

