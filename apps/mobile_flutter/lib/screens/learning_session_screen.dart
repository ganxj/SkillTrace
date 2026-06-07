import 'package:flutter/material.dart';

import '../models/learning_models.dart';
import '../services/api_client.dart';

class LearningSessionScreen extends StatefulWidget {
  const LearningSessionScreen({
    super.key,
    required this.api,
    required this.skill,
    this.mode = 'learn',
  });

  final ApiClient api;
  final Skill skill;
  final String mode;

  @override
  State<LearningSessionScreen> createState() => _LearningSessionScreenState();
}

class _LearningSessionScreenState extends State<LearningSessionScreen> {
  String? _sessionId;
  int _step = 0;
  int _questionIndex = 0;
  int? _selectedIndex;
  bool _answered = false;
  bool _submitting = false;
  String? _message;

  QuizQuestion? get _question => widget.skill.questions.isEmpty
      ? null
      : widget.skill.questions[
          _questionIndex < widget.skill.questions.length
              ? _questionIndex
              : widget.skill.questions.length - 1];

  @override
  void initState() {
    super.initState();
    widget.api.createSession(skill: widget.skill, mode: widget.mode).then((id) {
      if (mounted) setState(() => _sessionId = id);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.skill.title)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _ProgressHeader(step: _step),
          const SizedBox(height: 12),
          if (_step == 0) _buildLesson(context) else _buildQuiz(context),
        ],
      ),
    );
  }

  Widget _buildLesson(BuildContext context) {
    final keyPoints = widget.skill.keyPoints;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                    '${widget.skill.estimatedMinutes} 分钟 · ${widget.skill.kind}',
                    style: const TextStyle(color: Colors.black54)),
                const SizedBox(height: 10),
                Text('这一节先学什么',
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                Text(
                  widget.skill.lessonExplain.isNotEmpty
                      ? widget.skill.lessonExplain
                      : widget.skill.content,
                  style: Theme.of(context).textTheme.bodyLarge,
                ),
                if (keyPoints.isNotEmpty) ...[
                  const SizedBox(height: 14),
                  Text('你需要记住',
                      style: Theme.of(context)
                          .textTheme
                          .titleSmall
                          ?.copyWith(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  for (final point in keyPoints)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
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
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        FilledButton.icon(
          onPressed: _question == null ? null : () => setState(() => _step = 1),
          icon: const Icon(Icons.quiz_outlined),
          label: Text(_question == null ? '该课程缺少题目' : '开始做题'),
        ),
        if (_question == null) ...[
          const SizedBox(height: 10),
          const Card(
            child: Padding(
              padding: EdgeInsets.all(14),
              child: Text('该课程缺少题目，请在后台重新生成。'),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildQuiz(BuildContext context) {
    final question = _question;
    if (question == null) {
      return const Card(
          child: Padding(
              padding: EdgeInsets.all(14), child: Text('该课程缺少题目，请在后台重新生成。')));
    }

    final selected = _selectedIndex;
    final isUnknown = selected != null && question.options[selected] == '我不会';
    final isCorrect = selected == question.correctIndex;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('选择题 ${_questionIndex + 1}/${widget.skill.questions.length}',
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.w700)),
                const SizedBox(height: 10),
                Text(question.prompt,
                    style: Theme.of(context).textTheme.bodyLarge),
                const SizedBox(height: 14),
                for (var index = 0; index < question.options.length; index++)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: _OptionTile(
                      text: question.options[index],
                      selected: selected == index,
                      enabled: !_answered,
                      isCorrect: _answered && index == question.correctIndex,
                      isWrong: _answered &&
                          selected == index &&
                          selected != question.correctIndex,
                      onTap: () => setState(() => _selectedIndex = index),
                    ),
                  ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 12),
        if (!_answered)
          FilledButton(
            onPressed: selected == null
                ? null
                : () => setState(() => _answered = true),
            child: const Text('提交答案'),
          )
        else ...[
          Card(
            color:
                isCorrect ? const Color(0xFFE8F5E9) : const Color(0xFFFFF4E5),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Text(
                isCorrect
                    ? '答对了。${question.explanation}'
                    : isUnknown
                        ? '没关系，先记住这条：${question.explanation}'
                        : '这题不是这个选项。${question.explanation}',
              ),
            ),
          ),
          const SizedBox(height: 10),
          FilledButton(
            onPressed: _submitting
                ? null
                : () => _finishQuestion(
                      question: question,
                      score: isCorrect
                          ? 1
                          : isUnknown
                              ? 0.2
                              : 0.45,
                    ),
            child: Text(_submitting
                ? '记录中...'
                : _questionIndex + 1 < widget.skill.questions.length
                    ? '记录并做下一题'
                    : '完成本节'),
          ),
          TextButton(
            onPressed: _submitting
                ? null
                : () => setState(() {
                      _step = 0;
                      _selectedIndex = null;
                      _answered = false;
                    }),
            child: const Text('再看一遍讲解'),
          ),
        ],
        if (_message != null) ...[
          const SizedBox(height: 12),
          Card(
              child: Padding(
                  padding: const EdgeInsets.all(14), child: Text(_message!))),
        ],
      ],
    );
  }

  Future<void> _finishQuestion(
      {required QuizQuestion question, required double score}) async {
    setState(() => _submitting = true);
    try {
      await widget.api.submitEvidence(
        skill: widget.skill,
        sessionId: _sessionId,
        evidenceType: widget.mode == 'review' ? 'review_choice' : 'choice_quiz',
        score: score,
        prompt: question.prompt,
        response:
            question.options[_selectedIndex ?? question.options.length - 1],
      );
      if (_questionIndex + 1 < widget.skill.questions.length) {
        setState(() {
          _questionIndex += 1;
          _selectedIndex = null;
          _answered = false;
          _message = '已记录，继续下一题。';
        });
      } else {
        if (!mounted) return;
        Navigator.of(context).pop(true);
      }
    } catch (error) {
      setState(() => _message = '提交失败：$error');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }
}

class _ProgressHeader extends StatelessWidget {
  const _ProgressHeader({required this.step});

  final int step;

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme.primary;
    return Row(
      children: [
        _StepPill(label: '1 讲解', active: step == 0, color: color),
        Expanded(
            child: Container(height: 2, color: color.withValues(alpha: 0.25))),
        _StepPill(label: '2 做题', active: step == 1, color: color),
      ],
    );
  }
}

class _StepPill extends StatelessWidget {
  const _StepPill(
      {required this.label, required this.active, required this.color});

  final String label;
  final bool active;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: active ? color : Colors.white,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: color.withValues(alpha: 0.35)),
      ),
      child: Text(label,
          style: TextStyle(
              color: active ? Colors.white : color,
              fontWeight: FontWeight.w700)),
    );
  }
}

class _OptionTile extends StatelessWidget {
  const _OptionTile({
    required this.text,
    required this.selected,
    required this.enabled,
    required this.isCorrect,
    required this.isWrong,
    required this.onTap,
  });

  final String text;
  final bool selected;
  final bool enabled;
  final bool isCorrect;
  final bool isWrong;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    Color? color;
    IconData icon =
        selected ? Icons.radio_button_checked : Icons.radio_button_off;
    if (isCorrect) {
      color = const Color(0xFFE8F5E9);
      icon = Icons.check_circle;
    } else if (isWrong) {
      color = const Color(0xFFFFEBEE);
      icon = Icons.cancel;
    } else if (selected) {
      color = Theme.of(context).colorScheme.primaryContainer;
    }

    return Material(
      color: color ?? Colors.white,
      borderRadius: BorderRadius.circular(8),
      child: InkWell(
        borderRadius: BorderRadius.circular(8),
        onTap: enabled ? onTap : null,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              Icon(icon, size: 22),
              const SizedBox(width: 10),
              Expanded(child: Text(text)),
            ],
          ),
        ),
      ),
    );
  }
}
