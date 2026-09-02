import unittest

from core.claim_guardrails import filter_truth_claims
from core.domain import Claim
from core.preprocessor import preprocess_message
from core.text_signals import analyze_text


class Sprint17GuardTests(unittest.TestCase):
    def test_hype_statement_is_blocked(self):
        claim = Claim(
            id="c1",
            message_id="m1",
            statement="Nothing can stop this stock",
            entity="AVGO",
            ticker="AVGO",
        )

        result = filter_truth_claims(
            [claim],
            analyze_text("Nothing can stop this stock."),
        )

        self.assertEqual(result, [])

    def test_two_measurable_facts_are_split(self):
        result = preprocess_message(
            "Amazon revenue rose 13% and AWS operating income increased 22% in Q2."
        )

        extractable = [x for x in result if x.should_extract]

        self.assertEqual(len(extractable), 2)
        self.assertIn("Amazon revenue rose 13%", extractable[0].text)
        self.assertIn("AWS operating income increased 22%", extractable[1].text)

    def test_trailing_so_clause_becomes_inference(self):
        result = preprocess_message(
            "Adobe revenue grew 10%, operating margin reached 46%, so bears are officially dead."
        )

        inference = [
            x for x in result
            if x.context_type == "inference"
        ]

        self.assertEqual(len(inference), 1)
        self.assertFalse(inference[0].should_extract)
        self.assertEqual(
            inference[0].text.rstrip("."),
            "bears are officially dead",
        )


if __name__ == "__main__":
    unittest.main()
