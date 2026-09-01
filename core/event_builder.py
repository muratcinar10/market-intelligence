
import re
from collections import defaultdict

STOP={"ve","ile","için","bir","bu","the","and","of","to","in","is","may","can","son","yeni"}

def toks(text):
    return {x for x in re.findall(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+",(text or "").lower())
            if len(x)>2 and x not in STOP}

def jaccard(a,b):
    if not a or not b: return 0.0
    return len(a & b)/len(a | b)

def build_events(rows, threshold=0.36):
    events=[]
    for r in rows:
        tt=toks(r["text"])
        placed=False
        for e in events:
            if r["ticker"]==e["ticker"] and jaccard(tt,e["tokens"])>=threshold:
                e["rows"].append(r)
                e["tokens"] |= tt
                placed=True
                break
        if not placed:
            events.append({
                "event_id":len(events)+1,
                "ticker":r["ticker"],
                "tokens":set(tt),
                "rows":[r]
            })
    out=[]
    for e in events:
        texts=[x["text"] for x in e["rows"]]
        out.append({
            "event_id":e["event_id"],
            "ticker":e["ticker"],
            "source_count":len(set(x["author"] for x in e["rows"])),
            "message_count":len(e["rows"]),
            "representative_text":max(texts,key=len),
            "rows":e["rows"]
        })
    return out
