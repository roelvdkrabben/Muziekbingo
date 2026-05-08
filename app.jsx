// Main App — wires inspector + canvas, manages state, handles PNG export.
const { useState, useEffect, useRef, useLayoutEffect, useMemo: useMemoA } = React;

const DEFAULT_STATE = {
  // identity
  title: "MUZIEK BINGO",
  subtitle: "Een avond vol klassiekers",
  footerL: "Score 5 op een rij",
  footerR: "muziekbingo.app",
  // logo
  logoDataUrl: null,
  logoSize: 280,
  // typography
  titleFont: "Playfair Display",
  bodyFont: "EB Garamond",
  titleSize: 200,
  titleWeight: "900",
  titleTracking: 0.03,
  headerAlign: "center",
  // layout
  margin: 0.06,
  headerH: 0.24,
  footerH: 0.10,
  gridPadding: 60,
  // palette
  palette: {
    bg: "#f5f1ea",
    ink: "#1c1a18",
    accent1: "#b8312e",
    accent2: "#1a3d6b",
    accent3: "#d6b86b",
  },
  bandColor: "none",
  // decoration
  motif: "deco",
  density: 0.5,
  motifScale: 1,
  sideOrnaments: false,
  // grid area
  frame: "double",
  gridFill: "paper",
  // texture
  paperGrain: 0.18,
  // misc
  seed: 17,
};

