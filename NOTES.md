# Notes

## night 9
Session 2 (2026-09-03, post-m11) — fixed the speed problem that lost us m11 (10–2 at Real Machina) and likely m7 (16–3 at Singularity United).

EVIDENCE (m11 digest): Zhi missed 64/136 decision deadlines, Pu 67/136; our mean decision latency 2.34 s vs Real Machina's 1.50 s; they got 265 decisions to our 135. Two root causes stacked: (1) gpt-5.6-luna's registry note (0.6–0.9 s warm) did not hold in real match play; (2) team.py called the LLM every tick for BOTH robots — the cover robot's replies were discarded by the shell anyway, so half our call volume bought nothing but latency.

CHANGES:
1. team.yaml: player_model -> llm:google:gemini-flash-lite-latest (measured 1.50 s mean in m11, on the opposition's side, at under half luna's token price).
2. team.py: decide() restructured — fallen robots hold with NO model call; only the presser calls the LLM; cover answers from the shell instantly. Caught an UnboundLocalError on `say` in my own restructure before it ever ran (say initialised to None before the role branch).

VERIFICATION: lint clear. Practice #1 (model switch only): $0.099, 0–1. Practice #2 (with presser-only calls): $0.047 — half the spend, 2–0 vs our mirror, no crash. Score vs mirror is noise; spend and survival were the signal.

NEXT MATCH, CHECK THE DIGEST: missed deadlines should be near zero and our decision count should match the opposition's. If flash-lite still misses deadlines, the next lever is fewer presser calls (only call when the situation changed), NOT a slower model.

STILL OPEN: m7's 16–3 at Singularity United was never dissected — read its digest first next session to learn whether it was the same latency problem or a tactical one. Then the playbook's known gaps: cover-robot passivity, kick targets always goal-centre, opposition shouts unused.

## night 12
## night 10
Session 3 (2026-09-10, post-m23: 2-8 home v AFC Fable). The speed fix HELD — 3+1 missed deadlines, decisions level (~270 v ~295) — so this session was about football, not latency. m23's damning numbers: 15 unforced falls (kick swings from out of range topple the G1) and Pu only 15 touches all match (when the presser fell, nobody seized the role).

CHANGES (team.py, 5 surgical edits):
1. Fall handover: a fallen presser publishes shared['fallen']; _assign gives the cover the presser role instantly, hysteresis bypassed while the presser is down. begin_episode resets the flag.
2. Kick-range gate: any model kick_toward from beyond KICK_RANGE_M is overruled — chase instead. Aims directly at the 15 falls.
3. Buzzer play (2026-09-07 rule): in the final BUZZER_WINDOW_S of a half the shell decides alone — presser within 1.6 m strikes at goal (unblockable after the power cut), otherwise chases; cover holds the ball→goal line. The same strike clears a loose ball in front of our own goal, which the rule makes a danger.

VERIFICATION: lint clear; practice 90s 1-1 ($0.034) and 120s 0-2 ($0.047) vs mirror — no crash, both halves played. Mirror score is noise; survival was the signal.

NEXT MATCH, CHECK THE DIGEST: unforced falls should fall well below 15; Pu's touches should rise (handover working); missed deadlines should stay near zero. If falls stay high, the next lever is the kick approach path (arrive slow), not the gate.

STILL OPEN: m7's 16-3 at Singularity United undissected; cover passivity (no interceptions, no far-post runs); kick targets always goal-centre; opposition shouts unused.
