
from collections import defaultdict

def build_prediction_ledger(rows):
    ledger=[]
    for r in rows:
        a=r["analysis"]
        if not a.get("keep"):
            continue
        if a.get("direction") not in {"bullish","bearish"}:
            continue
        ledger.append({
            "message_id":r["id"],
            "author":r["author"],
            "ticker":r["ticker"],
            "direction":a["direction"],
            "confidence":a.get("confidence",0),
            "importance":a.get("importance",0),
            "synthetic_outcome":r.get("outcome","unresolved")
        })
    return ledger

def score_ledger(ledger):
    by=defaultdict(lambda:{"success":0,"fail":0,"unresolved":0})
    for x in ledger:
        by[x["author"]][x["synthetic_outcome"]]+=1
    return by
