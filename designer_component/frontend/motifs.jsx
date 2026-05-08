/* Motif libraries — each generator returns an array of SVG element nodes (React).
   They draw decorative ornaments around the reserved grid area.
   API: motif({palette, density, scale, region, seed, page})
   - palette: {bg, ink, accent1, accent2, accent3}
   - density: 0..1
   - scale: 0.5..1.8 size multiplier
   - region: {x,y,w,h} where to draw
   - seed: integer
   - page: {w,h}
*/

function mulberry32(a){
  return function(){
    a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = a;
    t = Math.imul(t ^ t >>> 15, t | 1);
    t ^= t + Math.imul(t ^ t >>> 7, t | 61);
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

function pickColor(rng, palette){
  const cs = [palette.accent1, palette.accent2, palette.accent3].filter(Boolean);
  return cs[Math.floor(rng()*cs.length)] || palette.ink;
}

// ----- shape primitives -----
function Triangle({cx, cy, size, rot, fill, opacity=1}) {
  const p = [
    [0, -size*0.6],
    [size*0.55, size*0.4],
    [-size*0.55, size*0.4],
  ].map(([x,y]) => `${x},${y}`).join(" ");
  return <polygon points={p} fill={fill} opacity={opacity}
    transform={`translate(${cx} ${cy}) rotate(${rot})`} />;
}

function Squiggle({cx, cy, size, rot, stroke, opacity=1}){
  const d = `M ${-size} 0 q ${size*0.5} ${-size*0.7} ${size} 0 t ${size} 0`;
  return <path d={d} fill="none" stroke={stroke} strokeWidth={size*0.18} strokeLinecap="round"
    opacity={opacity} transform={`translate(${cx} ${cy}) rotate(${rot})`} />;
}

function Star4({cx, cy, size, fill, opacity=1, rot=0}){
  const s = size, t = size*0.18;
  const d = `M 0,-${s} L ${t},-${t} L ${s},0 L ${t},${t} L 0,${s} L -${t},${t} L -${s},0 L -${t},-${t} Z`;
  return <path d={d} fill={fill} opacity={opacity}
    transform={`translate(${cx} ${cy}) rotate(${rot})`} />;
}

function Star8({cx, cy, size, fill, opacity=1}){
  const pts = [];
  for(let i=0;i<8;i++){
    const a = (i/8)*Math.PI*2;
    const r = i%2===0 ? size : size*0.42;
    pts.push(`${Math.cos(a)*r},${Math.sin(a)*r}`);
  }
  return <polygon points={pts.join(" ")} fill={fill} opacity={opacity}
    transform={`translate(${cx} ${cy})`} />;
}

function Rect({cx, cy, w, h, rot, fill, opacity=1}){
  return <rect x={-w/2} y={-h/2} width={w} height={h} fill={fill} opacity={opacity}
    transform={`translate(${cx} ${cy}) rotate(${rot})`} />;
}

function CircleM({cx, cy, r, fill, stroke, sw, opacity=1}){
  return <circle cx={cx} cy={cy} r={r} fill={fill||"none"} stroke={stroke||"none"}
    strokeWidth={sw||0} opacity={opacity} />;
}

// scatter helper: spawn N positions inside region, biased to edges
function scatter(rng, region, count, edgeBias=0){
  const pts = [];
  for(let i=0;i<count;i++){
    let rx = rng(), ry = rng();
    if(edgeBias > 0){
      const flip = rng() < 0.5;
      if(flip){ ry = ry < 0.5 ? ry*edgeBias : 1 - (1-ry)*edgeBias; }
      else    { rx = rx < 0.5 ? rx*edgeBias : 1 - (1-rx)*edgeBias; }
    }
    pts.push({
      x: region.x + rx*region.w,
      y: region.y + ry*region.h,
    });
  }
  return pts;
}

// =====================================================
// Confetti — tiny geometric pieces in palette colors
// =====================================================
function MotifConfetti({palette, density, scale, region, seed}){
  const rng = mulberry32(seed);
  const count = Math.floor((density*0.9 + 0.2) * (region.w*region.h)/40000);
  const items = [];
  for(let i=0;i<count;i++){
    const x = region.x + rng()*region.w;
    const y = region.y + rng()*region.h;
    const sz = (10 + rng()*40) * scale;
    const c = pickColor(rng, palette);
    const rot = rng()*360;
    const kind = Math.floor(rng()*5);
    if(kind===0) items.push(<Triangle key={i} cx={x} cy={y} size={sz} rot={rot} fill={c} />);
    else if(kind===1) items.push(<CircleM key={i} cx={x} cy={y} r={sz*0.35} fill={c} />);
    else if(kind===2) items.push(<Rect key={i} cx={x} cy={y} w={sz*1.4} h={sz*0.18} rot={rot} fill={c} />);
    else if(kind===3) items.push(<Squiggle key={i} cx={x} cy={y} size={sz*0.6} rot={rot} stroke={c} />);
    else items.push(<Rect key={i} cx={x} cy={y} w={sz*0.5} h={sz*0.5} rot={rot} fill={c} />);
  }
  return items;
}

// =====================================================
// Music — eighth notes, beamed pairs, treble clefs
// =====================================================
const NOTE_PATHS = {
  // single eighth note
  eighth: "M0,0 q-22,2 -42,16 q-22,16 -22,38 q0,18 16,24 q14,5 30,-2 q22,-9 30,-30 l0,-220 q22,18 36,32 q14,18 14,38 q0,20 -10,32 l8,8 q22,-22 22,-50 q0,-30 -22,-52 q-20,-22 -60,-44 z",
  // beamed pair (two eighths joined)
  beamed: "M0,0 q-22,2 -42,16 q-22,16 -22,38 q0,18 16,24 q14,5 30,-2 q22,-9 30,-30 l0,-220 l160,-30 l0,220 q-22,2 -42,16 q-22,16 -22,38 q0,18 16,24 q14,5 30,-2 q22,-9 30,-30 l0,-260 l-180,32 l0,-26 l180,-32 l0,30 z",
  // treble clef (simplified)
  treble: "M0,0 q-30,-20 -30,-58 q0,-50 50,-66 q34,-10 60,16 q22,22 22,52 q0,30 -20,50 q-22,22 -56,22 l-2,80 q40,4 64,32 q24,28 24,68 q0,46 -34,76 q-30,28 -74,28 q-44,0 -68,-26 q-22,-24 -22,-54 q0,-26 18,-44 q18,-18 44,-18 q24,0 40,16 q16,16 16,38 q0,18 -10,30 q-12,12 -28,14 q4,4 12,4 q22,0 36,-20 q14,-20 14,-46 q0,-32 -22,-54 q-22,-22 -56,-24 l-4,168 q-2,38 -38,38 q-30,0 -38,-32 q-4,-22 12,-38 q-12,-2 -22,-12 q-12,-12 -12,-30 q0,-22 18,-36 z M -2,-130 q14,-2 30,-16 q18,-16 18,-44 q0,-22 -14,-36 q-12,-12 -28,-12 q-22,0 -34,22 q-12,22 -8,52 q4,28 36,34 z",
};

function MotifMusic({palette, density, scale, region, seed}){
  const rng = mulberry32(seed);
  const count = Math.floor((density*0.6 + 0.15) * (region.w*region.h)/80000);
  const items = [];
  for(let i=0;i<count;i++){
    const x = region.x + rng()*region.w;
    const y = region.y + rng()*region.h;
    const sz = (0.35 + rng()*0.55) * scale;
    const rot = (rng()-0.5)*40;
    const r = rng();
    const c = pickColor(rng, palette);
    const which = r < 0.55 ? "eighth" : r < 0.85 ? "beamed" : "treble";
    items.push(
      <path key={i} d={NOTE_PATHS[which]} fill={c}
        transform={`translate(${x} ${y}) scale(${sz}) rotate(${rot})`} opacity={0.95} />
    );
  }
  return items;
}

// =====================================================
// Stars — sparkle pattern
// =====================================================
function MotifStars({palette, density, scale, region, seed}){
  const rng = mulberry32(seed);
  const count = Math.floor((density*0.9 + 0.2) * (region.w*region.h)/45000);
  const items = [];
  for(let i=0;i<count;i++){
    const x = region.x + rng()*region.w;
    const y = region.y + rng()*region.h;
    const sz = (10 + rng()*55) * scale;
    const c = pickColor(rng, palette);
    const r = rng();
    if(r < 0.55) items.push(<Star4 key={i} cx={x} cy={y} size={sz} fill={c} rot={rng()*45} />);
    else if(r < 0.85) items.push(<Star8 key={i} cx={x} cy={y} size={sz*0.7} fill={c} />);
    else items.push(<CircleM key={i} cx={x} cy={y} r={sz*0.18} fill={c} />);
  }
  return items;
}

// =====================================================
// Memphis — 80s/90s geometric chaos
// =====================================================
function MotifMemphis({palette, density, scale, region, seed}){
  const rng = mulberry32(seed);
  const count = Math.floor((density*0.8 + 0.25) * (region.w*region.h)/55000);
  const items = [];
  for(let i=0;i<count;i++){
    const x = region.x + rng()*region.w;
    const y = region.y + rng()*region.h;
    const sz = (30 + rng()*90) * scale;
    const c = pickColor(rng, palette);
    const k = Math.floor(rng()*6);
    if(k===0){
      // dot grid
      const items2 = [];
      for(let r=0;r<3;r++) for(let q=0;q<3;q++)
        items2.push(<circle key={`${r}-${q}`} cx={(q-1)*sz*0.4} cy={(r-1)*sz*0.4} r={sz*0.07} fill={c}/>);
      items.push(<g key={i} transform={`translate(${x} ${y})`}>{items2}</g>);
    } else if(k===1){
      items.push(<Triangle key={i} cx={x} cy={y} size={sz*0.7} rot={rng()*360} fill={c} />);
    } else if(k===2){
      // squiggle line
      items.push(<Squiggle key={i} cx={x} cy={y} size={sz*0.45} rot={rng()*360} stroke={c} />);
    } else if(k===3){
      items.push(
        <g key={i} transform={`translate(${x} ${y}) rotate(${rng()*360})`}>
          <circle cx="0" cy="0" r={sz*0.4} fill="none" stroke={c} strokeWidth={sz*0.06}/>
        </g>
      );
    } else if(k===4){
      // half-pill
      items.push(
        <g key={i} transform={`translate(${x} ${y}) rotate(${rng()*360})`}>
          <path d={`M ${-sz*0.5} 0 a ${sz*0.5} ${sz*0.5} 0 0 1 ${sz} 0 z`} fill={c}/>
        </g>
      );
    } else {
      items.push(<Rect key={i} cx={x} cy={y} w={sz*0.7} h={sz*0.18} rot={rng()*360} fill={c}/>);
    }
  }
  return items;
}

// =====================================================
// Floral — vine garlands with leaves and 5-petal flowers
// =====================================================
function MotifFloral({palette, density, scale, region, seed, page}){
  const rng = mulberry32(seed);
  const items = [];
  // garlands run along top and bottom edges of the region
  const garlandY = [region.y + 30*scale, region.y + region.h - 30*scale];
  garlandY.forEach((gy, gi) => {
    // wavy spine
    const segs = 12;
    let d = `M ${region.x} ${gy}`;
    for(let s=0; s<segs; s++){
      const x1 = region.x + ((s+0.5)/segs)*region.w;
      const x2 = region.x + ((s+1)/segs)*region.w;
      const y1 = gy + (s%2===0 ? -50*scale : 50*scale);
      d += ` Q ${x1} ${y1} ${x2} ${gy}`;
    }
    items.push(<path key={`spine-${gi}`} d={d} fill="none" stroke={palette.accent1} strokeWidth={3*scale} opacity={0.7}/>);

    // leaves + flowers along
    const count = Math.floor(40 * density * scale);
    for(let i=0;i<count;i++){
      const t = rng();
      const x = region.x + t*region.w;
      const y = gy + (Math.sin(t*Math.PI*8)*40 - 30 + rng()*60) * scale;
      const sz = (16 + rng()*18) * scale;
      const c = pickColor(rng, palette);
      if(rng() < 0.3){
        // 5-petal flower
        const flower = [];
        for(let p=0;p<5;p++){
          const a = (p/5)*Math.PI*2;
          flower.push(<ellipse key={p} cx={Math.cos(a)*sz*0.55} cy={Math.sin(a)*sz*0.55} rx={sz*0.35} ry={sz*0.55} fill={c}
            transform={`rotate(${a*180/Math.PI + 90} ${Math.cos(a)*sz*0.55} ${Math.sin(a)*sz*0.55})`} />);
        }
        items.push(<g key={`fl-${gi}-${i}`} transform={`translate(${x} ${y})`}>
          {flower}
          <circle cx="0" cy="0" r={sz*0.3} fill={palette.accent2 || palette.ink}/>
        </g>);
      } else {
        // leaf
        const rot = rng()*360;
        items.push(<ellipse key={`lf-${gi}-${i}`} cx={x} cy={y} rx={sz*0.3} ry={sz*0.7} fill={palette.accent3 || palette.accent1}
          transform={`rotate(${rot} ${x} ${y})`} opacity={0.85} />);
      }
    }
  });
  return items;
}

// =====================================================
// Art Deco — rays + chevrons
// =====================================================
function MotifDeco({palette, density, scale, region, seed}){
  const items = [];
  const cx = region.x + region.w/2;
  const cyTop = region.y + 20*scale;
  const cyBot = region.y + region.h - 20*scale;
  const rays = Math.max(7, Math.floor(13 + density*14));
  const rayLen = Math.min(region.w*0.55, 600*scale);

  [{y:cyTop, dir:1}, {y:cyBot, dir:-1}].forEach((side, idx) => {
    for(let i=0;i<rays;i++){
      const a = ((i/(rays-1)) - 0.5) * Math.PI * 0.95;
      const x2 = cx + Math.sin(a)*rayLen;
      const y2 = side.y + side.dir * Math.cos(a)*rayLen;
      const c = i%2 === 0 ? palette.accent1 : (palette.accent2 || palette.accent1);
      items.push(<line key={`r-${idx}-${i}`} x1={cx} y1={side.y} x2={x2} y2={y2}
        stroke={c} strokeWidth={6*scale} opacity={0.85} strokeLinecap="round"/>);
    }
    // central rondel
    items.push(<circle key={`d1-${idx}`} cx={cx} cy={side.y} r={36*scale} fill={palette.accent2 || palette.ink}/>);
    items.push(<circle key={`d2-${idx}`} cx={cx} cy={side.y} r={22*scale} fill={palette.bg}/>);
    items.push(<circle key={`d3-${idx}`} cx={cx} cy={side.y} r={10*scale} fill={palette.accent2 || palette.ink}/>);
  });

  // chevron borders left/right
  const chevH = 36*scale;
  const chevW = 24*scale;
  for(let y=region.y + 60*scale; y<region.y+region.h-60*scale; y += chevH*1.4){
    [region.x + 60, region.x + region.w - 60].forEach((x, side) => {
      const dx = side === 0 ? 1 : -1;
      items.push(<polyline key={`ch-${y}-${side}`}
        points={`${x},${y} ${x+chevW*dx},${y+chevH/2} ${x},${y+chevH}`}
        fill="none" stroke={palette.accent1} strokeWidth={4*scale} opacity={0.7}/>);
    });
  }
  return items;
}

// =====================================================
// Halftone — gradient dot field fading from edges to center
// =====================================================
function MotifHalftone({palette, density, scale, region, seed}){
  const rng = mulberry32(seed);
  const items = [];
  const step = 30 * (1.6 - scale*0.5);
  const cols = Math.floor(region.w/step);
  const rows = Math.floor(region.h/step);
  for(let r=0;r<rows;r++){
    for(let c=0;c<cols;c++){
      const x = region.x + (c+0.5)*step;
      const y = region.y + (r+0.5)*step;
      // distance from horizontal center axis (we keep central horizontal band light)
      const dxFromMid = Math.abs((c+0.5)/cols - 0.5);
      const dyFromMid = Math.abs((r+0.5)/rows - 0.5);
      const edge = Math.max(dxFromMid, dyFromMid);
      const radius = Math.max(0, edge*1.2 - 0.15) * step * 0.55 * (0.6 + density*1.0);
      if(radius < 0.6) continue;
      items.push(<circle key={`${r}-${c}`} cx={x} cy={y} r={radius} fill={palette.accent1} opacity={0.9}/>);
    }
  }
  return items;
}

// =====================================================
// Waves — parallel sine waves at top/bottom
// =====================================================
function MotifWaves({palette, density, scale, region, seed}){
  const items = [];
  const lines = Math.max(3, Math.floor(4 + density*7));
  const amp = 24 * scale;
  const wl = 240 * scale;
  ["top","bot"].forEach((side, sIdx) => {
    for(let i=0;i<lines;i++){
      const yBase = side === "top"
        ? region.y + 30*scale + i*(amp*1.6)
        : region.y + region.h - 30*scale - i*(amp*1.6);
      let d = `M ${region.x} ${yBase}`;
      for(let x = region.x; x < region.x + region.w; x += 16){
        const y = yBase + Math.sin((x/wl)*Math.PI*2 + i*0.5 + sIdx) * amp;
        d += ` L ${x} ${y}`;
      }
      const c = i%2===0 ? palette.accent1 : (palette.accent2 || palette.accent1);
      items.push(<path key={`${side}-${i}`} d={d} fill="none" stroke={c} strokeWidth={4*scale}
        opacity={0.85 - i*0.07} strokeLinecap="round"/>);
    }
  });
  return items;
}

// =====================================================
// Disco — concentric ringed sunburst + sparkles
// =====================================================
function MotifDisco({palette, density, scale, region, seed}){
  const rng = mulberry32(seed);
  const items = [];
  const cxs = [region.x + region.w*0.5];
  const cys = [region.y + 60*scale, region.y + region.h - 60*scale];
  cys.forEach((cy, ci) => {
    const cx = cxs[0];
    // sunburst rays
    const n = 32;
    for(let i=0;i<n;i++){
      const a = (i/n)*Math.PI*2;
      const r1 = 90*scale, r2 = (250 + (i%2)*60)*scale;
      items.push(<line key={`s-${ci}-${i}`}
        x1={cx + Math.cos(a)*r1} y1={cy + Math.sin(a)*r1}
        x2={cx + Math.cos(a)*r2} y2={cy + Math.sin(a)*r2}
        stroke={i%2===0 ? palette.accent1 : (palette.accent2||palette.accent1)} strokeWidth={6*scale}
        opacity={0.85}/>);
    }
    // central disco ball
    items.push(<circle key={`b-${ci}`} cx={cx} cy={cy} r={80*scale} fill={palette.accent2||palette.ink}/>);
    // facets
    const facets = [];
    for(let ry=-2;ry<=2;ry++) for(let rx=-2;rx<=2;rx++){
      facets.push(<rect key={`${ry}-${rx}`} x={rx*22*scale-10*scale} y={ry*22*scale-10*scale} width={20*scale} height={20*scale}
        fill={palette.bg} opacity={0.18 + ((rx+ry+4)%5)*0.05} />);
    }
    items.push(<g key={`f-${ci}`} transform={`translate(${cx} ${cy})`} clipPath={`url(#disco-clip-${ci})`}>{facets}</g>);
    items.push(<defs key={`d-${ci}`}><clipPath id={`disco-clip-${ci}`}><circle cx="0" cy="0" r={80*scale}/></clipPath></defs>);
  });

  // sparkles in sides
  const count = Math.floor(density*30);
  for(let i=0;i<count;i++){
    const x = region.x + rng()*region.w;
    const y = region.y + rng()*region.h;
    const sz = (10+rng()*30)*scale;
    items.push(<Star4 key={`sp-${i}`} cx={x} cy={y} size={sz} fill={palette.accent3||palette.accent1} opacity={0.85}/>);
  }
  return items;
}

// =====================================================
// Botanical — refined large palm/foliage in corners
// =====================================================
function MotifBotanical({palette, density, scale, region, seed}){
  const rng = mulberry32(seed);
  const items = [];
  // four corner fronds
  const corners = [
    {x: region.x + 80*scale, y: region.y + 80*scale, rot: -45},
    {x: region.x + region.w - 80*scale, y: region.y + 80*scale, rot: -135},
    {x: region.x + 80*scale, y: region.y + region.h - 80*scale, rot: 45},
    {x: region.x + region.w - 80*scale, y: region.y + region.h - 80*scale, rot: 135},
  ];
  corners.forEach((c, ci) => {
    const fronds = 5 + Math.floor(density*5);
    const len = (220 + density*200)*scale;
    const blades = [];
    for(let i=0;i<fronds;i++){
      const a = -55 + (110/(fronds-1))*i;
      const r = len * (0.7 + 0.3*Math.sin(i*0.7));
      blades.push(
        <ellipse key={i} cx={Math.cos(a*Math.PI/180)*r*0.5} cy={Math.sin(a*Math.PI/180)*r*0.5}
          rx={r*0.5} ry={r*0.07}
          fill={palette.accent1}
          opacity={0.85}
          transform={`rotate(${a} 0 0)`} />
      );
    }
    // little berries
    for(let i=0;i<5+Math.floor(density*8);i++){
      blades.push(<circle key={`b-${i}`} cx={(rng()-0.3)*len*0.5} cy={(rng()-0.3)*len*0.5} r={(6+rng()*8)*scale}
        fill={palette.accent2 || palette.accent1}/>);
    }
    items.push(<g key={ci} transform={`translate(${c.x} ${c.y}) rotate(${c.rot})`}>{blades}</g>);
  });
  return items;
}

// =====================================================
// None
// =====================================================
function MotifNone(){ return []; }

// Registry
window.MOTIFS = {
  none:      { label: "None",       fn: MotifNone },
  confetti:  { label: "Confetti",   fn: MotifConfetti },
  music:     { label: "Notes",      fn: MotifMusic },
  stars:     { label: "Stars",      fn: MotifStars },
  memphis:   { label: "Memphis",    fn: MotifMemphis },
  floral:    { label: "Floral",     fn: MotifFloral },
  deco:      { label: "Deco rays",  fn: MotifDeco },
  halftone:  { label: "Halftone",   fn: MotifHalftone },
  waves:     { label: "Waves",      fn: MotifWaves },
  disco:     { label: "Disco",      fn: MotifDisco },
  botanical: { label: "Botanical",  fn: MotifBotanical },
};

// motif preview swatches (small SVG icons used in the chip picker)
window.MOTIF_ICONS = {
  none:     <g><line x1="2" y1="11" x2="26" y2="11" stroke="currentColor" strokeWidth="1.2" opacity=".4"/></g>,
  confetti: <g fill="currentColor"><circle cx="5" cy="5" r="2"/><polygon points="14,3 18,3 16,7"/><rect x="22" y="6" width="3" height="3"/><circle cx="8" cy="14" r="1.4"/><polygon points="20,12 24,12 22,16"/><rect x="13" y="14" width="3" height="3"/></g>,
  music:    <g fill="currentColor"><path d="M6 16 L6 5 L16 3 L16 14"/><circle cx="5" cy="17" r="2"/><circle cx="15" cy="15" r="2"/></g>,
  stars:    <g fill="currentColor"><path d="M7 4 L8.2 7.5 L11.7 8 L9 10.4 L9.7 14 L7 12.2 L4.3 14 L5 10.4 L2.3 8 L5.8 7.5 Z"/><path d="M19 9 L20 11 L22 11.4 L20.5 13 L21 15 L19 14 L17 15 L17.5 13 L16 11.4 L18 11 Z"/></g>,
  memphis:  <g fill="currentColor"><polygon points="4,3 9,3 6.5,8"/><circle cx="18" cy="6" r="3" fill="none" stroke="currentColor" strokeWidth="1"/><path d="M3 14 q3 -3 6 0 t 6 0 t 6 0" fill="none" stroke="currentColor" strokeWidth="1"/></g>,
  floral:   <g fill="currentColor"><circle cx="6" cy="11" r="2"/><circle cx="3" cy="9" r="1.4"/><circle cx="9" cy="9" r="1.4"/><circle cx="3" cy="13" r="1.4"/><circle cx="9" cy="13" r="1.4"/><ellipse cx="18" cy="11" rx="2" ry="4" /><path d="M14 17 q4 -2 10 0" stroke="currentColor" strokeWidth="1" fill="none"/></g>,
  deco:     <g stroke="currentColor" strokeWidth="1" fill="none"><line x1="14" y1="11" x2="3" y2="3"/><line x1="14" y1="11" x2="9" y2="2"/><line x1="14" y1="11" x2="14" y2="2"/><line x1="14" y1="11" x2="19" y2="2"/><line x1="14" y1="11" x2="25" y2="3"/><circle cx="14" cy="11" r="2" fill="currentColor"/></g>,
  halftone: <g fill="currentColor"><circle cx="3" cy="11" r="2.4"/><circle cx="9" cy="11" r="1.6"/><circle cx="14" cy="11" r="0.7"/><circle cx="19" cy="11" r="1.6"/><circle cx="25" cy="11" r="2.4"/></g>,
  waves:    <g stroke="currentColor" strokeWidth="1.2" fill="none"><path d="M2 7 q3 -3 6 0 t 6 0 t 6 0 t 6 0"/><path d="M2 14 q3 -3 6 0 t 6 0 t 6 0 t 6 0"/></g>,
  disco:    <g fill="currentColor"><circle cx="14" cy="11" r="3"/><line x1="14" y1="11" x2="14" y2="2" stroke="currentColor"/><line x1="14" y1="11" x2="14" y2="20" stroke="currentColor"/><line x1="14" y1="11" x2="3" y2="11" stroke="currentColor"/><line x1="14" y1="11" x2="25" y2="11" stroke="currentColor"/><line x1="14" y1="11" x2="6" y2="3" stroke="currentColor"/><line x1="14" y1="11" x2="22" y2="3" stroke="currentColor"/></g>,
  botanical:<g fill="currentColor"><ellipse cx="6" cy="11" rx="6" ry="1.5" transform="rotate(-30 6 11)"/><ellipse cx="6" cy="11" rx="6" ry="1.5" transform="rotate(0 6 11)"/><ellipse cx="6" cy="11" rx="6" ry="1.5" transform="rotate(30 6 11)"/><ellipse cx="22" cy="11" rx="5" ry="1.4" transform="rotate(150 22 11)"/><ellipse cx="22" cy="11" rx="5" ry="1.4" transform="rotate(180 22 11)"/></g>,
};
