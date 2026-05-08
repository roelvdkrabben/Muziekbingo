// Theme presets — quick-applies a palette + motif + frame style + fonts.
// Each preset only sets a subset; user tweaks override.

window.PRESETS = [
  {
    id: "blank",
    label: "Blank",
    swatch: ["#f5f1ea", "#1c1a18", "#b8312e", "#1a3d6b", "#d6b86b"],
    apply: {
      palette: { bg:"#f5f1ea", ink:"#1c1a18", accent1:"#b8312e", accent2:"#1a3d6b", accent3:"#d6b86b" },
      motif: "none",
      density: 0.5,
      motifScale: 1,
      frame: "hairline",
      gridFill: "paper",
      titleFont: "Playfair Display",
      bodyFont: "EB Garamond",
      title: "MUZIEK BINGO",
      subtitle: "Een avond vol klassiekers",
      footerL: "Score 5 op een rij",
      footerR: "muziekbingo.app",
    },
  },
  {
    id: "carnival",
    label: "Oeteldonk",
    swatch: ["#f5e6c8", "#1a1a1a", "#d6212a", "#fff", "#f4c81f"],
    apply: {
      palette: { bg:"#f5e6c8", ink:"#1a1a1a", accent1:"#d6212a", accent2:"#f4c81f", accent3:"#1a1a1a" },
      motif: "confetti", density: 0.7, motifScale: 1.1,
      frame: "double", gridFill: "paper",
      titleFont: "Bungee", bodyFont: "EB Garamond",
      title: "OETELDONK BINGO", subtitle: "Alaaf · driemaal · alaaf",
      footerL: "11 nummers per jaar", footerR: "Bingo!",
    },
  },
  {
    id: "kerst",
    label: "Kerst",
    swatch: ["#f7f1e3", "#0e2a1a", "#7c1c1c", "#3a6b3c", "#c69c4d"],
    apply: {
      palette: { bg:"#f7f1e3", ink:"#0e2a1a", accent1:"#7c1c1c", accent2:"#3a6b3c", accent3:"#c69c4d" },
      motif: "floral", density: 0.6, motifScale: 1.0,
      frame: "ornaments", gridFill: "panel",
      titleFont: "IM Fell DW Pica", bodyFont: "EB Garamond",
      title: "KERST · MUZIEK · BINGO", subtitle: "Songs onder de boom",
      footerL: "Vrolijk Kerstfeest", footerR: "Eet smakelijk",
    },
  },
  {
    id: "neon80",
    label: "80s Neon",
    swatch: ["#0d0a1f", "#fff", "#ff2bd6", "#22e1ff", "#ffe347"],
    apply: {
      palette: { bg:"#fff5fb", ink:"#1a0530", accent1:"#ff2bd6", accent2:"#22e1ff", accent3:"#ffe347" },
      motif: "memphis", density: 0.75, motifScale: 1.2,
      frame: "tagged", gridFill: "paper",
      titleFont: "Monoton", bodyFont: "Space Mono",
      title: "TOTALLY 80s", subtitle: "MIXTAPE BINGO NIGHT",
      footerL: "Side A", footerR: "Side B",
    },
  },
  {
    id: "wedding",
    label: "Wedding",
    swatch: ["#faf6f1", "#3a2f28", "#a87f5b", "#d8c2a8", "#7a8a6e"],
    apply: {
      palette: { bg:"#faf6f1", ink:"#3a2f28", accent1:"#a87f5b", accent2:"#7a8a6e", accent3:"#d8c2a8" },
      motif: "floral", density: 0.55, motifScale: 0.95,
      frame: "ornaments", gridFill: "paper",
      titleFont: "Cormorant Garamond", bodyFont: "EB Garamond",
      title: "Music Bingo", subtitle: "for Sara & Daan · 12 juni",
      footerL: "Their wedding playlist", footerR: "First dance: ?",
    },
  },
  {
    id: "festival",
    label: "Summer fest",
    swatch: ["#ffe9c2", "#2b1a4a", "#ff6a3d", "#ffb45a", "#1a8a8e"],
    apply: {
      palette: { bg:"#ffe9c2", ink:"#2b1a4a", accent1:"#ff6a3d", accent2:"#1a8a8e", accent3:"#ffb45a" },
      motif: "botanical", density: 0.5, motifScale: 1.1,
      frame: "hairline", gridFill: "paper",
      titleFont: "Abril Fatface", bodyFont: "EB Garamond",
      title: "SUNSET BINGO", subtitle: "Beachside · feel-good hits",
      footerL: "Sand · sun · songs", footerR: "Stage 2",
    },
  },
  {
    id: "corporate",
    label: "Corporate",
    swatch: ["#ffffff", "#0d2545", "#0d2545", "#3a6ea8", "#c8d6e8"],
    apply: {
      palette: { bg:"#ffffff", ink:"#0d2545", accent1:"#0d2545", accent2:"#3a6ea8", accent3:"#c8d6e8" },
      motif: "deco", density: 0.45, motifScale: 0.85,
      frame: "hairline", gridFill: "paper",
      titleFont: "Bodoni Moda", bodyFont: "EB Garamond",
      title: "Q4 OFFSITE BINGO", subtitle: "Music edition · 14 dec",
      footerL: "Acme Industries", footerR: "Have fun.",
    },
  },
  {
    id: "denbosch",
    label: "Den Bosch",
    swatch: ["#f1ebde", "#1d2b48", "#c41f3e", "#f0c14b", "#1d2b48"],
    apply: {
      palette: { bg:"#f1ebde", ink:"#1d2b48", accent1:"#c41f3e", accent2:"#f0c14b", accent3:"#1d2b48" },
      motif: "deco", density: 0.55, motifScale: 1,
      frame: "double", gridFill: "panel",
      titleFont: "Cinzel", bodyFont: "EB Garamond",
      title: "BOSSCHE BINGO", subtitle: "Liederen onder de Sint-Jan",
      footerL: "Een Bossche bol als prijs", footerR: "Veel succes",
    },
  },
  {
    id: "disco",
    label: "Disco",
    swatch: ["#1a0b2e", "#fff", "#ff3df0", "#ffd84a", "#5cf0c5"],
    apply: {
      palette: { bg:"#fff5e9", ink:"#1a0b2e", accent1:"#ff3df0", accent2:"#5cf0c5", accent3:"#ffd84a" },
      motif: "disco", density: 0.55, motifScale: 1,
      frame: "hairline", gridFill: "paper",
      titleFont: "Limelight", bodyFont: "Space Mono",
      title: "DISCO INFERNO", subtitle: "Bingo on the dance floor",
      footerL: "Boogie until you bingo", footerR: "·",
    },
  },
  {
    id: "editorial",
    label: "Editorial",
    swatch: ["#f3eee5", "#15110d", "#15110d", "#a86a3c", "#c7bba2"],
    apply: {
      palette: { bg:"#f3eee5", ink:"#15110d", accent1:"#15110d", accent2:"#a86a3c", accent3:"#c7bba2" },
      motif: "halftone", density: 0.5, motifScale: 1,
      frame: "double", gridFill: "paper",
      titleFont: "Playfair Display", bodyFont: "EB Garamond",
      title: "Music Bingo", subtitle: "Vol. III — Twentieth-century pop",
      footerL: "No. 2480", footerR: "Printed in Den Bosch",
    },
  },
];

// Curated font lists for the canvas
window.TITLE_FONTS = [
  "Playfair Display","Bodoni Moda","DM Serif Display","Abril Fatface","Cinzel","IM Fell DW Pica","Cormorant Garamond","Cormorant Unicase",
  "Anton","Bebas Neue","Archivo Black","Big Shoulders Display","Bungee","Monoton","Limelight","Rye","Pirata One","Unifraktur Cook","Tangerine"
];
window.BODY_FONTS = [
  "EB Garamond","Cormorant Garamond","Space Mono","Inconsolata","DM Sans","Playfair Display","Bodoni Moda","Tangerine","Caveat"
];
