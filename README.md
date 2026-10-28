# Texting Wrapped

A Spotify-Wrapped-style year in texts, made from your Mac's iMessage database. It counts and never reads: no message text is opened, and your top five appear as blurred placeholder names.

## Make yours (about 2 minutes, free, Mac only)

1. Give Terminal Full Disk Access: System Settings → Privacy & Security → Full Disk Access → Terminal. Quit and reopen Terminal.
2. Paste this into Terminal:
   ```
   mkdir -p ~/texting-wrapped && cd ~/texting-wrapped && curl -fsSL https://eliotb26.github.io/texting-wrapped/wrapped.py -o wrapped.py && python3 wrapped.py
   ```
3. Your Wrapped opens in the browser. Play it, **Record video**, or **Download cards**. Everything runs in your browser; your numbers travel in the link's `#fragment`, which is never sent to a server.

It writes `wrapped_stats.json` (counts only, no names) and `wrapped_private.json` (who Person 1 to 5 are; keep that one to yourself).

## Use Claude Code?

Install the skill and just say "make my texting wrapped":
```
mkdir -p ~/.claude/skills/texting-wrapped && curl -fsSL https://eliotb26.github.io/texting-wrapped/skill/texting-wrapped/SKILL.md -o ~/.claude/skills/texting-wrapped/SKILL.md
```

What it counts for the last 12 months: total texts, who starts conversations, your busiest hour and day, your top five people, your longest daily streak, your reply speed against theirs, and your most-used reaction.

From [The Mutuals](https://themutuals.substack.com).