function App(){
  const [state, setState] = useState(DEFAULT_STATE);
  const [activePresetId, setActivePresetId] = useState("editorial");
  const [showMarker, setShowMarker] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [zoomMode, setZoomMode] = useState("fit"); // "fit" | "manual"
  const [exporting, setExporting] = useState(false);
  const [toast, setToast] = useState("");

  const stageRef = useRef(null);
  const innerRef = useRef(null);
  const svgRef = useRef(null);

  // fit-to-stage scaling
  useLayoutEffect(() => {
    const stage = stageRef.current;
    if(!stage) return;
    const recompute = () => {
      if(zoomMode !== "fit") return;
      const pad = 80;
      const sw = stage.clientWidth - pad;
      const sh = stage.clientHeight - pad;
      const sx = sw / window.PAGE_SIZE.w;
      const sy = sh / window.PAGE_SIZE.h;
      setZoom(Math.min(sx, sy));
    };
    recompute();
    const ro = new ResizeObserver(recompute);
    ro.observe(stage);
    return () => ro.disconnect();
  }, [zoomMode]);

  const applyPreset = (preset) => {
    setActivePresetId(preset.id);
    setState(s => ({...s, ...preset.apply}));
  };

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(""), 2400);
  };

  const exportPNG = async () => {
    setExporting(true);
    try {
      const svg = svgRef.current;
      // serialize the SVG (the visible one, with grid marker hidden)
      const tempState = {...state};
      // we already hide marker by passing showMarker=false in a fresh render; easiest: use the svg outerHTML but stripped of marker.
      // Instead: clone the SVG and remove the dashed rect (last <rect> with stroke-dasharray) if present.
      const clone = svg.cloneNode(true);
      // remove any element with stroke-dasharray attribute that is the marker
      clone.querySelectorAll('rect[stroke-dasharray]').forEach(el => el.remove());

      // ensure xmlns
      clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
      clone.setAttribute("width", window.PAGE_SIZE.w);
      clone.setAttribute("height", window.PAGE_SIZE.h);

      // inline the Google Fonts CSS so canvas renders text correctly
      const fontFamilies = new Set([state.titleFont, state.bodyFont]);
      const cssText = await buildFontCSS(fontFamilies);

      const styleEl = document.createElementNS("http://www.w3.org/2000/svg", "style");
      styleEl.textContent = cssText;
      clone.insertBefore(styleEl, clone.firstChild);

      const xml = new XMLSerializer().serializeToString(clone);
      const svgBlob = new Blob([xml], {type:"image/svg+xml;charset=utf-8"});
      const url = URL.createObjectURL(svgBlob);

      const img = new Image();
      img.crossOrigin = "anonymous";
      await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = url; });

      const canvas = document.createElement("canvas");
      canvas.width = window.PAGE_SIZE.w;
      canvas.height = window.PAGE_SIZE.h;
      const ctx = canvas.getContext("2d");
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);

      const blob = await new Promise(res => canvas.toBlob(res, "image/png", 1));
      const dlUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const safe = state.title.replace(/[^a-z0-9]+/gi, "-").toLowerCase().slice(0, 40) || "bingo-card";
      a.href = dlUrl; a.download = `${safe}-bg-2480x3508.png`;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(dlUrl), 1000);
      showToast("PNG exported · 2480 × 3508");
    } catch (err) {
      console.error(err);
      showToast("Export failed — see console");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div style={{height:"100%", display:"flex", flexDirection:"column"}}>
      <div className="topbar">
        <div className="brand">
          <div className="mark">M</div>
          <h1>Muziek<em>Bingo</em></h1>
          <span className="sub">Background designer · A4 · 300 DPI</span>
        </div>
        <div className="grow"></div>
        <button className="topbtn" onClick={() => setShowMarker(s => !s)}>
          {showMarker ? "◐ Hide grid marker" : "◑ Show grid marker"}
        </button>
        <button className="topbtn" onClick={() => setState(DEFAULT_STATE)}>Reset</button>
        <button className="topbtn primary" onClick={exportPNG} disabled={exporting}>
          {exporting ? "Exporting…" : "↓ Export PNG"}
        </button>
      </div>

      <div className="layout">
        <div className="stage" ref={stageRef}>
          <div className="stage-chrome">
            <span className="pill">A4 · 2480 × 3508 px</span>
            <span className="pill">{Math.round(zoom*100)}% preview</span>
            <span className="grow"></span>
            <span className="pill">{state.motif} · density {Math.round(state.density*100)}%</span>
          </div>

          <div ref={innerRef} className="stage-inner"
            style={{
              width: window.PAGE_SIZE.w,
              height: window.PAGE_SIZE.h,
              transform: `scale(${zoom})`,
            }}>
            <div className="a4">
              <window.A4Canvas ref={svgRef} state={state} showMarker={showMarker}/>
            </div>
          </div>

          <div className="zoom-controls">
            <button onClick={() => { setZoomMode("manual"); setZoom(z => Math.max(0.05, z*0.85)); }}>−</button>
            <span className="num">{Math.round(zoom*100)}%</span>
            <button onClick={() => { setZoomMode("manual"); setZoom(z => Math.min(2, z*1.18)); }}>+</button>
            <button title="Fit" style={{fontSize:10}} onClick={() => setZoomMode("fit")}>fit</button>
          </div>
        </div>

        <window.Inspector
          state={state} setState={setState}
          applyPreset={applyPreset}
          activePresetId={activePresetId}/>
      </div>

      <div className={"toast " + (toast ? "show":"")}>{toast}</div>
    </div>
  );
}

// Build a CSS @font-face block for the chosen Google Fonts, fetching the CSS
// and embedding the woff2 files as base64 so the SVG renders text in canvas.
async function buildFontCSS(families){
  try {
    const fams = [...families].map(f => `family=${encodeURIComponent(f)}:wght@400;700;900&family=${encodeURIComponent(f)}:ital,wght@1,400;1,700`).join("&");
    const cssUrl = `https://fonts.googleapis.com/css2?${fams}&display=swap`;
    const res = await fetch(cssUrl, {headers: {"User-Agent": "Mozilla/5.0"}});
    let cssText = await res.text();
    // find all url(...) and inline as base64
    const urls = [...cssText.matchAll(/url\((https:\/\/[^)]+)\)/g)].map(m => m[1]);
    const replaceMap = {};
    await Promise.all(urls.map(async u => {
      try {
        const r = await fetch(u);
        const buf = await r.arrayBuffer();
        const b64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
        replaceMap[u] = `data:font/woff2;base64,${b64}`;
      } catch(e){ /* skip */ }
    }));
    Object.entries(replaceMap).forEach(([u, dataUrl]) => {
      cssText = cssText.split(u).join(dataUrl);
    });
    return cssText;
  } catch(e) {
    console.warn("Font inlining failed; falling back to system fonts", e);
    return "";
  }
}

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
