
import argparse, json, time, urllib.request
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
    text=raw.get("response","").strip()
    try:
        return json.loads(text), text
    except Exception:
        return None, text

truth_schema={
  "type":"object",
  "properties":{"results":{"type":"array","items":{
    "type":"object",
    "properties":{
      "id":{"type":"integer"},
      "truth_status":{"type":"string","enum":TRUTH},
      "keep":{"type":"boolean"},
      "confidence":{"type":"integer","minimum":0,"maximum":100},
      "needs_large_model":{"type":"boolean"},
      "reason":{"type":"string"}
    },
    "required":["id","truth_status","keep","confidence","needs_large_model","reason"]
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
      "confidence":{"type":"integer","minimum":0,"maximum":100},
      "reason":{"type":"string"}
    },
    "required":["id","direction","category","importance","confidence","reason"]
  }}},
  "required":["results"]
}

def verify(model,batch):
    items=[{
        "id":r["id"],"message":r["text"],"event_date":r.get("event_date"),
        "evidence":r.get("ground_truth",""),
        "source":r.get("ground_truth_source_title","")
    } for r in batch]
    prompt="""/no_think
You are a financial fact verifier. Do ONLY truth verification.

Classes:
verified = factual claim materially matches evidence.
partly_true = core fact is true but the post adds unsupported certainty, prediction, exaggeration or material conclusion.
false = materially contradicts evidence.
stale = true old event explicitly presented as current/new.
unverified = meaningful claim cannot be verified from supplied evidence.
noise = ad, hype, ticker spam, vague chatter, question, or no falsifiable financial claim.

KEEP only verified and partly_true.
Use needs_large_model=true only for real ambiguity after comparing claim and evidence.
Do not omit IDs.
INPUT:
"""+json.dumps(items,ensure_ascii=False)
    return ollama(model,prompt,truth_schema,300)

