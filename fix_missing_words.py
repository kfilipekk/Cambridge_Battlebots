import os, re, subprocess

def replace_missed(text):
    text = text.replace('analyze_maps', 'analyse_maps')
    text = text.replace('Analyze_maps', 'Analyse_maps')
    return text

def run_cmd(cmd):
    return subprocess.check_output(cmd, shell=True, text=True).strip()

def fix_history():
    commits = run_cmd('git log --reverse --format="%H|%s|%ad" --date=iso main').split('\n')
    subprocess.run("git config core.safecrlf false", shell=True)
    subprocess.run("git branch -D clean_history6", shell=True, stderr=subprocess.DEVNULL)
    subprocess.run("git checkout --orphan clean_history6", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    for str_commit in commits:
        if not str_commit.strip(): continue
        parts = str_commit.split('|')
        c_hash = parts[0]
        c_msg = replace_missed(parts[1])
        c_date = parts[2]
        
        subprocess.run("git rm -rf .", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(f"git checkout {c_hash} -- .", shell=True)
        
        all_files = run_cmd('git ls-files').split()
        for fpath in all_files:
            if not fpath: continue
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                new_content = replace_missed(content)
                if new_content != content:
                    with open(fpath, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                
                # Check for filename itself! Since we already renamed it in the last pass, it might be named analyse_maps already, but let's double check.
            except Exception:
                pass
        
        subprocess.run("git add .", shell=True)
        
        env = dict(os.environ)
        env['GIT_COMMITTER_DATE'] = c_date
        env['GIT_AUTHOR_DATE'] = c_date
        subprocess.run(["git", "commit", "--allow-empty", "-m", c_msg, "--date", c_date], env=env)

    subprocess.run("git branch -f main clean_history6", shell=True)
    subprocess.run("git checkout main", shell=True)
    print("FINISHED MISSING WORDS REWRITE")

if __name__ == "__main__":
    fix_history()