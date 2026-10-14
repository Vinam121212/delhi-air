"""Personal exposure log: time outdoors → daily clean-air score and streaks.

The log lives in each visitor's own browser (cookies, see app.exposure_db); my_exposure.json is only a local backup.
"""
import base64
import json
import uuid
import zlib
from datetime import date, timedelta
from pathlib import Path

PATH = Path(__file__).parent / "my_exposure.json"
CIG_UG = 22.0          # µg/m³ of PM2.5 for 24 h ≈ one cigarette (Berkeley Earth)
GOOD_SCORE = 60        # a day at or above this counts toward the streak


COOKIE = "aqf_x"          # chunks are aqf_x0, aqf_x1, …
CHUNK = 3500
MAX_ENTRIES = 120         # keeps the cookies small (a few KB) so every server accepts them


def empty() -> dict:
    return {"entries": [], "purifier": False}


def load_file() -> dict | None:
    try:
        return json.loads(PATH.read_text())
    except Exception:
        return None


def save_file(db: dict):
    PATH.write_text(json.dumps(db, indent=2, default=str))


def encode(db: dict) -> list[str]:
    db = {**db, "entries": db["entries"][-MAX_ENTRIES:]}
    packed = zlib.compress(json.dumps(db, separators=(",", ":"), default=str).encode(), 9)
    raw = base64.urlsafe_b64encode(packed).decode().rstrip("=")
    return [raw[i:i + CHUNK] for i in range(0, len(raw), CHUNK)] or [""]


def decode(cookies: dict) -> dict | None:
    parts, i = [], 0
    while f"{COOKIE}{i}" in cookies:
        parts.append(cookies[f"{COOKIE}{i}"])
        i += 1
    if not parts:
        return None
    try:
        raw = "".join(parts)
        db = json.loads(zlib.decompress(base64.urlsafe_b64decode((raw + "=" * (-len(raw) % 4)).encode())))
        db.setdefault("entries", []); db.setdefault("purifier", False)
        return db
    except Exception:
        return None


def add_entry(db, *, day: date, start: str, minutes: int, location: str, activity: str, pm25: float, aqi: float,
              day_pm25: float):
    db["entries"].append({"id": uuid.uuid4().hex[:8], "day": day.isoformat(), "start": start, "minutes": int(minutes),
                          "location": location, "activity": activity, "pm25": round(float(pm25), 1),
                          "aqi": round(float(aqi), 0), "day_pm25": round(float(day_pm25), 1)})


def delete_entry(db, entry_id):
    db["entries"] = [e for e in db["entries"] if e["id"] != entry_id]


def day_summary(db, day: str):
    es = [e for e in db["entries"] if e["day"] == day]
    if not es:
        return None
    out_min = sum(e["minutes"] for e in es)
    out_dose = sum(e["pm25"] * e["minutes"] for e in es)                 # µg/m³·min outdoors
    indoor_pm = sum(e["day_pm25"] for e in es) / len(es) * (0.3 if db.get("purifier") else 0.65)
    in_min = max(0, 1440 - out_min)
    eff_pm = (out_dose + indoor_pm * in_min) / 1440                     # 24 h exposure-weighted PM2.5
    cig = eff_pm / CIG_UG
    score = int(round(max(0.0, min(100.0, 100 - (eff_pm - 10) * 1.1))))
    return {"day": day, "entries": es, "outdoor_min": out_min, "eff_pm": eff_pm, "cig": cig, "score": score}


def streaks(db, today: date):
    days = sorted({e["day"] for e in db["entries"]})
    good = {d for d in days if (s := day_summary(db, d)) and s["score"] >= GOOD_SCORE}
    cur, d = 0, today
    if d.isoformat() not in good:
        d -= timedelta(days=1)            # today not logged yet doesn't break the streak
    while d.isoformat() in good:
        cur += 1
        d -= timedelta(days=1)
    best = run = 0
    prev = None
    for dd in sorted(good):
        x = date.fromisoformat(dd)
        run = run + 1 if prev and (x - prev).days == 1 else 1
        best, prev = max(best, run), x
    return cur, best


BADGES = [(3, "🌱", "3-day streak"), (7, "🌿", "Clean-air week"), (14, "🌳", "Two clean weeks"), (30, "🏆", "Clean-air month")]
