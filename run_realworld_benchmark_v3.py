
import argparse, json, time, urllib.request, re
from pathlib import Path

TRUTH = ["verified","partly_true","false","stale","unverified","noise"]

def load(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]

def ollama(model, prompt, schema, timeout=600):
    payload={
        "model":model,
        "prompt":prompt,
        "stream":False,
        "format":schema,
        "keep_alive":"30m",
        "options":{"temperature":0,"num_ctx":16384}
    }
    req=urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type":"application/json"}
    )
    with urllib.request.urlopen(req,timeout=timeout) as r:
        raw=json.loads(r.read().decode())
    txt=raw.get("response","").strip()
    try:
        return json.loads(txt),txt
    except Exception:
        return None,txt

truth_schema={
  "type":"object",
  "properties":{"results":{"type":"array","items":{
    "type":"object",
    "properties":{
      "id":{"type":"integer"},
      "truth_status":{"type":"string","enum":TRUTH},
      "confidence":{"type":"number","minimum":0,"maximum":100},
      "needs_large_model":{"type":"boolean"},
      "reason":{"type":"string"}
    },
    "required":["id","truth_status","confidence","needs_large_model","reason"]
  }}},
  "required":["results"]
}

analysis_schema={
  "type":"object",
  "properties":{"results":{"type":"array","items":{
    "type":"object",
    "properties":{
      "id":{"type":"integer"},
      "direction":{"type":"string","enum":["bullish","bearish","neutral"]},
      "category":{"type":"string"},
      "importance":{"type":"integer","minimum":0,"maximum":100},
      "confidence":{"type":"number","minimum":0,"maximum":100},
      "reason":{"type":"string"}
    },
    "required":["id","direction","category","importance","confidence","reason"]
  }}},
  "required":["results"]
}

def norm_conf(v):
    try:
        x=float(v)
    except Exception:
        return 0
    # Qwen sometimes returns 0/1 instead of 0-100.
    if 0 <= x <= 1:
        x *= 100
    return max(0,min(100,int(round(x))))

def deterministic_keep(status):
    return status in {"verified","partly_true"}

def contradiction_in_reason(reason):
    r=(reason or "").lower()
    keys=[
        "contradict", "discrepancy", "does not match", "incorrect",
        "evidence shows", "but the evidence", "false"
    ]
    return any(k in r for k in keys)

def quick_noise(text):
    t=(text or "").strip().lower()
    if not t:
        return True
    if re.fullmatch(r"(?:#\w+\s*){3,}", t):
        return True
    noise_markers=["vip grub", "dm", "kimler ", "alınır mı", "alinir mi",
                   "bugün güzel duruyor", "takipte kal", "günaydın", "bol kazanç"]
    return any(x in t for x in noise_markers) and len(t.split()) < 12

def verify(model,batch):
    items=[{
        "id":r["id"],"message":r["text"],"event_date":r.get("event_date"),
        "evidence":r.get("ground_truth",""),
        "source":r.get("ground_truth_source_title","")
    } for r in batch]
    prompt="""/no_think
You verify financial social-media claims against supplied evidence.

Return only:
id, truth_status, confidence, needs_large_model, reason.

truth_status:
verified = claim matches evidence.
partly_true = central fact true but post adds unsupported prediction/exaggeration/material conclusion.
false = central factual claim contradicts evidence.
stale = old true event explicitly presented as current/new.
unverified = meaningful financial claim cannot be verified from evidence.
noise = advertisement, ticker spam, vague chatter, question, hype, or no falsifiable claim.

IMPORTANT CONSISTENCY RULES:
- If your reason says the evidence contradicts the message, truth_status MUST be false.
- Questions like "kimler taşıyor?" or "alınır mı?" are noise, not unverified.
- "bugün güzel duruyor", "takipte kal", hashtag spam and VIP/DM promotions are noise.
- A true fact plus "kesin %20 yükselir", "piyasa hiç fiyatlamadı" or similar unsupported prediction is partly_true.
- Explicit old-news repost is stale.
- confidence MUST be an integer 0-100, never 0-1.
- needs_large_model=true only for real ambiguity.

Return every id exactly once.
INPUT:
"""+json.dumps(items,ensure_ascii=False)
    return ollama(model,prompt,truth_schema,300)

