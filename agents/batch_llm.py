import json, urllib.request
class OllamaBatchProvider:
    def __init__(self, model="qwen3:8b", host="http://127.0.0.1:11434"):
        self.model=model; self.host=host.rstrip("/")
    def health(self):
        try:
            with urllib.request.urlopen(self.host+"/api/tags",timeout=2) as r: return r.status==200
        except Exception: return False
    def analyze_batch(self, items):
        prompt='''You are a financial market-intelligence classifier. Return ONLY JSON object: {"results":[...]}. One result per input: {"id":1,"keep":true,"category":"earnings|contract|deliveries|dc_capex|technical|options|macro|official|guidance|other","direction":"bullish|bearish|neutral","importance":0,"novelty":0,"confidence":0,"claim":"","reason":""}. Discard hype, ads, ticker spam, vague chatter. Keep measurable claims, disclosures, consensus comparisons, contracts/orders, earnings/guidance, demand checks, regulation, options flow, and falsifiable technical setups. Scores 0-100. INPUT:\n'''+json.dumps(items,ensure_ascii=False)
        payload={"model":self.model,"prompt":prompt,"stream":False,"format":"json","keep_alive":"30m","options":{"temperature":0,"num_ctx":8192}}
        req=urllib.request.Request(self.host+"/api/generate",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=600) as r: raw=json.loads(r.read().decode())
        obj=json.loads(raw["response"]); results=obj.get("results",[]) if isinstance(obj,dict) else obj
        by_id={int(x.get("id")):x for x in results if x.get("id") is not None}; out=[]
        for item in items:
            x=by_id.get(int(item["id"]),{}); x["id"]=item["id"]; x["keep"]=bool(x.get("keep",False)); x["category"]=str(x.get("category","other")).lower(); d=str(x.get("direction","neutral")).lower(); x["direction"]=d if d in {"bullish","bearish","neutral"} else "neutral"
            for k in ["importance","novelty","confidence"]:
                try: v=int(x.get(k,0))
                except: v=0
                x[k]=max(0,min(100,v))
            x["claim"]=str(x.get("claim","")).strip(); x["reason"]=str(x.get("reason","")).strip(); out.append(x)
        return out
