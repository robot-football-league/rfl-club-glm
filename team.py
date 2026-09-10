"""GLM FC — behaviour layer. Founded Founding Night by GLM-5.3 for Zhipu.

Each player runs the league's LLM football agent (fast tier) for its read
of the game, wrapped in a deterministic tactical shell that enforces the
one structural rule of 2v2 football: exactly one robot presses the ball,
the other covers the line between ball and own goal. The shell also
validates every reply, so a malformed or missing model answer degrades to
sound positional football rather than an error.

Imports: stdlib math and gauntlet.football only.
"""

import math

X_LIMIT = 6.5          # pitch is 14 x 9 m; stay off the walls
Y_LIMIT = 4.0
COVER_OFFSET_M = 2.0   # cover stands this far goal-side of the ball
SWITCH_MARGIN_M = 1.5  # hysteresis: presser changes only if clearly beaten
BALL_MEMORY_S = 3.0    # trust the world model's ball memory this long
KICK_RANGE_M = 1.2     # inside this, strike at goal rather than dribble
BUZZER_WINDOW_S = 8.0  # final seconds of a half: shell-only buzzer play
BUZZER_KICK_RANGE_M = 1.6  # at the death, stretch for the unblockable shot


def _clamp(pt):
    return [max(-X_LIMIT, min(X_LIMIT, pt[0])),
            max(-Y_LIMIT, min(Y_LIMIT, pt[1]))]


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


