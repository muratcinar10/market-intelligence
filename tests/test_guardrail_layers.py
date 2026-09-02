import unittest

from core.claim_guardrails import filter_truth_claims
from core.claim_segmenter import segment_message
from core.domain import Claim
from core.text_signals import analyze_text


class GuardrailLayerTests(unittest.TestCase):
    def test_prediction_signal_english(self):
        signals = analyze_text("NVDA will hit $300 before Christmas.")
        self.assertTrue(signals.prediction)

    def test_prediction_signal_turkish(self):
        signals = analyze_text("THYAO yıl sonuna kadar ikiye katlanacak.")
        self.assertTrue(signals.prediction)

    def test_rumor_not_treated_as_simple_prediction(self):
        signals = analyze_text(
            "Sources say Apple may acquire an AI startup."
        )
        self.assertTrue(signals.rumor)

    def test_inference_signal(self):
        signals = analyze_text(
            "Revenue rose 30%, which means demand is unstoppable."
        )
        self.assertTrue(signals.inference)

    def test_opinion_signal(self):
        signals = analyze_text("META is ridiculously undervalued here.")
        self.assertTrue(signals.opinion)

    def test_sarcasm_hint(self):
        signals = analyze_text(
            "Sure, a 40% revenue decline is exactly what shareholders wanted."
        )
        self.assertTrue(signals.sarcasm_hint)

    def test_segment_sentences(self):
        parts = segment_message(
            "AMD launched MI450 today. NVIDIA should be worried."
        )
        self.assertEqual(len(parts), 2)

    def test_segment_while(self):
        parts = segment_message(
            "Revenue rose 20% while margins fell 4%."
        )
        self.assertEqual(len(parts), 2)

    def test_prediction_claim_is_blocked(self):
        claim = Claim(
            id="c1",
            message_id="m1",
            statement="THYAO will double",
            ticker="THYAO",
            event_type="price_prediction",
        )

        signals = analyze_text("THYAO will double from here.")

        result = filter_truth_claims([claim], signals)

        self.assertEqual(result, [])

    def test_factual_claim_survives(self):
        claim = Claim(
            id="c2",
            message_id="m2",
            statement="AMD revenue rose 20%",
            ticker="AMD",
            event_type="earnings",
        )

        signals = analyze_text("AMD revenue rose 20%.")

        result = filter_truth_claims([claim], signals)

        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
