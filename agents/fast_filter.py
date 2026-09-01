
import re
NOISE=[
    r"🚀",r"\bpremium\b",r"\bdm\b",r"kaçıran üzülür",r"roket başladı",
    r"#tuprs #tcell",r"bugün güzel duruyor",r"takipte kal"
]
EVIDENCE=[
    "konsensüs","beklenti","eps","marj","sözleşme","resmi bildirim","guidance","capex",
    "registrations","teslimat","channel checks","call hacmi","hedef","stop","kap","revenue",
    "backlog","contract","order","ebitda","temettü","dividend","regülasyon","export"
]
def classify(text):
    t=(text or "").lower()
    ev=sum(k in t for k in EVIDENCE)
    if any(re.search(p,t) for p in NOISE) and ev==0:
        return "discard"
    if len(t.split()) < 6 and ev==0:
        return "discard"
    return "candidate"
