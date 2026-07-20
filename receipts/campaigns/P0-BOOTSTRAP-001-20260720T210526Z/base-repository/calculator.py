def classify(value):
    """Classify a number by sign. The seed intentionally mishandles zero."""
    return "positive" if value > 0 else "negative"
