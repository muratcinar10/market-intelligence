# Market Intelligence v0.9 Optimized

Amaç: tweet bazlı 8B LLM analizini bırakıp event bazlı analiz yapmak.

Akış:
1. Fast Filter
2. Duplicate/Event Builder
3. Qwen 1.7B küçük model tüm eventleri değerlendirir
4. Yalnızca zor/ambiguous eventler Qwen 8B'e gider

Önce küçük modeli indir:
```bash
ollama pull qwen3:1.7b
```

Çalıştır:
```bash
cd ~/Downloads/market_intelligence_v09_optimized
python3 run_v09.py --input data/tweets_10000.jsonl --limit 1000 --small-model qwen3:1.7b --large-model qwen3:8b
```

Hedef:
v0.7'deki ~4399 saniyeyi ciddi biçimde aşağı çekmek.
