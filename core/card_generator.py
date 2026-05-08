import random
import logging
from collections import Counter

from core.models import Track

logger = logging.getLogger(__name__)

SONGS_PER_CARD = 24  # 5x5 grid minus center free space


def generate_card_set(
    tracks: list[Track],
    num_cards: int,
    songs_per_card: int = SONGS_PER_CARD,
    attempts_per_card: int = 100,
    seed: int | None = None,
) -> tuple[list[list[Track]], dict]:
    """
    Generate `num_cards` distinct bingo cards from `tracks`.

    Returns (cards, stats). Each card is a list of `songs_per_card` Tracks
    in randomized order — the caller inserts the free space at position 12.

    Raises ValueError if playlist is too small.
    """
    if len(tracks) < songs_per_card:
        raise ValueError(
            f"Playlist heeft {len(tracks)} nummers; minimaal {songs_per_card} nodig."
        )

    rng = random.Random(seed)
    cards: list[list[Track]] = []
    usage: Counter[str] = Counter()

    for card_idx in range(num_cards):
        best_card: list[Track] | None = None
        best_score: tuple = (float("inf"), float("inf"))

        for _ in range(attempts_per_card):
            weights = [1.0 / (usage[t.spotify_id] + 1) for t in tracks]
            candidate = _weighted_sample_without_replacement(tracks, songs_per_card, weights, rng)

            if not cards:
                best_card = candidate
                break

            candidate_ids = {t.spotify_id for t in candidate}
            overlaps = [len(candidate_ids & {t.spotify_id for t in c}) for c in cards]
            score = (max(overlaps), sum(overlaps))

            if score < best_score:
                best_score = score
                best_card = candidate

        rng.shuffle(best_card)
        cards.append(best_card)
        for t in best_card:
            usage[t.spotify_id] += 1

        if card_idx > 0 and best_score[0] > 12:
            logger.warning(
                "Kaart %d heeft hoge overlap: %d gedeelde nummers. "
                "Overweeg een grotere playlist.",
                card_idx + 1,
                best_score[0],
            )

    stats = _compute_stats(cards, len(tracks))
    return cards, stats


def _weighted_sample_without_replacement(
    items: list, k: int, weights: list[float], rng: random.Random
) -> list:
    """Efraimidis-Spirakis weighted reservoir sampling (O(n log n))."""
    keys = [(rng.random() ** (1.0 / max(w, 1e-10)), i) for i, w in enumerate(weights)]
    keys.sort(reverse=True)
    return [items[i] for _, i in keys[:k]]


def _compute_stats(cards: list[list[Track]], total_tracks: int) -> dict:
    overlaps: list[int] = []
    for i in range(len(cards)):
        for j in range(i + 1, len(cards)):
            ids_i = {t.spotify_id for t in cards[i]}
            ids_j = {t.spotify_id for t in cards[j]}
            overlaps.append(len(ids_i & ids_j))

    usage: Counter[str] = Counter()
    for c in cards:
        for t in c:
            usage[t.spotify_id] += 1

    return {
        "max_overlap_observed": max(overlaps) if overlaps else 0,
        "avg_overlap": round(sum(overlaps) / len(overlaps), 2) if overlaps else 0,
        "theoretical_min_avg_overlap": round((24 * 24) / total_tracks, 2),
        "song_usage_min": min(usage.values()) if usage else 0,
        "song_usage_max": max(usage.values()) if usage else 0,
        "tracks_unused": total_tracks - len(usage),
        "total_cards": len(cards),
        "playlist_size": total_tracks,
    }


def card_to_grid(card: list[Track]) -> list[Track | None]:
    """
    Insert None at position 12 (center free space) to produce a 25-element grid.
    Positions 0-11 → tracks 0-11, position 12 → None (FREE), positions 13-24 → tracks 12-23.
    """
    grid: list[Track | None] = list(card[:12]) + [None] + list(card[12:])
    assert len(grid) == 25
    return grid
