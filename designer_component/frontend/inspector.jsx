// Inspector — control panel for the bingo card designer.
const { useState: useStateI } = React;

function Section({ title, badge, defaultOpen=true, children }){
  return (
    <details className="section" open={defaultOpen}>
      <summary>
        <span className="caret"></span>
        <span className="title">{title}</span>
        {badge && <span className="badge">{badge}</span>}
      </summary>
      <div className="section-body">{children}</div>
    </details>
  );
}

function Field({ label, children }){
  return <div className="field"><div className="label">{label}</div>{children}</div>;
}

function Slider({ value, onChange, min, max, step=1, suffix="" }){
  return (
    <div className="slider-row">
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(parseFloat(e.target.value))}/>
      <span className="num">{value}{suffix}</span>
    </div>
  );
}

function Segmented({ value, onChange, options }){
  return (
    <div className="segmented">
      {options.map(o => (
        <button key={o.value} className={value===o.value ? "active":""}
          onClick={() => onChange(o.value)}>{o.label}</button>
      ))}
    </div>
  );
}

function Toggle({ value, onChange }){
  return <div className={"toggle " + (value?"on":"")} onClick={() => onChange(!value)} role="switch" aria-checked={value}/>;
}

function isLight(hex){
  if(!hex) return false;
  const h = hex.replace("#","");
  const r = parseInt(h.slice(0,2),16), g = parseInt(h.slice(2,4),16), b = parseInt(h.slice(4,6),16);
  return (r*299 + g*587 + b*114)/1000 > 160;
}

function Swatch({ value, onChange, label }){
  return (
    <div>
      <div className={"swatch " + (isLight(value)?"light":"")} style={{background: value}}>
        <input type="color" value={value} onChange={e => onChange(e.target.value)}/>
        <span className="hex">{value}</span>
      </div>
      <div className="label" style={{textAlign:"center", marginTop:4, fontSize:8}}>{label}</div>
    </div>
  );
}

function MotifChip({ id, value, label, onChange }){
  const icon = window.MOTIF_ICONS[id];
  return (
    <button className={"chip " + (value===id?"active":"")} onClick={() => onChange(id)}>
      <svg viewBox="0 0 28 22" style={{color: value===id ? "#f5f1ea" : "#3a3530"}}>{icon}</svg>
      {label}
    </button>
  );
}

function PresetCard({ preset, active, onPick }){
  const swatch = preset.swatch;
  return (
    <div className={"preset-card " + (active?"active":"")} onClick={() => onPick(preset)}>
      <svg viewBox="0 0 100 71" style={{display:"block", width:"100%", height:"100%"}}>
        <rect x="0" y="0" width="100" height="71" fill={swatch[0]}/>
        {/* tiny header band */}
        <rect x="6" y="6" width="88" height="14" fill={swatch[2]} opacity="0.18"/>
        <rect x="14" y="11" width="42" height="3" fill={swatch[1]}/>
        <rect x="14" y="15" width="22" height="1.5" fill={swatch[2]}/>
        {/* 5×5 grid hint */}
        <g stroke={swatch[1]} strokeWidth="0.4" fill="none" opacity="0.6">
          {[0,1,2,3,4,5].map(i =>
            <React.Fragment key={i}>
              <line x1={20} y1={26+i*5} x2={80} y2={26+i*5}/>
              <line x1={20+i*12} y1={26} x2={20+i*12} y2={56}/>
            </React.Fragment>
          )}
        </g>
        {/* footer accent */}
        <circle cx="14" cy="64" r="1.5" fill={swatch[2]}/>
        <rect x="18" y="63" width="20" height="1.2" fill={swatch[1]} opacity="0.7"/>
        <rect x="62" y="63" width="22" height="1.2" fill={swatch[1]} opacity="0.4"/>
      </svg>
      <span className="label">{preset.label}</span>
    </div>
  );
}

