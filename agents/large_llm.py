
import json, urllib.request
class LargeLLM:
    def __init__(self, model="qwen3:8b", host="http://127.0.0.1:11434"):
        self.model=model; self.host=host.rstrip("/")
    def analyze(self, events):
        if not events: return []
        prompt="""You are the senior financial analyst. Resolve ONLY ambiguous events.
Return JSON {"results":[...]} with:
{"event_id":1,"keep":true,"direction":"bullish|bearish|neutral","category":"other","importance":0,"confidence":0}
INPUT:
"""+json.dumps([{
            "event_id":e["event_id"],"ticker":e["ticker"],"source_count":e["source_count"],
            "message_count":e["message_count"],"text":e["representative_text"]
        } for e in events],ensure_ascii=False)
        payload={"model":self.model,"prompt":prompt,"stream":False,"format":"json","keep_alive":"30m","options":{"temperature":0,"num_ctx":8192}}
        req=urllib.request.Request(self.host+"/api/generate",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=600) as r:
            raw=json.loads(r.read().decode())
        obj=json.loads(raw["response"])
        return obj.get("results",[])
