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
