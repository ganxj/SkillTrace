import 'package:ai_learning_os_mobile/main.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('shows the learning shell', (WidgetTester tester) async {
    await tester.pumpWidget(const LearningOsApp());

    expect(find.text('今日'), findsOneWidget);
    expect(find.text('路线图'), findsOneWidget);
    expect(find.text('复习'), findsOneWidget);
    expect(find.text('Tutor'), findsOneWidget);
  });
}
