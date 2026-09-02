Kurulum:
cd ~/Downloads
unzip -o market_intelligence_engine_v4.zip -d market_intelligence_v09_optimized

Test:
cd ~/Downloads/market_intelligence_v09_optimized
python3 run_realworld_benchmark_v4.py   --input ~/Downloads/market_intelligence_realworld_benchmark_v1/data/realworld_500.jsonl   --limit 100   --batch-size 10   --small-model qwen3:1.7b   --large-model qwen3:8b
