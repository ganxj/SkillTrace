import 'package:flutter/material.dart';

import '../models/learning_models.dart';
import '../services/api_client.dart';
import 'learning_session_screen.dart';
import 'widgets.dart';

class SkillsScreen extends StatelessWidget {
  const SkillsScreen({
    super.key,
    required this.api,
    required this.currentDomain,
    required this.onCurrentDomainChanged,
  });

  final ApiClient api;
  final DomainPack? currentDomain;
  final ValueChanged<DomainPack> onCurrentDomainChanged;

  @override
  Widget build(BuildContext context) {
    return ScreenFrame(
      title: '课程',
      subtitle: '选择当前学习课程，今日推荐会只展示这个课程里的章节。',
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
          final current = currentDomain ?? data.latest;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (final domain in data.domains)
                _CourseCard(
                  domain: domain,
                  latest: domain.id == data.latest.id,
                  current: domain.id == current.id,
                  onSetCurrent: () => onCurrentDomainChanged(domain),
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

class CourseRoadmapScreen extends StatefulWidget {
  const CourseRoadmapScreen({
    super.key,
    required this.api,
    required this.domain,
  });

  final ApiClient api;
  final DomainPack domain;

  @override
  State<CourseRoadmapScreen> createState() => _CourseRoadmapScreenState();
}

class _CourseRoadmapScreenState extends State<CourseRoadmapScreen> {
  int _refreshKey = 0;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.domain.name)),
      body: ScreenFrame(
        title: '章节路线图',
        subtitle: widget.domain.description.isEmpty
            ? widget.domain.slug
            : widget.domain.description,
        child: LoadingOrError<_RoadmapData>(
          future: _loadRoadmap(_refreshKey),
          builder: (context, data) {
            if (data.skills.isEmpty) {
              return const ErrorCard(message: '该课程还没有章节，请在后台重新生成。');
            }
            final currentSkillId = _currentSkillId(data);
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (var index = 0; index < data.skills.length; index++)
                  _ChapterTile(
                    index: index,
                    skill: data.skills[index],
                    status: _statusFor(
                      data.skills[index],
                      data.statesBySkillId,
                      currentSkillId,
                    ),
                    onTap: () => _openSession(context, data.skills[index]),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }

  Future<_RoadmapData> _loadRoadmap(int _) async {
    final skills = await widget.api.getSkills(domainSlug: widget.domain.slug);
    final states = await widget.api.getLearnerState();
    return _RoadmapData(
      skills: skills,
      statesBySkillId: {
        for (final state in states) state.skillId: state,
      },
    );
  }

  String? _currentSkillId(_RoadmapData data) {
    for (final skill in data.skills) {
      if (!_isLearned(data.statesBySkillId[skill.id])) return skill.id;
    }
    return data.skills.isEmpty ? null : data.skills.last.id;
  }

  ChapterStatus _statusFor(
    Skill skill,
    Map<String, LearnerState> statesBySkillId,
    String? currentSkillId,
  ) {
    if (_isLearned(statesBySkillId[skill.id])) return ChapterStatus.done;
    if (skill.id == currentSkillId) return ChapterStatus.current;
    return ChapterStatus.locked;
  }

  bool _isLearned(LearnerState? state) {
    return state != null && (state.evidenceCount > 0 || state.mastery > 0);
  }

  Future<void> _openSession(BuildContext context, Skill skill) async {
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => LearningSessionScreen(
          api: widget.api,
          skill: skill,
        ),
      ),
    );
    if (changed == true && mounted) {
      setState(() => _refreshKey += 1);
    }
  }
}

class _RoadmapData {
  const _RoadmapData({required this.skills, required this.statesBySkillId});

  final List<Skill> skills;
  final Map<String, LearnerState> statesBySkillId;
}

enum ChapterStatus { done, current, locked }

class _CourseListData {
  const _CourseListData({required this.domains, required this.latest});

  final List<DomainPack> domains;
  final DomainPack latest;
}

class _CourseCard extends StatelessWidget {
  const _CourseCard({
    required this.domain,
    required this.latest,
    required this.current,
    required this.onSetCurrent,
    required this.onTap,
  });

  final DomainPack domain;
  final bool latest;
  final bool current;
  final VoidCallback onSetCurrent;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                if (current)
                  const Chip(
                    avatar: Icon(Icons.flag_outlined, size: 18),
                    label: Text('当前学习'),
                  ),
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
            Wrap(
              alignment: WrapAlignment.end,
              spacing: 8,
              runSpacing: 8,
              children: [
                if (!current)
                  FilledButton.tonalIcon(
                    onPressed: onSetCurrent,
                    icon: const Icon(Icons.flag_outlined),
                    label: const Text('设为当前学习'),
                  ),
                FilledButton.icon(
                  onPressed: onTap,
                  icon: const Icon(Icons.account_tree_outlined),
                  label: const Text('查看章节'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _ChapterTile extends StatelessWidget {
  const _ChapterTile({
    required this.index,
    required this.skill,
    required this.status,
    required this.onTap,
  });

  final int index;
  final Skill skill;
  final ChapterStatus status;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
        childrenPadding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
        leading: CircleAvatar(
          backgroundColor: _statusColor(context).withValues(alpha: 0.16),
          foregroundColor: _statusColor(context),
          child: Icon(_statusIcon(), size: 20),
        ),
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
              Chip(
                avatar: Icon(_statusIcon(), size: 18),
                label: Text(_statusText()),
              ),
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
            const _SectionTitle(text: '要点'),
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
            const _SectionTitle(text: '题目'),
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

  String _statusText() {
    return switch (status) {
      ChapterStatus.done => '已学',
      ChapterStatus.current => '当前',
      ChapterStatus.locked => '未学',
    };
  }

  IconData _statusIcon() {
    return switch (status) {
      ChapterStatus.done => Icons.check_rounded,
      ChapterStatus.current => Icons.play_arrow_rounded,
      ChapterStatus.locked => Icons.radio_button_unchecked,
    };
  }

  Color _statusColor(BuildContext context) {
    return switch (status) {
      ChapterStatus.done => const Color(0xFF206B59),
      ChapterStatus.current => Theme.of(context).colorScheme.primary,
      ChapterStatus.locked => Colors.black45,
    };
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
          Text(
            question.prompt,
            style: const TextStyle(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 6),
          for (final option in question.options)
            Padding(
              padding: const EdgeInsets.only(top: 3),
              child: Text('- $option'),
            ),
        ],
      ),
    );
  }
}
