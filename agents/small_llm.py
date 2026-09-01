
import json, urllib.request

class SmallLLM:
    def __init__(self, model="qwen3:1.7b", host="http://127.0.0.1:11434"):
        self.model=model; self.host=host.rstrip("/")
    def health(self):
        try:
            with urllib.request.urlopen(self.host+"/api/tags",timeout=2) as r: return r.status==200
        except: return False
    def classify_events(self, events):
        prompt="""Classify each financial event. Return ONLY JSON {"results":[...]}.
Each result:
{"event_id":1,"keep":true,"direction":"bullish|bearish|neutral","category":"earnings|contract|deliveries|dc_capex|technical|options|macro|official|guidance|other","importance":0,"confidence":0,"needs_large_model":false}
Discard ads, hype, ticker spam, vague chatter. Keep measurable claims and falsifiable setups.
Set needs_large_model=true only if ambiguous, contradictory, rumor-heavy, or hard to classify.
INPUT:
"""+json.dumps([{
            "event_id":e["event_id"],"ticker":e["ticker"],"source_count":e["source_count"],
            "message_count":e["message_count"],"text":e["representative_text"]
        } for e in events],ensure_ascii=False)
        payload={"model":self.model,"prompt":prompt,"stream":False,"format":"json","keep_alive":"30m","options":{"temperature":0,"num_ctx":8192}}
        req=urllib.request.Request(self.host+"/api/generate",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=300) as r:
            raw=json.loads(r.read().decode())
        obj=json.loads(raw["response"])
        return obj.get("results",[])
