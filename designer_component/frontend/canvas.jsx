// A4 canvas — renders the full 2480×3508 page as SVG.
// Layout: header zone (top), grid zone (middle, calm), footer zone (bottom).

const { useMemo } = React;

const PAGE = { w: 2480, h: 3508 };

// Layout helpers — return zone rectangles based on header/footer percentages
function computeZones(state){
  const headerH = state.headerH * PAGE.h;
  const footerH = state.footerH * PAGE.h;
  const margin = state.margin * PAGE.w;
  const gridY = headerH;
  const gridH = PAGE.h - headerH - footerH;
  return {
    margin,
    header: { x: margin, y: 0,                     w: PAGE.w - margin*2, h: headerH },
    grid:   { x: margin*0.5, y: gridY,             w: PAGE.w - margin,   h: gridH },
    inner:  { x: margin + state.gridPadding,
              y: gridY + state.gridPadding,
              w: PAGE.w - margin*2 - state.gridPadding*2,
              h: gridH - state.gridPadding*2 },
    footer: { x: margin, y: PAGE.h - footerH,      w: PAGE.w - margin*2, h: footerH },
    leftStrip:  { x: 0, y: gridY, w: margin*0.5, h: gridH },
    rightStrip: { x: PAGE.w - margin*0.5, y: gridY, w: margin*0.5, h: gridH },
  };
}

function PaperTexture({ seed, intensity }){
  if(intensity <= 0) return null;
  const id = `paper-${seed}`;
  return (
    <>
      <filter id={id} x="0" y="0" width="100%" height="100%">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={seed} />
        <feColorMatrix values={`0 0 0 0 0
                                 0 0 0 0 0
                                 0 0 0 0 0
                                 0 0 0 ${intensity*0.4} 0`} />
      </filter>
      <rect x="0" y="0" width={PAGE.w} height={PAGE.h} filter={`url(#${id})`} />
    </>
  );
}

// Frame around grid area
function GridFrame({ rect, style, palette, scale=1 }){
  const sw = 4 * scale;
  if(style === "none") return null;
  if(style === "hairline"){
    return <rect x={rect.x} y={rect.y} width={rect.w} height={rect.h}
      fill="none" stroke={palette.ink} strokeWidth={sw}/>;
  }
  if(style === "double"){
    return (
      <>
        <rect x={rect.x} y={rect.y} width={rect.w} height={rect.h}
          fill="none" stroke={palette.ink} strokeWidth={sw}/>
        <rect x={rect.x+18} y={rect.y+18} width={rect.w-36} height={rect.h-36}
          fill="none" stroke={palette.ink} strokeWidth={sw*0.55}/>
      </>
    );
  }
  if(style === "tagged"){
    const c = 60;
    const path = `
      M ${rect.x+c} ${rect.y}
      L ${rect.x+rect.w-c} ${rect.y}
      L ${rect.x+rect.w} ${rect.y+c}
      L ${rect.x+rect.w} ${rect.y+rect.h-c}
      L ${rect.x+rect.w-c} ${rect.y+rect.h}
      L ${rect.x+c} ${rect.y+rect.h}
      L ${rect.x} ${rect.y+rect.h-c}
      L ${rect.x} ${rect.y+c}
      Z`;
    return <path d={path} fill="none" stroke={palette.ink} strokeWidth={sw*1.3}/>;
  }
  if(style === "ornaments"){
    const c = 80;
    const ornament = (x, y, sx, sy) => (
      <g transform={`translate(${x} ${y}) scale(${sx} ${sy})`}>
        <path d={`M 0 0 L ${c*1.4} 0 M 0 0 L 0 ${c*1.4}`}
          stroke={palette.ink} strokeWidth={sw} fill="none"/>
        <circle cx={c*0.4} cy={c*0.4} r={10} fill={palette.accent1 || palette.ink}/>
        <path d={`M ${c*0.7} ${c*0.2} q 30 -10 60 0 M ${c*0.2} ${c*0.7} q -10 30 0 60`}
          stroke={palette.ink} strokeWidth={sw*0.6} fill="none"/>
      </g>
    );
    return (
      <>
        <rect x={rect.x} y={rect.y} width={rect.w} height={rect.h}
          fill="none" stroke={palette.ink} strokeWidth={sw*0.7}/>
        {ornament(rect.x, rect.y, 1, 1)}
        {ornament(rect.x+rect.w, rect.y, -1, 1)}
        {ornament(rect.x, rect.y+rect.h, 1, -1)}
        {ornament(rect.x+rect.w, rect.y+rect.h, -1, -1)}
      </>
    );
  }
  if(style === "ribbon"){
    return (
      <>
        <rect x={rect.x} y={rect.y} width={rect.w} height={rect.h}
          fill="none" stroke={palette.ink} strokeWidth={sw}/>
        <g transform={`translate(${rect.x+rect.w/2} ${rect.y})`}>
          <path d={`M -240 -50 L 240 -50 L 270 -10 L 240 30 L 200 0 L -200 0 L -240 30 L -270 -10 Z`}
            fill={palette.accent1 || palette.ink}/>
          <text x="0" y="-8" textAnchor="middle" fill={palette.bg}
            style={{font: `700 30px "Bebas Neue", sans-serif`, letterSpacing:"0.2em"}}>BINGO</text>
        </g>
      </>
    );
  }
  return null;
}

