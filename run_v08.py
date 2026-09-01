import json,argparse,time,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from agents.fast_filter import classify as fast_classify
from agents.batch_llm import OllamaBatchProvider
from core.duplicate import cluster as dup_cluster
from core.outcome import build_prediction_ledger, score_ledger
from core.reliability_v2 import from_counts
BASE=Path(__file__).parent; CACHE_DIR=BASE/'cache'; CACHE_DIR.mkdir(exist_ok=True)
def load(path,limit=None):
    rows=[json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]; return rows[:limit] if limit else rows
def key_for(batch,model): return hashlib.sha256((model+'|'+'|'.join(f"{x['id']}:{x['text']}" for x in batch)).encode()).hexdigest()
def cached_batch(provider,batch,model):
    fp=CACHE_DIR/f"{key_for(batch,model)}.json"
    if fp.exists(): return json.loads(fp.read_text(encoding='utf-8')),True
    items=[{"id":r["id"],"ticker":r["ticker"],"text":r["text"]} for r in batch]; out=provider.analyze_batch(items); fp.write_text(json.dumps(out,ensure_ascii=False),encoding='utf-8'); return out,False
def metrics(rows):
    tp=fp=tn=fn=dir_ok=dir_n=0
    for r in rows:
        pred=bool(r['analysis']['keep']); gold=bool(r['gold_keep'])
        if pred and gold: tp+=1
        elif pred and not gold: fp+=1
        elif not pred and not gold: tn+=1
        else: fn+=1
        if gold and pred:
            dir_n+=1; dir_ok+=int(r['analysis']['direction']==r['gold_direction'])
    p=tp/(tp+fp) if tp+fp else 0; rc=tp/(tp+fn) if tp+fn else 0; f=2*p*rc/(p+rc) if p+rc else 0; da=dir_ok/dir_n if dir_n else 0
    return p,rc,f,da,fp,fn
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--input',default=str(BASE/'data/tweets_10000.jsonl')); ap.add_argument('--limit',type=int,default=1000); ap.add_argument('--batch-size',type=int,default=25); ap.add_argument('--workers',type=int,default=2); ap.add_argument('--model',default='qwen3:8b'); args=ap.parse_args()
    rows=load(args.input,args.limit); provider=OllamaBatchProvider(args.model)
    if not provider.health(): raise SystemExit('Ollama çalışmıyor.')
    analyzed=[]; queue=[]; fast_discard=0
    for r in rows:
        pf=fast_classify(r['text'])
        if pf['decision']=='discard':
            r['analysis']={"keep":False,"category":"prefilter","direction":"neutral","importance":0,"novelty":0,"confidence":95,"claim":"","reason":pf['reason']}; analyzed.append(r); fast_discard+=1
        else: queue.append(r)
    batches=[queue[i:i+args.batch_size] for i in range(0,len(queue),args.batch_size)]; started=time.time(); cache_hits=0; completed=0
    def task(batch): return batch,cached_batch(provider,batch,args.model)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for fut in as_completed([ex.submit(task,b) for b in batches]):
            batch,(outs,hit)=fut.result(); cache_hits+=int(hit); by={x['id']:x for x in outs}
            for r in batch: r['analysis']=by[r['id']]; analyzed.append(r)
            completed+=1; print(f'Batch {completed}/{len(batches)} complete')
    elapsed=time.time()-started; analyzed.sort(key=lambda r:r['id']); p,rc,f,da,fp,fn=metrics(analyzed); kept=[r for r in analyzed if r['analysis']['keep']]; clusters=dup_cluster(kept); multi=[c for c in clusters if len(c['rows'])>=2]; ledger=build_prediction_ledger(analyzed); scored=score_ledger(ledger); learned={a:from_counts(v['success'],v['fail']) for a,v in scored.items()}; hidden={r['author']:100*r['author_true_hit_rate'] for r in analyzed}; errs=[abs(learned[a]-hidden[a]) for a in learned if a in hidden]; mae=sum(errs)/len(errs) if errs else 0
    print('\n=== MARKET INTELLIGENCE v0.8 ==='); print(f'Messages: {len(analyzed)}'); print(f'Fast-discarded: {fast_discard}'); print(f'Sent to LLM: {len(queue)}'); print(f'Batches: {len(batches)}'); print(f'Cache hits: {cache_hits}'); print(f'Precision: {p:.1%}'); print(f'Recall:    {rc:.1%}'); print(f'F1:        {f:.1%}'); print(f'Direction accuracy: {da:.1%}'); print(f'False positives: {fp}'); print(f'False negatives: {fn}'); print(f'Duplicate clusters (2+): {len(multi)}'); print(f'Prediction ledger rows: {len(ledger)}'); print(f'Source reliability MAE: {mae:.2f} pts'); print(f'LLM elapsed: {elapsed:.1f}s');
    if queue: print(f'Effective avg per LLM-reviewed message: {elapsed/len(queue):.2f}s')
    out=BASE/'results/v08_summary.json'; out.write_text(json.dumps({"messages":len(analyzed),"precision":p,"recall":rc,"f1":f,"direction_accuracy":da,"false_positives":fp,"false_negatives":fn,"fast_discarded":fast_discard,"llm_reviewed":len(queue),"batches":len(batches),"cache_hits":cache_hits,"duplicate_clusters":len(multi),"prediction_ledger_rows":len(ledger),"source_reliability_mae_points":mae,"llm_elapsed_seconds":elapsed},indent=2),encoding='utf-8'); print(f'\nSaved: {out}')
if __name__=='__main__': main()
