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
LESSON_DIR = Path(__file__).resolve().parents[1] / "lessons"


def load_lesson(path):
    lesson = json.loads(path.read_text(encoding="utf-8"))
    eligible_sources("medium", lesson)
    resolved = []
    question_dir = (path.parent / "questions").resolve()
    for source in lesson["sources"]:
        if not isinstance(source, dict) or set(source) - {
            "question",
            "generator",
            "level",
        }:
            raise ValueError(f"{path}: invalid source reference")
        if ("question" in source) == ("generator" in source):
            raise ValueError(f"{path}: source requires a question or generator")
        source_level(source)
        if "question" in source:
            name = source["question"]
            if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", name):
                raise ValueError(f"{path}: invalid question reference")
            question_path = (question_dir / f"{name}.json").resolve()
            if question_path.parent != question_dir:
                raise ValueError(f"{path}: question must stay in questions directory")
            question = validate(json.loads(question_path.read_text(encoding="utf-8")))
            # Keep an omitted level implicit so its default is lesson-specific.
            question.pop("level", None)
            if "level" in source:
                question["level"] = source_level(source)
            resolved.append(question)
        else:
            if (
                not isinstance(source["generator"], str)
                or source["generator"] not in GENERATORS
            ):
                raise ValueError(f"{path}: unknown generator")
            resolved.append(copy.deepcopy(source))
    lesson["sources"] = resolved
    return lesson


def source_level(source, default=2):
    value = source.get("level", default)
    if type(value) is not int or value < 1:
        raise ValueError("Source level must be a positive integer")
    return value


def eligible_sources(level, lesson):
    if not isinstance(lesson, dict):
        raise ValueError("Lesson must be an object")
    sources = lesson.get("sources")
    if not isinstance(sources, list) or not sources or not all(
        isinstance(s, dict) for s in sources
    ):
        raise ValueError("Lesson requires sources")
    default = 2 if any(s.get("level") == 1 for s in sources) else 1
    return [s for s in sources if source_level(s, default) == 1 or level != "easy"]


def available_levels(lesson):
    return [level for level in LEVELS if eligible_sources(level, lesson)]


def validate(question, generated=False):
    if not isinstance(question, dict):
        raise ValueError("Question must be an object")
    q = copy.deepcopy(question)
    choices = q.get("choices")
    if not isinstance(choices, list) or len(choices) < (1 if generated else 4):
        raise ValueError("Question requires choices (at least four for static pools)")
    # A generator may reuse the same dictionary for several choice slots.
    choices = q["choices"] = [copy.deepcopy(choice) for choice in choices]
    for choice in choices:
        if not isinstance(choice, dict):
            raise ValueError("Choice must be an object")
        choice.pop("id", None)
        for field in ("text", "translation"):
            if (
                not isinstance(choice.get(field), str)
                or not choice[field].strip()
                or len(choice[field]) > 3000
            ):
                raise ValueError("Choices require text and translation")
        choice.setdefault("speechText", choice["text"])
        if (
            not isinstance(choice["speechText"], str)
            or not choice["speechText"].strip()
            or len(choice["speechText"]) > 3000
        ):
            raise ValueError("Invalid speech text")
        if "isCorrect" in choice and type(choice["isCorrect"]) is not bool:
            raise ValueError("Invalid correct marker")
        if "image" in choice and (
            not isinstance(choice["image"], str)
            or not re.fullmatch(r"[a-z]+(?:-[a-z]+)*\.jpg", choice["image"])
        ):
            raise ValueError(
                "Choice image must be an English word with a .jpg extension"
            )
    marked = [c for c in choices if c.get("isCorrect")]
    if (generated and not marked) or (not generated and marked):
        raise ValueError("Only generated questions require correct markers")
    if generated and len({c["text"].strip() for c in marked}) > 1:
        raise ValueError("Correct markers must agree on Georgian text")
    q.setdefault("choiceLayout", "long")
    if q["choiceLayout"] not in ("short", "long"):
        raise ValueError("Invalid choice layout")
    return q


def generate(source, static):
    """Retry a broken generator once, then use any static pool."""
    for _ in range(2):
        try:
            q = validate(GENERATORS[source["generator"]](), generated=True)
            while len(q["choices"]) < 4:
                q["choices"].append(copy.deepcopy(random.choice(q["choices"])))
            return q, True
        except Exception:
            # Trusted generators can raise arbitrary exceptions or return bad data.
            pass
    if static:
        return copy.deepcopy(random.choice(static)), False
    raise ValueError("Generator failed twice and no static questions are available")


def questions(level, lesson=None):
    settings = LEVELS[level]
    lesson = LESSON if lesson is None else lesson
    result = []
    used = set()
    sources = eligible_sources(level, lesson)
    static = [validate(s) for s in sources if "generator" not in s]
    generators = [s for s in sources if "generator" in s]
    # Fallback may ignore difficulty and previously used answers.
    fallback = [validate(s) for s in lesson["sources"] if "generator" not in s]
    if not static and not generators:
        raise ValueError("Lesson requires at least one source")
    for i in range(settings["questionCount"]):
        available = [
            q
            for q in static
            if any(c["text"].strip() not in used for c in q["choices"])
        ]
        sources = available + generators
        if not sources:
            # Start a new cycle after every static answer has been used.
            used.clear()
            available = static
            sources = static + generators
        for _ in range(100):
            source = random.choice(sources)
            generated = "generator" in source
            if generated:
                q, generated = generate(source, fallback)
                if not generated:
                    correct = random.choice(q["choices"])
                    break
                candidates = [c for c in q["choices"] if c.get("isCorrect")]
            else:
                q = copy.deepcopy(source)
                candidates = [c for c in q["choices"] if c["text"].strip() not in used]
            correct = random.choice(candidates)
            if correct["text"].strip() not in used:
                break
        else:
            if available:
                # Do not let an exhausted generator hide unused vocabulary.
                q = copy.deepcopy(random.choice(available))
                correct = random.choice(
                    [c for c in q["choices"] if c["text"].strip() not in used]
                )
            else:
                # A generator's output space is unknown. Bounded retries keep
                # exhausted or very repetitive generators from blocking a lesson.
                used.clear()
        used.add(correct["text"].strip())
        others = [c for c in q["choices"] if c is not correct]
        q["choices"] = [correct] + random.sample(others, 3)
        random.shuffle(q["choices"])
        for index, choice in enumerate(q["choices"]):
            choice["id"] = str(index)
        q.update(
            id=f"q{i + 1}",
            rate=settings["rate"],
            correctChoiceId=correct["id"],
            correctText=correct["text"].strip(),
            speechText=correct["speechText"],
            correctAnswerText=f'{correct["text"]} ({correct["translation"]})',
        )
        result.append(q)
    return result


LESSONS = {
    lesson["id"]: lesson
    for lesson in (
        load_lesson(LESSON_DIR / name)
        for name in (
            "basics.json",
            "numbers.json",
            "animals.json",
            "city.json",
            "documents-state-government-law.json",
            "food-products.json",
            "fruits-and-vegetables.json",
            "weather-and-nature.json",
        )
    )
}
LESSON = LESSONS["basics"]
