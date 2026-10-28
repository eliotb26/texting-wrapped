# iMessage Wrapped

A Spotify-Wrapped-style video of your year in texts, made on your Mac. **Use it at [eliotcbrown.com/imessage-wrapped](https://eliotcbrown.com/imessage-wrapped/).**

It counts, it never reads: timestamps, who sent each message, 1:1 or group, and tapback reactions. No message text is opened, and the stats it shares have no names.

Make yours (Terminal needs Full Disk Access):

```
mkdir -p ~/imessage-wrapped && cd ~/imessage-wrapped && curl -fsSL https://eliotcbrown.com/imessage-wrapped/wrapped.py -o wrapped.py && python3 wrapped.py
```

Claude Code skill:

```
mkdir -p ~/.claude/skills/imessage-wrapped && curl -fsSL https://eliotcbrown.com/imessage-wrapped/skill/imessage-wrapped/SKILL.md -o ~/.claude/skills/imessage-wrapped/SKILL.md
```

Files: `wrapped.py` (the counter), `studio.html` (the video page), `skill/` (the Claude Code skill).