def analyze(model,batch):
    items=[{"id":r["id"],"ticker":r["ticker"],"message":r["text"],"evidence":r.get("ground_truth","")} for r in batch]
    prompt="""/no_think
Classify market impact for already verified useful financial posts.
Return every id exactly once.

direction = bullish, bearish, neutral.
category = earnings, deliveries, contract, dc_capex, acquisition, regulation, official, macro, technical, options, dividend, analyst, other.
importance = 0-100.
confidence = 0-100.

Rules:
- Pure financial filing with no quantified beat/miss => official + neutral.
- Vehicle recall => regulation + bearish.
- Strong deliveries versus consensus => deliveries + bullish.
- AI infrastructure expansion / hyperscaler capex => dc_capex + bullish.
- Acquisition announcement => acquisition.
INPUT:
"""+json.dumps(items,ensure_ascii=False)
    return ollama(model,prompt,analysis_schema,300)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--limit",type=int,default=100)
    ap.add_argument("--batch-size",type=int,default=10)
    ap.add_argument("--small-model",default="qwen3:1.7b")
    ap.add_argument("--large-model",default="qwen3:8b")
    a=ap.parse_args()

    rows=load(a.input)[:a.limit]
    result={}
    raw=[]
    small_coverage=0
    escalated=set()
    fast_noise=0
    t0=time.time()

    # Deterministic cheap noise filter first.
    remaining=[]
    for r in rows:
        if quick_noise(r["text"]):
            result[r["id"]]={
                "id":r["id"],"truth_status":"noise","keep":False,
                "truth_confidence":100,"needs_large_model":False,
                "truth_reason":"Deterministic noise filter."
            }
            fast_noise += 1
        else:
            remaining.append(r)

    batches=[remaining[i:i+a.batch_size] for i in range(0,len(remaining),a.batch_size)]

    for bi,b in enumerate(batches,1):
        obj,txt=verify(a.small_model,b)
        raw.append({"stage":"truth_small","batch":bi,"raw":txt})
        small={}
        if obj:
            for x in obj.get("results",[]):
                try:
                    status=str(x["truth_status"]).lower()
                    conf=norm_conf(x.get("confidence",0))
                    reason=str(x.get("reason",""))
                    # Sanity override when model's own reasoning contradicts its label.
                    if status=="verified" and contradiction_in_reason(reason):
                        status="false"
                    small[int(x["id"])]={
                        "id":int(x["id"]),
                        "truth_status":status,
                        "keep":deterministic_keep(status),
                        "truth_confidence":conf,
                        "needs_large_model":bool(x.get("needs_large_model",False)),
                        "truth_reason":reason
                    }
                except Exception:
                    pass

        to_large=[]
        for r in b:
            p=small.get(r["id"])
            if p is None:
                to_large.append(r); escalated.add(r["id"]); continue

            small_coverage += 1

            # Accept only easy, high-confidence classes locally.
            easy = p["truth_status"] in {"verified","noise"} and p["truth_confidence"] >= 80
            if easy and not p["needs_large_model"]:
                result[r["id"]]=p
            else:
                to_large.append(r); escalated.add(r["id"])

        if to_large:
            obj2,txt2=verify(a.large_model,to_large)
            raw.append({"stage":"truth_large","batch":bi,"raw":txt2})
            large={}
            if obj2:
                for x in obj2.get("results",[]):
                    try:
                        status=str(x["truth_status"]).lower()
                        conf=norm_conf(x.get("confidence",0))
                        reason=str(x.get("reason",""))
                        if status=="verified" and contradiction_in_reason(reason):
                            status="false"
                        large[int(x["id"])]={
                            "id":int(x["id"]),
                            "truth_status":status,
                            "keep":deterministic_keep(status),
                            "truth_confidence":conf,
                            "needs_large_model":False,
                            "truth_reason":reason
                        }
                    except Exception:
                        pass
            for r in to_large:
                result[r["id"]]=large.get(r["id"],{
                    "id":r["id"],"truth_status":"unverified","keep":False,
                    "truth_confidence":0,"needs_large_model":False,
                    "truth_reason":"Missing large-model output."
                })

        print(f"Truth {bi}/{len(batches)} | fast-noise={fast_noise} | small={small_coverage} | 8B={len(escalated)}")

    kept=[r for r in rows if result[r["id"]]["keep"]]
    kbatches=[kept[i:i+a.batch_size] for i in range(0,len(kept),a.batch_size)]
    for bi,b in enumerate(kbatches,1):
        obj,txt=analyze(a.small_model,b)
        raw.append({"stage":"analysis_small","batch":bi,"raw":txt})
        amap={}
        if obj:
            for x in obj.get("results",[]):
                try:
                    amap[int(x["id"])]={
                        "direction":str(x["direction"]).lower(),
                        "category":str(x["category"]).lower(),
                        "importance":int(x["importance"]),
                        "analysis_confidence":norm_conf(x.get("confidence",0)),
                        "analysis_reason":str(x.get("reason",""))
                    }
                except Exception:
                    pass
        missing=[r for r in b if r["id"] not in amap]
        if missing:
            obj2,txt2=analyze(a.large_model,missing)
            raw.append({"stage":"analysis_large","batch":bi,"raw":txt2})
            if obj2:
                for x in obj2.get("results",[]):
                    try:
                        amap[int(x["id"])]={
                            "direction":str(x["direction"]).lower(),
                            "category":str(x["category"]).lower(),
                            "importance":int(x["importance"]),
                            "analysis_confidence":norm_conf(x.get("confidence",0)),
                            "analysis_reason":str(x.get("reason",""))
                        }
                    except Exception:
                        pass
        for r in b:
            result[r["id"]].update(amap.get(r["id"],{
                "direction":"neutral","category":"other","importance":0,
                "analysis_confidence":0,"analysis_reason":"Missing analysis."
            }))

    for r in rows:
        result[r["id"]].setdefault("direction","neutral")
        result[r["id"]].setdefault("category","noise")
        result[r["id"]].setdefault("importance",0)

    tp=fp=tn=fn=0
    truth_ok=0
    dir_ok=dir_n=0
    cat_ok=cat_n=0
    by_class={k:[0,0] for k in TRUTH}

    for r in rows:
        p=result[r["id"]]
        gk=bool(r["gold_keep"]); pk=bool(p["keep"])
        if pk and gk: tp+=1
        elif pk and not gk: fp+=1
        elif not pk and not gk: tn+=1
        else: fn+=1

        gt=r["gold_truth_status"]; by_class[gt][1]+=1
        if p["truth_status"]==gt:
            truth_ok+=1; by_class[gt][0]+=1

        if pk and gk:
            dir_n+=1; dir_ok += int(p["direction"]==r["gold_direction"])
            cat_n+=1; cat_ok += int(p["category"]==r["gold_category"])

    precision=tp/(tp+fp) if tp+fp else 0
    recall=tp/(tp+fn) if tp+fn else 0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0
    elapsed=time.time()-t0

    summary={
        "messages":len(rows),"fast_noise":fast_noise,
        "precision":precision,"recall":recall,"f1":f1,
        "truth_accuracy":truth_ok/len(rows) if rows else 0,
        "direction_accuracy":dir_ok/dir_n if dir_n else 0,
        "category_accuracy":cat_ok/cat_n if cat_n else 0,
        "false_positives":fp,"false_negatives":fn,
        "small_model_coverage":small_coverage,
        "large_model_escalations":len(escalated),
        "elapsed_seconds":elapsed,
        "truth_by_class":{k:(x/y if y else 0) for k,(x,y) in by_class.items()}
    }

    out=Path("results"); out.mkdir(exist_ok=True)
    (out/"realworld_v3_predictions.jsonl").write_text(
        "\n".join(json.dumps(result[r["id"]],ensure_ascii=False) for r in rows)+"\n",
        encoding="utf-8")
    (out/"realworld_v3_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"realworld_v3_raw_llm.json").write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding="utf-8")

    print("\n=== GERÇEK DÜNYA BENCHMARK v3 ===")
    print(f"Mesaj: {len(rows)}")
    print(f"Fast noise:     {fast_noise}")
    print(f"KEEP Precision: {precision:.1%}")
    print(f"KEEP Recall:    {recall:.1%}")
    print(f"KEEP F1:        {f1:.1%}")
    print(f"Truth Accuracy: {summary['truth_accuracy']:.1%}")
    print(f"Direction Acc:  {summary['direction_accuracy']:.1%}")
    print(f"Category Acc:   {summary['category_accuracy']:.1%}")
    print(f"False Positive: {fp}")
    print(f"False Negative: {fn}")
    print(f"Small coverage: {small_coverage}/{len(remaining)} non-noise")
    print(f"8B Escalation:  {len(escalated)}")
    print(f"Toplam süre:    {elapsed:.1f}s")
    print("Truth sınıfları:")
    for k,v in sorted(summary["truth_by_class"].items()):
        print(f"  {k:12} {v:.1%}")

if __name__=="__main__":
    main()
