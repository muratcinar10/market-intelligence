
import re

STOP={"ve","ile","için","bir","bu","the","and","of","to","in","is","may","can"}

def tokens(text):
    return {
        x for x in re.findall(r"[a-zA-Z0-9çğıöşüÇĞİÖŞÜ]+", (text or "").lower())
        if len(x) > 2 and x not in STOP
    }

def jaccard(a,b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)

def cluster(rows, threshold=0.45):
    clusters=[]
    for r in rows:
        t=tokens(r.get("text",""))
        placed=False
        for c in clusters:
            if r.get("ticker")==c["ticker"] and jaccard(t,c["tokens"]) >= threshold:
                c["rows"].append(r)
                c["tokens"] |= t
                placed=True
                break
        if not placed:
            clusters.append({
                "ticker":r.get("ticker",""),
                "tokens":set(t),
                "rows":[r]
            })
    return clusters
