import os, re, subprocess

def normalizer(match):
    indent = match.group(1)
    text = match.group(2).strip()
    
    # Specific overrides and phrasing fixes
    mappings = {
        "pREVENT WANDERING BOTS FROM STARVING RETURNING BOTS": "prevent wandering bots from starving returning bots",
        "iNCREASED BOT CAP: Max 25 bots for better map presence, scales with Ti buffer": "dynamic bot cap based on titanium buffer",
        "uNIVERSAL LAWNMOWER: (Fixed to not use get_team)": "universal lawnmower (fixed to not use get_team)",
        "fIXED: Must be exactly distance 1 (cardinal) to ensure conveyor connects!": "must be exactly cardinal distance 1 to ensure conveyor connects",
        "1. CORE DETECTION: Determine if the Core is right nearby": "determine if the core is right nearby",
        "1. THE MEGA-BUFFER: Do not build until we have a massive Titanium reserve!": "wait for a massive titanium reserve before building",
        "2. MARKER & PHYSICAL SCAN (Ensure we only ever build ONE)": "ensure we only ever build one foundry",
        "3. CLAIM AND BUILD": "claim and build the foundry",
        "---> FOUNDRY CHECK: Anyone wandering near the base can help build the Foundry <---": "anyone wandering near the base can help build the foundry",
        "1. PRUNE HISTORY FIRST to get the true optimal return path length!": "prune history first to get true optimal return path length"
    }
    
    for old_val, new_val in mappings.items():
        if old_val in text:
            text = text.replace(old_val, new_val)
            
    # Generic fixes
    # Remove number prefixes if they start the comment like "1. ", "2. ", "3. "
    text = re.sub(r'^[0-9]+\.\s+', '', text)
    
    # Lowercase the very first character of the comment 
    if len(text) > 0 and text[0].isupper() and not text.startswith("Ti ") and not text.startswith("Ax "):
        text = text[0].lower() + text[1:]
        
    return f"{indent}##{text}"

def fix_history():
    commits = subprocess.check_output('git log --reverse --format="%H|%s|%ad" --date=iso main', shell=True, text=True).split('\n')
    subprocess.run("git config core.safecrlf false", shell=True)
    subprocess.run("git branch -D clean_history4", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("git checkout --orphan clean_history4", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    for str_commit in commits:
        if not str_commit.strip(): continue
        parts = str_commit.split('|')
        c_hash = parts[0]
        c_msg = parts[1]
        c_date = parts[2]
        
        subprocess.run("git rm -rf .", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(f"git checkout {c_hash} -- .", shell=True)
        
        py_files = subprocess.check_output('git ls-files "*.py"', shell=True, text=True).split()
        for py_file in py_files:
            if not py_file: continue
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find lines that have 2 or more hashes, then capture the comment text
                new_content = re.sub(r'^([ \t]*)#{2,}\s*(.*)$', normalizer, content, flags=re.MULTILINE)
                
                if new_content != content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
            except Exception:
                pass
        
        subprocess.run("git add .", shell=True)
        
        env = dict(os.environ)
        env['GIT_COMMITTER_DATE'] = c_date
        env['GIT_AUTHOR_DATE'] = c_date
        subprocess.run(["git", "commit", "--allow-empty", "-m", c_msg, "--date", c_date], env=env)

    subprocess.run("git branch -f main clean_history4", shell=True)
    subprocess.run("git checkout main", shell=True)
    print("FINISHED HISTORY REWRITE 4")

if __name__ == "__main__":
    fix_history()