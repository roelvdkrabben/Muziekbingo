// MuziekBingo Designer — Streamlit component variant
const { useState, useEffect, useRef, useLayoutEffect } = React;

// ── Streamlit component protocol ─────────────────────────────────────────────
const Streamlit = (() => {
  let _ready = false;
  function send(type, data) {
    window.parent.postMessage(Object.assign({ isStreamlitMessage: true, type }, data), "*");
  }
  return {
    setComponentReady() {
      if (_ready) return;
      _ready = true;
      send("streamlit:componentReady", { apiVersion: 1 });
    },
    setFrameHeight(h) { send("streamlit:setFrameHeight", { height: h }); },
    setComponentValue(value) { send("streamlit:componentValue", { value }); },
  };
})();

const DEFAULT_STATE = {
  title: "MUZIEK BINGO",
  subtitle: "Een avond vol klassiekers",
  footerL: "Score 5 op een rij",
  footerR: "muziekbingo.app",
  logoDataUrl: null,
  logoSize: 280,
  titleFont: "Playfair Display",
  bodyFont: "EB Garamond",
  titleSize: 200,
  titleWeight: "900",
  titleTracking: 0.03,
  headerAlign: "center",
  margin: 0.06,
  headerH: 0.24,
  footerH: 0.10,
  gridPadding: 60,
  palette: { bg: "#f5f1ea", ink: "#1c1a18", accent1: "#b8312e", accent2: "#1a3d6b", accent3: "#d6b86b" },
  bandColor: "none",
  motif: "deco",
  density: 0.5,
  motifScale: 1,
  sideOrnaments: false,
  frame: "double",
  gridFill: "paper",
  paperGrain: 0.18,
  seed: 17,
};

async function buildFontCSS(families) {
  try {
    const fams = [...families].map(f =>
      `family=${encodeURIComponent(f)}:wght@400;700;900&family=${encodeURIComponent(f)}:ital,wght@1,400;1,700`
    ).join("&");
    const cssUrl = `https://fonts.googleapis.com/css2?${fams}&display=swap`;
    const res = await fetch(cssUrl, { headers: { "User-Agent": "Mozilla/5.0" } });
    let cssText = await res.text();
    const urls = [...cssText.matchAll(/url\((https:\/\/[^)]+)\)/g)].map(m => m[1]);
    const replaceMap = {};
    await Promise.all(urls.map(async u => {
      try {
        const r = await fetch(u);
        const buf = await r.arrayBuffer();
        const b64 = btoa(String.fromCharCode(...new Uint8Array(buf)));
        replaceMap[u] = `data:font/woff2;base64,${b64}`;
      } catch (e) { }
    }));
    Object.entries(replaceMap).forEach(([u, dataUrl]) => {
      cssText = cssText.split(u).join(dataUrl);
    });
    return cssText;
  } catch (e) {
    return "";
  }
}

async function svgToPngBase64(svg, state) {
  const clone = svg.cloneNode(true);
  clone.querySelectorAll('rect[stroke-dasharray]').forEach(el => el.remove());
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  clone.setAttribute("width", window.PAGE_SIZE.w);
  clone.setAttribute("height", window.PAGE_SIZE.h);

  const fontFamilies = new Set([state.titleFont, state.bodyFont]);
  const cssText = await buildFontCSS(fontFamilies);
  const styleEl = document.createElementNS("http://www.w3.org/2000/svg", "style");
  styleEl.textContent = cssText;
  clone.insertBefore(styleEl, clone.firstChild);

  const xml = new XMLSerializer().serializeToString(clone);
  const svgBlob = new Blob([xml], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(svgBlob);

  const img = new Image();
  img.crossOrigin = "anonymous";
  await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = url; });

  // Render at 50% resolution for Streamlit transport (~4× smaller payload)
  const scale = 0.5;
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(window.PAGE_SIZE.w * scale);
  canvas.height = Math.round(window.PAGE_SIZE.h * scale);
  const ctx = canvas.getContext("2d");
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  URL.revokeObjectURL(url);

  const blob = await new Promise(res => canvas.toBlob(res, "image/jpeg", 0.92));
  return new Promise(res => {
    const reader = new FileReader();
    reader.onload = e => res(e.target.result.split(',')[1]);
    reader.readAsDataURL(blob);
  });
}