def analyze(model,batch):
    items=[{"id":r["id"],"ticker":r["ticker"],"message":r["text"],"evidence":r.get("ground_truth","")} for r in batch]
    prompt="""/no_think
You are a market-impact classifier. These posts already passed fact verification.
Return direction, category, importance and confidence only.

direction = bullish, bearish, neutral.
category examples = earnings, deliveries, contract, dc_capex, acquisition, regulation, official, macro, technical, options, dividend, analyst, other.
Do not force bullish.
Financial filing with no beat/miss => official + neutral.
Vehicle recall => regulation + bearish.
Strong deliveries vs consensus => deliveries + bullish.
AI infrastructure expansion => dc_capex + bullish.
Acquisition announcement => acquisition.
Do not omit IDs.
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
    t0=time.time()

    batches=[rows[i:i+a.batch_size] for i in range(0,len(rows),a.batch_size)]

    for bi,b in enumerate(batches,1):
        obj,text=verify(a.small_model,b)
        raw.append({"stage":"truth_small","batch":bi,"raw":text})
        small={}
        if obj:
            for x in obj.get("results",[]):
                if "id" in x:
                    small[int(x["id"])]=x

        to_large=[]
        for r in b:
            x=small.get(r["id"])
            if x is None:
                to_large.append(r); escalated.add(r["id"])
                continue
            small_coverage += 1
            conf=int(x.get("confidence",0) or 0)
            if bool(x.get("needs_large_model",False)) or conf < 65:
                to_large.append(r); escalated.add(r["id"])
            else:
                result[r["id"]]=x

        if to_large:
            obj2,text2=verify(a.large_model,to_large)
            raw.append({"stage":"truth_large","batch":bi,"raw":text2})
            large={}
            if obj2:
                for x in obj2.get("results",[]):
                    if "id" in x:
                        large[int(x["id"])]=x
            for r in to_large:
                result[r["id"]]=large.get(r["id"],{
                    "id":r["id"],"truth_status":"unverified","keep":False,
                    "confidence":0,"needs_large_model":False,
                    "reason":"missing output"
                })
        print(f"Truth {bi}/{len(batches)} | small={small_coverage} | 8B={len(escalated)}")

    kept=[r for r in rows if bool(result[r["id"]].get("keep",False))]
    kbatches=[kept[i:i+a.batch_size] for i in range(0,len(kept),a.batch_size)]

    for bi,b in enumerate(kbatches,1):
        obj,text=analyze(a.small_model,b)
        raw.append({"stage":"analysis_small","batch":bi,"raw":text})
        amap={}
        if obj:
            for x in obj.get("results",[]):
                if "id" in x:
                    amap[int(x["id"])]=x
        missing=[r for r in b if r["id"] not in amap]
        if missing:
            obj2,text2=analyze(a.large_model,missing)
            raw.append({"stage":"analysis_large","batch":bi,"raw":text2})
            if obj2:
                for x in obj2.get("results",[]):
                    if "id" in x:
                        amap[int(x["id"])]=x
        for r in b:
            result[r["id"]].update(amap.get(r["id"],{
                "direction":"neutral","category":"other","importance":0,"confidence_analysis":0
            }))
        print(f"Analysis {bi}/{len(kbatches)}")

    for r in rows:
        x=result[r["id"]]
        x.setdefault("direction","neutral")
        x.setdefault("category","noise")
        x.setdefault("importance",0)

    tp=fp=tn=fn=0
    truth_ok=0
    dir_ok=dir_n=0
    cat_ok=cat_n=0
    by_class={k:[0,0] for k in TRUTH}

    for r in rows:
        p=result[r["id"]]
        gk=bool(r["gold_keep"]); pk=bool(p.get("keep",False))
        if pk and gk: tp+=1
        elif pk and not gk: fp+=1
        elif not pk and not gk: tn+=1
        else: fn+=1

        gt=r["gold_truth_status"]
        by_class[gt][1]+=1
        if p.get("truth_status")==gt:
            truth_ok+=1
            by_class[gt][0]+=1

        if pk and gk:
            dir_n+=1
            dir_ok += int(p.get("direction") == r["gold_direction"])
            cat_n+=1
            cat_ok += int(p.get("category") == r["gold_category"])

    precision=tp/(tp+fp) if tp+fp else 0
    recall=tp/(tp+fn) if tp+fn else 0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0
    elapsed=time.time()-t0

    summary={
        "messages":len(rows),
        "precision":precision,
        "recall":recall,
        "f1":f1,
        "truth_accuracy":truth_ok/len(rows) if rows else 0,
        "direction_accuracy":dir_ok/dir_n if dir_n else 0,
        "category_accuracy":cat_ok/cat_n if cat_n else 0,
        "false_positives":fp,
        "false_negatives":fn,
        "small_model_coverage":small_coverage,
        "large_model_escalations":len(escalated),
        "elapsed_seconds":elapsed,
        "truth_by_class":{k:(x/y if y else 0) for k,(x,y) in by_class.items()}
    }

    out=Path("results")
    out.mkdir(exist_ok=True)
    (out/"realworld_v2_predictions.jsonl").write_text(
        "\n".join(json.dumps(result[r["id"]],ensure_ascii=False) for r in rows)+"\n",
        encoding="utf-8"
    )
    (out/"realworld_v2_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"realworld_v2_raw_llm.json").write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding="utf-8")

    print("\n=== GERÇEK DÜNYA BENCHMARK v2 ===")
    print(f"Mesaj: {len(rows)}")
    print(f"KEEP Precision: {precision:.1%}")
    print(f"KEEP Recall:    {recall:.1%}")
    print(f"KEEP F1:        {f1:.1%}")
    print(f"Truth Accuracy: {summary['truth_accuracy']:.1%}")
    print(f"Direction Acc:  {summary['direction_accuracy']:.1%}")
    print(f"Category Acc:   {summary['category_accuracy']:.1%}")
    print(f"False Positive: {fp}")
    print(f"False Negative: {fn}")
    print(f"Small coverage: {small_coverage}/{len(rows)}")
    print(f"8B Escalation:  {len(escalated)}")
    print(f"Toplam süre:    {elapsed:.1f}s")
    print("Truth sınıfları:")
    for k,v in sorted(summary["truth_by_class"].items()):
        print(f"  {k:12} {v:.1%}")

if __name__=="__main__":
    main()
