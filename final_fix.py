import os
import subprocess
import re

def run_cmd(cmd):
    return subprocess.check_output(cmd, shell=True, text=True).strip()

def fix_history():
    commits = run_cmd('git log --reverse --format="%H|%s|%ad" --date=iso main').split('\n')
    
    run_cmd("git config core.safecrlf false") 
    
    try:
        run_cmd("git branch -D clean_history3")
    except:
        pass
        
    run_cmd("git checkout --orphan clean_history3")
    subprocess.run("git rm -rf .", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    def replacer(match):
        char = match.group(1)
        if char:
            return '##' + char.lower()
        return '##'

    for commit_info in commits:
        if not commit_info.strip(): continue
        
        parts = commit_info.split('|')
        c_hash = parts[0]
        c_msg = parts[1]
        c_date = parts[2]
        
        subprocess.run("git rm -rf .", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        run_cmd(f"git checkout {c_hash} -- .")
        
        py_files = run_cmd('git ls-files "*.py"').split()
        for py_file in py_files:
            if not py_file: continue
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Replace "##comment " with "##" and lowercase the next letter!
                # Also catch any lingering "# " just in case
                new_content = re.sub(r'##comment\s*(.)?', replacer, content)
                new_content = re.sub(r'#\s*(?=[A-Za-z0-9_])(.)?', replacer, new_content)

                if new_content != content:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
            except Exception:
                pass
        
        run_cmd("git add .")
        
        env = dict(os.environ)
        env['GIT_COMMITTER_DATE'] = c_date
        env['GIT_AUTHOR_DATE'] = c_date
        
        subprocess.run(["git", "commit", "--allow-empty", "-m", c_msg, "--date", c_date], env=env)

    run_cmd("git branch -f main clean_history3")
    run_cmd("git checkout main")
    print("FINISHED HISTORY REWRITE 3")

if __name__ == "__main__":
    fix_history()