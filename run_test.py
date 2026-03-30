import subprocess
import sys

cmd = [
    r".\.venv\Scripts\cambc.exe", "run", "bots/my_bot", "bots/opponent", 
    "maps/default_small1.map26", "--seed", "1"
]

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    out = result.stdout + "\n" + result.stderr
except subprocess.TimeoutExpired as e:
    out = "TIMEOUT\n" + (e.stdout.decode() if e.stdout else "") + "\n" + (e.stderr.decode() if e.stderr else "")
except Exception as e:
    out = str(e)

with open("test_out.txt", "w", encoding="utf-8") as f:
    f.write(out)

print("Done running test match.")
