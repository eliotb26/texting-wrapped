"""iMessage Wrapped: a Spotify-Wrapped-style year in texts, from your Mac's iMessage database.

Privacy: this never reads message text. It counts timestamps, who sent each message,
chat type and tapback reactions. Contacts come out as "Person 1..5" in the shareable
file; their real handles stay in wrapped_private.json on your laptop.

Usage (Terminal needs Full Disk Access: System Settings > Privacy & Security):
    python3 wrapped.py                 # last 12 months, then opens your Wrapped in the browser
    python3 wrapped.py --days 365 --out stats.json --no-open

The browser link carries your counts in its #fragment, which browsers never send to the server.
"""
import argparse
import base64
import json
import shutil
import sqlite3
import statistics
import tempfile
import webbrowser
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)
NEW_CONVO_GAP = timedelta(hours=6)   # a message after 6 quiet hours starts a new conversation
MAX_REPLY = timedelta(hours=12)      # ignore "replies" slower than this
NO_REPLY = timedelta(hours=24)       # a conversation I start with no answer within a day
DRIFT_RATIO = 3                      # "drifted": under a third of last year's messages
LAST_YEAR_TOP = 10
TAPBACKS = {2000: "Loved", 2001: "Liked", 2002: "Disliked", 2003: "Laughed", 2004: "Emphasized", 2005: "Questioned"}
STUDIO_URL = "https://eliotcbrown.com/imessage-wrapped/"
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def copy_db():
    src = Path.home() / "Library/Messages/chat.db"
    tmp = Path(tempfile.mkdtemp(prefix="wrapped-"))
    for suffix in ("", "-wal", "-shm"):
        f = Path(str(src) + suffix)
        if f.exists():
            shutil.copy2(f, tmp / f.name)
    return tmp / "chat.db"


def to_local(apple_ts):
    secs = apple_ts / 1e9 if apple_ts > 1e11 else apple_ts  # newer macOS stores nanoseconds
    return (APPLE_EPOCH + timedelta(seconds=secs)).astimezone()


