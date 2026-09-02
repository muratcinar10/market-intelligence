import unittest
from unittest.mock import patch

from agents.claim_extractor import extract_claims
from core.domain import ContextType, NormalizedMessage


class NonFactualContextTests(unittest.TestCase):
    @patch("agents.claim_extractor._call_ollama")
    def test_prediction_is_context_not_claim(self, mocked_call):
        mocked_call.return_value = '{"claims":[]}'

        message = NormalizedMessage(
            id="m1",
            source="test",
            text="THYAO yıl sonuna kadar ikiye katlanacak.",
        )

        result = extract_claims(message)

        self.assertEqual(result.claims, [])
        self.assertEqual(len(result.contexts), 1)
        self.assertEqual(
            result.contexts[0].context_type,
            ContextType.PREDICTION,
        )

    @patch("agents.claim_extractor._call_ollama")
    def test_opinion_is_context_not_claim(self, mocked_call):
        mocked_call.return_value = '{"claims":[]}'

        message = NormalizedMessage(
            id="m2",
            source="test",
            text="META is ridiculously undervalued here.",
        )

        result = extract_claims(message)

        self.assertEqual(result.claims, [])
        self.assertEqual(len(result.contexts), 1)
        self.assertEqual(
            result.contexts[0].context_type,
            ContextType.OPINION,
        )

    @patch("agents.claim_extractor._call_ollama")
    def test_inference_links_to_claim(self, mocked_call):
        mocked_call.return_value = """
        {
          "claims": [
            {
              "statement": "TSMC revenue rose 33% YoY",
              "entity": "TSMC",
              "ticker": "TSM",
              "metric": "revenue_growth",
              "value": "33% YoY",
              "period": null,
              "event_type": "monthly_revenue",
              "speculative_extension": null
            }
          ]
        }
        """

        message = NormalizedMessage(
            id="m3",
            source="test",
            text="TSMC revenue rose 33% YoY, which means NVIDIA demand is unstoppable.",
        )

        result = extract_claims(message)

        self.assertEqual(len(result.claims), 1)
        self.assertEqual(len(result.contexts), 1)
        self.assertEqual(
            result.contexts[0].context_type,
            ContextType.INFERENCE,
        )
        self.assertEqual(
            result.contexts[0].related_claim_ids,
            [result.claims[0].id],
        )


if __name__ == "__main__":
    unittest.main()
