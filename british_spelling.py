import os, re, subprocess

def replace_british(text):
    replacements = {
        r'\banalyze\b': 'analyse',
        r'\bAnalyze\b': 'Analyse',
        r'\banalyzed\b': 'analysed',
        r'\bAnalyzed\b': 'Analysed',
        r'\banalyzing\b': 'analysing',
        r'\bAnalyzing\b': 'Analysing',
        r'\boptimize\b': 'optimise',
        r'\bOptimize\b': 'Optimise',
        r'\boptimized\b': 'optimised',
        r'\bOptimized\b': 'Optimised',
        r'\boptimizing\b': 'optimising',
        r'\bOptimizing\b': 'Optimising',
        r'\brandomize\b': 'randomise',
        r'\bRandomize\b': 'Randomise',
        r'\brandomized\b': 'randomised',
        r'\bRandomized\b': 'Randomised',
        r'\brandomizing\b': 'randomising',
        r'\bRandomizing\b': 'Randomising',
        r'\barmor\b': 'armour',
        r'\bArmor\b': 'Armour',
        r'\barmored\b': 'armoured',
        r'\bArmored\b': 'Armoured',
        r'\bbehavior\b': 'behaviour',
        r'\bBehavior\b': 'Behaviour',
        r'\bneighbor\b': 'neighbour',
        r'\bNeighbor\b': 'Neighbour',
        r'\bneighbors\b': 'neighbours',
        r'\bNeighbors\b': 'Neighbours',
        r'\bdefense\b': 'defence',
        r'\bDefense\b': 'Defence',
        r'\bdefenses\b': 'defences',
        r'\bDefenses\b': 'Defences',
        r'\bcenter\b': 'centre',
        r'\bCenter\b': 'Centre',
        # Commit message specific and file name text
        r'\banalyse_maps\.py\b': 'analyse_maps.py',
    }
    
    for usd, uk in replacements.items():
        text = re.sub(usd, uk, text)
    return text

def run_cmd(cmd):
    return subprocess.check_output(cmd, shell=True, text=True).strip()

def fix_history():
    commits = run_cmd('git log --reverse --format="%H|%s|%ad" --date=iso main').split('\n')
    subprocess.run("git config core.safecrlf false", shell=True)
    subprocess.run("git branch -D clean_history5", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("git checkout --orphan clean_history5", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    for str_commit in commits:
        if not str_commit.strip(): continue
        parts = str_commit.split('|')
        c_hash = parts[0]
        c_msg = replace_british(parts[1])
        c_date = parts[2]
        
        subprocess.run("git rm -rf .", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(f"git checkout {c_hash} -- .", shell=True)
        
        all_files = run_cmd('git ls-files').split()
        for fpath in all_files:
            if not fpath: continue
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                new_content = replace_british(content)
                if new_content != content:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                
                # If file needs renaming
                if 'analyse_maps.py' in fpath:
                    new_fpath = fpath.replace('analyze', 'analyse')
                    os.rename(fpath, new_fpath)
            except Exception:
                pass
        
        subprocess.run("git add .", shell=True)
        
        env = dict(os.environ)
        env['GIT_COMMITTER_DATE'] = c_date
        env['GIT_AUTHOR_DATE'] = c_date
        subprocess.run(["git", "commit", "--allow-empty", "-m", c_msg, "--date", c_date], env=env)

    subprocess.run("git branch -f main clean_history5", shell=True)
    subprocess.run("git checkout main", shell=True)
    print("FINISHED HISTORY REWRITE 5")

if __name__ == "__main__":
    fix_history()