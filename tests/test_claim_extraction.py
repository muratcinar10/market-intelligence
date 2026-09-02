import unittest
from unittest.mock import patch

from agents.claim_extractor import _extract_json, extract_claims
from core.domain import NormalizedMessage


class ClaimExtractionTests(unittest.TestCase):
    def test_extract_json_valid(self):
        raw = '{"claims":[{"statement":"AMD revenue was $11.5B"}]}'
        payload = _extract_json(raw)

        self.assertEqual(
            payload["claims"][0]["statement"],
            "AMD revenue was $11.5B",
        )

    def test_extract_json_from_wrapped_text(self):
        raw = 'Here is the result:\n{"claims":[{"statement":"NVDA revenue rose"}]}\nDone.'
        payload = _extract_json(raw)

        self.assertEqual(
            payload["claims"][0]["statement"],
            "NVDA revenue rose",
        )

    @patch("agents.claim_extractor._call_ollama")
    def test_financial_message_produces_claims(self, mocked_call):
        mocked_call.return_value = """
        {
          "claims": [
            {
              "statement": "AMD Q2 revenue was $11.5B",
              "entity": "AMD",
              "ticker": "AMD",
              "metric": "revenue",
              "value": "$11.5B",
              "period": "Q2",
              "event_type": "earnings",
              "speculative_extension": null
            },
            {
              "statement": "AMD data center revenue more than doubled",
              "entity": "AMD",
              "ticker": "AMD",
              "metric": "data_center_revenue",
              "value": "more than doubled",
              "period": null,
              "event_type": "earnings",
              "speculative_extension": null
            }
          ]
        }
        """

        message = NormalizedMessage(
            id="msg-amd",
            source="test",
            text="AMD Q2 revenue was $11.5B and data center revenue more than doubled.",
        )

        result = extract_claims(message)

        self.assertTrue(result.has_claims)
        self.assertEqual(len(result.claims), 2)
        self.assertEqual(result.claims[0].ticker, "AMD")

    @patch("agents.claim_extractor._call_ollama")
    def test_opinion_only_message_has_no_claims(self, mocked_call):
        mocked_call.return_value = '{"claims":[]}'

        message = NormalizedMessage(
            id="msg-nvda",
            source="test",
            text="NVDA to the moon 🚀",
        )

        result = extract_claims(message)

        self.assertFalse(result.has_claims)
        self.assertEqual(result.claims, [])

    @patch("agents.claim_extractor._call_ollama")
    def test_speculative_extension_is_separated(self, mocked_call):
        mocked_call.return_value = """
        {
          "claims": [
            {
              "statement": "Tesla delivered 480126 vehicles",
              "entity": "Tesla",
              "ticker": "TSLA",
              "metric": "deliveries",
              "value": "480126",
              "period": null,
              "event_type": "deliveries",
              "speculative_extension": "the stock will definitely explode"
            }
          ]
        }
        """

        message = NormalizedMessage(
            id="msg-tsla",
            source="test",
            text="Tesla delivered 480126 vehicles, so the stock will definitely explode.",
        )

        result = extract_claims(message)

        self.assertEqual(len(result.claims), 1)
        self.assertEqual(
            result.claims[0].speculative_extension,
            "the stock will definitely explode.",
        )

    def test_extract_json_after_thinking_block(self):
        raw = """Thinking...
some reasoning
...done thinking.

{
  "claims": [
    {
      "statement": "Amazon may acquire a startup"
    }
  ]
}
"""
        payload = _extract_json(raw)

        self.assertEqual(len(payload["claims"]), 1)
        self.assertEqual(
            payload["claims"][0]["statement"],
            "Amazon may acquire a startup",
        )

    def test_extract_json_prefers_claim_object(self):
        raw = """
junk {"foo": "bar"}
more junk
{"claims":[{"statement":"Tesla delivered 480126 vehicles"}]}
"""
        payload = _extract_json(raw)

        self.assertEqual(len(payload["claims"]), 1)


if __name__ == "__main__":
    unittest.main()
