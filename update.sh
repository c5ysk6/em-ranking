#!/bin/bash
# EIGHT MEN ランキング 毎日自動更新スクリプト

LOG="/Users/c5ysk6/Documents/eight-men-monthly-ranking/update.log"
echo "===== $(date '+%Y-%m-%d %H:%M:%S') 開始 =====" >> "$LOG"

# HTMLを生成
python3 "/Users/c5ysk6/Documents/eight-men-monthly-ranking/generate_ranking.py" >> "$LOG" 2>&1

# GitHubにpush
cd /Users/c5ysk6/Documents/eight-men-monthly-ranking
git add index.html >> "$LOG" 2>&1
git commit -m "update $(date '+%Y-%m-%d')" >> "$LOG" 2>&1
git push >> "$LOG" 2>&1

echo "===== 完了 =====" >> "$LOG"
