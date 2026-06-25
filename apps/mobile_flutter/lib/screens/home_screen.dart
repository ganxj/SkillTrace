import 'package:flutter/material.dart';

import '../models/learning_models.dart';
import '../services/api_client.dart';
import 'learning_session_screen.dart';
import 'widgets.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.api, this.currentDomain});

  final ApiClient api;
  final DomainPack? currentDomain;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late Future<_TodayData> _todayFuture;
  final Set<String> _learnedThisSession = {};

  @override
  void initState() {
    super.initState();
    _todayFuture = _loadToday();
  }

  @override
  void didUpdateWidget(covariant HomeScreen oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.currentDomain?.slug != widget.currentDomain?.slug) {
      _learnedThisSession.clear();
      _todayFuture = _loadToday();
    }
  }

  @override
  Widget build(BuildContext context) {
    return ScreenFrame(
      title: '今天学什么',
      subtitle: widget.currentDomain == null
          ? '今日会默认使用最新发布课程。'
          : '当前学习：${widget.currentDomain!.name}。先看讲解，再做选择题。',
      child: LoadingOrError<_TodayData>(
        future: _todayFuture,
        builder: (context, data) {
          if (data.items.isEmpty) {
            return const ErrorCard(
              message: '暂无学习建议，请先在课程页选择当前学习课程或进入章节学习。',
            );
          }
          final firstPendingId = _firstPendingSkillId(data);
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Align(
                alignment: Alignment.centerRight,
                child: FilledButton.tonalIcon(
                  onPressed: _refreshToday,
                  icon: const Icon(Icons.refresh_outlined),
                  label: const Text('刷新今日学习'),
                ),
              ),
              const SizedBox(height: 12),
              for (var index = 0; index < data.items.length; index++) ...[
                SkillCard(
                  skill: data.items[index].skill,
                  reason: data.items[index].reason,
                  statusLabel: _statusFor(
                    data.items[index].skill,
                    data.statesBySkillId,
                    firstPendingId,
                    fallbackCurrent: index == 0,
                  ),
                  actionLabel: data.items[index].skill.id == firstPendingId
                      ? '开始学习'
                      : '学习',
                  onTap: () => _openSession(context, data.items[index].skill),
                ),
                if (index + 1 < data.items.length) const SizedBox(height: 10),
              ],
            ],
          );
        },
      ),
    );
  }

  void _refreshToday() {
    setState(() {
      _learnedThisSession.clear();
      _todayFuture = _loadToday();
    });
  }

  Future<_TodayData> _loadToday() async {
    final states = await widget.api.getLearnerState();
    final statesBySkillId = {
      for (final state in states) state.skillId: state,
    };
    final skills = await widget.api.getSkills(
      domainSlug: widget.currentDomain?.slug,
    );
    final items = skills
        .where((skill) => !_isLearnedSkill(skill.id, statesBySkillId))
        .take(5)
        .map((skill) => ReviewItem(skill: skill, reason: '新知识点'))
        .toList();
    return _TodayData(
      items: items,
      statesBySkillId: statesBySkillId,
    );
  }

  String? _firstPendingSkillId(_TodayData data) {
    for (final item in data.items) {
      if (!_isLearnedSkill(item.skill.id, data.statesBySkillId)) {
        return item.skill.id;
      }
    }
    return null;
  }

  String _statusFor(
    Skill skill,
    Map<String, LearnerState> statesBySkillId,
    String? firstPendingId, {
    required bool fallbackCurrent,
  }) {
    final state = _isLearnedSkill(skill.id, statesBySkillId);
    if (state) return '已学';
    if (skill.id == firstPendingId || fallbackCurrent) return '当前';
    return '待学';
  }

  bool _isLearned(LearnerState? state) {
    return state != null && (state.evidenceCount > 0 || state.mastery > 0);
  }

  bool _isLearnedSkill(
    String skillId,
    Map<String, LearnerState> statesBySkillId,
  ) {
    return _learnedThisSession.contains(skillId) ||
        _isLearned(statesBySkillId[skillId]);
  }

  Future<void> _openSession(BuildContext context, Skill skill) async {
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => LearningSessionScreen(api: widget.api, skill: skill),
      ),
    );
    if (changed == true && mounted) {
      setState(() => _learnedThisSession.add(skill.id));
    }
  }
}

class _TodayData {
  const _TodayData({required this.items, required this.statesBySkillId});

  final List<ReviewItem> items;
  final Map<String, LearnerState> statesBySkillId;
}
