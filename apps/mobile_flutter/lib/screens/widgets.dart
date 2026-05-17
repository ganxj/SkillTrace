import 'package:flutter/material.dart';

import '../models/learning_models.dart';

class ScreenFrame extends StatelessWidget {
  const ScreenFrame({super.key, required this.title, required this.child, this.subtitle});

  final String title;
  final String? subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 24),
      children: [
        Text(title, style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w700)),
        if (subtitle != null) ...[
          const SizedBox(height: 6),
          Text(subtitle!, style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.black54)),
        ],
        const SizedBox(height: 18),
        child,
      ],
    );
  }
}

class SkillCard extends StatelessWidget {
  const SkillCard({super.key, required this.skill, this.reason, this.onTap});

  final Skill skill;
  final String? reason;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  Chip(label: Text('${skill.estimatedMinutes} min')),
                  Chip(label: Text('Lv.${skill.difficulty}')),
                  if (reason != null) Chip(label: Text(reason!)),
                ],
              ),
              const SizedBox(height: 8),
              Text(skill.title, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              Text(skill.summary),
              if (skill.prerequisites.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text('前置：${skill.prerequisites.join(', ')}', style: const TextStyle(color: Colors.brown)),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class LoadingOrError<T> extends StatelessWidget {
  const LoadingOrError({super.key, required this.future, required this.builder});

  final Future<T> future;
  final Widget Function(BuildContext context, T data) builder;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<T>(
      future: future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator()));
        }
        if (snapshot.hasError) {
          return Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Text('API 暂不可用：${snapshot.error}'),
            ),
          );
        }
        return builder(context, snapshot.data as T);
      },
    );
  }
}

