import 'package:flutter/material.dart';

import '../models/learning_models.dart';

class ScreenFrame extends StatelessWidget {
  const ScreenFrame(
      {super.key, required this.title, required this.child, this.subtitle});

  final String title;
  final String? subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 24),
      children: [
        Text(title,
            style: Theme.of(context)
                .textTheme
                .headlineMedium
                ?.copyWith(fontWeight: FontWeight.w700)),
        if (subtitle != null) ...[
          const SizedBox(height: 6),
          Text(subtitle!,
              style: Theme.of(context)
                  .textTheme
                  .bodyMedium
                  ?.copyWith(color: Colors.black54)),
        ],
        const SizedBox(height: 18),
        child,
      ],
    );
  }
}

class SkillCard extends StatelessWidget {
  const SkillCard({
    super.key,
    required this.skill,
    this.reason,
    this.statusLabel,
    this.actionLabel = '进入',
    this.onTap,
  });

  final Skill skill;
  final String? reason;
  final String? statusLabel;
  final String actionLabel;
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
                  Chip(label: Text('${skill.estimatedMinutes} 分钟')),
                  Chip(label: Text('Lv.${skill.difficulty}')),
                  Chip(label: Text('${skill.questions.length} 题')),
                  if (reason != null) Chip(label: Text(reason!)),
                ],
              ),
              const SizedBox(height: 8),
              Text(skill.title,
                  style: Theme.of(context)
                      .textTheme
                      .titleMedium
                      ?.copyWith(fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              Text(skill.summary),
              if (skill.prerequisites.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text('前置：${skill.prerequisites.join(', ')}',
                    style: const TextStyle(color: Colors.brown)),
              ],
              const SizedBox(height: 12),
              Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  if (statusLabel != null)
                    _StatusBadge(label: statusLabel!)
                  else
                    const Spacer(),
                  const SizedBox(width: 10),
                  FilledButton.tonalIcon(
                    onPressed: onTap,
                    icon: const Icon(Icons.play_arrow_rounded),
                    label: Text(actionLabel),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final color = switch (label) {
      '已学' => const Color(0xFF206B59),
      '当前' => Theme.of(context).colorScheme.primary,
      _ => Colors.black54,
    };
    return Expanded(
      child: Align(
        alignment: Alignment.centerLeft,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: color.withValues(alpha: 0.35)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.flag_outlined, size: 16, color: color),
              const SizedBox(width: 6),
              Text(
                label,
                style: TextStyle(color: color, fontWeight: FontWeight.w700),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class LoadingOrError<T> extends StatelessWidget {
  const LoadingOrError(
      {super.key, required this.future, required this.builder});

  final Future<T> future;
  final Widget Function(BuildContext context, T data) builder;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<T>(
      future: future,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return const Center(
              child: Padding(
                  padding: EdgeInsets.all(24),
                  child: CircularProgressIndicator()));
        }
        if (snapshot.hasError) {
          return ErrorCard(message: 'API 暂不可用：${snapshot.error}');
        }
        return builder(context, snapshot.data as T);
      },
    );
  }
}

class ErrorCard extends StatelessWidget {
  const ErrorCard({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Text(message),
      ),
    );
  }
}
