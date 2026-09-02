
import unittest

from datetime import datetime

from core.domain import (

    Claim,

    Evidence,

    EvidenceRelation,

    NormalizedMessage,

    TruthDecision,

    TruthStatus,

)

class DomainModelTests(unittest.TestCase):

    def test_normalized_message(self):

        message = NormalizedMessage(

            id="msg-1",

            source="reddit",

            text="NVDA reported new results",

            published_at=datetime(2026, 9, 2),

            ticker="NVDA",

            engagement={"upvotes": 120},

        )

        self.assertEqual(message.source, "reddit")

        self.assertEqual(message.ticker, "NVDA")

        self.assertEqual(message.engagement["upvotes"], 120)

    def test_claim_and_evidence(self):

        claim = Claim(

            id="claim-1",

            message_id="msg-1",

            statement="Data Center revenue increased 117% YoY",

            ticker="NVDA",

            metric="data_center_revenue",

            value="+117% YoY",

            event_type="earnings",

        )

        evidence = Evidence(

            id="evidence-1",

            claim_id=claim.id,

            source="company_ir",

            text="Official earnings release confirms the reported figure.",

            relation=EvidenceRelation.SUPPORTS,

        )

        self.assertEqual(evidence.claim_id, claim.id)

        self.assertEqual(evidence.relation, EvidenceRelation.SUPPORTS)

    def test_truth_confidence_bounds(self):

        decision = TruthDecision(

            claim_id="claim-1",

            status=TruthStatus.VERIFIED,

            confidence=0.97,

            reason="Supported by primary-source evidence.",

        )

        self.assertEqual(decision.status, TruthStatus.VERIFIED)

        with self.assertRaises(ValueError):

            TruthDecision(

                claim_id="claim-2",

                status=TruthStatus.FALSE,

                confidence=1.5,

                reason="invalid confidence",

            )

if __name__ == "__main__":

    unittest.main()

