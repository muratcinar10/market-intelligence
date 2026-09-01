
import json,argparse,time
from pathlib import Path
from agents.fast_filter import classify
from core.event_builder import build_events
from agents.small_llm import SmallLLM
from agents.large_llm import LargeLLM

BASE=Path(__file__).parent

def load(path,limit=None):
    rows=[json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    return rows[:limit] if limit else rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",default=str(BASE/"data/tweets_10000.jsonl"))
    ap.add_argument("--limit",type=int,default=1000)
    ap.add_argument("--small-model",default="qwen3:1.7b")
    ap.add_argument("--large-model",default="qwen3:8b")
    ap.add_argument("--event-threshold",type=float,default=0.36)
    args=ap.parse_args()

    rows=load(args.input,args.limit)
    t0=time.time()

    candidates=[]
    discarded=0
    for r in rows:
        if classify(r["text"])=="discard":
            discarded+=1
        else:
            candidates.append(r)

    events=build_events(candidates,args.event_threshold)
    small=SmallLLM(args.small_model)
    large=LargeLLM(args.large_model)
    if not small.health():
        raise SystemExit(f"Small model not available. Run: ollama pull {args.small_model}")

    t1=time.time()
    small_results=small.classify_events(events)
    t2=time.time()
    by={int(x["event_id"]):x for x in small_results if "event_id" in x}

    ambiguous=[]
    for e in events:
        r=by.get(e["event_id"],{})
        if r.get("needs_large_model"):
            ambiguous.append(e)

    large_results=[]
    if ambiguous:
        large_results=large.analyze(ambiguous)
    t3=time.time()

    print("\n=== MARKET INTELLIGENCE v0.9 OPTIMIZED ===")
    print(f"Messages: {len(rows)}")
    print(f"Fast-discarded: {discarded}")
    print(f"Candidates after filter: {len(candidates)}")
    print(f"Events after clustering: {len(events)}")
    print(f"Small-model events: {len(events)}")
    print(f"Large-model escalations: {len(ambiguous)}")
    print(f"Prefilter+event build: {t1-t0:.1f}s")
    print(f"Small model elapsed: {t2-t1:.1f}s")
    print(f"Large model elapsed: {t3-t2:.1f}s")
    print(f"TOTAL elapsed: {t3-t0:.1f}s")

    out=BASE/"results/v09_summary.json"
    out.write_text(json.dumps({
        "messages":len(rows),"discarded":discarded,"candidates":len(candidates),
        "events":len(events),"large_escalations":len(ambiguous),
        "prefilter_seconds":t1-t0,"small_model_seconds":t2-t1,
        "large_model_seconds":t3-t2,"total_seconds":t3-t0
    },indent=2),encoding="utf-8")
    print(f"Saved: {out}")

if __name__=="__main__":
    main()
