
import argparse, json, time, urllib.request
from pathlib import Path

def load_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]

def extract_json(text):
    text=(text or "").strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    candidates=[]
    depth=0; start=None; in_str=False; esc=False
    for i,ch in enumerate(text):
        if in_str:
            if esc: esc=False
            elif ch=="\\": esc=True
            elif ch=='"': in_str=False
            continue
        if ch=='"':
            in_str=True; continue
        if ch=="{":
            if depth==0: start=i
            depth+=1
        elif ch=="}" and depth>0:
            depth-=1
            if depth==0 and start is not None:
                candidates.append(text[start:i+1]); start=None
    for c in reversed(candidates):
        try: return json.loads(c)
        except Exception: pass
    return None

def ollama_generate(model,prompt,timeout=600):
    payload={
        "model":model,"prompt":prompt,"stream":False,"format":"json","keep_alive":"30m",
        "options":{"temperature":0,"num_ctx":16384}
    }
    req=urllib.request.Request(
        "http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type":"application/json"}
    )
    with urllib.request.urlopen(req,timeout=timeout) as r:
        raw=json.loads(r.read().decode())
    return raw.get("response","")

def classify_batch(model,batch):
    items=[{
        "id":r["id"],"ticker":r["ticker"],"message":r["text"],
        "evidence":{
            "ground_truth":r.get("ground_truth",""),
            "source_title":r.get("ground_truth_source_title",""),
            "event_date":r.get("event_date")
        }
    } for r in batch]
    prompt="""You are a financial intelligence verification engine.
For EVERY input item, compare the social-media message against the supplied retrieved evidence.
Return ONLY valid JSON:
{"results":[{"id":1,"keep":true,"truth_status":"verified","direction":"bullish","category":"earnings","importance":85,"confidence":90,"needs_large_model":false,"reason":"short reason"}]}
truth_status: verified, partly_true, false, stale, unverified, noise.
verified = materially matches evidence.
partly_true = core fact true but exaggerated/unsupported conclusion.
false = contradicts evidence.
stale = old true event presented as new/current.
unverified = relevant claim but evidence insufficient.
noise = ad/hype/spam/vague chatter/no falsifiable claim.
keep=true only for verified or partly_true useful messages.
keep=false for false, stale, unverified, noise.
direction: bullish, bearish, neutral.
category: earnings, deliveries, contract, dc_capex, acquisition, regulation, official, macro, technical, options, noise.
needs_large_model=true only if genuinely ambiguous.
Do not omit any input id.
INPUT:
"""+json.dumps(items,ensure_ascii=False)
    raw=ollama_generate(model,prompt)
    obj=extract_json(raw)
    if not obj or not isinstance(obj,dict):
        return [],raw
    return obj.get("results",[]) or [],raw

def normalize(x):
    keep=x.get("keep",False)
    if isinstance(keep,str): keep=keep.lower().strip() in {"true","1","yes","keep"}
    truth=str(x.get("truth_status","unverified")).lower()
    if truth not in {"verified","partly_true","false","stale","unverified","noise"}: truth="unverified"
    direction=str(x.get("direction","neutral")).lower()
    if direction not in {"bullish","bearish","neutral"}: direction="neutral"
    return {
        "id":int(x["id"]),"keep":bool(keep),"truth_status":truth,"direction":direction,
        "category":str(x.get("category","noise")).lower(),
        "importance":int(x.get("importance",0) or 0),
        "confidence":int(x.get("confidence",0) or 0),
        "needs_large_model":bool(x.get("needs_large_model",False)),
        "reason":str(x.get("reason","")).strip()
    }