// Header text block
function Header({ state, zone }){
  const cx = zone.x + zone.w/2;
  const cy = zone.y + zone.h*0.55;
  const align = state.headerAlign;
  const x = align === "left" ? zone.x + 40 : align === "right" ? zone.x + zone.w - 40 : cx;
  const anchor = align === "left" ? "start" : align === "right" ? "end" : "middle";

  // place logo above title if present
  const hasLogo = !!state.logoDataUrl;
  const logoSize = state.logoSize || 280;
  const logoY = zone.y + 80;

  return (
    <g>
      {hasLogo && (
        <image href={state.logoDataUrl}
          x={align==="left" ? zone.x+40 : align==="right" ? zone.x+zone.w-40-logoSize : cx - logoSize/2}
          y={logoY} width={logoSize} height={logoSize}
          preserveAspectRatio="xMidYMid meet" />
      )}

      <text x={x} y={hasLogo ? logoY + logoSize + 100 : cy - 40}
        textAnchor={anchor} fill={state.palette.ink}
        style={{
          font: `${state.titleWeight} ${state.titleSize}px "${state.titleFont}", serif`,
          letterSpacing: state.titleTracking + "em",
        }}>
        {state.title}
      </text>
      {state.subtitle && (
        <text x={x} y={hasLogo ? logoY + logoSize + 100 + state.titleSize*1.05 : cy - 40 + state.titleSize*1.05}
          textAnchor={anchor} fill={state.palette.accent1}
          style={{
            font: `italic 400 ${Math.max(28, state.titleSize*0.32)}px "${state.bodyFont}", serif`,
            letterSpacing: "0.04em",
          }}>
          {state.subtitle}
        </text>
      )}
    </g>
  );
}

function Footer({ state, zone }){
  const left = zone.x + 20;
  const right = zone.x + zone.w - 20;
  const y = zone.y + zone.h*0.55;
  return (
    <g>
      <line x1={zone.x} y1={zone.y + 30} x2={zone.x+zone.w} y2={zone.y+30}
        stroke={state.palette.ink} strokeWidth="2" opacity="0.5"/>
      {state.footerL && (
        <text x={left} y={y} textAnchor="start" fill={state.palette.ink}
          style={{font: `400 36px "${state.bodyFont}", serif`, letterSpacing:"0.04em"}}>
          {state.footerL}
        </text>
      )}
      {state.footerR && (
        <text x={right} y={y} textAnchor="end" fill={state.palette.ink}
          style={{font: `italic 400 36px "${state.bodyFont}", serif`, letterSpacing:"0.04em"}}>
          {state.footerR}
        </text>
      )}
    </g>
  );
}

// Wrap text into lines that fit within maxWidth, using rough char-width estimate.
function wrapLines(text, maxWidth, fontSize, bold) {
  const charW = fontSize * (bold ? 0.58 : 0.50);
  const charsPerLine = Math.max(4, Math.floor(maxWidth / charW));
  const words = text.split(' ');
  const lines = [];
  let cur = '';
  for (const w of words) {
    const test = cur ? cur + ' ' + w : w;
    if (test.length > charsPerLine && cur) { lines.push(cur); cur = w; }
    else cur = test;
  }
  if (cur) lines.push(cur);
  return lines.slice(0, 3);
}