function App() {
  const [state, setState] = useState(DEFAULT_STATE);
  const [activePresetId, setActivePresetId] = useState("editorial");
  const [showMarker, setShowMarker] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [zoomMode, setZoomMode] = useState("fit");
  const [exporting, setExporting] = useState(false);
  const [toast, setToast] = useState("");
  const [saved, setSaved] = useState(false);

  const stageRef = useRef(null);
  const svgRef = useRef(null);

  // Signal Streamlit after first paint
  useEffect(() => {
    Streamlit.setComponentReady();
    const h = Math.max(800, (window.screen.availHeight || 1080) - 160);
    Streamlit.setFrameHeight(h);
  }, []);

  useLayoutEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const recompute = () => {
      if (zoomMode !== "fit") return;
      const pad = 60;
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
    setState(s => ({ ...s, ...preset.apply }));
    setSaved(false);
  };

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  };

  const downloadPNG = async () => {
    setExporting(true);
    try {
      // For download: use PNG at full quality
      const svg = svgRef.current;
      const clone = svg.cloneNode(true);
      clone.querySelectorAll('rect[stroke-dasharray]').forEach(el => el.remove());
      clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
      clone.setAttribute("width", window.PAGE_SIZE.w);
      clone.setAttribute("height", window.PAGE_SIZE.h);
      const fontFamilies = new Set([state.titleFont, state.bodyFont]);
      const cssText = await buildFontCSS(fontFamilies);
      const styleEl = document.createElementNS("http://www.w3.org/2000/svg", "style");
      styleEl.textContent = cssText;
      clone.insertBefore(styleEl, clone.firstChild);
      const xml = new XMLSerializer().serializeToString(clone);
      const svgBlob = new Blob([xml], { type: "image/svg+xml;charset=utf-8" });
      const url = URL.createObjectURL(svgBlob);
      const img = new Image();
      img.crossOrigin = "anonymous";
      await new Promise((res, rej) => { img.onload = res; img.onerror = rej; img.src = url; });
      const canvas = document.createElement("canvas");
      canvas.width = window.PAGE_SIZE.w; canvas.height = window.PAGE_SIZE.h;
      canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      const blob = await new Promise(res => canvas.toBlob(res, "image/png", 1));
      const a = document.createElement("a");
      const safe = state.title.replace(/[^a-z0-9]+/gi, "-").toLowerCase().slice(0, 40) || "bingo-bg";
      a.href = URL.createObjectURL(blob);
      a.download = `${safe}-2480x3508.png`;
      document.body.appendChild(a); a.click();
      setTimeout(() => { a.remove(); URL.revokeObjectURL(a.href); }, 1000);
      showToast("PNG gedownload (2480 × 3508 px)");
    } catch (err) {
      showToast("Download mislukt — zie console");
      console.error(err);
    } finally {
      setExporting(false);
    }
  };

  const useAsBackground = async () => {
    setExporting(true);
    try {
      const b64 = await svgToPngBase64(svgRef.current, state);
      const gridRect = window.computeGridRect(state);
      Streamlit.setComponentValue({
        png_base64: b64,
        grid_rect: gridRect,
        title: state.title,
      });
      setSaved(true);
      showToast("Achtergrond verstuurd — het formulier verschijnt boven de designer");
    } catch (err) {
      showToast("Mislukt — zie console");
      console.error(err);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <div className="topbar">
        <div className="brand">
          <div className="mark">M</div>
          <h1>Muziek<em>Bingo</em></h1>
          <span className="sub">Background Designer · A4 · 300 DPI</span>
        </div>
        <div className="grow"></div>
        <button className="topbtn" onClick={() => setShowMarker(s => !s)}>
          {showMarker ? "Verberg raster" : "Toon raster"}
        </button>
        <button className="topbtn" onClick={() => { setState(DEFAULT_STATE); setSaved(false); }}>Reset</button>
        <button className="topbtn" onClick={downloadPNG} disabled={exporting}>
          PNG downloaden
        </button>
        <button className={"topbtn " + (saved ? "success" : "primary")} onClick={useAsBackground} disabled={exporting}>
          {exporting ? "Bezig…" : saved ? "Opgeslagen" : "Gebruik als achtergrond"}
        </button>
      </div>

      <div className="layout">
        <div className="stage" ref={stageRef}>
          <div className="stage-chrome">
            <span className="pill">A4 · 2480 × 3508 px</span>
            <span className="pill">{Math.round(zoom * 100)}% preview</span>
            <span className="grow"></span>
            <span className="pill">{state.motif} · {Math.round(state.density * 100)}%</span>
          </div>

          <div className="stage-inner" style={{
            width: window.PAGE_SIZE.w,
            height: window.PAGE_SIZE.h,
            transform: `scale(${zoom})`,
          }}>
            <div className="a4">
              <window.A4Canvas ref={svgRef} state={state} showMarker={showMarker} />
            </div>
          </div>

          <div className="zoom-controls">
            <button onClick={() => { setZoomMode("manual"); setZoom(z => Math.max(0.04, z * 0.85)); }}>−</button>
            <span className="num">{Math.round(zoom * 100)}%</span>
            <button onClick={() => { setZoomMode("manual"); setZoom(z => Math.min(2, z * 1.18)); }}>+</button>
            <button style={{ fontSize: 9 }} onClick={() => setZoomMode("fit")}>fit</button>
          </div>
        </div>

        <window.Inspector
          state={state} setState={setState}
          applyPreset={applyPreset}
          activePresetId={activePresetId} />
      </div>

      <div className={"toast " + (toast ? "show" : "")}>{toast}</div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
