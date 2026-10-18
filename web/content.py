"""Load and snapshot private lesson content."""
import copy
import json
import random
import re
from pathlib import Path
from lessons.generators import GENERATORS

LEVELS = {
    "easy": {"label": "Лёгкий", "rate": 80, "questionCount": 7},
    "medium": {"label": "Средний", "rate": 100, "questionCount": 10},
    "hard": {"label": "Сложный", "rate": 120, "questionCount": 15},
}
LESSON = json.loads((Path(__file__).resolve().parents[1] / "lessons/basics.json").read_text(encoding="utf-8"))


def validate(question, generated=False):
    q = copy.deepcopy(question)
    choices = q.get("choices")
    if not isinstance(choices, list) or len(choices) < 4:
        raise ValueError("At least four choices required")
    for choice in choices:
        if not isinstance(choice, dict) or not isinstance(choice.get("id"), str) or not choice["id"]:
            raise ValueError("Invalid choice ID")
        for field in ("text", "translation"):
            if not isinstance(choice.get(field), str) or not choice[field].strip() or len(choice[field]) > 3000:
                raise ValueError("Choices require text and translation")
        choice.setdefault("speechText", choice["text"])
        if not isinstance(choice["speechText"], str) or not choice["speechText"].strip() or len(choice["speechText"]) > 3000:
            raise ValueError("Invalid speech text")
        if "isCorrect" in choice and type(choice["isCorrect"]) is not bool:
            raise ValueError("Invalid correct marker")
        if "image" in choice and (not isinstance(choice["image"], str) or not re.fullmatch(r"[A-Za-z0-9_-]+\.(?:png|jpg|jpeg|webp)", choice["image"])):
            raise ValueError("Choice image must be a local image filename")
    for field in ("id", "text", "translation"):
        if len({c[field].strip() for c in choices}) != len(choices):
            raise ValueError("Choices must be distinct")
    marked = [c for c in choices if c.get("isCorrect")]
    if (generated and len(marked) != 1) or (not generated and marked):
        raise ValueError("Only generated questions require one correct marker")
    q.setdefault("choiceLayout", "long")
    if q["choiceLayout"] not in ("short", "long"):
        raise ValueError("Invalid choice layout")
    return q


def questions(level):
    settings = LEVELS[level]
    result, used = [], set()
    static = [validate(s) for s in LESSON["sources"] if "generator" not in s]
    generators = [s for s in LESSON["sources"] if "generator" in s]
    for i in range(settings["questionCount"]):
        for _ in range(1000):
            available = [q for q in static if any(c["text"].strip() not in used for c in q["choices"])]
            sources = available + generators
            if not sources:
                raise ValueError("Not enough distinct correct answers")
            source = random.choice(sources)
            generated = "generator" in source
            q = validate(GENERATORS[source["generator"]](), generated=True) if generated else copy.deepcopy(source)
            candidates = [c for c in q["choices"] if c.get("isCorrect")] if generated else [c for c in q["choices"] if c["text"].strip() not in used]
            correct = random.choice(candidates)
            if correct["text"].strip() not in used:
                break
        else:
            raise ValueError("Could not generate a distinct correct answer")
        used.add(correct["text"].strip())
        wrong = [c for c in q["choices"] if c["id"] != correct["id"]]
        q["choices"] = [correct] + random.sample(wrong, 3)
        random.shuffle(q["choices"])
        q.update(id=f"q{i + 1}", rate=settings["rate"], correctChoiceId=correct["id"],
                 speechText=correct["speechText"],
                 correctAnswerText=f'{correct["text"]} ({correct["translation"]})')
        result.append(q)
    return result
