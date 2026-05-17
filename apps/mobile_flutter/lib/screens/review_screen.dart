import 'package:flutter/material.dart';

import '../models/learning_models.dart';
import '../services/api_client.dart';
import 'learning_session_screen.dart';
import 'widgets.dart';

class ReviewScreen extends StatelessWidget {
  const ReviewScreen({super.key, required this.api});

  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    return ScreenFrame(
      title: '到期复习',
      subtitle: '低掌握度、低置信度、长时间未见的知识点会优先出现。',
      child: LoadingOrError<List<ReviewItem>>(
        future: api.getNextReview(),
        builder: (context, items) => Column(
          children: items
              .map(
                (item) => SkillCard(
                  skill: item.skill,
                  reason: item.reason,
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => LearningSessionScreen(api: api, skill: item.skill, mode: 'review'),
                    ),
                  ),
                ),
              )
              .toList(),
        ),
      ),
    );
  }
}

