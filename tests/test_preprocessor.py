import unittest

from core.preprocessor import preprocess_message


class PreprocessorTests(unittest.TestCase):
    def test_pure_prediction_is_blocked(self):
        result = preprocess_message(
            "THYAO yıl sonuna kadar ikiye katlanacak."
        )

        self.assertEqual(len(result), 1)
        self.assertFalse(result[0].should_extract)
        self.assertEqual(result[0].kind, "prediction_only")

    def test_pure_opinion_is_blocked(self):
        result = preprocess_message(
            "META is ridiculously undervalued here."
        )

        self.assertEqual(len(result), 1)
        self.assertFalse(result[0].should_extract)

    def test_fact_plus_opinion_separates(self):
        result = preprocess_message(
            "AMD launched its MI450 accelerator today. Honestly, NVIDIA should be worried."
        )

        extractable = [r for r in result if r.should_extract]

        self.assertEqual(len(extractable), 1)
        self.assertIn("AMD launched", extractable[0].text)

    def test_turkish_fact_plus_opinion(self):
        result = preprocess_message(
            "AKBNK net faiz marjını 120 baz puan artırdı. Yönetim sonunda işini yapıyor."
        )

        extractable = [r for r in result if r.should_extract]

        self.assertEqual(len(extractable), 1)

    def test_explicit_inference_attached(self):
        result = preprocess_message(
            "Google Cloud revenue grew 29% YoY, which means AWS is losing the AI war."
        )

        extractable = [r for r in result if r.should_extract]
        inference = [
            r for r in result
            if r.context_type == "inference"
        ]

        self.assertEqual(len(extractable), 1)
        self.assertEqual(len(inference), 1)
        self.assertFalse(inference[0].should_extract)
        self.assertEqual(
            inference[0].text.rstrip("."),
            "AWS is losing the AI war",
        )

    def test_rumor_is_extractable(self):
        result = preprocess_message(
            "Sources say Apple is considering acquiring an AI startup for about $6 billion."
        )

        self.assertTrue(result[0].should_extract)
        self.assertEqual(result[0].kind, "rumor_candidate")

    def test_sarcastic_prefix_removed(self):
        result = preprocess_message(
            "Amazing performance: margins fell from 18% to 11%."
        )

        self.assertTrue(result[0].should_extract)
        self.assertEqual(
            result[0].text.rstrip("."),
            "margins fell from 18% to 11%",
        )


if __name__ == "__main__":
    unittest.main()