class GLMPlayer:
    """An LLM brain inside a positional shell."""

    def __init__(self, agent, shirt, shared):
        self.agent = agent
        self.shirt = shirt
        self.shared = shared          # role state shared with the teammate
        self.last_ball = None         # [x, y] last credible ball position

    # -- engine contract ------------------------------------------------

    def begin_episode(self, log_dir=None):
        self.shared["presser"] = None
        self.shared["fallen"] = None
        self.last_ball = None
        try:
            self.agent.begin_episode(log_dir)
        except Exception:
            pass

    def decide(self, obs):
        # Fallen robots hold immediately: no model call, no latency.
        self_state = obs.get("self") or {}
        if self_state.get("fallen"):
            # Publish the fall so the teammate seizes the presser role
            # at once (m23: 15 unforced falls, and nobody went for the
            # ball while our presser was down and cover waited on
            # hysteresis). Fallen still means hold: no model call.
            self.shared["fallen"] = self.shirt
            return {"skill": "hold"}
        if self.shared.get("fallen") == self.shirt:
            # Recovered: release the flag so roles normalise.
            self.shared["fallen"] = None

        you = obs.get("you") or {}
        own_goal = you.get("defend_goal_xy") or [0.0, 0.0]
        atk_goal = you.get("attack_goal_xy") or [0.0, 0.0]
        me = self_state.get("field_xy") or [0.0, 0.0]

        ball = self._ball(obs)
        mate = self._teammate(obs)
        presser, took_over = self._assign(ball, me, mate)

        # Buzzer play (2026-09-07 rule): in the final seconds of a half
        # the shell decides alone — no model call lands in time, and a
        # ball struck at the buzzer cannot be blocked because every
        # robot loses power at the whistle. Stretch to 1.6 m for the
        # shot; the same upfield strike clears a loose ball in front of
        # our own goal, which the rule makes a danger, not a relief.
        t_rem = obs.get("time_remaining_s")
        if isinstance(t_rem, (int, float)) and t_rem <= BUZZER_WINDOW_S:
            if ball is not None and presser == self.shirt:
                if _dist(me, ball) <= BUZZER_KICK_RANGE_M:
                    return {"skill": "kick_toward",
                            "target": _clamp(atk_goal)}
                return {"skill": "go_to_ball"}
            if ball is not None:
                gx = own_goal[0] - ball[0]
                gy = own_goal[1] - ball[1]
                n = math.hypot(gx, gy) or 1.0
                target = _clamp([ball[0] + gx / n * COVER_OFFSET_M,
                                 ball[1] + gy / n * COVER_OFFSET_M])
            else:
                target = _clamp([(own_goal[0] + me[0]) / 2.0,
                                 (own_goal[1] + me[1]) / 2.0])
            return {"skill": "walk_to", "target": target}

        say = None
        if ball is not None and presser == self.shirt:
            # Only the presser spends a model call: it is the only role
            # whose reply the shell can use. m11 cost us half our
            # decisions to latency while the cover robot's calls were
            # being discarded here anyway.
            reply = {}
            try:
                r = self.agent.decide(obs)
                if isinstance(r, dict):
                    reply = r
            except Exception:
                reply = {}
            say = reply.get("say")
            out = self._valid(reply)
            if out is not None and out.get("skill") == "kick_toward" \
                    and _dist(me, ball) > KICK_RANGE_M:
                # A swing from out of range misses and can topple the
                # G1 (m23: 15 unforced falls). Chase instead.
                out = None
            if out is None:
                if _dist(me, ball) <= KICK_RANGE_M:
                    out = {"skill": "kick_toward", "target": _clamp(atk_goal)}
                else:
                    out = {"skill": "go_to_ball"}
            if took_over and not say:
                say = "Mine!"
        else:
            # Covering (or the ball is lost): hold the ball-goal line.
            if ball is not None:
                gx = own_goal[0] - ball[0]
                gy = own_goal[1] - ball[1]
                n = math.hypot(gx, gy) or 1.0
                target = _clamp([ball[0] + gx / n * COVER_OFFSET_M,
                                 ball[1] + gy / n * COVER_OFFSET_M])
            else:
                target = _clamp([(own_goal[0] + me[0]) / 2.0,
                                 (own_goal[1] + me[1]) / 2.0])
            out = {"skill": "walk_to", "target": target}
        if say:
            out["say"] = str(say)[:120]
        return out

    # -- internals ------------------------------------------------------

    def _ball(self, obs):
        ball = (obs.get("detections") or {}).get("ball")
        if isinstance(ball, dict):
            xy = ball.get("field_xy")
            if xy and ball.get("age_s", 0.0) <= BALL_MEMORY_S:
                self.last_ball = [float(xy[0]), float(xy[1])]
        return self.last_ball

    def _teammate(self, obs):
        for t in (obs.get("detections") or {}).get("teammates") or []:
            if isinstance(t, dict) and t.get("field_xy"):
                xy = t["field_xy"]
                return [float(xy[0]), float(xy[1])]
        return None

    def _assign(self, ball, me, mate):
        """One presser, with hysteresis; shared with the teammate."""
        shirts = self.shared.get("shirts") or {self.shirt}
        other = None
        for s in shirts:
            if s != self.shirt:
                other = s
        prev = self.shared.get("presser")
        if prev not in shirts:
            prev = None
        # A fallen presser cannot press: the mate seizes the role at
        # once, no hysteresis (m23: our presser went down 15 times and
        # nobody went for the ball while cover waited on the margin).
        if prev is not None and prev != self.shirt \
                and self.shared.get("fallen") == prev:
            self.shared["presser"] = self.shirt
            return self.shirt, True
        if ball is None or (prev is not None and mate is None):
            # Lost the ball or lost sight of the mate: keep the current role.
            presser = prev if prev is not None else self.shirt
            self.shared["presser"] = presser
            return presser, False
        my_d = _dist(me, ball)
        mate_d = _dist(mate, ball) if mate else 99.0
        if prev is None:
            presser = self.shirt if my_d <= mate_d else other
        elif prev == self.shirt:
            presser = other if mate_d + SWITCH_MARGIN_M < my_d else self.shirt
        else:
            presser = self.shirt if my_d + SWITCH_MARGIN_M < mate_d else other
        if presser is None:
            presser = self.shirt
        self.shared["presser"] = presser
        return presser, (presser == self.shirt and prev != self.shirt)

    @staticmethod
    def _valid(reply):
        """Pass through only well-formed skill replies."""
        skill = reply.get("skill")
        if skill in ("go_to_ball", "hold"):
            return {"skill": skill}
        if skill in ("kick_toward", "walk_to", "turn_to"):
            t = reply.get("target")
            if isinstance(t, (list, tuple)) and len(t) == 2:
                try:
                    x, y = float(t[0]), float(t[1])
                except (TypeError, ValueError):
                    return None
                return {"skill": skill, "target": _clamp([x, y])}
        return None


def build_team(ctx):
    from gauntlet.football import make_football_agent
    cfg = ctx["config"]
    base = ctx["team_index"] * 2
    roster = cfg.get("players") or [{}, {}]
    model = cfg.get("player_model") or "llm:mock:ok"
    shared = {"presser": None, "shirts": set()}
    players = []
    for k in range(2):
        agent = make_football_agent(
            roster[k].get("model", model),
            base + k,
            seed=base + k,
            prompt=roster[k].get("prompt", cfg.get("prompt", "football_v2")),
        )
        players.append(GLMPlayer(agent, base + k, shared))
    shared["shirts"] = {p.shirt for p in players}
    return {"players": players, "manager": None}
