#!/usr/bin/env bash
# track.sh — Sentinel Guard status tracker
# Usage: ./track.sh [api_url] [token]
set -euo pipefail

API_URL="${1:-${SENTINEL_API_URL:-http://localhost:8000/api/v1}}"
TOKEN="${2:-}"
INTERVAL=10

if [[ -z "$TOKEN" ]]; then
    echo "Usage: ./track.sh [api_url] [token]"
    echo "       Or set SENTINEL_API_URL and export token as second arg"
    exit 1
fi

auth_header() { echo "Authorization: Bearer $TOKEN"; }

print_bar() {
    local score="$1"
    local filled=$(( score / 5 ))
    local bar=""
    for ((i=0; i<20; i++)); do
        if (( i < filled )); then bar+="█"; else bar+="░"; fi
    done
    echo "$bar"
}

color() {
    local score="$1"
    if   (( score >= 80 )); then echo -e "\033[31m"   # red
    elif (( score >= 50 )); then echo -e "\033[33m"   # yellow
    else                        echo -e "\033[32m"    # green
    fi
}

reset="\033[0m"

echo "Sentinel Guard — Live Tracker"
echo "API: $API_URL"
echo "Press Ctrl+C to stop"
echo "──────────────────────────────────────────"

while true; do
    response=$(curl -sf -H "$(auth_header)" "$API_URL/scans" 2>/dev/null || echo "[]")

    total=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d))" 2>/dev/null || echo 0)
    running=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(sum(1 for s in d if s.get('status')=='running'))" 2>/dev/null || echo 0)
    avg_risk=$(echo "$response" | python3 -c "
import sys,json
d=json.load(sys.stdin)
scores=[s.get('risk_score',0) for s in d if s.get('risk_score') is not None]
print(round(sum(scores)/len(scores),1) if scores else 0)
" 2>/dev/null || echo 0)
    critical=$(echo "$response" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(sum(s.get('finding_counts',{}).get('critical',0) for s in d))
" 2>/dev/null || echo 0)

    score_int=${avg_risk%.*}
    c=$(color "$score_int")
    bar=$(print_bar "$score_int")

    clear
    echo -e "  🛡️  \033[1;37mSentinel Guard Tracker\033[0m  —  $(date '+%H:%M:%S')"
    echo "  ─────────────────────────────────────────"
    printf "  %-18s %s\n" "Total Scans:"   "$total"
    printf "  %-18s %s\n" "Running:"       "$running"
    printf "  %-18s ${c}%s${reset}\n" "Critical:"  "$critical"
    printf "  %-18s ${c}%s / 100${reset}\n" "Avg Risk:"  "$avg_risk"
    echo -e "  Risk: ${c}${bar}${reset} ${avg_risk}/100"
    echo "  ─────────────────────────────────────────"
    echo "  API: $API_URL  |  Refresh: every ${INTERVAL}s"

    sleep "$INTERVAL"
done
