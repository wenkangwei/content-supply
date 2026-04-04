#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
FEATURE_FILE="$PROJECT_DIR/feature_list.json"
PROGRESS_FILE="$PROJECT_DIR/claude-progress.txt"
SESSION_COUNT=0
MAX_SESSIONS=50          # 安全上限
COMPRESS_EVERY=3         # 每 N 个 session 压缩上下文
AUTO_CONFIRM_HOURS=0     # 0 = 不自动确认, 需要 break 等人工

cd "$PROJECT_DIR"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ---------- helpers ----------
next_feature() {
    python3 -c "
import json, sys
with open('$FEATURE_FILE') as f:
    data = json.load(f)
unpassed = [f for f in data['features'] if not f['passes']]
unpassed.sort(key=lambda x: x['priority'])
if unpassed:
    f = unpassed[0]
    print(json.dumps(f, ensure_ascii=False))
else:
    print('ALL_DONE')
"
}

count_remaining() {
    python3 -c "
import json
with open('$FEATURE_FILE') as f:
    data = json.load(f)
print(sum(1 for f in data['features'] if not f['passes']))
"
}

total_features() {
    python3 -c "
import json
with open('$FEATURE_FILE') as f:
    data = json.load(f)
print(len(data['features']))
"
}

mark_passed() {
    local fid="$1"
    python3 -c "
import json
with open('$FEATURE_FILE') as f:
    data = json.load(f)
for f in data['features']:
    if f['id'] == '$fid':
        f['passes'] = True
with open('$FEATURE_FILE', 'w') as out:
    json.dump(data, out, ensure_ascii=False, indent=2)
"
}

build_prompt() {
    local fid="$1" desc="$2" steps="$3"
    cat <<PROMPT
You are the Coding Agent for the content-supply project.

## Context
- Read CLAUDE.md for project conventions
- Read claude-progress.txt for what previous sessions did
- Read feature_list.json for the full roadmap
- Project directory: $PROJECT_DIR

## Your Task
Implement feature **$fid**: $desc

## Acceptance Criteria
$steps

## Protocol
1. First read CLAUDE.md and the last 20 lines of claude-progress.txt
2. Read relevant existing source files to understand current state
3. Implement ONLY this feature — do not touch other features
4. Run tests to verify: \`cd $PROJECT_DIR && python -m pytest tests/ -x --tb=short 2>&1 | tail -20\`
   If pytest is not installed, run: \`pip install -e ".[dev]"\` first
5. If tests pass, update feature_list.json: set this feature's passes to true
6. Git commit with message: "feat($fid): $desc"
7. Append session notes to claude-progress.txt

## Rules
- If existing tests are broken, FIX them first before adding new code
- If you need human input (API keys, credentials, decisions), output exactly: NEEDS_HUMAN: <reason>
- Do NOT modify features other than $fid
- Keep changes minimal and focused
PROMPT
}

# ---------- main loop ----------
log "=== Content Supply Platform — Auto Runner ==="
TOTAL=$(total_features)
log "Total features: $TOTAL, Remaining: $(count_remaining)"

while [ "$SESSION_COUNT" -lt "$MAX_SESSIONS" ]; do
    FEATURE_JSON=$(next_feature)

    if [ "$FEATURE_JSON" = "ALL_DONE" ]; then
        log "ALL FEATURES COMPLETE!"
        break
    fi

    FID=$(echo "$FEATURE_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
    DESC=$(echo "$FEATURE_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['description'])")
    STEPS=$(echo "$FEATURE_JSON" | python3 -c "
import json, sys
f = json.load(sys.stdin)
print('\n'.join(f'- {s}' for s in f.get('steps', [])))
")

    SESSION_COUNT=$((SESSION_COUNT + 1))
    REMAINING=$(count_remaining)
    log "--- Session $SESSION_COUNT | $FID | Remaining: $REMAINING/$TOTAL ---"
    log "Feature: $DESC"

    # Build prompt
    PROMPT_FILE="/tmp/csupply_prompt_${FID}.txt"
    build_prompt "$FID" "$DESC" "$STEPS" > "$PROMPT_FILE"

    # Execute claude
    log "Starting claude -p for $FID..."
    if claude -p "$(cat "$PROMPT_FILE")" \
         --allowedTools "Read,Edit,Write,Bash,Glob,Grep,Agent" \
         --output-format text 2>&1 | tee "/tmp/csupply_output_${FID}.log"; then
        log "$FID completed successfully"
    else
        log "$FID had errors — checking if feature was still implemented"
    fi

    # Check if feature was marked as passed
    PASSED=$(python3 -c "
import json
with open('$FEATURE_FILE') as f:
    data = json.load(f)
for f in data['features']:
    if f['id'] == '$FID':
        print('true' if f['passes'] else 'false')
        break
")

    if [ "$PASSED" = "true" ]; then
        log "$FID PASSED"
    else
        log "$FID NOT PASSED — retrying once more"
        # Retry with more specific instructions
        claude -p "$(cat "$PROMPT_FILE")

IMPORTANT: The previous attempt did not mark this feature as passed. Focus on getting tests to pass. If blocked, output NEEDS_HUMAN." \
             --allowedTools "Read,Edit,Write,Bash,Glob,Grep,Agent" \
             --output-format text 2>&1 | tee "/tmp/csupply_output_${FID}_retry.log"
    fi

    # Check for human input needed
    if grep -q "NEEDS_HUMAN" "/tmp/csupply_output_${FID}.log" 2>/dev/null; then
        log "NEEDS HUMAN INPUT — stopping for review"
        grep "NEEDS_HUMAN" "/tmp/csupply_output_${FID}.log"
        break
    fi

    # Periodic session compression
    if [ $((SESSION_COUNT % COMPRESS_EVERY)) -eq 0 ]; then
        log "Compressing claude-progress.txt (keeping last 50 lines)"
        # Keep header + last N lines
        python3 -c "
lines = open('$PROGRESS_FILE').readlines()
if len(lines) > 60:
    with open('$PROGRESS_FILE', 'w') as f:
        f.writelines(lines[:5])  # header
        f.write('... (earlier sessions compressed) ...\n\n')
        f.writelines(lines[-50:])
"
    fi

    # Git save point
    if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        log "Saving uncommitted changes..."
        git add -A
        git commit -m "wip: after $FID session" --allow-empty
    fi

    log "Session $SESSION_COUNT done. Remaining: $(count_remaining)/$TOTAL"
    echo ""
done

log "=== Auto Runner Finished ==="
log "Sessions executed: $SESSION_COUNT"
log "Remaining features: $(count_remaining)/$TOTAL"
