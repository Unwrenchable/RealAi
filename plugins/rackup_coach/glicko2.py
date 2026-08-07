"""
ROC — Rack of Champions official player ladder: Glicko-2.

Locked product decisions:
  - Continuous Glicko-2 rating (singles ladder)
  - Display: "{band} • {rating}" e.g. Advanced • 547
  - Bands are labels only (never matchmaking inputs)
  - Defaults: rating=500, RD=175, vol=0.06, min_RD=30, tau=0.5
  - Cross-league → seed_from_external (high RD from low confidence)
  - Teams/doubles TrueSkill is NOT in this module

Reference: Mark E. Glickman, "Example of the Glicko-2 system" (2013).
RealAI computes; RackUp persists rating / rd / volatility only.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

# --- Locked defaults ---
DEFAULT_RATING = 500.0
DEFAULT_RD = 175.0
DEFAULT_VOL = 0.06
MIN_RD = 30.0
MAX_RD = 350.0
TAU = 0.5  # system constant (system volatility constraint)
EPSILON = 1e-6

# Display scale clamp (product)
RATING_MIN = 100.0
RATING_MAX = 1200.0

# Glicko-2 internal scale factor
_Q = math.log(10) / 400.0  # not used directly in G2; G2 uses 173.7178
_SCALE = 173.7178  # converts rating/RD to Glicko-2 µ/φ space


@dataclass
class PlayerRating:
    """Glicko-2 player state on the ROC continuous ladder."""

    rating: float = DEFAULT_RATING
    rd: float = DEFAULT_RD
    volatility: float = DEFAULT_VOL
    player_id: str = ""

    def __post_init__(self) -> None:
        self.rating = float(self.rating)
        self.rd = float(max(MIN_RD, min(MAX_RD, self.rd)))
        self.volatility = float(self.volatility) if self.volatility else DEFAULT_VOL

    @property
    def band(self) -> str:
        return band_for(self.rating)

    @property
    def display(self) -> str:
        return f"{self.band} • {int(round(self.rating))}"

    @property
    def mu(self) -> float:
        return (self.rating - DEFAULT_RATING) / _SCALE

    @property
    def phi(self) -> float:
        return self.rd / _SCALE

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id or None,
            "rating": round(self.rating, 2),
            "rd": round(self.rd, 2),
            "volatility": round(self.volatility, 6),
            "band": self.band,
            "display": self.display,
            "mu": round(self.mu, 6),
            "phi": round(self.phi, 6),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None = None, **kwargs: Any) -> "PlayerRating":
        d = dict(data or {})
        d.update(kwargs)
        return cls(
            rating=float(d.get("rating", d.get("r", DEFAULT_RATING)) or DEFAULT_RATING),
            rd=float(d.get("rd", d.get("rating_deviation", DEFAULT_RD)) or DEFAULT_RD),
            volatility=float(
                d.get("volatility", d.get("vol", d.get("sigma", DEFAULT_VOL))) or DEFAULT_VOL
            ),
            player_id=str(d.get("player_id") or d.get("id") or ""),
        )

    def clone(self) -> "PlayerRating":
        return PlayerRating(
            rating=self.rating,
            rd=self.rd,
            volatility=self.volatility,
            player_id=self.player_id,
        )


def band_for(rating: float | int | None) -> str:
    """
    Locked ROC display bands (labels only).
    <400 Novice | 400–499 Intermediate | 500–599 Advanced | 600–699 Expert | ≥700 Elite
    """
    r = float(rating or 0)
    if r < 400:
        return "Novice"
    if r < 500:
        return "Intermediate"
    if r < 600:
        return "Advanced"
    if r < 700:
        return "Expert"
    return "Elite"


def clamp_rating(r: float) -> float:
    return max(RATING_MIN, min(RATING_MAX, float(r)))


def clamp_rd(rd: float) -> float:
    return max(MIN_RD, min(MAX_RD, float(rd)))


def _g(phi: float) -> float:
    return 1.0 / math.sqrt(1.0 + 3.0 * phi * phi / (math.pi * math.pi))


def _E(mu: float, mu_j: float, phi_j: float) -> float:
    return 1.0 / (1.0 + math.exp(-_g(phi_j) * (mu - mu_j)))


def _volatility_update(
    phi: float,
    sigma: float,
    v: float,
    delta: float,
    tau: float = TAU,
) -> float:
    """Illinois algorithm for new volatility (Glickman)."""
    a = math.log(sigma * sigma)
    # f(x) helper
    phi2 = phi * phi
    delta2 = delta * delta

    def f(x: float) -> float:
        ex = math.exp(x)
        num = ex * (delta2 - phi2 - v - ex)
        den = 2.0 * (phi2 + v + ex) ** 2
        return (num / den) - ((x - a) / (tau * tau))

    # initial brackets
    A = a
    if delta2 > phi2 + v:
        B = math.log(delta2 - phi2 - v)
    else:
        k = 1
        while f(a - k * tau) < 0:
            k += 1
            if k > 100:
                break
        B = a - k * tau

    fA = f(A)
    fB = f(B)
    for _ in range(100):
        if abs(B - A) <= EPSILON:
            break
        C = A + (A - B) * fA / (fB - fA)
        fC = f(C)
        if fC * fB < 0:
            A = B
            fA = fB
        else:
            fA /= 2.0
        B = C
        fB = fC
    return math.exp(A / 2.0)


def update_glicko2(
    player: PlayerRating,
    *,
    opp_rating: float,
    opp_rd: float,
    score: float,
    tau: float = TAU,
) -> PlayerRating:
    """
    Update one player after a single game period against one opponent.

    score: 1.0 win, 0.0 loss, 0.5 draw
    Returns new PlayerRating (does not mutate input).
    """
    score = float(score)
    if score < 0.0:
        score = 0.0
    if score > 1.0:
        score = 1.0

    mu = (player.rating - DEFAULT_RATING) / _SCALE
    phi = player.rd / _SCALE
    sigma = player.volatility

    mu_j = (float(opp_rating) - DEFAULT_RATING) / _SCALE
    phi_j = float(opp_rd) / _SCALE

    g_phi_j = _g(phi_j)
    E = _E(mu, mu_j, phi_j)
    # variance and delta
    v_inv = g_phi_j * g_phi_j * E * (1.0 - E)
    if v_inv <= 0:
        v_inv = 1e-12
    v = 1.0 / v_inv
    delta = v * g_phi_j * (score - E)

    sigma_prime = _volatility_update(phi, sigma, v, delta, tau=tau)

    # pre-rating period RD
    phi_star = math.sqrt(phi * phi + sigma_prime * sigma_prime)
    # new RD and rating
    phi_prime = 1.0 / math.sqrt(1.0 / (phi_star * phi_star) + 1.0 / v)
    mu_prime = mu + phi_prime * phi_prime * g_phi_j * (score - E)

    new_rating = clamp_rating(mu_prime * _SCALE + DEFAULT_RATING)
    new_rd = clamp_rd(phi_prime * _SCALE)

    return PlayerRating(
        rating=new_rating,
        rd=new_rd,
        volatility=sigma_prime,
        player_id=player.player_id,
    )


def apply_match(
    winner: PlayerRating | dict[str, Any],
    loser: PlayerRating | dict[str, Any],
    *,
    draw: bool = False,
    tau: float = TAU,
    winner_score: float | None = None,
    loser_score: float | None = None,
) -> dict[str, Any]:
    """
    Apply a singles match to both players (simultaneous, using pre-match states).

    Returns winner_after / loser_after / deltas and display chips.
    For draws, pass draw=True (both score 0.5).
    """
    w = winner if isinstance(winner, PlayerRating) else PlayerRating.from_dict(winner)
    l = loser if isinstance(loser, PlayerRating) else PlayerRating.from_dict(loser)

    if draw:
        ws, ls = 0.5, 0.5
    else:
        ws = 1.0 if winner_score is None else float(winner_score)
        ls = 0.0 if loser_score is None else float(loser_score)

    w_before = w.clone()
    l_before = l.clone()

    w_after = update_glicko2(
        w, opp_rating=l.rating, opp_rd=l.rd, score=ws, tau=tau
    )
    l_after = update_glicko2(
        l, opp_rating=w.rating, opp_rd=w.rd, score=ls, tau=tau
    )

    return {
        "algorithm": "glicko2_v1",
        "ladder": "roc_glicko2",
        "draw": draw,
        "winner_before": w_before.to_dict(),
        "loser_before": l_before.to_dict(),
        "winner_after": w_after.to_dict(),
        "loser_after": l_after.to_dict(),
        "deltas": {
            "winner_rating": round(w_after.rating - w_before.rating, 3),
            "loser_rating": round(l_after.rating - l_before.rating, 3),
            "winner_rd": round(w_after.rd - w_before.rd, 3),
            "loser_rd": round(l_after.rd - l_before.rd, 3),
            "winner_volatility": round(w_after.volatility - w_before.volatility, 6),
            "loser_volatility": round(l_after.volatility - l_before.volatility, 6),
        },
        "display": {
            "winner_before": w_before.display,
            "winner_after": w_after.display,
            "loser_before": l_before.display,
            "loser_after": l_after.display,
        },
        "tau": tau,
        "defaults": {
            "rating": DEFAULT_RATING,
            "rd": DEFAULT_RD,
            "volatility": DEFAULT_VOL,
            "min_rd": MIN_RD,
            "tau": TAU,
        },
    }


def apply_match_for_player(
    player: PlayerRating | dict[str, Any],
    opponent: PlayerRating | dict[str, Any],
    *,
    won: bool,
    draw: bool = False,
    tau: float = TAU,
) -> dict[str, Any]:
    """
    Convenience: update from the calling player's POV.
    Internally uses apply_match so both after-states are consistent.
    """
    p = player if isinstance(player, PlayerRating) else PlayerRating.from_dict(player)
    o = opponent if isinstance(opponent, PlayerRating) else PlayerRating.from_dict(opponent)

    if draw:
        result = apply_match(p, o, draw=True, tau=tau)
        # normalize labels: player is "self"
        self_after = result["winner_after"]  # both 0.5; winner slot is player
        # re-run with player as first arg for draw consistency
        result = apply_match(p, o, draw=True, tau=tau)
        return {
            **result,
            "player_after": result["winner_after"],
            "opponent_after": result["loser_after"],
            "player_delta": result["deltas"]["winner_rating"],
            "outcome": 0.5,
        }

    if won:
        result = apply_match(p, o, draw=False, tau=tau)
        return {
            **result,
            "player_after": result["winner_after"],
            "opponent_after": result["loser_after"],
            "player_delta": result["deltas"]["winner_rating"],
            "outcome": 1.0,
        }
    else:
        result = apply_match(o, p, draw=False, tau=tau)
        # player is loser
        return {
            **result,
            "player_after": result["loser_after"],
            "opponent_after": result["winner_after"],
            "player_delta": result["deltas"]["loser_rating"],
            "outcome": 0.0,
            # keep winner/loser as actual match roles
        }


def seed_from_external(
    estimate: float,
    *,
    confidence: float = 0.5,
    player_id: str = "",
    from_system: str = "",
    from_value: Any = None,
) -> dict[str, Any]:
    """
    Convert a cross-league estimate into a ROC Glicko-2 seed.

    Low confidence → high RD (uncertain). Glicko-2 then tightens RD with play.
    confidence in [0, 1].
    """
    try:
        conf = float(confidence)
    except (TypeError, ValueError):
        conf = 0.5
    conf = max(0.05, min(0.95, conf))

    rating = clamp_rating(float(estimate))
    # Map confidence → RD: conf 0.95 → ~MIN_RD+20, conf 0.3 → ~DEFAULT_RD+80
    # High uncertainty for foreign systems
    rd = clamp_rd(MIN_RD + (1.0 - conf) * (MAX_RD - MIN_RD) * 0.85)
    # Floor: external seeds never start below ~120 RD unless very high conf
    if conf < 0.85:
        rd = max(rd, 120.0)
    if conf < 0.65:
        rd = max(rd, 150.0)
    if conf < 0.5:
        rd = max(rd, DEFAULT_RD)

    pr = PlayerRating(
        rating=rating,
        rd=rd,
        volatility=DEFAULT_VOL,
        player_id=player_id,
    )
    return {
        "seed": pr.to_dict(),
        "rating": pr.rating,
        "rd": pr.rd,
        "volatility": pr.volatility,
        "band": pr.band,
        "display": pr.display,
        "confidence": round(conf, 2),
        "from_system": from_system,
        "from_value": from_value,
        "method": "seed_from_external_glicko2",
        "notes": (
            "External rating converted to ROC continuous seed with elevated RD. "
            "Glicko-2 takes over after rated ROC matches; do not re-seed over history."
        ),
        "persist_hint": {
            "fields_to_write": ["rating", "rd", "volatility", "rating_updated_at"],
            "when": "matches_played_rackup == 0 and no ROC Glicko history",
            "owner": "RackUp DB — RealAI does not persist",
        },
    }


def rating_from_player_payload(
    player: Any = None,
    payload: dict[str, Any] | None = None,
    *,
    prefix: str = "",
) -> PlayerRating:
    """Build PlayerRating from PlayerProfile / dict + optional payload overrides."""
    payload = payload or {}
    if hasattr(player, "to_dict"):
        d = player.to_dict()
    elif isinstance(player, dict):
        d = dict(player)
    else:
        d = {}

    def pick(*keys: str, default: Any = None) -> Any:
        for k in keys:
            pk = f"{prefix}{k}" if prefix else k
            if pk in payload and payload[pk] is not None:
                return payload[pk]
            if k in d and d[k] is not None:
                return d[k]
        return default

    return PlayerRating(
        rating=float(pick("rating", "r", default=DEFAULT_RATING) or DEFAULT_RATING),
        rd=float(pick("rd", "rating_deviation", default=DEFAULT_RD) or DEFAULT_RD),
        volatility=float(
            pick("volatility", "vol", "sigma", default=DEFAULT_VOL) or DEFAULT_VOL
        ),
        player_id=str(pick("player_id", "id", default="") or ""),
    )


def expected_score(player: PlayerRating, opponent: PlayerRating) -> float:
    """Glicko expected score (for intel / matchmaking)."""
    mu = (player.rating - DEFAULT_RATING) / _SCALE
    mu_j = (opponent.rating - DEFAULT_RATING) / _SCALE
    phi_j = opponent.rd / _SCALE
    return _E(mu, mu_j, phi_j)


def matchmaking_uncertainty_window(rd: float, base_window: float = 45.0) -> float:
    """Widen matchmaking window when RD is high (uncertain players)."""
    rd = float(rd or DEFAULT_RD)
    # at RD=30 → ~1.0×, at RD=175 → ~1.5×, at RD=300 → ~2.0×
    factor = 1.0 + max(0.0, (rd - MIN_RD) / (MAX_RD - MIN_RD))
    return base_window * factor


def system_info() -> dict[str, Any]:
    return {
        "algorithm": "glicko2_v1",
        "ladder": "roc_glicko2",
        "defaults": {
            "rating": DEFAULT_RATING,
            "rd": DEFAULT_RD,
            "volatility": DEFAULT_VOL,
            "min_rd": MIN_RD,
            "max_rd": MAX_RD,
            "tau": TAU,
        },
        "display": "{band} • {rating}",
        "bands": {
            "Novice": "<400",
            "Intermediate": "400-499",
            "Advanced": "500-599",
            "Expert": "600-699",
            "Elite": ">=700",
        },
        "example": "Advanced • 547",
        "teams_trueskill": False,
        "note": "Singles Glicko-2 only this pass; teams/doubles TrueSkill later.",
    }
