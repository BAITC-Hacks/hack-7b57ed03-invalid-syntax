from __future__ import annotations

import re

from app.ai.contracts import MergedSegment

NAME = r"([А-ЯЁӘҒҚҢӨҰҮҺІ][а-яёәғқңөұүһі-]+(?:\s+[А-ЯЁӘҒҚҢӨҰҮҺІ][а-яёәғқңөұүһі-]+){1,2})"
ADDRESS = re.compile(NAME + r"\s*,?\s*(?:вам слово|расскажите|доложите|ответьте|прокомментируйте)", re.IGNORECASE)


def contextual_speaker_mapping(transcript: list[MergedSegment]) -> list[MergedSegment]:
    """Conservative fallback: map only a clear address to the next different speaker."""
    names: dict[str, tuple[str, float]] = {}
    for index, segment in enumerate(transcript[:-1]):
        match = ADDRESS.search(segment.text)
        if not match:
            continue
        for following in transcript[index + 1:index + 4]:
            if following.speaker_label != segment.speaker_label:
                names[following.speaker_label] = (match.group(1), 0.72)
                break
    labels = {segment.speaker_label for segment in transcript}
    ordinals = {label: index + 1 for index, label in enumerate(sorted(labels))}
    for segment in transcript:
        name, confidence = names.get(segment.speaker_label, (f"Speaker {ordinals[segment.speaker_label]}", 0.0))
        segment.speaker_name = name
        segment.speaker_confidence = confidence
    return transcript