def metrics(rows,preds):
    by={p["id"]:p for p in preds}
    tp=fp=tn=fn=0; truth_ok=0; dir_ok=dir_n=0; cat_ok=cat_n=0
    classes={k:[0,0] for k in ["verified","partly_true","false","stale","unverified","noise"]}
    for r in rows:
        p=by.get(r["id"],{"keep":False,"truth_status":"unverified","direction":"neutral","category":"noise"})
        gk=bool(r["gold_keep"]); pk=bool(p["keep"])
        if pk and gk: tp+=1
        elif pk and not gk: fp+=1
        elif not pk and not gk: tn+=1
        else: fn+=1
        gt=r["gold_truth_status"]; classes[gt][1]+=1
        if p["truth_status"]==gt:
            truth_ok+=1; classes[gt][0]+=1
        if gk and pk:
            dir_n+=1; dir_ok+=int(p["direction"]==r["gold_direction"])
            cat_n+=1; cat_ok+=int(p["category"]==r["gold_category"])
    precision=tp/(tp+fp) if tp+fp else 0
    recall=tp/(tp+fn) if tp+fn else 0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0
    return {
        "messages":len(rows),"precision":precision,"recall":recall,"f1":f1,
        "truth_accuracy":truth_ok/len(rows) if rows else 0,
        "direction_accuracy":dir_ok/dir_n if dir_n else 0,
        "category_accuracy":cat_ok/cat_n if cat_n else 0,
        "false_positives":fp,"false_negatives":fn,
        "truth_by_class":{k:(a/b if b else 0) for k,(a,b) in classes.items()}
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--small-model",default="qwen3:1.7b")
    ap.add_argument("--large-model",default="qwen3:8b")
    ap.add_argument("--batch-size",type=int,default=20)
    ap.add_argument("--limit",type=int,default=500)
    args=ap.parse_args()

    rows=load_jsonl(args.input)[:args.limit]
    outdir=Path("results"); outdir.mkdir(exist_ok=True)
    preds=[]; raw_log=[]; escalated=set(); t0=time.time()

    batches=[rows[i:i+args.batch_size] for i in range(0,len(rows),args.batch_size)]
    for bi,batch in enumerate(batches,1):
        small_results,raw=classify_batch(args.small_model,batch)
        raw_log.append({"stage":"small","batch":bi,"raw":raw})
        norm=[]
        for x in small_results:
            try: norm.append(normalize(x))
            except Exception: pass
        by={x["id"]:x for x in norm}
        to_large=[]
        for r in batch:
            p=by.get(r["id"])
            if p is None or p["needs_large_model"]:
                to_large.append(r); escalated.add(r["id"])
            else:
                preds.append(p)
        if to_large:
            large_results,raw2=classify_batch(args.large_model,to_large)
            raw_log.append({"stage":"large","batch":bi,"raw":raw2})
            lnorm=[]
            for x in large_results:
                try: lnorm.append(normalize(x))
                except Exception: pass
            lby={x["id"]:x for x in lnorm}
            for r in to_large:
                preds.append(lby.get(r["id"],{
                    "id":r["id"],"keep":False,"truth_status":"unverified","direction":"neutral",
                    "category":"noise","importance":0,"confidence":0,"needs_large_model":False,
                    "reason":"Model output could not be parsed."
                }))
        print(f"Batch {bi}/{len(batches)} complete | predictions={len(preds)} | escalations={len(escalated)}")

    elapsed=time.time()-t0
    preds=sorted(preds,key=lambda x:x["id"])
    m=metrics(rows,preds)
    m["elapsed_seconds"]=elapsed
    m["large_model_escalations"]=len(escalated)
    m["avg_seconds_per_message"]=elapsed/len(rows) if rows else 0

    (outdir/"realworld_predictions.jsonl").write_text(
        "\n".join(json.dumps(x,ensure_ascii=False) for x in preds)+"\n",encoding="utf-8")
    (outdir/"realworld_summary.json").write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding="utf-8")
    (outdir/"realworld_raw_llm.json").write_text(json.dumps(raw_log,ensure_ascii=False,indent=2),encoding="utf-8")

    print("\n=== GERÇEK DÜNYA BENCHMARK v1 ===")
    print(f"Mesaj: {m['messages']}")
    print(f"KEEP Precision: {m['precision']:.1%}")
    print(f"KEEP Recall:    {m['recall']:.1%}")
    print(f"KEEP F1:        {m['f1']:.1%}")
    print(f"Truth Accuracy: {m['truth_accuracy']:.1%}")
    print(f"Direction Acc:  {m['direction_accuracy']:.1%}")
    print(f"Category Acc:   {m['category_accuracy']:.1%}")
    print(f"False Positive: {m['false_positives']}")
    print(f"False Negative: {m['false_negatives']}")
    print(f"8B Escalation:  {m['large_model_escalations']}")
    print(f"Toplam süre:    {m['elapsed_seconds']:.1f}s")
    print(f"Ort./mesaj:     {m['avg_seconds_per_message']:.3f}s")
    print("\nTruth sınıfları:")
    for k,v in m["truth_by_class"].items():
        print(f"  {k:12} {v:.1%}")
    print("\nKaydedildi: results/realworld_predictions.jsonl, results/realworld_summary.json, results/realworld_raw_llm.json")

if __name__=="__main__":
    main()
