"""Quiz selection and transitions, independent of HTTP and storage.

Call transitions while holding the attempt store's transaction lock.
"""

from web.content import LESSONS, LEVELS, questions


class QuizConflict(Exception):
    """The requested transition is not valid for the current question."""


class InvalidSelection(Exception):
    """The requested lesson, level, or voice is unavailable."""


def validate_selection(level, lesson_id, voice, voices):
    if not isinstance(voice, str) or voice not in voices:
        raise InvalidSelection("Выберите доступный голос.")
    if (
        not isinstance(level, str)
        or level not in LEVELS
        or not isinstance(lesson_id, str)
        or lesson_id not in LESSONS
    ):
        raise InvalidSelection("Выберите доступный уровень и урок.")


def prepare_questions(level, lesson_id):
    lesson = LESSONS[lesson_id]
    if not isinstance(lesson, dict):
        raise ValueError("Lesson must be an object")
    return questions(level, lesson)


def answer(a, question_id, choice_id):
    if a["index"] >= len(a["questions"]):
        raise QuizConflict("Урок завершён.")
    q = a["questions"][a["index"]]
    if question_id != q["id"] or choice_id not in [c["id"] for c in q["choices"]]:
        raise QuizConflict("Недопустимый вопрос или вариант ответа.")
    if q["id"] not in a["audioReady"]:
        raise QuizConflict("Прослушайте аудио перед ответом.")
    if a["feedback"] is None:
        selected = next(c for c in q["choices"] if c["id"] == choice_id)
        correct = selected["text"].strip() == q["correctText"]
        a["score"] += int(correct)
        a["feedback"] = {
            "isCorrect": correct,
            "correctAnswerText": q["correctAnswerText"],
            "selectedChoiceId": choice_id,
            "correctChoiceIds": [
                c["id"] for c in q["choices"]
                if c["text"].strip() == q["correctText"]
            ],
            "choiceTexts": {c["id"]: c["text"] for c in q["choices"]},
        }
    return a["feedback"]


def advance(a, question_id):
    if (
        a["index"] >= len(a["questions"])
        or question_id != a["questions"][a["index"]]["id"]
        or a["feedback"] is None
    ):
        raise QuizConflict("Ответьте на текущий вопрос, прежде чем продолжить.")
    a["index"] += 1
    a["feedback"] = None


def require_complete(a):
    if a["index"] != len(a["questions"]):
        raise QuizConflict("Урок ещё не завершён.")
