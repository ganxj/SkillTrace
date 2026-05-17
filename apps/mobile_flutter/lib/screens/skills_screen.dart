import 'package:flutter/material.dart';

import '../models/learning_models.dart';
import '../services/api_client.dart';
import 'learning_session_screen.dart';
import 'widgets.dart';

class SkillsScreen extends StatelessWidget {
  const SkillsScreen({super.key, required this.api});

  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    return ScreenFrame(
      title: '量化技能树',
      subtitle: '首个 Domain Pack，用来验证通用学习底座。',
      child: LoadingOrError<List<Skill>>(
        future: api.getSkills(),
        builder: (context, skills) => Column(
          children: skills
              .map(
                (skill) => SkillCard(
                  skill: skill,
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(builder: (_) => LearningSessionScreen(api: api, skill: skill)),
                  ),
                ),
              )
              .toList(),
        ),
      ),
    );
  }
}

