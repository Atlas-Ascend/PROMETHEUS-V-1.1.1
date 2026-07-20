import unittest

from calculator import classify


class CalculatorTests(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(classify(7), "positive")

    def test_negative(self):
        self.assertEqual(classify(-3), "negative")

    def test_zero(self):
        self.assertEqual(classify(0), "zero")


if __name__ == "__main__":
    unittest.main()
