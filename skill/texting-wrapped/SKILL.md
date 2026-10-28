---
name: texting-wrapped
description: Make a Spotify-Wrapped-style "Texting Wrapped" from the user's Mac iMessage database (counts only, never message text) and open it as a video with story cards. Use when the user asks for their texting wrapped, texting stats, who they text most, or a Wrapped for their messages.
---

# Texting Wrapped

Builds a year-in-texts from `~/Library/Messages/chat.db` and opens it in the Texting Wrapped studio, where the user can play it, record a video and download story cards.

## Rules
- Never read, print or summarize the text of any message. Only counts: timestamps, sender, chat type, reactions.
- The top five come out as "Person 1 to 5". Their real phone numbers stay in `wrapped_private.json` on the user's Mac. Don't open that file unless the user asks for their own names, and never put names in anything shared.

## Steps
1. Check access: `sqlite3 "file:$HOME/Library/Messages/chat.db?mode=ro" "select 1" 2>&1`. If it says "authorization denied", tell the user to turn on Full Disk Access for the app running Claude Code (System Settings → Privacy & Security → Full Disk Access), restart it, and stop.
2. Work in a folder of its own: `mkdir -p ~/texting-wrapped && cd ~/texting-wrapped`.
3. Get the script: `curl -fsSL https://eliotb26.github.io/texting-wrapped/wrapped.py -o wrapped.py`.
4. Run it: `python3 wrapped.py` (add `--days 730` for two years). It prints the headline stats and opens the studio with the user's numbers loaded. The numbers travel in the link's `#fragment`, which never reaches a server.
5. Tell the user three or four of their stats in plain words (who texts first, busiest hour, longest streak, reply speed), and that **Record video** and **Download cards** in the studio save everything with names blurred.
