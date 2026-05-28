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
      title: '课程',
      subtitle: '选择后台发布的课程包，查看完整章节路线图并进入学习。',
      child: FutureBuilder<_CourseListData>(
        future: _loadCourses(),
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: CircularProgressIndicator(),
              ),
            );
          }
          if (snapshot.hasError) {
            return ErrorCard(message: 'API 暂不可用：${snapshot.error}');
          }
          final data = snapshot.data!;
          if (data.domains.isEmpty) {
            return const ErrorCard(message: '暂无课程，请先在后台上传 PDF 生成课程。');
          }
          return Column(
            children: [
              for (final domain in data.domains)
                _CourseCard(
                  domain: domain,
                  latest: domain.id == data.latest.id,
                  onTap: () => Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => CourseRoadmapScreen(
                        api: api,
                        domain: domain,
                      ),
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }

  Future<_CourseListData> _loadCourses() async {
    final latest = await api.getLatestDomain();
    final domains = await api.getDomains();
    return _CourseListData(domains: domains.reversed.toList(), latest: latest);
  }
}

class CourseRoadmapScreen extends StatelessWidget {
  const CourseRoadmapScreen({
    super.key,
    required this.api,
    required this.domain,
  });

  final ApiClient api;
  final DomainPack domain;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(domain.name)),
      body: ScreenFrame(
        title: '章节路线图',
        subtitle: domain.description.isEmpty ? domain.slug : domain.description,
        child: LoadingOrError<List<Skill>>(
          future: api.getSkills(domainSlug: domain.slug),
          builder: (context, skills) {
            if (skills.isEmpty) {
              return const ErrorCard(message: '该课程还没有章节，请在后台重新生成。');
            }
            return Column(
              children: [
                for (var index = 0; index < skills.length; index++)
                  _ChapterTile(
                    index: index,
                    skill: skills[index],
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => LearningSessionScreen(
                          api: api,
                          skill: skills[index],
                        ),
                      ),
                    ),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}

class _CourseListData {
  const _CourseListData({required this.domains, required this.latest});

  final List<DomainPack> domains;
  final DomainPack latest;
}

class _CourseCard extends StatelessWidget {
  const _CourseCard({
    required this.domain,
    required this.latest,
    required this.onTap,
  });

  final DomainPack domain;
  final bool latest;
  final VoidCallback onTap;

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
                  if (latest) const Chip(label: Text('最新发布')),
                  Chip(label: Text(domain.version)),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                domain.name,
                style: Theme.of(context)
                    .textTheme
                    .titleMedium
                    ?.copyWith(fontWeight: FontWeight.w700),
              ),
              if (domain.description.isNotEmpty) ...[
                const SizedBox(height: 6),
                Text(domain.description),
              ],
              const SizedBox(height: 12),
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton.tonalIcon(
                  onPressed: onTap,
                  icon: const Icon(Icons.account_tree_outlined),
                  label: const Text('查看章节'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ChapterTile extends StatelessWidget {
  const _ChapterTile({
    required this.index,
    required this.skill,
    required this.onTap,
  });

  final int index;
  final Skill skill;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
        childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
        leading: CircleAvatar(child: Text('${index + 1}')),
        title: Text(
          skill.title,
          style: const TextStyle(fontWeight: FontWeight.w700),
        ),
        subtitle: Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Text(skill.summary),
        ),
        children: [
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              Chip(label: Text('${skill.estimatedMinutes} 分钟')),
              Chip(label: Text('Lv.${skill.difficulty}')),
              Chip(label: Text('${skill.questions.length} 道题')),
              if (skill.prerequisites.isNotEmpty)
                Chip(label: Text('前置 ${skill.prerequisites.length}')),
            ],
          ),
          if (skill.lessonExplain.isNotEmpty) ...[
            const SizedBox(height: 10),
            Align(
              alignment: Alignment.centerLeft,
              child: Text(
                skill.lessonExplain,
                maxLines: 4,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
          if (skill.keyPoints.isNotEmpty) ...[
            const SizedBox(height: 12),
            _SectionTitle(text: '要点'),
            for (final point in skill.keyPoints.take(4))
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Icon(Icons.check_circle_outline, size: 18),
                    const SizedBox(width: 8),
                    Expanded(child: Text(point)),
                  ],
                ),
              ),
          ],
          if (skill.questions.isNotEmpty) ...[
            const SizedBox(height: 12),
            _SectionTitle(text: '题目'),
            for (final question in skill.questions.take(3))
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: _QuestionPreview(question: question),
              ),
          ],
          const SizedBox(height: 12),
          Align(
            alignment: Alignment.centerRight,
            child: FilledButton.icon(
              onPressed: onTap,
              icon: const Icon(Icons.play_arrow_rounded),
              label: const Text('进入学习'),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Text(
        text,
        style: Theme.of(context)
            .textTheme
            .titleSmall
            ?.copyWith(fontWeight: FontWeight.w700),
      ),
    );
  }
}

class _QuestionPreview extends StatelessWidget {
  const _QuestionPreview({required this.question});

  final QuizQuestion question;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAF7),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFDDE5DD)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(question.prompt,
              style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          for (final option in question.options)
            Padding(
              padding: const EdgeInsets.only(top: 3),
              child: Text('• $option'),
            ),
        ],
      ),
    );
  }
}
