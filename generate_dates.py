import random
from datetime import datetime, timedelta

def get_random_date(start_dt, end_dt):
    delta = end_dt - start_dt
    while True:
        random_second = random.randint(0, int(delta.total_seconds()))
        dt = start_dt + timedelta(seconds=random_second)
        if dt.hour >= 12 or dt.hour == 0:
            return dt

start = datetime(2026, 3, 8)
end = datetime(2026, 4, 1)

##we need dates for the commits. Looking at the log, there are ~25 commits.
dates = [get_random_date(start, end) for _ in range(100)]
dates.sort()

with open("commit_dates.txt", "w") as f:
    for d in dates:
        f.write(d.strftime("%Y-%m-%dT%H:%M:%S") + "\n")
