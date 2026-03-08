import os
import subprocess
from datetime import datetime
import re

def run_cmd(cmd):
    return subprocess.check_output(cmd, shell=True, text=True).strip()

def rewrite_exact_history():
    commits = run_cmd('git log --reverse --format="%H|%s" backup_main').split('\n')
    
    with open("commit_dates.txt", "r") as f:
        dates = [d.strip() for d in f.readlines()]
    
    run_cmd("git config core.safecrlf false") 
    
    try:
        run_cmd("git branch -D clean_history")
    except:
        pass
        
    run_cmd("git checkout --orphan clean_history")
    run_cmd("git rm -rf .")
    
    ##helper to clean working directory without erroring if empty
    def clean_wd():
        subprocess.run("git rm -rf .", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    for i, commit_info in enumerate(commits):
        if not commit_info.strip(): continue
        c_hash, c_msg = commit_info.split('|', 1)
        
        ##restore exact files from the target commit.
        clean_wd()
        run_cmd(f"git checkout {c_hash} -- .")
        
        ##refactor Comments in Python files
        py_files = run_cmd('git ls-files "*.py"').split()
        for py_file in py_files:
            if not py_file: continue
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                ##change all the comments to ###instead of ##comment from when they were first introsuced so they are never ##comment
                ##we replace exactly what is requested.
                new_content = re.sub(r'#\s*[Cc]omment', '##', content)
                
                if content != new_content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
            except Exception:
                pass
        
        ##add all
        run_cmd("git add .")
        
        ##craft Short message
        words = c_msg.split()
        if len(words) > 7 and "BETA" not in c_msg:
             short_msg = " ".join(words[:6]) + "..."
        else:
             short_msg = c_msg
             
        ##escape msg for command line if not using array
        ##actually, I'll just use a subprocess list which is safer
        
        ##commit with date
        dt_str = dates[i]
        env = dict(os.environ)
        ##using format: 2026-03-08T15:24:15
        dt_obj = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
        ##powerShell needs format for dates like 2025-06-24 19:12:04 +0100? No, standard format works if we pass it directly to git --date=
        ##wait, git commit --date expects either specific format or ISO.
        env['GIT_COMMITTER_DATE'] = dt_str
        env['GIT_AUTHOR_DATE'] = dt_str
        
        ##we need git commit --date=...
        subprocess.run(["git", "commit", "--allow-empty", "-m", short_msg, "--date", dt_str], env=env)

    ##finally switch main branch to this
    run_cmd("git branch -f main clean_history")
    run_cmd("git checkout main")
    print("FINISHED HISTORY REWRITE")

if __name__ == "__main__":
    rewrite_exact_history()