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
  final _answerController = TextEditingController();
  String? _sessionId;
  double _score = 0.7;
  bool _submitting = false;
  String? _message;

  @override
  void initState() {
    super.initState();
    widget.api.createSession(skill: widget.skill, mode: widget.mode).then((id) {
      if (mounted) setState(() => _sessionId = id);
    });
  }

  @override
  void dispose() {
    _answerController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.skill.title)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${widget.skill.estimatedMinutes} 分钟 · ${widget.mode}', style: const TextStyle(color: Colors.black54)),
                  const SizedBox(height: 10),
                  Text(widget.skill.content, style: Theme.of(context).textTheme.bodyLarge),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _answerController,
            minLines: 4,
            maxLines: 8,
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              labelText: '用自己的话解释一下',
              hintText: '例如：这个概念解决什么问题，容易误解在哪里？',
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              const Text('自评分'),
              Expanded(
                child: Slider(
                  value: _score,
                  min: 0,
                  max: 1,
                  divisions: 10,
                  label: '${(_score * 100).round()}%',
                  onChanged: (value) => setState(() => _score = value),
                ),
              ),
            ],
          ),
          FilledButton(
            onPressed: _submitting ? null : _submit,
            child: Text(_submitting ? '提交中...' : '提交掌握证据'),
          ),
          if (_message != null) ...[
            const SizedBox(height: 12),
            Card(child: Padding(padding: const EdgeInsets.all(14), child: Text(_message!))),
          ],
        ],
      ),
    );
  }

  Future<void> _submit() async {
    setState(() => _submitting = true);
    try {
      await widget.api.submitEvidence(
        skill: widget.skill,
        sessionId: _sessionId,
        evidenceType: widget.mode == 'review' ? 'review' : 'explain',
        score: _score,
        response: _answerController.text,
      );
      setState(() => _message = '已记录，本知识点的掌握度和复习时间已更新。');
    } catch (error) {
      setState(() => _message = '提交失败：$error');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }
}

