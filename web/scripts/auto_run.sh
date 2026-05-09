#!/bin/bash
# auto_run.sh - Content Supply Web 自动化工作流脚本
# 遵循 agent-harness-framework 范式

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err()   { echo -e "${RED}[ERR]${NC} $1"; }

# ===== Commands =====

cmd_status() {
  log_info "=== Content Supply Web Status ==="

  if [ ! -f "feature_list.json" ]; then
    log_err "feature_list.json not found. Run 'auto_run.sh init' first."
    exit 1
  fi

  # Parse feature list with python
  python3 -c "
import json
with open('feature_list.json') as f:
    features = json.load(f)
total = len(features)
passed = sum(1 for f in features if f.get('passes'))
pending = [f for f in features if not f.get('passes')]

bar_len = 40
filled = int(bar_len * passed / total) if total else 0
bar = '█' * filled + '░' * (bar_len - filled)
print(f'\n  Progress: [{bar}] {passed}/{total} ({100*passed//total}%)')
print()

if pending:
    print('  Next features:')
    for f in sorted(pending, key=lambda x: x.get('priority', 5))[:5]:
        print(f'    [{f[\"id\"]}] P{f.get(\"priority\",\"?\")} - {f[\"description\"][:60]}')
    print()
"
  # Show recent progress
  if [ -f "claude-progress.txt" ]; then
    log_info "Recent progress:"
    tail -10 claude-progress.txt
  fi
}

cmd_check() {
  log_info "Running pre-flight checks..."
  local ok=true

  # Check node
  if command -v node &>/dev/null; then
    log_ok "Node.js: $(node --version)"
  else
    log_err "Node.js not found"
    ok=false
  fi

  # Check npm
  if command -v npm &>/dev/null; then
    log_ok "npm: $(npm --version)"
  else
    log_err "npm not found"
    ok=false
  fi

  # Check dependencies
  if [ -d "node_modules" ]; then
    log_ok "node_modules exists"
  else
    log_warn "node_modules missing. Run: npm install"
    ok=false
  fi

  # Type check
  log_info "TypeScript type check..."
  if npm run type-check 2>&1 | grep -q "error"; then
    log_err "TypeScript errors found"
    npm run type-check 2>&1 | grep "error"
    ok=false
  else
    log_ok "TypeScript: no errors"
  fi

  # Build check
  log_info "Build check..."
  if npm run build > /dev/null 2>&1; then
    log_ok "Build: success"
  else
    log_err "Build failed"
    ok=false
  fi

  if $ok; then
    log_ok "All checks passed!"
  else
    log_err "Some checks failed. Fix before proceeding."
    exit 1
  fi
}

cmd_dev() {
  log_info "Starting dev server..."
  npm run dev
}

cmd_build() {
  log_info "Building for production..."
  npm run build
  log_ok "Build complete: dist/"
}

cmd_test() {
  log_info "Running tests..."
  npm run test 2>/dev/null || log_warn "No tests configured yet"
}

cmd_clean() {
  log_info "Cleaning build artifacts..."
  rm -rf dist/ node_modules/.vite node_modules/.tmp
  log_ok "Cleaned dist/, .vite cache"
}

cmd_init() {
  log_info "Initializing project..."
  if [ ! -d "node_modules" ]; then
    log_info "Installing dependencies..."
    npm install
  fi
  log_ok "Project initialized. Run 'auto_run.sh dev' to start."
}

# ===== Main =====

case "${1:-status}" in
  status)  cmd_status ;;
  check)   cmd_check ;;
  dev)     cmd_dev ;;
  build)   cmd_build ;;
  test)    cmd_test ;;
  clean)   cmd_clean ;;
  init)    cmd_init ;;
  *)
    echo "Usage: $0 {status|check|dev|build|test|clean|init}"
    echo ""
    echo "  status  Show feature progress (default)"
    echo "  check   Run pre-flight checks (type-check + build)"
    echo "  dev     Start development server"
    echo "  build   Build for production"
    echo "  test    Run tests"
    echo "  clean   Remove build artifacts"
    echo "  init    Install dependencies and initialize"
    exit 1
    ;;
esac
