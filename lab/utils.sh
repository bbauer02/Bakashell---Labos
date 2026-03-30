#!/bin/bash
# === Utility functions for Linux Lab ===

PROGRESS_FILE="/opt/linux-lab/data/progress.json"
TOTAL_EXERCISES=93

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════╗"
    echo "║            🐧 LINUX CLI LAB 🐧                 ║"
    echo "║        Tutoriel Interactif BTS SIO              ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step_header() {
    local step=$1
    local title=$2
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${BLUE}  ÉTAPE ${step} : ${title}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_exercise() {
    local num=$1
    local points=$2
    local desc=$3
    echo -e "${YELLOW}  📝 Exercice ${num}${NC} ${DIM}(${points} pts)${NC}"
    echo -e "     ${desc}"
    echo ""
}

print_success() {
    echo -e "  ${GREEN}✅ $1${NC}"
}

print_fail() {
    echo -e "  ${RED}❌ $1${NC}"
}

print_hint() {
    echo -e "  ${DIM}💡 Indice: $1${NC}"
}

print_info() {
    echo -e "  ${CYAN}ℹ️  $1${NC}"
}

# Progress management
get_score() {
    jq -r '.score' "$PROGRESS_FILE" 2>/dev/null || echo 0
}

get_completed() {
    jq -r '.completed[]' "$PROGRESS_FILE" 2>/dev/null
}

is_completed() {
    local exercise_id=$1
    jq -e ".completed | index(\"${exercise_id}\")" "$PROGRESS_FILE" > /dev/null 2>&1
}

add_score() {
    local exercise_id=$1
    local points=$2

    if is_completed "$exercise_id"; then
        echo -e "  ${DIM}(déjà validé)${NC}"
        return 0
    fi

    local current_score
    current_score=$(get_score)
    local new_score=$((current_score + points))

    local tmp=$(mktemp)
    jq ".score = ${new_score} | .completed += [\"${exercise_id}\"]" "$PROGRESS_FILE" > "$tmp" && mv "$tmp" "$PROGRESS_FILE"

    echo -e "  ${GREEN}+${points} points !${NC}"
    return 0
}

print_score() {
    local score
    score=$(get_score)
    local completed
    completed=$(jq '.completed | length' "$PROGRESS_FILE" 2>/dev/null || echo 0)
    local max_score=302

    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}SCORE : ${score} / ${max_score} points${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}Exercices complétés : ${completed} / ${TOTAL_EXERCISES}${NC}"

    # Progress bar
    local pct=0
    if [ "$max_score" -gt 0 ]; then
        pct=$((score * 100 / max_score))
    fi
    local filled=$((pct / 4))
    local empty=$((25 - filled))
    local bar=""
    for ((i=0; i<filled; i++)); do bar+="█"; done
    for ((i=0; i<empty; i++)); do bar+="░"; done
    echo -e "${CYAN}║${NC}  [${GREEN}${bar}${NC}] ${pct}%"

    # Grade
    local grade=""
    if [ "$pct" -ge 90 ]; then grade="🏆 Excellent !"
    elif [ "$pct" -ge 70 ]; then grade="🎉 Très bien !"
    elif [ "$pct" -ge 50 ]; then grade="👍 Bien !"
    elif [ "$pct" -ge 30 ]; then grade="📚 En progression"
    else grade="🚀 C'est parti !"
    fi
    echo -e "${CYAN}║${NC}  ${grade}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════╝${NC}"
    echo ""
}