function GridCells({ tracks, inner, state }) {
  if (!tracks || tracks.length === 0) return null;
  const cellW = inner.w / 5;
  const cellH = inner.h / 5;
  const scale = state.cellFontScale || 1.0;
  const titleSize = Math.max(28, cellH * 0.17 * scale);
  const artistSize = Math.max(20, cellH * 0.12 * scale);
  const lineH  = titleSize * 1.25;
  const lineHA = artistSize * 1.25;
  const PAD = Math.max(6, cellW * 0.03);
  const sep = state.cellSeparator != null ? state.cellSeparator : "";
  const align = state.cellTitleAlign || "center";
  const vAlign = state.cellVerticalAlign || "middle";
  const anchor = align === "center" ? "middle" : "start";
  const availW = cellW - PAD * 2;
  const textX = (col) => align === "center"
    ? inner.x + col * cellW + cellW / 2
    : inner.x + col * cellW + PAD;

  const clipPaths = [];
  const cells = [];
  let trackIdx = 0;
  for (let pos = 0; pos < 25; pos++) {
    const row = Math.floor(pos / 5);
    const col = pos % 5;
    const cellTop = inner.y + row * cellH;
    const cellLeft = inner.x + col * cellW;

    clipPaths.push(
      <clipPath key={`cp${pos}`} id={`gcc${pos}`}>
        <rect x={cellLeft} y={cellTop} width={cellW} height={cellH}/>
      </clipPath>
    );

    if (pos === 12) {
      cells.push(
        <text key={pos}
          x={cellLeft + cellW / 2}
          y={cellTop + cellH / 2 + titleSize * 0.35}
          textAnchor="middle" fontFamily={state.bodyFont} fontWeight="700"
          fontSize={titleSize * 0.9} fill={state.palette.accent1 || "#b8312e"} opacity="0.7">
          FREE
        </text>
      );
      continue;
    }
    const track = tracks[trackIdx++] || { title: "—", artist: "" };
    const hasArtist = !!track.artist;
    const titleLines = wrapLines(track.title, availW, titleSize, true);
    const titleBlockH = titleLines.length * lineH;
    const hasSep = !!sep;
    const totalTextH = titleBlockH + (hasSep ? lineHA * 0.9 : 0) + (hasArtist ? lineHA : 0);
    const topOffset = vAlign === "middle" ? Math.max(PAD, (cellH - totalTextH) / 2) : PAD;

    let y = cellTop + topOffset;
    const textEls = [];
    titleLines.forEach((line, i) => {
      textEls.push(
        <text key={`t${i}`} x={textX(col)} y={y + titleSize + i * lineH}
          textAnchor={anchor} fontFamily={state.bodyFont} fontWeight="700"
          fontSize={titleSize} fill={state.palette.ink || "#1c1a18"}>
          {line}
        </text>
      );
    });
    y += titleBlockH;
    if (hasSep) {
      textEls.push(
        <text key="sep" x={textX(col)} y={y + artistSize * 0.85}
          textAnchor={anchor} fontFamily={state.bodyFont} fontWeight="400"
          fontSize={artistSize * 0.8} fill={state.palette.ink || "#5a5048"} opacity="0.45">
          {sep}
        </text>
      );
      y += lineHA * 0.9;
    }
    if (hasArtist) {
      textEls.push(
        <text key="art" x={textX(col)} y={y + artistSize}
          textAnchor={anchor} fontFamily={state.bodyFont} fontWeight="400"
          fontSize={artistSize} fill={state.palette.ink || "#5a5048"} opacity="0.65">
          {track.artist}
        </text>
      );
    }

    cells.push(<g key={pos} clipPath={`url(#gcc${pos})`}>{textEls}</g>);
  }
  return (
    <g className="grid-cells-preview">
      <defs>{clipPaths}</defs>
      {cells}
    </g>
  );
}

