"""Load and snapshot private lesson content."""
import copy
import json
from pathlib import Path
from lessons.generators import GENERATORS

LEVELS = {
    "easy": {"label": "Easy", "rate": 80, "questionCount": 7},
    "medium": {"label": "Medium", "rate": 100, "questionCount": 10},
    "hard": {"label": "Hard", "rate": 120, "questionCount": 15},
}
LESSON = json.loads((Path(__file__).resolve().parents[1] / "lessons/basics.json").read_text(encoding="utf-8"))


def validate(question):
    q = copy.deepcopy(question)
    text = q.get("speechText")
    if not isinstance(text, str) or not text.strip() or len(text) > 3000:
        raise ValueError("Invalid speech text")
    choices = q.get("choices")
    if not isinstance(choices, list) or len(choices) != 5:
        raise ValueError("Exactly five choices required")
    for choice in choices:
        if not isinstance(choice, dict) or not isinstance(choice.get("id"), str) or not choice["id"]:
            raise ValueError("Invalid choice ID")
        if not isinstance(choice.get("label"), str) or not choice["label"].strip():
            raise ValueError("Text choices require labels")
    if len({c["id"] for c in choices}) != 5 or len({c["label"].strip() for c in choices}) != 5:
        raise ValueError("Choices must be distinct")
    if "correctChoiceId" not in q:
        matches = [c["id"] for c in choices if c["label"].strip() == text.strip()]
        if len(matches) != 1:
            raise ValueError("Explicit correct choice required")
        q["correctChoiceId"] = matches[0]
    if q["correctChoiceId"] not in [c["id"] for c in choices]:
        raise ValueError("Correct choice must exist")
    q.setdefault("correctAnswerText", text)
    if not isinstance(q["correctAnswerText"], str) or not q["correctAnswerText"].strip():
        raise ValueError("Invalid feedback text")
    return q


def questions(level):
    settings = LEVELS[level]
    result = []
    for i in range(settings["questionCount"]):
        source = LESSON["sources"][i % len(LESSON["sources"])]
        q = validate(GENERATORS[source["generator"]]() if "generator" in source else source)
        q.update(id=f"q{i + 1}", rate=settings["rate"])
        result.append(q)
    return result
