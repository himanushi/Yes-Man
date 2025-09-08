#!/bin/bash
# Incrementally update agent context files based on new feature plan
# Supports: CLAUDE.md, GEMINI.md, and .github/copilot-instructions.md
# O(1) operation - only reads current context file and new plan.md

set -e

REPO_ROOT=$(git rev-parse --show-toplevel)
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
# Remove feature/ prefix from branch name for directory
FEATURE_DIR_NAME="${CURRENT_BRANCH#feature/}"
FEATURE_DIR="$REPO_ROOT/specs/$FEATURE_DIR_NAME"
NEW_PLAN="$FEATURE_DIR/plan.md"

# Determine which agent context files to update
CLAUDE_FILE="$REPO_ROOT/CLAUDE.md"
GEMINI_FILE="$REPO_ROOT/GEMINI.md"
COPILOT_FILE="$REPO_ROOT/.github/copilot-instructions.md"

# Allow override via argument
AGENT_TYPE="$1"

if [ ! -f "$NEW_PLAN" ]; then
    echo "ERROR: No plan.md found at $NEW_PLAN"
    exit 1
fi

echo "=== Updating agent context files for feature $CURRENT_BRANCH ==="

# Extract tech from new plan (Japanese format)
NEW_LANG=$(grep "^**言語/バージョン**: " "$NEW_PLAN" 2>/dev/null | head -1 | sed 's/^**言語\/バージョン**: //' | grep -v "NEEDS CLARIFICATION" || echo "")
NEW_FRAMEWORK=$(grep "^**主要依存関係**: " "$NEW_PLAN" 2>/dev/null | head -1 | sed 's/^**主要依存関係**: //' | grep -v "NEEDS CLARIFICATION" || echo "")
NEW_TESTING=$(grep "^**テスト**: " "$NEW_PLAN" 2>/dev/null | head -1 | sed 's/^**テスト**: //' | grep -v "NEEDS CLARIFICATION" || echo "")
NEW_DB=$(grep "^**ストレージ**: " "$NEW_PLAN" 2>/dev/null | head -1 | sed 's/^**ストレージ**: //' | grep -v "N/A" | grep -v "NEEDS CLARIFICATION" || echo "")
NEW_PROJECT_TYPE=$(grep "^**プロジェクトタイプ**: " "$NEW_PLAN" 2>/dev/null | head -1 | sed 's/^**プロジェクトタイプ**: //' || echo "")

