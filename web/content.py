"""Load and snapshot private lesson content."""
import copy
import json
import random
from pathlib import Path
from lessons.generators import GENERATORS

LEVELS = {
    "easy": {"label": "Лёгкий", "rate": 80, "questionCount": 7},
    "medium": {"label": "Средний", "rate": 100, "questionCount": 10},
    "hard": {"label": "Сложный", "rate": 120, "questionCount": 15},
}
LESSON = json.loads((Path(__file__).resolve().parents[1] / "lessons/basics.json").read_text(encoding="utf-8"))


def validate(question):
    q = copy.deepcopy(question)
    text = q.get("speechText")
    if not isinstance(text, str) or not text.strip() or len(text) > 3000:
        raise ValueError("Invalid speech text")
    choices = q.get("choices")
    if not isinstance(choices, list) or len(choices) < 4:
        raise ValueError("At least four choices required")
    for choice in choices:
        if not isinstance(choice, dict) or not isinstance(choice.get("id"), str) or not choice["id"]:
            raise ValueError("Invalid choice ID")
        if not isinstance(choice.get("label"), str) or not choice["label"].strip():
            raise ValueError("Text choices require labels")
        if "image" in choice and (not isinstance(choice["image"], str) or not choice["image"].startswith("/static/choices/") or ".." in choice["image"] or "?" in choice["image"] or "#" in choice["image"]):
            raise ValueError("Choice images must use /static/choices/ paths")
    if len({c["id"] for c in choices}) != len(choices) or len({c["label"].strip() for c in choices}) != len(choices):
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
    q.setdefault("choiceLayout", "long")
    if q["choiceLayout"] not in ("short", "long"):
        raise ValueError("Invalid choice layout")
    return q


def questions(level):
    settings = LEVELS[level]
    result = []
    for i in range(settings["questionCount"]):
        source = LESSON["sources"][i % len(LESSON["sources"])]
        q = validate(GENERATORS[source["generator"]]() if "generator" in source else source)
        correct = next(c for c in q["choices"] if c["id"] == q["correctChoiceId"])
        wrong = [c for c in q["choices"] if c["id"] != q["correctChoiceId"]]
        q["choices"] = [correct] + random.sample(wrong, 3)
        random.shuffle(q["choices"])
        q.update(id=f"q{i + 1}", rate=settings["rate"])
        result.append(q)
    return result
