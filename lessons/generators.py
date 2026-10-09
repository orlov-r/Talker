"""Trusted question generators. Never exposed as browser assets."""
import random

NUMBERS = ["ერთი", "ორი", "სამი", "ოთხი", "ხუთი", "ექვსი", "შვიდი", "რვა", "ცხრა", "ათი",
           "თერთმეტი", "თორმეტი", "ცამეტი", "თოთხმეტი", "თხუთმეტი", "თექვსმეტი",
           "ჩვიდმეტი", "თვრამეტი", "ცხრამეტი", "ოცი"]


def number():
    values = random.sample(range(1, 21), 5)
    correct = random.choice(values)
    return {
        "speechText": NUMBERS[correct - 1],
        "correctAnswerText": f"{NUMBERS[correct - 1]} ({correct})",
        "correctChoiceId": str(correct),
        "choices": [{"id": str(value), "label": str(value)} for value in values],
    }


GENERATORS = {"number": number}