# Function to update a single agent context file
update_agent_file() {
    local target_file="$1"
    local agent_name="$2"
    
    echo "Updating $agent_name context file: $target_file"
    
    # Create temp file for new context
    local temp_file=$(mktemp)
    
    # If file doesn't exist, create from template
    if [ ! -f "$target_file" ]; then
        echo "Creating new $agent_name context file..."
        
        # Check if this is the SDD repo itself
        if [ -f "$REPO_ROOT/templates/agent-file-template.md" ]; then
            cp "$REPO_ROOT/templates/agent-file-template.md" "$temp_file"
        else
            echo "ERROR: Template not found at $REPO_ROOT/templates/agent-file-template.md"
            return 1
        fi
        
        # Replace placeholders with proper escaping (correct template format)
        PROJECT_NAME=$(basename "$REPO_ROOT")
        CURRENT_DATE=$(date +%Y-%m-%d)
        sed -i.bak "s/\[プロジェクト名\]/$PROJECT_NAME/" "$temp_file"
        sed -i.bak "s/\[日付\]/$CURRENT_DATE/" "$temp_file"
        sed -i.bak "s|\[すべての PLAN.MD ファイルから抽出\]|- $NEW_LANG + $NEW_FRAMEWORK ($CURRENT_BRANCH)|" "$temp_file"
        
        # Add project structure based on type (correct template format)
        if [[ "$NEW_PROJECT_TYPE" == *"web"* ]]; then
            sed -i.bak "s|\[計画からの実際の構造\]|audio_layer/\nface_ui/\nlangflow_flows/\ntests/|" "$temp_file"
        else
            sed -i.bak "s|\[計画からの実際の構造\]|audio_layer/\nface_ui/\nlangflow_flows/\ntests/|" "$temp_file"
        fi
        
        # Add minimal commands (correct template format)
        if [[ "$NEW_LANG" == *"Python"* ]]; then
            COMMANDS="pytest tests/ && ruff check audio_layer/"
        elif [[ "$NEW_LANG" == *"Rust"* ]]; then
            COMMANDS="cargo test && cargo clippy"
        elif [[ "$NEW_LANG" == *"JavaScript"* ]] || [[ "$NEW_LANG" == *"TypeScript"* ]]; then
            COMMANDS="npm test && npm run lint"
        else
            COMMANDS="# Add commands for $NEW_LANG"
        fi
        sed -i.bak "s|\[アクティブテクノロジー用のコマンドのみ\]|$COMMANDS|" "$temp_file"
        
        # Add code style (correct template format)
        sed -i.bak "s|\[言語固有、使用中の言語のみ\]|$NEW_LANG: Follow standard conventions|" "$temp_file"
        
        # Add recent changes (correct template format)
        sed -i.bak "s|\[最新の3つの機能とその追加内容\]|- $CURRENT_BRANCH: Added $NEW_LANG + $NEW_FRAMEWORK|" "$temp_file"
        
        rm "$temp_file.bak"
    else
        echo "Updating existing $agent_name context file..."
        
        # Extract manual additions
        local manual_start=$(grep -n "<!-- MANUAL ADDITIONS START -->" "$target_file" | cut -d: -f1)
        local manual_end=$(grep -n "<!-- MANUAL ADDITIONS END -->" "$target_file" | cut -d: -f1)
        
        if [ ! -z "$manual_start" ] && [ ! -z "$manual_end" ]; then
            sed -n "${manual_start},${manual_end}p" "$target_file" > /tmp/manual_additions.txt
        fi
        
        # Parse existing file and create updated version
        python3 - "$target_file" "$temp_file" "$NEW_LANG" "$NEW_FRAMEWORK" "$NEW_DB" "$NEW_PROJECT_TYPE" "$CURRENT_BRANCH" << 'EOF'
import re
import sys
from datetime import datetime

# Get command line arguments
target_file = sys.argv[1]
temp_file = sys.argv[2]
new_lang = sys.argv[3] if len(sys.argv) > 3 else ""
new_framework = sys.argv[4] if len(sys.argv) > 4 else ""
new_db = sys.argv[5] if len(sys.argv) > 5 else ""
new_project_type = sys.argv[6] if len(sys.argv) > 6 else ""
current_branch = sys.argv[7] if len(sys.argv) > 7 else ""

# Read existing file
with open(target_file, 'r') as f:
    content = f.read()

# Check if new tech already exists (correct Japanese section name)
tech_section = re.search(r'## アクティブテクノロジー\n(.*?)\n\n', content, re.DOTALL)
if tech_section:
    existing_tech = tech_section.group(1)
    
    # Add new tech if not already present
    new_additions = []
    if new_lang and new_lang not in existing_tech:
        new_additions.append(f"- {new_lang} + {new_framework} ({current_branch})")
    if new_db and new_db not in existing_tech and new_db != "N/A":
        new_additions.append(f"- {new_db} ({current_branch})")
    
    if new_additions:
        updated_tech = existing_tech + "\n" + "\n".join(new_additions)
        content = content.replace(tech_section.group(0), f"## アクティブテクノロジー\n{updated_tech}\n\n")

# Update project structure if needed (correct Japanese section name)
if new_project_type == "web" and "frontend/" not in content:
    struct_section = re.search(r'## プロジェクト構造\n```\n(.*?)\n```', content, re.DOTALL)
    if struct_section:
        updated_struct = struct_section.group(1) + "\nfrontend/src/      # Web UI"
        content = re.sub(r'(## プロジェクト構造\n```\n).*?(\n```)', 
                        f'\\1{updated_struct}\\2', content, flags=re.DOTALL)

# Add new commands if language is new (correct Japanese section name)
if new_lang and f"# {new_lang}" not in content:
    commands_section = re.search(r'## コマンド\n```bash\n(.*?)\n```', content, re.DOTALL)
    if not commands_section:
        commands_section = re.search(r'## コマンド\n(.*?)\n\n', content, re.DOTALL)
    
    if commands_section:
        new_commands = commands_section.group(1)
        if "Python" in new_lang:
            new_commands += "\npytest tests/ && ruff check audio_layer/"
        elif "Rust" in new_lang:
            new_commands += "\ncargo test && cargo clippy"
        elif "JavaScript" in new_lang or "TypeScript" in new_lang:
            new_commands += "\nnpm test && npm run lint"
        
        if "```bash" in content:
            content = re.sub(r'(## コマンド\n```bash\n).*?(\n```)', 
                            f'\\1{new_commands}\\2', content, flags=re.DOTALL)
        else:
            content = re.sub(r'(## コマンド\n).*?(\n\n)', 
                            f'\\1{new_commands}\\2', content, flags=re.DOTALL)

# Update recent changes (keep only last 3) (correct Japanese section name)
changes_section = re.search(r'## 最近の変更\n(.*?)(\n\n|$)', content, re.DOTALL)
if changes_section:
    changes = changes_section.group(1).strip().split('\n')
    changes.insert(0, f"- {current_branch}: Added {new_lang} + {new_framework}")
    # Keep only last 3
    changes = changes[:3]
    content = re.sub(r'(## 最近の変更\n).*?(\n\n|$)', 
                    f'\\1{chr(10).join(changes)}\\2', content, flags=re.DOTALL)

# Update date (correct Japanese format)
content = re.sub(r'最終更新: \d{4}-\d{2}-\d{2}', 
                f'最終更新: {datetime.now().strftime("%Y-%m-%d")}', content)

# Write to temp file
with open(temp_file, 'w') as f:
    f.write(content)
EOF

        # Restore manual additions if they exist
        if [ -f /tmp/manual_additions.txt ]; then
            # Remove old manual section from temp file
            sed -i.bak '/<!-- MANUAL ADDITIONS START -->/,/<!-- MANUAL ADDITIONS END -->/d' "$temp_file"
            # Append manual additions
            cat /tmp/manual_additions.txt >> "$temp_file"
            rm /tmp/manual_additions.txt "$temp_file.bak"
        fi
    fi
    
    # Move temp file to final location
    mv "$temp_file" "$target_file"
    echo "✅ $agent_name context file updated successfully"
}

