import os
import subprocess
import re
from datetime import datetime

def run_cmd(cmd):
    return subprocess.check_output(cmd, shell=True, text=True).strip()

def fix_history():
    commits = run_cmd('git log --reverse --format="%H|%s|%ad" --date=iso main').split('\n')
    
    run_cmd("git config core.safecrlf false") 
    
    try:
        run_cmd("git branch -D clean_history2")
    except:
        pass
        
    run_cmd("git checkout --orphan clean_history2")
    run_cmd("git rm -rf .")
    
    def clean_wd():
        subprocess.run("git rm -rf .", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    for i, commit_info in enumerate(commits):
        if not commit_info.strip(): continue
        
        ##parse old commit data
        parts = commit_info.split('|')
        c_hash = parts[0]
        c_msg = parts[1]
        c_date = parts[2]
        
        ##checkout files from that commit
        clean_wd()
        run_cmd(f"git checkout {c_hash} -- .")
        
        ##add to gitignore if not present
        gitignore_content = ""
        if os.path.exists(".gitignore"):
            with open(".gitignore", "r") as f:
                gitignore_content = f.read()
        
        files_to_ignore = ["run_batch.py", "auto_improve.py", "analyse_maps.py"]
        added_to_ignore = False
        for fi in files_to_ignore:
            if fi not in gitignore_content:
                gitignore_content += f"\n{fi}"
                added_to_ignore = True
                
        if added_to_ignore:
            with open(".gitignore", "w") as f:
                f.write(gitignore_content.strip() + "\n")
            
        ##remove these files if they exist in this commit
        for fi in files_to_ignore:
            if os.path.exists(fi):
                os.remove(fi)
        
        ##refactor comments in Python files
        py_files = run_cmd('git ls-files "*.py"').split()
        for py_file in py_files:
            if not py_file: continue
            ##skip the ignored ones just in case
            if py_file in files_to_ignore: continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                new_lines = []
                for line in lines:
                    ##match any '#' that is not inside quotes (simple heuristic: look for leading spaces + '#')
                    ##user wants to replace '# ' or '#' with '##'
                    ##we will replace lines that start with optional whitespace then '#'
                    if re.match(r'^\s*#(?!##comment)', line):
                        line = re.sub(r'(^\s*)#\s*', r'\1##', line)
                    new_lines.append(line)
                    
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
            except Exception:
                pass
        
        ##add all changes
        run_cmd("git add .")
        
        ##fix Message (Remove BETA prefixes)
        ##e.g., "BETA 8.1 - Rushers & Lawnmower Enabled" -> "Rushers & Lawnmower Enabled"
        # "BETA 9.0" -> "Update logic" (if empty)
        c_msg = re.sub(r'^BETA\s+[\d\.]+\s*(?:-\s*)?', '', c_msg).strip()
        if not c_msg:
            c_msg = "Update logic"
            
        ##commit keeping the SAME date we generated previously
        env = dict(os.environ)
        env['GIT_COMMITTER_DATE'] = c_date
        env['GIT_AUTHOR_DATE'] = c_date
        
        subprocess.run(["git", "commit", "--allow-empty", "-m", c_msg, "--date", c_date], env=env)

    ##finally switch main branch to this
    run_cmd("git branch -f main clean_history2")
    run_cmd("git checkout main")
    print("FINISHED HISTORY REWRITE 2")

if __name__ == "__main__":
    fix_history()