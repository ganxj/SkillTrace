import 'package:flutter/material.dart';

import '../services/api_client.dart';
import 'widgets.dart';

class TutorScreen extends StatefulWidget {
  const TutorScreen({super.key, required this.api});

  final ApiClient api;

  @override
  State<TutorScreen> createState() => _TutorScreenState();
}

class _TutorScreenState extends State<TutorScreen> {
  final _controller = TextEditingController();
  final List<_ChatLine> _lines = [];
  bool _sending = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ScreenFrame(
      title: 'AI Tutor',
      subtitle: '默认 Mock，可由后端 AI_PROVIDER 切换到 OpenAI。',
      child: Column(
        children: [
          if (_lines.isEmpty)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(14),
                child: Text('问一个学习问题。Tutor 会保持短回复，并引导你形成下一步学习动作。'),
              ),
            )
          else
            ..._lines.map((line) => _ChatBubble(line: line)),
          const SizedBox(height: 12),
          TextField(
            controller: _controller,
            minLines: 2,
            maxLines: 5,
            decoration: const InputDecoration(
              border: OutlineInputBorder(),
              labelText: '输入问题',
            ),
          ),
          const SizedBox(height: 10),
          FilledButton(
            onPressed: _sending ? null : _send,
            child: Text(_sending ? '发送中...' : '发送'),
          ),
        ],
      ),
    );
  }

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    setState(() {
      _sending = true;
      _lines.add(_ChatLine(role: '我', text: text));
      _controller.clear();
    });
    try {
      final reply = await widget.api.sendTutorMessage(message: text);
      setState(() => _lines.add(_ChatLine(role: 'Tutor (${reply.provider})', text: reply.response)));
    } catch (error) {
      setState(() => _lines.add(_ChatLine(role: '系统', text: '发送失败：$error')));
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }
}

class _ChatLine {
  const _ChatLine({required this.role, required this.text});

  final String role;
  final String text;
}

class _ChatBubble extends StatelessWidget {
  const _ChatBubble({required this.line});

  final _ChatLine line;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(line.role, style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            Text(line.text),
          ],
        ),
      ),
    );
  }
}

