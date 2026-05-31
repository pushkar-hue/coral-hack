from datetime import datetime, timedelta, timezone

def get_next_weekday(dt, weekday_idx, hour_utc, minute_utc):
    days_ahead = weekday_idx - dt.weekday()
    if days_ahead <= 0:
        if days_ahead == 0 and (dt.hour < hour_utc or (dt.hour == hour_utc and dt.minute < minute_utc)):
            days_ahead = 0
        else:
            days_ahead += 7
    next_date = dt + timedelta(days=days_ahead)
    return next_date.replace(hour=hour_utc, minute=minute_utc, second=0, microsecond=0)

now_utc = datetime.now(timezone.utc)
next_lc = get_next_weekday(now_utc, 6, 2, 30)
next_cc = get_next_weekday(now_utc, 2, 14, 30)

print("Now UTC:", now_utc.isoformat())
print("Next LC:", next_lc.isoformat())
print("Next CC:", next_cc.isoformat())
