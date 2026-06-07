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
  int _refreshKey = 0;

  @override
  Widget build(BuildContext context) {
    return ScreenFrame(
      title: '今天学什么',
      subtitle: widget.currentDomain == null
          ? '今日会默认使用最新发布课程。'
          : '当前学习：${widget.currentDomain!.name}。先看讲解，再做选择题。',
      child: LoadingOrError<_TodayData>(
        future: _loadToday(_refreshKey),
        builder: (context, data) {
          if (data.items.isEmpty) {
            return const ErrorCard(
              message: '暂无学习建议，请先在课程页选择当前学习课程或进入章节学习。',
            );
          }
          final firstPendingId = _firstPendingSkillId(data);
          return Column(
            children: [
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
                  actionLabel: index == 0 ? '开始学习' : '学习',
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

  Future<_TodayData> _loadToday(int _) async {
    final items = await widget.api.getNextReview(
      domainSlug: widget.currentDomain?.slug,
    );
    final states = await widget.api.getLearnerState();
    return _TodayData(
      items: items,
      statesBySkillId: {
        for (final state in states) state.skillId: state,
      },
    );
  }

  String? _firstPendingSkillId(_TodayData data) {
    for (final item in data.items) {
      if (!_isLearned(data.statesBySkillId[item.skill.id])) {
        return item.skill.id;
      }
    }
    return data.items.isEmpty ? null : data.items.first.skill.id;
  }

  String _statusFor(
    Skill skill,
    Map<String, LearnerState> statesBySkillId,
    String? firstPendingId, {
    required bool fallbackCurrent,
  }) {
    final state = statesBySkillId[skill.id];
    if (_isLearned(state)) return '已学';
    if (skill.id == firstPendingId || fallbackCurrent) return '当前';
    return '待学';
  }

  bool _isLearned(LearnerState? state) {
    return state != null && (state.evidenceCount > 0 || state.mastery > 0);
  }

  Future<void> _openSession(BuildContext context, Skill skill) async {
    final changed = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => LearningSessionScreen(api: widget.api, skill: skill),
      ),
    );
    if (changed == true && mounted) {
      setState(() => _refreshKey += 1);
    }
  }
}

class _TodayData {
  const _TodayData({required this.items, required this.statesBySkillId});

  final List<ReviewItem> items;
  final Map<String, LearnerState> statesBySkillId;
}
