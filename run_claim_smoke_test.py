from agents.claim_extractor import extract_claims
from core.domain import NormalizedMessage


CASES = [
    {
        "id": "c1",
        "text": "AMD Q2 revenue was $11.5B and data center revenue more than doubled.",
        "expected_claims": 2,
        "expect_speculative": False,
    },
    {
        "id": "c2",
        "text": "NVDA to the moon 🚀",
        "expected_claims": 0,
        "expect_speculative": False,
    },
    {
        "id": "c3",
        "text": "Tesla delivered 480126 vehicles, so the stock will definitely explode.",
        "expected_claims": 1,
        "expect_speculative": True,
    },
    {
        "id": "c4",
        "text": "Apple announced a new $100 billion share buyback.",
        "expected_claims": 1,
        "expect_speculative": False,
    },
    {
        "id": "c5",
        "text": "Meta is trash, management has no idea what they are doing.",
        "expected_claims": 0,
        "expect_speculative": False,
    },
    {
        "id": "c6",
        "text": "Microsoft cloud revenue grew 27% year over year.",
        "expected_claims": 1,
        "expect_speculative": False,
    },
    {
        "id": "c7",
        "text": "Rumor says Amazon may acquire a robotics startup for $4B.",
        "expected_claims": 1,
        "expect_speculative": False,
    },
    {
        "id": "c8",
        "text": "TSMC reported August revenue up 33% YoY, which means NVIDIA demand is unstoppable.",
        "expected_claims": 1,
        "expect_speculative": True,
    },
    {
        "id": "c9",
        "text": "ASELSAN signed a 2.1 billion TL contract.",
        "expected_claims": 1,
        "expect_speculative": False,
    },
    {
        "id": "c10",
        "text": "THYAO will double from here. Easy money.",
        "expected_claims": 0,
        "expect_speculative": False,
    },
]


def main():
    claim_count_correct = 0
    speculative_correct = 0

    for case in CASES:
        message = NormalizedMessage(
            id=case["id"],
            source="smoke_test",
            text=case["text"],
        )

        result = extract_claims(message, model="qwen3:1.7b")

        actual_count = len(result.claims)
        count_ok = actual_count == case["expected_claims"]

        has_speculative = any(
            bool(c.speculative_extension)
            for c in result.claims
        )

        speculative_ok = has_speculative == case["expect_speculative"]

        claim_count_correct += int(count_ok)
        speculative_correct += int(speculative_ok)

        print("=" * 80)
        print("TEXT:", case["text"])
        print("EXPECTED CLAIMS:", case["expected_claims"])
        print("ACTUAL CLAIMS:", actual_count)
        print("COUNT OK:", count_ok)
        print("EXPECTED SPECULATIVE:", case["expect_speculative"])
        print("ACTUAL SPECULATIVE:", has_speculative)
        print("SPECULATIVE OK:", speculative_ok)

        for idx, claim in enumerate(result.claims, 1):
            print(f"  CLAIM {idx}:")
            print("    statement:", claim.statement)
            print("    entity:", claim.entity)
            print("    ticker:", claim.ticker)
            print("    metric:", claim.metric)
            print("    value:", claim.value)
            print("    period:", claim.period)
            print("    event_type:", claim.event_type)
            print("    speculative_extension:", claim.speculative_extension)

        print("RAW:", result.raw_model_output)

    total = len(CASES)

    print("\n=== CLAIM SMOKE TEST SUMMARY ===")
    print(f"Cases: {total}")
    print(f"Claim-count accuracy: {claim_count_correct}/{total} = {claim_count_correct/total:.1%}")
    print(f"Speculative-separation accuracy: {speculative_correct}/{total} = {speculative_correct/total:.1%}")


if __name__ == "__main__":
    main()