window.A4Canvas = React.forwardRef(function A4Canvas({ state, showMarker, tracks }, ref){
  const zones = useMemo(() => computeZones(state), [state]);
  const motif = window.MOTIFS[state.motif] || window.MOTIFS.none;

  // motifs only render in margins (not over grid). We use top header zone, footer zone, and side strips.
  const motifTop = motif.fn({
    palette: state.palette, density: state.density, scale: state.motifScale,
    region: zones.header, seed: state.seed, page: PAGE,
  });
  const motifBottom = motif.fn({
    palette: state.palette, density: state.density * 0.85, scale: state.motifScale,
    region: zones.footer, seed: state.seed + 7, page: PAGE,
  });
  const motifLeft = state.sideOrnaments ? motif.fn({
    palette: state.palette, density: state.density * 0.6, scale: state.motifScale * 0.8,
    region: zones.leftStrip, seed: state.seed + 13, page: PAGE,
  }) : [];
  const motifRight = state.sideOrnaments ? motif.fn({
    palette: state.palette, density: state.density * 0.6, scale: state.motifScale * 0.8,
    region: zones.rightStrip, seed: state.seed + 19, page: PAGE,
  }) : [];

  // grid area fill
  let gridFill = "transparent";
  if(state.gridFill === "paper") gridFill = "#fdfcf8";
  else if(state.gridFill === "panel") gridFill = state.palette.bg;
  else if(state.gridFill === "white") gridFill = "#ffffff";
  else if(state.gridFill === "tint") gridFill = "rgba(0,0,0,0.04)";

  return (
    <svg ref={ref}
      xmlns="http://www.w3.org/2000/svg"
      viewBox={`0 0 ${PAGE.w} ${PAGE.h}`}
      width={PAGE.w} height={PAGE.h}>
      {/* page background */}
      <rect x="0" y="0" width={PAGE.w} height={PAGE.h} fill={state.palette.bg}/>

      {/* paper texture */}
      <PaperTexture seed={state.seed} intensity={state.paperGrain}/>

      {/* margin tinted bands (optional) */}
      {state.bandColor && state.bandColor !== "none" && (
        <>
          <rect x="0" y="0" width={PAGE.w} height={zones.header.h} fill={state.palette.accent1} opacity={0.1}/>
          <rect x="0" y={PAGE.h - zones.footer.h} width={PAGE.w} height={zones.footer.h} fill={state.palette.accent1} opacity={0.1}/>
        </>
      )}

      {/* decorative motifs in margins */}
      <g>{motifTop}{motifBottom}{motifLeft}{motifRight}</g>

      {/* grid fill area (clean, low contrast) */}
      <rect x={zones.grid.x} y={zones.grid.y} width={zones.grid.w} height={zones.grid.h}
        fill={gridFill} />

      {/* grid frame */}
      <GridFrame rect={{
        x: zones.grid.x + state.gridPadding,
        y: zones.grid.y + state.gridPadding,
        w: zones.grid.w - state.gridPadding*2,
        h: zones.grid.h - state.gridPadding*2,
      }} style={state.frame} palette={state.palette}/>

      {/* header text */}
      <Header state={state} zone={zones.header}/>

      {/* footer text */}
      <Footer state={state} zone={zones.footer}/>

      {/* cell grid lines (only when marker shown) */}
      {showMarker && (
        <>
          {/* dashed outer marker */}
          <rect x={zones.grid.x + state.gridPadding}
                y={zones.grid.y + state.gridPadding}
                width={zones.grid.w - state.gridPadding*2}
                height={zones.grid.h - state.gridPadding*2}
            fill="none" stroke="rgba(0,0,0,0.5)" strokeWidth="6" strokeDasharray="20 16"/>
          {/* thin cell dividers */}
          {Array.from({length: 4}, (_, i) => i + 1).map(i => {
            const cw = (zones.grid.w - state.gridPadding*2) / 5;
            const ch = (zones.grid.h - state.gridPadding*2) / 5;
            const gx = zones.grid.x + state.gridPadding;
            const gy = zones.grid.y + state.gridPadding;
            const gw = zones.grid.w - state.gridPadding*2;
            const gh = zones.grid.h - state.gridPadding*2;
            return (
              <React.Fragment key={i}>
                <line x1={gx + i*cw} y1={gy} x2={gx + i*cw} y2={gy + gh}
                  stroke="rgba(0,0,0,0.25)" strokeWidth="2"/>
                <line x1={gx} y1={gy + i*ch} x2={gx + gw} y2={gy + i*ch}
                  stroke="rgba(0,0,0,0.25)" strokeWidth="2"/>
              </React.Fragment>
            );
          })}
        </>
      )}

      {/* track text preview (stripped from exported PNG via class selector) */}
      <GridCells tracks={tracks} inner={zones.inner} state={state} />
    </svg>
  );
});

window.computeGridRect = function(state){
  const z = computeZones(state);
  return {
    x: z.grid.x + state.gridPadding,
    y: z.grid.y + state.gridPadding,
    w: z.grid.w - state.gridPadding*2,
    h: z.grid.h - state.gridPadding*2,
  };
};

window.PAGE_SIZE = PAGE;
