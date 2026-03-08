import os, sys, re, random
from datetime import datetime, timedelta
import subprocess

def process_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        ##replace occurrences of ##comment with ###new_content = re.sub(r'#\s*(?i)comment', '##', content)
        
        ##since the user stated "change all the comments to ##"
        ##let's be thorough on simple standard comments that look like ##comment or similar
        ##if it just replaces '##comment', it works perfectly as requested.
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
    except:
        pass

if __name__ == "__main__":
    ##refactor
    files = subprocess.check_output("git ls-files '*.py'", shell=True, text=True).split()
    for f in files:
        if f.strip():
            process_file(f.strip())
            
    subprocess.run("git add -u", shell=True)
    
    ##get Date
    dt_str = "2026-03-08T15:00:00"
    if os.path.exists("commit_dates.txt"):
        with open("commit_dates.txt", "r") as f:
            lines = f.readlines()
        if lines:
            dt_str = lines.pop(0).strip()
            with open("commit_dates.txt", "w") as f:
                f.writelines(lines)
                
    ##shorten Message
    msg = subprocess.check_output("git log -1 --format=%B", shell=True, text=True).strip()
    lines = msg.split('\n')
    short_msg = lines[0]
    
    if len(short_msg.split()) > 7 and "BETA" not in short_msg:
         short_msg = " ".join(short_msg.split()[:5]) + "..."
    ##if the user's msg has merge etc, keep it
    
    env = dict(os.environ)
    env['GIT_COMMITTER_DATE'] = dt_str
    env['GIT_AUTHOR_DATE'] = dt_str
    
    subprocess.run(["git", "commit", "--amend", "-m", short_msg, "--date", dt_str], env=env)
