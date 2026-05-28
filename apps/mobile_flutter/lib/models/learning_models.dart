class DomainPack {
  const DomainPack({
    required this.id,
    required this.slug,
    required this.name,
    required this.version,
    required this.description,
  });

  final String id;
  final String slug;
  final String name;
  final String version;
  final String description;

  factory DomainPack.fromJson(Map<String, dynamic> json) {
    return DomainPack(
      id: json['id'] as String,
      slug: json['slug'] as String,
      name: json['name'] as String,
      version: json['version'] as String,
      description: json['description'] as String? ?? '',
    );
  }
}

class QuizQuestion {
  const QuizQuestion({
    required this.prompt,
    required this.options,
    required this.correctIndex,
    required this.explanation,
  });

  final String prompt;
  final List<String> options;
  final int correctIndex;
  final String explanation;

  factory QuizQuestion.fromJson(Map<String, dynamic> json) {
    return QuizQuestion(
      prompt: json['prompt'] as String? ?? '',
      options: (json['options'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .toList(),
      correctIndex: json['correct_index'] as int? ?? 0,
      explanation: json['explanation'] as String? ?? '',
    );
  }
}

class Skill {
  const Skill({
    required this.id,
    required this.slug,
    required this.title,
    required this.summary,
    required this.kind,
    required this.difficulty,
    required this.estimatedMinutes,
    required this.content,
    required this.lessonExplain,
    required this.keyPoints,
    required this.questions,
    required this.prerequisites,
  });

  final String id;
  final String slug;
  final String title;
  final String summary;
  final String kind;
  final int difficulty;
  final int estimatedMinutes;
  final String content;
  final String lessonExplain;
  final List<String> keyPoints;
  final List<QuizQuestion> questions;
  final List<String> prerequisites;

  factory Skill.fromJson(Map<String, dynamic> json) {
    return Skill(
      id: json['id'] as String,
      slug: json['slug'] as String,
      title: json['title'] as String,
      summary: json['summary'] as String? ?? '',
      kind: json['kind'] as String? ?? 'concept',
      difficulty: json['difficulty'] as int? ?? 1,
      estimatedMinutes: json['estimated_minutes'] as int? ?? 5,
      content: json['content'] as String? ?? '',
      lessonExplain:
          json['lesson_explain'] as String? ?? json['content'] as String? ?? '',
      keyPoints: (json['key_points'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .toList(),
      questions: (json['questions'] as List<dynamic>? ?? const [])
          .map((item) => QuizQuestion.fromJson(item as Map<String, dynamic>))
          .toList(),
      prerequisites: (json['prerequisites'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .toList(),
    );
  }
}

class LearnerState {
  const LearnerState({
    required this.skillId,
    required this.mastery,
    required this.confidence,
    required this.evidenceCount,
    this.skill,
    this.reviewDueAt,
  });

  final String skillId;
  final double mastery;
  final double confidence;
  final int evidenceCount;
  final Skill? skill;
  final DateTime? reviewDueAt;

  factory LearnerState.fromJson(Map<String, dynamic> json) {
    return LearnerState(
      skillId: json['skill_id'] as String,
      mastery: (json['mastery'] as num? ?? 0).toDouble(),
      confidence: (json['confidence'] as num? ?? 0).toDouble(),
      evidenceCount: json['evidence_count'] as int? ?? 0,
      skill: json['skill'] == null
          ? null
          : Skill.fromJson(json['skill'] as Map<String, dynamic>),
      reviewDueAt: json['review_due_at'] == null
          ? null
          : DateTime.tryParse(json['review_due_at'] as String),
    );
  }
}

class ReviewItem {
  const ReviewItem({required this.skill, required this.reason, this.state});

  final Skill skill;
  final String reason;
  final LearnerState? state;

  factory ReviewItem.fromJson(Map<String, dynamic> json) {
    return ReviewItem(
      skill: Skill.fromJson(json['skill'] as Map<String, dynamic>),
      reason: json['reason'] as String? ?? '学习建议',
      state: json['state'] == null
          ? null
          : LearnerState.fromJson(json['state'] as Map<String, dynamic>),
    );
  }
}

class TutorReply {
  const TutorReply({required this.response, required this.provider});

  final String response;
  final String provider;

  factory TutorReply.fromJson(Map<String, dynamic> json) {
    return TutorReply(
      response: json['response'] as String? ?? '',
      provider: json['provider'] as String? ?? 'mock',
    );
  }
}
