import unittest

from calculator import classify


class AdversarialContractTests(unittest.TestCase):
    def test_boolean_is_not_silently_treated_as_one(self):
        with self.assertRaises(TypeError):
            classify(True)

    def test_nan_has_no_sign(self):
        with self.assertRaises(ValueError):
            classify(float("nan"))

    def test_string_is_rejected(self):
        with self.assertRaises(TypeError):
            classify("7")


if __name__ == "__main__":
    unittest.main()
