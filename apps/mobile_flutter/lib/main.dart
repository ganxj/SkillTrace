import 'package:flutter/material.dart';

import 'screens/home_screen.dart';
import 'screens/review_screen.dart';
import 'screens/skills_screen.dart';
import 'screens/tutor_screen.dart';
import 'models/learning_models.dart';
import 'services/api_client.dart';
import 'services/current_course_store.dart';

void main() {
  runApp(const LearningOsApp());
}

class LearningOsApp extends StatelessWidget {
  const LearningOsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI Learning OS',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF206B59)),
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF6F7F4),
      ),
      home: LearningShell(api: ApiClient()),
    );
  }
}

class LearningShell extends StatefulWidget {
  const LearningShell({super.key, required this.api});

  final ApiClient api;

  @override
  State<LearningShell> createState() => _LearningShellState();
}

class _LearningShellState extends State<LearningShell> {
  int _index = 0;
  DomainPack? _currentDomain;
  final _courseStore = CurrentCourseStore();

  @override
  void initState() {
    super.initState();
    _loadCurrentDomain();
  }

  Future<void> _loadCurrentDomain() async {
    try {
      final latest = await widget.api.getLatestDomain();
      final domains = await widget.api.getDomains();
      final savedDomainId = await _courseStore.readDomainId();
      DomainPack? savedDomain;
      if (savedDomainId != null) {
        for (final domain in domains) {
          if (domain.id == savedDomainId) {
            savedDomain = domain;
            break;
          }
        }
      }
      if (!mounted) return;
      setState(() => _currentDomain = savedDomain ?? latest);
    } catch (_) {
      // The screens below already surface API errors in context.
    }
  }

  Future<void> _setCurrentDomain(DomainPack domain) async {
    setState(() => _currentDomain = domain);
    await _courseStore.saveDomainId(domain.id);
  }

  @override
  Widget build(BuildContext context) {
    final screens = [
      HomeScreen(api: widget.api, currentDomain: _currentDomain),
      SkillsScreen(
        api: widget.api,
        currentDomain: _currentDomain,
        onCurrentDomainChanged: (domain) => _setCurrentDomain(domain),
      ),
      ReviewScreen(api: widget.api),
      TutorScreen(api: widget.api),
    ];
    return Scaffold(
      body: SafeArea(child: screens[_index]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (value) => setState(() => _index = value),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.today_outlined), label: '今日'),
          NavigationDestination(
              icon: Icon(Icons.menu_book_outlined), label: '课程'),
          NavigationDestination(
              icon: Icon(Icons.refresh_outlined), label: '复习'),
          NavigationDestination(
              icon: Icon(Icons.chat_bubble_outline), label: 'Tutor'),
        ],
      ),
    );
  }
}
