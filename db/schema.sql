CREATE TABLE IF NOT EXISTS playlists (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    fetched_at TIMESTAMP NOT NULL,
    tracks_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS designs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    image_path TEXT NOT NULL,
    grid_x INTEGER NOT NULL,
    grid_y INTEGER NOT NULL,
    grid_w INTEGER NOT NULL,
    grid_h INTEGER NOT NULL,
    font_scale REAL NOT NULL DEFAULT 1.0,
    separator TEXT NOT NULL DEFAULT ' — ',
    title_align TEXT NOT NULL DEFAULT 'left',
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS card_sets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    playlist_id TEXT NOT NULL,
    design_id INTEGER NOT NULL,
    num_cards INTEGER NOT NULL,
    show_cover_art BOOLEAN NOT NULL,
    seed INTEGER NOT NULL,
    cards_json TEXT NOT NULL,
    stats_json TEXT NOT NULL,
    pdf_path TEXT,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (playlist_id) REFERENCES playlists(id),
    FOREIGN KEY (design_id) REFERENCES designs(id)
);
