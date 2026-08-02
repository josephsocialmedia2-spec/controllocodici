from __future__ import annotations

import unittest
from f1.advisor import LocalAdvisor


class AdvisorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.advisor = LocalAdvisor("")

    def test_non_interessato(self) -> None:
        advice = self.advisor.suggest("No grazie, non mi interessa.", [])
        self.assertEqual(advice.category, "NON_INTERESSATO")

    def test_no_signature(self) -> None:
        advice = self.advisor.suggest("Guardi che io non firmo niente.", [])
        self.assertEqual(advice.category, "NON_FIRMO")

    def test_custom_script_override(self) -> None:
        advisor = LocalAdvisor("[RISPOSTA:NON_INTERESSATO]\nRisposta personalizzata.")
        advice = advisor.suggest("Non sono interessato", [])
        self.assertEqual(advice.text, "Risposta personalizzata.")


if __name__ == "__main__":
    unittest.main()
