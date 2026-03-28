import os
import glob
import time
import subprocess
import json
from string import ascii_lowercase
from cambc.api import api_get
from cambc.auth import load_credentials

##replay to ASCII parsing
TERRAIN_ICONS = {0: ".", 1: "#", 2: "T", 3: "A"}

def fetch_teams():
    print("Fetching leaderboard approximations via search API...")
    teams = {}
    ##iterate through a few letters to gather a good sample of teams
    for c in ascii_lowercase[:5]:  ##just a-e is usually enough for a small ladder
        try:
            res = api_get(f"/api/teams/search?q={c}")
            for t in res.get("teams", []):
                teams[t.get("teamId")] = t
        except Exception:
            pass
    return sorted(teams.values(), key=lambda x: x.get("rating", 0))

def find_target_opponent():
    creds = load_credentials()
    my_team_id = creds.get("team", {}).get("id")
    my_rating = 0
    
    try:
        my_team = api_get(f"/api/teams/{my_team_id}")
        if my_team.get("rating"):
            my_rating = my_team["rating"].get("rating", 0)
    except:
        pass

    teams = fetch_teams()
    print(f"My rating: {my_rating:.0f}")
    
    ##target the player immediately above us
    target = None
    for t in teams:
        if t.get("teamId") == my_team_id:
            continue
        if t.get("rating", 0) >= my_rating:
            target = t
            break
            
    ##fallback to highest rated if we are the highest or couldn't find
    if not target and teams:
        target = teams[-1]
        
    if target:
        print(f"Found target: {target.get('teamName')} ({target.get('rating',0):.0f})")
    
    return target

def analyze_replay(replay_path):
    print(f"Analysing {replay_path}...")
    with open(replay_path, "rb") as f:
        data = f.read()

    ##heuristic: the map is at the beginning. Find the width & height.
    try:
        width = data[data.find(b'\x08') + 1]
        height = data[data.find(b'\x10') + 1]
        row_signature = bytes([0x0A, width])

        rows = []
        idx = 0
        while len(rows) < height:
            idx = data.find(row_signature, idx)
            if idx == -1:
                break
            rows.append(data[idx + 2 : idx + 2 + width])
            idx += 2 + width

        output_filename = replay_path.replace(".replay26", "_ANALYSIS.txt")
        with open(output_filename, "w", encoding="utf-8") as out:
            out.write(f"--- REPLAY START MAP ANALYSIS: {replay_path} ---\n")
            out.write("+" + "-" * width + "+\n")
            for row in rows:
                row_str = "".join([TERRAIN_ICONS.get(b, "?") for b in row])
                out.write("|" + row_str + "|\n")
            out.write("+" + "-" * width + "+\n\n")
            
            ##simple text dump of strings/errors or bot positions found later in the binary:
            strings = [s.decode('ascii') for s in data.split(b'\x00') if len(s) > 4 and all(32 <= c < 127 for c in s)]
            if strings:
                out.write("Detected Events/Bot Signatures in Replay Blob:\n")
                for s in strings[:50]:
                    out.write(f"- {s}\n")
        
        print(f"✅ Saved analysis to {output_filename}")
    except Exception as e:
        print(f"Failed to parse replay binary heuristic: {e}")

def run_auto_improve():
    target = find_target_opponent()
    if not target:
        print("No target found.")
        return

    print("Queuing unrated match against target...")
    subprocess.run(["cambc", "unrated", target["teamId"]], shell=True)
    
    print("Check your dashboard to download the replay (.replay26) once it finishes.")
    print("Once downloaded into the workspace, this script will analyse any .replay26 files.")
    
    for rp in glob.glob("*.replay26"):
        analyze_replay(rp)

if __name__ == "__main__":
    run_auto_improve()