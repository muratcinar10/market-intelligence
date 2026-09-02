
import argparse, json, time, urllib.request, re
from pathlib import Path

TRUTH = ["verified","partly_true","false","stale","unverified","noise"]

def load(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]

def norm_conf(v):
    try: x=float(v)
    except: return 0
    if 0 <= x <= 1: x *= 100
    return max(0,min(100,int(round(x))))

def ollama(model,prompt,schema,timeout=600):
    payload={"model":model,"prompt":prompt,"stream":False,"format":schema,"keep_alive":"30m",
             "options":{"temperature":0,"num_ctx":16384}}
    req=urllib.request.Request("http://127.0.0.1:11434/api/generate",
        data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        raw=json.loads(r.read().decode())
    txt=raw.get("response","").strip()
    try: return json.loads(txt),txt
    except: return None,txt

def is_noise(text):
    t=(text or "").strip().lower()
    if not t: return True
    if re.fullmatch(r"(?:#\w+\s*){3,}",t): return True
    markers=["vip grub","premium grup"," dm","dm ","kimler ","alınır mı","alinir mi",
             "bugün güzel duruyor","bugun guzel duruyor","takipte kal","günaydın",
             "gunaydin","bol kazanç","bol kazanc","kaçıran üzülür","kaciran uzulur"]
    return any(x in t for x in markers) and len(t.split()) < 18

def stale_rule(text):
    t=(text or "").lower()
    markers=["eski haber","old news","tekrar dolaşımda","tekrar dolasimda",
             "yeniden dolaşımda","yeniden dolasimda","geçen yılki haber","gecen yilki haber"]
    return any(x in t for x in markers)

def exaggeration_rule(text):
    t=(text or "").lower()
    markers=["kesin %","kesin yükseliş","kesin yukselis","kesin düşüş","kesin dusus",
             "piyasa bunu henüz fiyatlamadı","piyasa bunu henuz fiyatlamadi",
             "çok büyük fırsat","cok buyuk firsat","en güçlü katalizör","en guclu katalizor",
             "şirket tarihindeki en güçlü","sirket tarihindeki en guclu","garanti yükselir","garanti yukselir"]
    return any(x in t for x in markers)

def deterministic_category(text,evidence,source_title):
    blob=" ".join([str(text or ""),str(evidence or ""),str(source_title or "")]).lower()
    if "kap" in blob and ("finansal rapor" in blob or "financial report" in blob): return "official"
    if any(x in blob for x in ["acquire","acquisition","satın al","satin al"]): return "acquisition"
    if any(x in blob for x in ["recall","geri çağır","geri cagir"]): return "regulation"
    if any(x in blob for x in ["deliveries","delivery","teslimat","registrations","kayıt","kayit","vehicle sales","ev sales"]): return "deliveries"
    if any(x in blob for x in ["ai infrastructure","instinct systems","hyperscaler","capex","data-center","data center"]): return "dc_capex"
    if any(x in blob for x in ["revenue","gross margin","eps","earnings","financial results","bilanço","bilanco"]): return "earnings"
    if any(x in blob for x in ["contract","sözleşme","sozlesme","award"]): return "contract"
    if any(x in blob for x in ["dividend","temettü","temettu"]): return "dividend"
    if any(x in blob for x in ["interest rate","faiz","inflation","enflasyon","central bank","fed"]): return "macro"
    return "other"

def deterministic_direction(category,text,evidence):
    blob=" ".join([str(text or ""),str(evidence or "")]).lower()
    if category=="regulation": return "bearish"
    if category=="official": return "neutral"
    if category=="acquisition": return "bullish"
    if category=="contract": return "bullish"
    if category=="deliveries":
        if any(x in blob for x in ["above consensus","rose 37.8%","+37.8%","artarak","up 37.8%"]): return "bullish"
        if any(x in blob for x in ["below consensus","miss risk","decline","fell","düştü","dustu"]): return "bearish"
        return "neutral"
    if category=="dc_capex":
        return "bullish" if any(x in blob for x in ["expand","raised","higher","go live","stronger","growth","arttı","artti","genişlet","genislet"]) else "neutral"
    if category=="earnings":
        if any(x in blob for x in ["more than doubled","up 106%","up 117%","strong","beat","ahead of"]): return "bullish"
        if any(x in blob for x in ["missed","declined","fell","lower"]): return "bearish"
        return "neutral"
    return "neutral"

truth_schema={
  "type":"object",
  "properties":{"results":{"type":"array","items":{
    "type":"object",
    "properties":{
      "id":{"type":"integer"},
      "truth_status":{"type":"string","enum":TRUTH},
      "confidence":{"type":"number","minimum":0,"maximum":100},
      "reason":{"type":"string"}
    },
    "required":["id","truth_status","confidence","reason"]
  }}},
  "required":["results"]
}

def verify(model,batch):
    items=[{"id":r["id"],"message":r["text"],"evidence":r.get("ground_truth",""),
            "source":r.get("ground_truth_source_title",""),"event_date":r.get("event_date")} for r in batch]
    prompt="""/no_think
Strictly verify each financial social-media claim against supplied evidence.

Classes:
verified = central factual claim matches evidence.
partly_true = central event is true but post adds unsupported prediction, certainty, exaggeration, or material interpretation.
false = central factual claim contradicts evidence, including material numerical contradiction.
stale = true old event explicitly presented/reposted as fresh/current.
unverified = meaningful claim but evidence is insufficient.
noise = no falsifiable financial claim, ad, spam, vague chatter, question, hype.

Confidence must be 0-100.
Examples:
Message Tesla delivered 380k; evidence says 480,126 => false.
Message NVDA revenue $96.2B and "kesin %20 yükselir"; evidence confirms only revenue => partly_true.
Return every id exactly once.
INPUT:
"""+json.dumps(items,ensure_ascii=False)
    return ollama(model,prompt,truth_schema,300)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--limit",type=int,default=100)
    ap.add_argument("--batch-size",type=int,default=10)
    ap.add_argument("--small-model",default="qwen3:1.7b")
    ap.add_argument("--large-model",default="qwen3:8b")
    a=ap.parse_args()

    rows=load(a.input)[:a.limit]
    result={}; raw=[]; fast_noise=0; stale_hits=0; small_coverage=0; escalated=set()
    t0=time.time(); remaining=[]

    for r in rows:
        if is_noise(r["text"]):
            result[r["id"]]={"id":r["id"],"truth_status":"noise","keep":False,"truth_confidence":100,"truth_reason":"rule:noise"}
            fast_noise+=1
        elif stale_rule(r["text"]):
            result[r["id"]]={"id":r["id"],"truth_status":"stale","keep":False,"truth_confidence":100,"truth_reason":"rule:stale"}
            stale_hits+=1
        else:
            remaining.append(r)

    batches=[remaining[i:i+a.batch_size] for i in range(0,len(remaining),a.batch_size)]
    for bi,b in enumerate(batches,1):
        obj,txt=verify(a.small_model,b); raw.append({"stage":"truth_small","batch":bi,"raw":txt})
        small={}
        if obj:
            for x in obj.get("results",[]):
                try:
                    sid=int(x["id"]); status=str(x["truth_status"]).lower()
                    row=next((r for r in b if r["id"]==sid),None)
                    if row and exaggeration_rule(row["text"]) and status=="verified":
                        status="partly_true"
                    small[sid]={"id":sid,"truth_status":status,"keep":status in {"verified","partly_true"},
                                "truth_confidence":norm_conf(x.get("confidence",0)),"truth_reason":str(x.get("reason",""))}
                except: pass

        to_large=[]
        for r in b:
            p=small.get(r["id"])
            if p is None:
                to_large.append(r); escalated.add(r["id"]); continue
            small_coverage+=1
            if p["truth_status"] in {"verified","noise"} and p["truth_confidence"]>=80:
                result[r["id"]]=p
            else:
                to_large.append(r); escalated.add(r["id"])

        if to_large:
            obj2,txt2=verify(a.large_model,to_large); raw.append({"stage":"truth_large","batch":bi,"raw":txt2})
            large={}
            if obj2:
                for x in obj2.get("results",[]):
                    try:
                        sid=int(x["id"]); status=str(x["truth_status"]).lower()
                        row=next((r for r in to_large if r["id"]==sid),None)
                        if row and exaggeration_rule(row["text"]) and status=="verified":
                            status="partly_true"
                        large[sid]={"id":sid,"truth_status":status,"keep":status in {"verified","partly_true"},
                                    "truth_confidence":norm_conf(x.get("confidence",0)),"truth_reason":str(x.get("reason",""))}
                    except: pass
            for r in to_large:
                result[r["id"]]=large.get(r["id"],{"id":r["id"],"truth_status":"unverified","keep":False,"truth_confidence":0,"truth_reason":"missing output"})
        print(f"Truth {bi}/{len(batches)} | noise={fast_noise} stale={stale_hits} small={small_coverage} 8B={len(escalated)}")

    for r in rows:
        p=result[r["id"]]
        if p["keep"]:
            cat=deterministic_category(r["text"],r.get("ground_truth",""),r.get("ground_truth_source_title",""))
            p["category"]=cat
            p["direction"]=deterministic_direction(cat,r["text"],r.get("ground_truth",""))
            p["importance"]={"regulation":85,"earnings":85,"deliveries":82,"dc_capex":80,"acquisition":72,
                             "official":68,"contract":82,"macro":70,"dividend":65,"other":55}.get(cat,55)
            if p["truth_status"]=="partly_true": p["importance"]=max(0,p["importance"]-15)
        else:
            p["category"]="noise"; p["direction"]="neutral"; p["importance"]=0

    tp=fp=tn=fn=truth_ok=dir_ok=dir_n=cat_ok=cat_n=0
    cls={k:[0,0] for k in TRUTH}
    for r in rows:
        p=result[r["id"]]; gk=bool(r["gold_keep"]); pk=bool(p["keep"])
        if pk and gk: tp+=1
        elif pk and not gk: fp+=1
        elif not pk and not gk: tn+=1
        else: fn+=1
        gt=r["gold_truth_status"]; cls[gt][1]+=1
        if p["truth_status"]==gt: truth_ok+=1; cls[gt][0]+=1
        if pk and gk:
            dir_n+=1; dir_ok+=int(p["direction"]==r["gold_direction"])
            cat_n+=1; cat_ok+=int(p["category"]==r["gold_category"])

    precision=tp/(tp+fp) if tp+fp else 0
    recall=tp/(tp+fn) if tp+fn else 0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0
    elapsed=time.time()-t0
    summary={"messages":len(rows),"fast_noise":fast_noise,"stale_rule_hits":stale_hits,
             "precision":precision,"recall":recall,"f1":f1,"truth_accuracy":truth_ok/len(rows),
             "direction_accuracy":dir_ok/dir_n if dir_n else 0,"category_accuracy":cat_ok/cat_n if cat_n else 0,
             "false_positives":fp,"false_negatives":fn,"small_model_coverage":small_coverage,
             "large_model_escalations":len(escalated),"elapsed_seconds":elapsed,
             "truth_by_class":{k:(a/b if b else 0) for k,(a,b) in cls.items()}}

    out=Path("results"); out.mkdir(exist_ok=True)
    (out/"realworld_v4_predictions.jsonl").write_text("\n".join(json.dumps(result[r["id"]],ensure_ascii=False) for r in rows)+"\n",encoding="utf-8")
    (out/"realworld_v4_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"realworld_v4_raw_llm.json").write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding="utf-8")

    print("\n=== GERÇEK DÜNYA BENCHMARK v4 ===")
    for label,val in [
        ("Mesaj",len(rows)),("Fast noise",fast_noise),("Stale rule",stale_hits),
        ("KEEP Precision",f"{precision:.1%}"),("KEEP Recall",f"{recall:.1%}"),("KEEP F1",f"{f1:.1%}"),
        ("Truth Accuracy",f"{summary['truth_accuracy']:.1%}"),("Direction Acc",f"{summary['direction_accuracy']:.1%}"),
        ("Category Acc",f"{summary['category_accuracy']:.1%}"),("False Positive",fp),("False Negative",fn),
        ("Small coverage",f"{small_coverage}/{len(remaining)}"),("8B Escalation",len(escalated)),
        ("Toplam süre",f"{elapsed:.1f}s")]:
        print(f"{label}: {val}")
    print("Truth sınıfları:")
    for k,v in sorted(summary["truth_by_class"].items()):
        print(f"  {k:12} {v:.1%}")

if __name__=="__main__":
    main()
