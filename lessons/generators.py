"""Trusted question generators. Never exposed as browser assets."""

import random

NUMBERS = [
    "ერთი",
    "ორი",
    "სამი",
    "ოთხი",
    "ხუთი",
    "ექვსი",
    "შვიდი",
    "რვა",
    "ცხრა",
    "ათი",
    "თერთმეტი",
    "თორმეტი",
    "ცამეტი",
    "თოთხმეტი",
    "თხუთმეტი",
    "თექვსმეტი",
    "ჩვიდმეტი",
    "თვრამეტი",
    "ცხრამეტი",
    "ოცი",
]


def number_to_text(value):
    """Return the Georgian name of an integer from 0 through 1000."""
    if type(value) is not int or not 0 <= value <= 1000:
        raise ValueError("Number must be an integer from 0 to 1000")
    if value == 0:
        return "ნული"
    if value <= 20:
        return NUMBERS[value - 1]
    if value == 1000:
        return "ათასი"
    if value >= 100:
        hundreds, remainder = divmod(value, 100)
        word = ("ასი", "ორასი", "სამასი", "ოთხასი", "ხუთასი",
                "ექვსასი", "შვიდასი", "რვაასი", "ცხრაასი")[hundreds - 1]
        return word if not remainder else word[:-1] + " " + number_to_text(remainder)
    twenties, remainder = divmod(value, 20)
    word = ("ოცი", "ორმოცი", "სამოცი", "ოთხმოცი")[twenties - 1]
    return word if not remainder else word[:-1] + "და" + number_to_text(remainder)


def fractional_number_to_text(whole, hundredths):
    """Join two integer names; 3.05 is spoken as three five, not three zero five."""
    if any(type(part) is not int or not 0 <= part <= 99
           for part in (whole, hundredths)):
        raise ValueError("Fraction parts must be integers from 0 to 99")
    return number_to_text(whole) + " " + number_to_text(hundredths)


def number(maximum=20):
    """Ask for a Georgian number with four consecutive digit choices."""
    correct = random.randint(1, maximum)
    offset = random.randint(max(0, correct - maximum + 3), min(3, correct - 1))
    start = correct - offset
    return {
        "choiceLayout": "short",
        "choices": [
            {
                "text": number_to_text(value),
                "translation": str(value),
                "isCorrect": value == correct,
            }
            for value in range(start, start + 4)
        ],
    }


SEMI_ROUND_OFFSETS = (-15, -10, -5, 0, 5, 10, 15)
ALL_NUMBER_OFFSETS = (-21, -20, -19, -11, -10, -9, -1, 0, 1, 9, 10, 11, 19, 20, 21)


def mutations(value, minimum, maximum, offsets):
    """Keep only mutations inside the part's range, without wrapping or carrying."""
    return [value + offset for offset in offsets
            if minimum <= value + offset <= maximum]


def integer_question(maximum, semi_round=False):
    minimum, step = (20, 5) if semi_round else (0, 1)
    correct = random.randrange(minimum, maximum + 1, step)
    offsets = SEMI_ROUND_OFFSETS if semi_round else ALL_NUMBER_OFFSETS
    return {
        "choiceLayout": "short",
        "choices": [
            {"text": number_to_text(value), "translation": str(value),
             "isCorrect": value == correct}
            for value in mutations(correct, minimum, maximum, offsets)
        ],
    }


def fractional_question(maximum_whole, semi_round=False):
    whole = random.randrange(maximum_whole + 1)
    hundredths = random.randrange(0, 100, 5 if semi_round else 1)
    offsets = SEMI_ROUND_OFFSETS if semi_round else ALL_NUMBER_OFFSETS
    return {
        "choiceLayout": "short",
        "choices": [
            {"text": fractional_number_to_text(w, h),
             "translation": f"{w}.{h:02d}",
             "isCorrect": (w, h) == (whole, hundredths)}
            for w in mutations(whole, 0, maximum_whole, offsets)
            for h in mutations(hundredths, 0, 99, offsets)
        ],
    }


GENERATORS = {
    "number": number,
    "number-1-10": lambda: number(10),
    "number-1-20": lambda: number(20),
    "number-20-100-semi-round": lambda: integer_question(100, True),
    "number-0-100": lambda: integer_question(100),
    "number-20-1000-semi-round": lambda: integer_question(1000, True),
    "number-0-1000": lambda: integer_question(1000),
    "fraction-9-99-semi-round": lambda: fractional_question(9, True),
    "fraction-9-99": lambda: fractional_question(9),
    "fraction-99-99-semi-round": lambda: fractional_question(99, True),
    "fraction-99-99": lambda: fractional_question(99),
}