def load(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = con.execute(
        """
        SELECT m.date, m.is_from_me, m.associated_message_type, c.ROWID, c.style,
               COALESCE(h.id, c.chat_identifier)
        FROM message m
        JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
        JOIN chat c ON c.ROWID = cmj.chat_id
        LEFT JOIN handle h ON h.ROWID = m.handle_id
        WHERE m.date > 0
        ORDER BY m.date
        """
    ).fetchall()
    con.close()
    out = []
    for date, mine, assoc, chat_id, style, handle in rows:
        out.append({"t": to_local(date), "mine": bool(mine), "assoc": assoc or 0, "chat": chat_id,
                    "group": style == 43, "handle": handle})
    return out


def longest_streak(days):
    best = run = 0
    prev = None
    for d in sorted(days):
        run = run + 1 if prev and d - prev == timedelta(days=1) else 1
        best, prev = max(best, run), d
    return best


def per_chat_stats(msgs):
    by_chat = defaultdict(list)
    for m in msgs:
        by_chat[m["chat"]].append(m)
    started, unanswered = Counter(), 0
    my_replies, their_replies = [], []
    streaks = {}
    for chat, ms in by_chat.items():
        if ms[0]["group"]:
            continue
        prev = None
        for i, m in enumerate(ms):
            if prev is None or m["t"] - prev["t"] > NEW_CONVO_GAP:
                started["me" if m["mine"] else "them"] += 1
                if m["mine"] and not answered_within(ms, i, NO_REPLY):
                    unanswered += 1
            elif m["mine"] != prev["mine"] and m["t"] - prev["t"] <= MAX_REPLY:
                (my_replies if m["mine"] else their_replies).append((m["t"] - prev["t"]).total_seconds())
            prev = m
        streaks[chat] = longest_streak({m["t"].date() for m in ms})
    return by_chat, started, unanswered, my_replies, their_replies, streaks


def answered_within(ms, i, limit):
    """Did the other person write back within `limit` of message i?"""
    for m in ms[i + 1:]:
        if m["t"] - ms[i]["t"] > limit:
            return False
        if not m["mine"]:
            return True
    return False


def by_month(texts):
    """Messages per calendar month, oldest first."""
    counts = Counter(m["t"].strftime("%Y-%m") for m in texts)
    return [{"month": k, "messages": counts[k]} for k in sorted(counts)]


def one_to_one_counts(texts):
    return Counter(m["chat"] for m in texts if not m["group"])


def circle_change(texts, last_year, first_seen, since):
    """Who is new this year, and who from last year's top 10 has faded. Chat ids only, never names."""
    now, before = one_to_one_counts(texts), one_to_one_counts(last_year)
    new_people = [c for c in now if first_seen[c] >= since]
    if not before:
        return {"new_people": len(new_people)}, {}
    last_top = [c for c, _ in before.most_common(LAST_YEAR_TOP)]
    drifted = [c for c in last_top if now.get(c, 0) * DRIFT_RATIO < before[c]]
    new_in_top5 = [c for c, _ in now.most_common(5) if c not in last_top]
    shared = {"new_people": len(new_people), "drifted_from": len(drifted), "last_year_top": len(last_top),
              "new_in_top5": len(new_in_top5)}
    return shared, {"drifted": drifted, "new_in_top5": new_in_top5}


def build(msgs, last_year, first_seen, since):
    texts = [m for m in msgs if m["assoc"] == 0]
    reactions = Counter(TAPBACKS[m["assoc"]] for m in msgs if m["mine"] and m["assoc"] in TAPBACKS)
    by_chat, started, unanswered, my_r, their_r, streaks = per_chat_stats(texts)
    months = by_month(texts)
    circle, circle_private = circle_change(texts, [m for m in last_year if m["assoc"] == 0], first_seen, since)

    one_to_one = {c: ms for c, ms in by_chat.items() if not ms[0]["group"]}
    groups = {c: ms for c, ms in by_chat.items() if ms[0]["group"]}
    ranked = sorted(one_to_one.items(), key=lambda kv: len(kv[1]), reverse=True)
    top = []
    private = []
    for i, (chat, ms) in enumerate(ranked[:5], 1):
        sent = sum(m["mine"] for m in ms)
        top.append({"label": f"Person {i}", "messages": len(ms), "sent": sent, "received": len(ms) - sent,
                    "streak_days": streaks.get(chat, 0)})
        private.append({"label": f"Person {i}", "handle": ms[0]["handle"]})

    hours = Counter(m["t"].hour for m in texts if m["mine"])
    days = Counter(m["t"].weekday() for m in texts if m["mine"])
    sent = [m for m in texts if m["mine"]]
    late = sum(1 for m in sent if m["t"].hour >= 22 or m["t"].hour < 4)
    total_starts = started["me"] + started["them"] or 1
    best_streak_chat = max(streaks, key=streaks.get) if streaks else None
    busiest_day = Counter(m["t"].date() for m in texts).most_common(1)

    stats = {
        "window": {"from": texts[0]["t"].date().isoformat() if texts else None,
                   "to": texts[-1]["t"].date().isoformat() if texts else None},
        "messages_total": len(texts),
        "sent": len(sent),
        "received": len(texts) - len(sent),
        "people_texted": len(one_to_one),
        "group_chats_active": len(groups),
        "group_share_pct": round(100 * sum(len(ms) for ms in groups.values()) / max(len(texts), 1), 1),
        "busiest_hour": hours.most_common(1)[0][0] if hours else None,
        "sent_by_hour": [hours.get(h, 0) for h in range(24)],
        "busiest_weekday": WEEKDAYS[days.most_common(1)[0][0]] if days else None,
        "late_night_pct": round(100 * late / max(len(sent), 1), 1),
        "i_start_pct": round(100 * started["me"] / total_starts, 1),
        "my_median_reply_min": round(statistics.median(my_r) / 60, 1) if my_r else None,
        "their_median_reply_min": round(statistics.median(their_r) / 60, 1) if their_r else None,
        "longest_streak_days": streaks.get(best_streak_chat, 0),
        "busiest_day_count": busiest_day[0][1] if busiest_day else 0,
        "reactions_sent": dict(reactions.most_common()),
        "top_people": top,
        "top5_share_pct": round(100 * sum(p["messages"] for p in top) / max(len(texts), 1), 1),
        "by_month": months,
        "busiest_month": max(months, key=lambda x: x["messages"])["month"] if months else None,
        "unanswered_pct": round(100 * unanswered / max(started["me"], 1), 1),
        **circle,
    }
    handle = {c: ms[0]["handle"] for c, ms in by_chat.items()}
    handle.update({m["chat"]: m["handle"] for m in last_year if m["chat"] not in handle})
    private = {"top5": private, **{k: [handle.get(c) for c in v] for k, v in circle_private.items()}}
    return stats, private


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=365)
    ap.add_argument("--out", default="wrapped_stats.json")
    ap.add_argument("--no-open", action="store_true", help="don't open the video studio in your browser")
    args = ap.parse_args()
    try:
        db = copy_db()
    except PermissionError:
        raise SystemExit("macOS blocked access to Messages. Give your terminal Full Disk Access "
                         "(System Settings > Privacy & Security > Full Disk Access), reopen it, and rerun.")
    since = datetime.now().astimezone() - timedelta(days=args.days)
    everything = load(db)
    first_seen = {}
    for m in everything:
        first_seen.setdefault(m["chat"], m["t"])
    msgs = [m for m in everything if m["t"] >= since]
    last_year = [m for m in everything if since - timedelta(days=args.days) <= m["t"] < since]
    stats, private = build(msgs, last_year, first_seen, since)
    stats["history_from"] = everything[0]["t"].date().isoformat() if everything else None  # "new" only means new since here
    shutil.rmtree(db.parent, ignore_errors=True)
    Path(args.out).write_text(json.dumps(stats, indent=2))
    Path("wrapped_private.json").write_text(json.dumps(private, indent=2))
    print(json.dumps({k: v for k, v in stats.items() if k not in ("sent_by_hour", "top_people", "by_month")}, indent=2))
    print(f"\nSaved {args.out} (shareable, no names) and wrapped_private.json (who Person 1-5 are, and who you drifted from; keep it private).")
    if not args.no_open:
        open_studio(stats)


def open_studio(stats):
    """Open the studio with the counts in the URL fragment (after #), which never leaves the browser."""
    packed = base64.urlsafe_b64encode(json.dumps(stats, separators=(",", ":")).encode()).decode().rstrip("=")
    url = f"{STUDIO_URL}#s={packed}"
    print(f"\nOpening your Wrapped: {STUDIO_URL}")
    if not webbrowser.open(url):
        print("Couldn't open a browser. Open the link above and drop wrapped_stats.json on it.")


if __name__ == "__main__":
    main()