# Update files based on argument or detect existing files
case "$AGENT_TYPE" in
    "claude")
        update_agent_file "$CLAUDE_FILE" "Claude Code"
        ;;
    "gemini") 
        update_agent_file "$GEMINI_FILE" "Gemini CLI"
        ;;
    "copilot")
        update_agent_file "$COPILOT_FILE" "GitHub Copilot"
        ;;
    "")
        # Update all existing files
        [ -f "$CLAUDE_FILE" ] && update_agent_file "$CLAUDE_FILE" "Claude Code"
        [ -f "$GEMINI_FILE" ] && update_agent_file "$GEMINI_FILE" "Gemini CLI" 
        [ -f "$COPILOT_FILE" ] && update_agent_file "$COPILOT_FILE" "GitHub Copilot"
        
        # If no files exist, create based on current directory or ask user
        if [ ! -f "$CLAUDE_FILE" ] && [ ! -f "$GEMINI_FILE" ] && [ ! -f "$COPILOT_FILE" ]; then
            echo "No agent context files found. Creating Claude Code context file by default."
            update_agent_file "$CLAUDE_FILE" "Claude Code"
        fi
        ;;
    *)
        echo "ERROR: Unknown agent type '$AGENT_TYPE'. Use: claude, gemini, copilot, or leave empty for all."
        exit 1
        ;;
esac
echo ""
echo "Summary of changes:"
if [ ! -z "$NEW_LANG" ]; then
    echo "- Added language: $NEW_LANG"
fi
if [ ! -z "$NEW_FRAMEWORK" ]; then
    echo "- Added framework: $NEW_FRAMEWORK"
fi
if [ ! -z "$NEW_DB" ] && [ "$NEW_DB" != "N/A" ]; then
    echo "- Added database: $NEW_DB"
fi

echo ""
echo "Usage: $0 [claude|gemini|copilot]"
echo "  - No argument: Update all existing agent context files"
echo "  - claude: Update only CLAUDE.md"
echo "  - gemini: Update only GEMINI.md" 
echo "  - copilot: Update only .github/copilot-instructions.md"