window.Inspector = function Inspector({ state, setState, applyPreset, activePresetId }){
  const set = (k, v) => setState(s => ({...s, [k]: v}));
  const setPalette = (k, v) => setState(s => ({...s, palette: {...s.palette, [k]: v}}));

  const onLogoUpload = (file) => {
    if(!file) return;
    const reader = new FileReader();
    reader.onload = e => set("logoDataUrl", e.target.result);
    reader.readAsDataURL(file);
  };

  return (
    <div className="inspector">
      {/* Presets */}
      <div style={{padding:"14px 18px 4px"}}>
        <div className="label">Presets</div>
        <div className="hint" style={{marginTop:4}}>One-click starting points. Tweak everything below.</div>
      </div>
      <div className="preset-grid">
        {window.PRESETS.map(p => (
          <PresetCard key={p.id} preset={p} active={activePresetId===p.id} onPick={applyPreset}/>
        ))}
      </div>

      {/* Header */}
      <Section title="Header" badge="Title · Subtitle · Logo">
        <Field label="Title">
          <input type="text" value={state.title} onChange={e => set("title", e.target.value)}/>
        </Field>
        <Field label="Subtitle">
          <input type="text" value={state.subtitle} onChange={e => set("subtitle", e.target.value)}/>
        </Field>
        <Field label="Alignment">
          <Segmented value={state.headerAlign} onChange={v => set("headerAlign", v)}
            options={[{value:"left",label:"Left"},{value:"center",label:"Center"},{value:"right",label:"Right"}]}/>
        </Field>
        <Field label="Title size">
          <Slider value={state.titleSize} min={80} max={280} step={4} onChange={v => set("titleSize", v)} suffix="px"/>
        </Field>
        <Field label="Title tracking">
          <Slider value={state.titleTracking} min={-0.04} max={0.4} step={0.005} onChange={v => set("titleTracking", v)} suffix="em"/>
        </Field>
        <Field label="Title weight">
          <Segmented value={state.titleWeight} onChange={v => set("titleWeight", v)}
            options={[{value:"400",label:"Reg"},{value:"700",label:"Bold"},{value:"900",label:"Black"}]}/>
        </Field>
        <Field label="Header height">
          <Slider value={Math.round(state.headerH*100)} min={10} max={40} step={1}
            onChange={v => set("headerH", v/100)} suffix="%"/>
        </Field>

        {/* logo upload */}
        <div style={{height:1, background:"var(--line)", margin:"6px 0"}}></div>
        <Field label="Logo">
          {state.logoDataUrl ? (
            <div style={{display:"flex", alignItems:"center", gap:10}}>
              <div style={{
                width:60, height:60, borderRadius:8, border:"1px solid var(--line)",
                background:`url(${state.logoDataUrl}) center/contain no-repeat #fff`,
              }}/>
              <button className="topbtn" style={{flex:1, justifyContent:"center"}}
                onClick={() => set("logoDataUrl", null)}>Remove</button>
            </div>
          ) : (
            <label className="topbtn" style={{justifyContent:"center", cursor:"pointer"}}>
              <input type="file" accept="image/png,image/jpeg,image/svg+xml" style={{display:"none"}}
                onChange={e => onLogoUpload(e.target.files[0])}/>
              ↑ Upload PNG / JPG / SVG
            </label>
          )}
        </Field>
        {state.logoDataUrl && (
          <Field label="Logo size">
            <Slider value={state.logoSize} min={120} max={600} step={10}
              onChange={v => set("logoSize", v)} suffix="px"/>
          </Field>
        )}
      </Section>

      {/* Typography */}
      <Section title="Typography" badge="Fonts" defaultOpen={false}>
        <Field label="Title font">
          <select value={state.titleFont} onChange={e => set("titleFont", e.target.value)}>
            {window.TITLE_FONTS.map(f => <option key={f} value={f} style={{fontFamily:f}}>{f}</option>)}
          </select>
        </Field>
        <Field label="Body font (subtitle, footer)">
          <select value={state.bodyFont} onChange={e => set("bodyFont", e.target.value)}>
            {window.BODY_FONTS.map(f => <option key={f} value={f} style={{fontFamily:f}}>{f}</option>)}
          </select>
        </Field>
      </Section>

      {/* Palette */}
      <Section title="Palette" badge="5 colors">
        <div className="swatch-row">
          <Swatch value={state.palette.bg}      onChange={v => setPalette("bg", v)}      label="Background"/>
          <Swatch value={state.palette.ink}     onChange={v => setPalette("ink", v)}     label="Ink"/>
          <Swatch value={state.palette.accent1} onChange={v => setPalette("accent1", v)} label="Accent 1"/>
          <Swatch value={state.palette.accent2} onChange={v => setPalette("accent2", v)} label="Accent 2"/>
          <Swatch value={state.palette.accent3} onChange={v => setPalette("accent3", v)} label="Accent 3"/>
        </div>
        <Field label="Margin band tint">
          <Segmented value={state.bandColor||"none"} onChange={v => set("bandColor", v)}
            options={[{value:"none",label:"None"},{value:"accent",label:"Accent wash"}]}/>
        </Field>
      </Section>

      {/* Decoration */}
      <Section title="Decoration" badge="Motif · Density">
        <Field label="Motif">
          <div className="chip-grid">
            {Object.entries(window.MOTIFS).map(([id, m]) => (
              <MotifChip key={id} id={id} label={m.label} value={state.motif} onChange={v => set("motif", v)}/>
            ))}
          </div>
        </Field>
        <Field label="Density">
          <Slider value={Math.round(state.density*100)} min={0} max={100}
            onChange={v => set("density", v/100)} suffix="%"/>
        </Field>
        <Field label="Element scale">
          <Slider value={state.motifScale} min={0.5} max={1.8} step={0.05}
            onChange={v => set("motifScale", v)} suffix="×"/>
        </Field>
        <div className="field-row">
          <span className="label inline">Side ornaments</span>
          <Toggle value={state.sideOrnaments} onChange={v => set("sideOrnaments", v)}/>
        </div>
        <div className="field-row">
          <button className="topbtn" style={{flex:1, justifyContent:"center"}}
            onClick={() => set("seed", Math.floor(Math.random()*100000))}>↻ Reshuffle</button>
        </div>
      </Section>

      {/* Grid area */}
      <Section title="Grid area" badge="Where the 5×5 sits">
        <Field label="Fill">
          <Segmented value={state.gridFill} onChange={v => set("gridFill", v)}
            options={[
              {value:"paper",label:"Paper"},
              {value:"panel",label:"Panel"},
              {value:"white",label:"White"},
              {value:"tint",label:"Soft tint"},
            ]}/>
        </Field>
        <Field label="Frame">
          <Segmented value={state.frame} onChange={v => set("frame", v)}
            options={[
              {value:"none",label:"None"},
              {value:"hairline",label:"Hairline"},
              {value:"double",label:"Double"},
              {value:"tagged",label:"Cut"},
              {value:"ornaments",label:"Ornament"},
              {value:"ribbon",label:"Ribbon"},
            ]}/>
        </Field>
        <Field label="Grid padding">
          <Slider value={state.gridPadding} min={0} max={300} step={10}
            onChange={v => set("gridPadding", v)} suffix="px"/>
        </Field>
        <Field label="Footer height">
          <Slider value={Math.round(state.footerH*100)} min={5} max={30} step={1}
            onChange={v => set("footerH", v/100)} suffix="%"/>
        </Field>
      </Section>

      {/* Cell text style */}
      <Section title="Tekst in cellen" badge="Lettergrootte · Uitlijning">
        <Field label="Lettergrootte">
          <Slider value={state.cellFontScale} min={0.5} max={2.0} step={0.05}
            onChange={v => set("cellFontScale", v)} suffix="×"/>
        </Field>
        <Field label="Tussenlijn">
          <select value={state.cellSeparator} onChange={e => set("cellSeparator", e.target.value)}>
            <option value="">geen</option>
            <option value="—"> — </option>
            <option value="·"> · </option>
            <option value="/">  /  </option>
            <option value="|">  |  </option>
          </select>
        </Field>
        <Field label="Uitlijning">
          <Segmented value={state.cellTitleAlign} onChange={v => set("cellTitleAlign", v)}
            options={[{value:"left",label:"Links"},{value:"center",label:"Midden"}]}/>
        </Field>
        <Field label="Verticaal">
          <Segmented value={state.cellVerticalAlign} onChange={v => set("cellVerticalAlign", v)}
            options={[{value:"top",label:"Boven"},{value:"middle",label:"Midden"}]}/>
        </Field>
      </Section>

      {/* Footer */}
      <Section title="Footer" defaultOpen={false}>
        <Field label="Footer left">
          <input type="text" value={state.footerL} onChange={e => set("footerL", e.target.value)}/>
        </Field>
        <Field label="Footer right">
          <input type="text" value={state.footerR} onChange={e => set("footerR", e.target.value)}/>
        </Field>
      </Section>

      {/* Texture */}
      <Section title="Texture" defaultOpen={false}>
        <Field label="Paper grain">
          <Slider value={Math.round(state.paperGrain*100)} min={0} max={60} step={1}
            onChange={v => set("paperGrain", v/100)} suffix="%"/>
        </Field>
        <Field label="Page margin">
          <Slider value={Math.round(state.margin*100)} min={3} max={12} step={0.5}
            onChange={v => set("margin", v/100)} suffix="%"/>
        </Field>
      </Section>

      <div style={{padding:"18px", color:"var(--muted)"}} className="hint">
        Output: 2480 × 3508 px (A4, 300 DPI). PNG export uses these exact dimensions — drag your bingo grid over the marked area in your bingo app.
      </div>

      <div className="made-by">
        <span>Made by</span>
        <img src="assets/taigers-logo.png" alt="Taigers" className="made-by-logo"/>
      </div>
    </div>
  );
};
