import math
from enum import Enum


class Sign(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    ZERO = "zero"


def _validate(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("unsupported numeric input")
    if isinstance(value, float) and math.isnan(value):
        raise ValueError("NaN has no sign")


def classify(value):
    _validate(value)
    if value > 0:
        return Sign.POSITIVE.value
    if value < 0:
        return Sign.NEGATIVE.value
    return Sign.ZERO.value
