"""Trusted question generators. Never exposed as browser assets."""
import random

NUMBERS = ["ერთი", "ორი", "სამი", "ოთხი", "ხუთი", "ექვსი", "შვიდი", "რვა", "ცხრა", "ათი",
           "თერთმეტი", "თორმეტი", "ცამეტი", "თოთხმეტი", "თხუთმეტი", "თექვსმეტი",
           "ჩვიდმეტი", "თვრამეტი", "ცხრამეტი", "ოცი"]


def number_to_text(value):
    """Return the Georgian name of an integer from 1 through 20."""
    if type(value) is not int or not 1 <= value <= 20:
        raise ValueError("Number must be an integer from 1 to 20")
    return NUMBERS[value - 1]


def number():
    correct = random.randint(1, 20)
    offset = random.randint(max(0, correct - 17), min(3, correct - 1))
    start = correct - offset
    return {
        "choiceLayout": "short",
        "choices": [{"id": str(value), "text": number_to_text(value),
                     "translation": str(value), "isCorrect": value == correct}
                    for value in range(start, start + 4)],
    }


GENERATORS = {"number": number}
