import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from core.models import Track
from core.card_generator import generate_card_set, card_to_grid


def _make_tracks(n: int) -> list[Track]:
    return [
        Track(
            spotify_id=f"track_{i:04d}",
            title=f"Nummer {i}",
            artist=f"Artiest {i % 20}",
            album="Album",
            cover_url_300="",
            cover_url_64="",
        )
        for i in range(n)
    ]


def test_too_few_tracks():
    with pytest.raises(ValueError):
        generate_card_set(_make_tracks(10), num_cards=5)


def test_card_length():
    tracks = _make_tracks(50)
    cards, _ = generate_card_set(tracks, num_cards=10, seed=42)
    assert len(cards) == 10
    for card in cards:
        assert len(card) == 24
        assert len({t.spotify_id for t in card}) == 24, "Kaart bevat duplicaten"


def test_reproducibility():
    tracks = _make_tracks(80)
    cards_a, stats_a = generate_card_set(tracks, num_cards=20, seed=1337)
    cards_b, stats_b = generate_card_set(tracks, num_cards=20, seed=1337)
    for a, b in zip(cards_a, cards_b):
        assert [t.spotify_id for t in a] == [t.spotify_id for t in b]


def test_overlap_acceptable():
    # 500 attempts needed to reliably hit ≤ 9 for 200 cards from 100 songs
    tracks = _make_tracks(100)
    cards, stats = generate_card_set(tracks, num_cards=200, seed=7, attempts_per_card=500)
    assert stats["max_overlap_observed"] <= 9, (
        f"Maximale overlap {stats['max_overlap_observed']} > 9"
    )


def test_grid_has_free_space():
    tracks = _make_tracks(50)
    cards, _ = generate_card_set(tracks, num_cards=3, seed=1)
    for card in cards:
        grid = card_to_grid(card)
        assert len(grid) == 25
        assert grid[12] is None, "Positie 12 moet None (FREE) zijn"
        non_free = [t for t in grid if t is not None]
        assert len(non_free) == 24
