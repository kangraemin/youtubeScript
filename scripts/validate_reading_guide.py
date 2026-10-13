"""학습 본문 구조·출처 범위 검사. 의미적 완전성은 원문 대조가 별도로 필요하다."""
def validate_reading_guide(guide, transcript_raw):
    if not isinstance(guide, dict):
        return ['reading_guide 필수 — 짧은 요약과 별개로 학습 본문을 작성할 것']
    errors = []
    for key in ('title', 'introduction'):
        if not isinstance(guide.get(key), str) or not guide[key].strip():
            errors.append(f'reading_guide.{key} 필수')
    topics = guide.get('topics')
    if not isinstance(topics, list) or not topics:
        errors.append('reading_guide.topics 필수')
    else:
        ids = set()
        for i, topic in enumerate(topics):
            if not isinstance(topic, dict):
                errors.append(f'topics[{i}] 객체 필요'); continue
            for key in ('id', 'title', 'speaker', 'ts'):
                if not isinstance(topic.get(key), str) or not topic[key].strip():
                    errors.append(f'topics[{i}].{key} 필수')
            ident = topic.get('id')
            if isinstance(ident, str):
                if ident in ids: errors.append(f'topics[{i}].id 중복')
                ids.add(ident)
            for key in ('points', 'background', 'takeaways'):
                values = topic.get(key)
                if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
                    errors.append(f'topics[{i}].{key} 문자열 목록 필요')
                elif key == 'points' and not values:
                    errors.append(f'topics[{i}].points 본문 없음')
    for key in ('perspectives', 'lessons', 'sources'):
        if not isinstance(guide.get(key), list): errors.append(f'reading_guide.{key} 목록 필요')
    coverage = guide.get('coverage')
    if not isinstance(coverage, dict):
        errors.append('reading_guide.coverage 필수')
    elif transcript_raw is not None:
        count = len(transcript_raw.splitlines())
        if coverage.get('read_lines') != count or coverage.get('transcript_lines') != count:
            errors.append(f'전수 독해 범위 불일치 — 원문 {count}줄')
    else:
        errors.append('학습 본문은 원문 파일 없이 저장할 수 없음')
    return errors
