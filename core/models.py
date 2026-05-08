from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Track:
    spotify_id: str
    title: str
    artist: str
    album: str
    cover_url_300: str
    cover_url_64: str

    def to_dict(self) -> dict:
        return {
            "spotify_id": self.spotify_id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "cover_url_300": self.cover_url_300,
            "cover_url_64": self.cover_url_64,
        }

    @staticmethod
    def from_dict(d: dict) -> "Track":
        return Track(
            spotify_id=d["spotify_id"],
            title=d["title"],
            artist=d["artist"],
            album=d["album"],
            cover_url_300=d.get("cover_url_300", ""),
            cover_url_64=d.get("cover_url_64", ""),
        )


@dataclass
class Design:
    id: Optional[int]
    name: str
    image_path: str
    grid_x: int
    grid_y: int
    grid_w: int
    grid_h: int
    font_scale: float = 1.0
    separator: str = " — "
    title_align: str = "left"
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def grid_rect(self) -> tuple[int, int, int, int]:
        return (self.grid_x, self.grid_y, self.grid_w, self.grid_h)


@dataclass
class CardSet:
    id: Optional[int]
    name: str
    playlist_id: str
    design_id: int
    num_cards: int
    show_cover_art: bool
    seed: int
    cards_json: str
    stats_json: str
    pdf_path: Optional[str]
    created_at: datetime = field(default_factory=datetime.now)
