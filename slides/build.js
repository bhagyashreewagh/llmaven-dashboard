const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");

// ── Icons ──────────────────────────────────────────────────────────────────
const { FaDatabase, FaChartBar, FaUserSecret, FaLayerGroup, FaRobot,
        FaBrain, FaCheckCircle, FaArrowRight, FaFlask, FaTools } = require("react-icons/fa");
const { MdPrivacyTip, MdQueryStats, MdTimeline } = require("react-icons/md");

async function iconPng(IconComponent, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(
    React.createElement(IconComponent, { color, size: String(size) })
  );
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

// ── Color Palette ──────────────────────────────────────────────────────────
const C = {
  navy:     "0F172A",
  blue:     "065A82",
  teal:     "0D9488",
  tealDark: "0F766E",
  ice:      "E0F2FE",
  white:    "FFFFFF",
  offwhite: "F8FAFC",
  gray:     "64748B",
  lightgray:"CBD5E1",
  dark:     "1E293B",
  mid:      "475569",
};

const FONT_TITLE = "Georgia";
const FONT_BODY  = "Calibri";

// ── Main ───────────────────────────────────────────────────────────────────
async function build() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9"; // 10" × 5.625"
  pres.title  = "LLMoxie Analytics Pipeline";
  pres.author = "Bhagyashree Wagh";

  // ── Slide 1: Title ────────────────────────────────────────────────────────
  {
    const sl = pres.addSlide();
    sl.background = { color: C.navy };

    // Left teal accent bar
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 0, w: 0.45, h: 5.625,
      fill: { color: C.teal }, line: { color: C.teal }
    });

    // Subtle grid dots (decorative circles) — bottom-right, below text area
    const dotColor = "1E3A5F";
    for (let col = 0; col < 6; col++) {
      for (let row = 0; row < 3; row++) {
        sl.addShape(pres.shapes.OVAL, {
          x: 6.5 + col * 0.55, y: 4.2 + row * 0.5, w: 0.1, h: 0.1,
          fill: { color: dotColor }, line: { color: dotColor }
        });
      }
    }

    // Eyebrow label
    sl.addText("eScience Institute, University of Washington", {
      x: 0.6, y: 1.05, w: 8.5, h: 0.35,
      fontFace: FONT_BODY, fontSize: 11, color: "94A3B8",
      bold: false, align: "left", margin: 0
    });

    // Main title
    sl.addText("LLMoxie Analytics\nPipeline", {
      x: 0.6, y: 1.55, w: 8.5, h: 1.85,
      fontFace: FONT_TITLE, fontSize: 48, color: C.white,
      bold: true, align: "left", margin: 0
    });

    // Subtitle
    sl.addText("Understanding how LLMs are used\nin research software engineering", {
      x: 0.6, y: 3.5, w: 7.5, h: 1.0,
      fontFace: FONT_BODY, fontSize: 18, color: "94A3B8",
      align: "left", margin: 0
    });

    // Name + date
    sl.addText("Bhagyashree Wagh  ·  May 2026", {
      x: 0.6, y: 4.8, w: 5, h: 0.35,
      fontFace: FONT_BODY, fontSize: 11, color: "475569",
      align: "left", margin: 0
    });
  }

  // ── Slide 2: The Problem ──────────────────────────────────────────────────
  {
    const sl = pres.addSlide();
    sl.background = { color: C.white };

    // Title
    sl.addText("We're logging every LLM call.", {
      x: 0.5, y: 0.35, w: 9, h: 0.65,
      fontFace: FONT_TITLE, fontSize: 34, color: C.navy,
      bold: true, align: "left", margin: 0
    });
    sl.addText("But what are we actually learning from it?", {
      x: 0.5, y: 0.98, w: 9, h: 0.45,
      fontFace: FONT_BODY, fontSize: 18, color: C.teal,
      bold: false, align: "left", margin: 0
    });

    // Thin separator
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y: 1.52, w: 9, h: 0.025,
      fill: { color: C.lightgray }, line: { color: C.lightgray }
    });

    // Three problem cards
    const problems = [
      { icon: FaDatabase, label: "Raw data, no structure",
        desc: "Thousands of individual JSON files with no sessions, no easy querying, no aggregation." },
      { icon: FaUserSecret, label: "Privacy risk",
        desc: "Real user identities appear in raw logs. No anonymization before storage or analysis." },
      { icon: FaChartBar, label: "No visibility",
        desc: "No way to see which models are used most, who's spending what, or when usage spikes." },
    ];

    const iconColors = [C.blue, C.teal, C.blue];
    const bgColors   = ["EFF6FF", "F0FDFA", "EFF6FF"];

    for (let i = 0; i < problems.length; i++) {
      const x = 0.5 + i * 3.1;
      const { icon, label, desc } = problems[i];

      // Card background
      sl.addShape(pres.shapes.RECTANGLE, {
        x, y: 1.7, w: 2.9, h: 3.45,
        fill: { color: bgColors[i] },
        line: { color: C.lightgray, width: 0.75 },
        shadow: { type: "outer", blur: 8, offset: 2, angle: 135, color: "000000", opacity: 0.06 }
      });

      // Icon circle
      sl.addShape(pres.shapes.OVAL, {
        x: x + 1.05, y: 1.95, w: 0.8, h: 0.8,
        fill: { color: iconColors[i] },
        line: { color: iconColors[i] }
      });

      const iconData = await iconPng(icon, "#FFFFFF", 256);
      sl.addImage({ data: iconData, x: x + 1.18, y: 2.08, w: 0.54, h: 0.54 });

      // Label
      sl.addText(label, {
        x: x + 0.15, y: 2.9, w: 2.6, h: 0.5,
        fontFace: FONT_TITLE, fontSize: 14, color: C.navy,
        bold: true, align: "center", margin: 0
      });

      // Description
      sl.addText(desc, {
        x: x + 0.15, y: 3.45, w: 2.6, h: 1.5,
        fontFace: FONT_BODY, fontSize: 12, color: C.mid,
        align: "center", margin: 0
      });
    }
  }

  // ── Slide 3: The Vision ───────────────────────────────────────────────────
  {
    const sl = pres.addSlide();
    sl.background = { color: C.offwhite };

    sl.addText("What this pipeline unlocks", {
      x: 0.5, y: 0.3, w: 9, h: 0.65,
      fontFace: FONT_TITLE, fontSize: 34, color: C.navy,
      bold: true, align: "left", margin: 0
    });
    sl.addText("From raw logs to actionable research intelligence", {
      x: 0.5, y: 0.95, w: 9, h: 0.38,
      fontFace: FONT_BODY, fontSize: 16, color: C.gray,
      align: "left", margin: 0
    });

    const items = [
      { icon: FaLayerGroup, color: C.teal,   bg: "F0FDFA",
        title: "Proper Sessions",
        body:  "Group individual requests into sessions to see full conversation context, not isolated calls." },
      { icon: FaUserSecret, color: C.blue,   bg: "EFF6FF",
        title: "Anonymized Data",
        body:  "Real identities replaced with consistent anonymous IDs. Reversible internally by admins." },
      { icon: MdQueryStats, color: C.tealDark, bg: "F0FDFA",
        title: "Dashboard + Querying",
        body:  "Live Streamlit dashboard with cost, usage, latency, and session analytics across 6 views." },
      { icon: FaBrain,      color: C.blue,   bg: "EFF6FF",
        title: "Fine-tuning Datasets",
        body:  "Export curated interaction data to generate datasets for model fine-tuning." },
      { icon: FaTools,      color: C.teal,   bg: "F0FDFA",
        title: "Evaluate Tool Use",
        body:  "Understand how researchers use tools, skills, and MCP servers in practice." },
    ];

    // 3-2 grid layout — bottom row centered on slide
    const positions = [
      { x: 0.4, y: 1.5 }, { x: 3.5, y: 1.5 }, { x: 6.6, y: 1.5 },
      { x: 1.9, y: 3.45 }, { x: 5.25, y: 3.45 },
    ];

    for (let i = 0; i < items.length; i++) {
      const { x, y } = positions[i];
      const { icon, color, bg, title, body } = items[i];
      const w = 2.85, h = 1.75;

      sl.addShape(pres.shapes.RECTANGLE, {
        x, y, w, h,
        fill: { color: bg },
        line: { color: C.lightgray, width: 0.75 },
        shadow: { type: "outer", blur: 6, offset: 2, angle: 135, color: "000000", opacity: 0.07 }
      });

      // Icon circle (small)
      sl.addShape(pres.shapes.OVAL, {
        x: x + 0.12, y: y + 0.2, w: 0.52, h: 0.52,
        fill: { color }, line: { color }
      });
      const iconData = await iconPng(icon, "#FFFFFF", 256);
      sl.addImage({ data: iconData, x: x + 0.18, y: y + 0.26, w: 0.4, h: 0.4 });

      sl.addText(title, {
        x: x + 0.72, y: y + 0.2, w: 2.05, h: 0.42,
        fontFace: FONT_TITLE, fontSize: 13, color: C.navy,
        bold: true, align: "left", margin: 0
      });
      sl.addText(body, {
        x: x + 0.12, y: y + 0.75, w: 2.62, h: 0.88,
        fontFace: FONT_BODY, fontSize: 11, color: C.mid,
        align: "left", margin: 0
      });
    }
  }

  // ── Slide 4: Architecture ─────────────────────────────────────────────────
  {
    const sl = pres.addSlide();
    sl.background = { color: C.white };

    sl.addText("How it works", {
      x: 0.5, y: 0.3, w: 9, h: 0.65,
      fontFace: FONT_TITLE, fontSize: 34, color: C.navy,
      bold: true, align: "left", margin: 0
    });
    sl.addText("One pipeline, three steps", {
      x: 0.5, y: 0.95, w: 9, h: 0.38,
      fontFace: FONT_BODY, fontSize: 16, color: C.gray,
      align: "left", margin: 0
    });

    // Flow: 3 boxes + arrows
    const boxes = [
      { x: 0.5,  label: "LiteLLM Proxy",   sub: "Logs every API call\nas one JSON file",  color: C.blue },
      { x: 3.55, label: "Azure Data Lake",  sub: "litellm-logs container\nlogs/YYYY/MM/DD/", color: C.teal },
      { x: 6.6,  label: "Streamlit Dashboard", sub: "Reads all data\nRefreshes every 5 min", color: C.tealDark },
    ];

    for (const b of boxes) {
      sl.addShape(pres.shapes.RECTANGLE, {
        x: b.x, y: 1.6, w: 2.75, h: 2.4,
        fill: { color: b.color },
        line: { color: b.color },
        shadow: { type: "outer", blur: 10, offset: 3, angle: 135, color: "000000", opacity: 0.2 }
      });
      sl.addText(b.label, {
        x: b.x + 0.12, y: 1.82, w: 2.51, h: 0.65,
        fontFace: FONT_TITLE, fontSize: 16, color: C.white,
        bold: true, align: "center", margin: 0
      });
      sl.addText(b.sub, {
        x: b.x + 0.12, y: 2.55, w: 2.51, h: 1.25,
        fontFace: FONT_BODY, fontSize: 12.5, color: "B2D8F0",
        align: "center", margin: 0
      });
    }

    // Arrows between boxes — centered vertically on boxes (box center = 1.6 + 1.2 = 2.8)
    for (const ax of [3.2, 6.28]) {
      sl.addShape(pres.shapes.RECTANGLE, {
        x: ax, y: 2.745, w: 0.28, h: 0.1,
        fill: { color: C.gray }, line: { color: C.gray }
      });
      sl.addText("▶", {
        x: ax + 0.14, y: 2.625, w: 0.32, h: 0.35,
        fontFace: FONT_BODY, fontSize: 18, color: C.gray,
        align: "center", margin: 0
      });
    }

    // Bottom annotations
    const notes = [
      { x: 0.5,  text: "Logs every API call\nas one .json file" },
      { x: 3.55, text: "4,900+ files · 1.3 GB\nMay 2026 onwards" },
      { x: 6.6,  text: "Live at azurewebsites.net\nAnonymized · No PII" },
    ];
    for (const n of notes) {
      sl.addText(n.text, {
        x: n.x, y: 4.15, w: 2.75, h: 0.85,
        fontFace: FONT_BODY, fontSize: 11, color: C.mid,
        align: "center", margin: 0
      });
    }
  }

  // ── Slide 5: What We Built ─────────────────────────────────────────────────
  {
    const sl = pres.addSlide();
    sl.background = { color: C.offwhite };

    sl.addText("What's been built", {
      x: 0.5, y: 0.3, w: 9, h: 0.65,
      fontFace: FONT_TITLE, fontSize: 34, color: C.navy,
      bold: true, align: "left", margin: 0
    });

    // Left column: checklist
    const done = [
      "Live dashboard connected to Azure Data Lake",
      "Reads all historical data (4,900+ log files)",
      "6 analytics tabs: Overview, Cost, Time, Users, Sessions, AI Q&A",
      "Reversible PII anonymization (user_001, user_002...)",
      "Reverse mapping stored securely in Azure Key Vault",
      "Auto-refresh every 5 minutes, always current",
      "Deployed on Azure App Service with managed identity",
    ];

    for (let i = 0; i < done.length; i++) {
      const y = 1.1 + i * 0.53;

      // Teal check circle
      sl.addShape(pres.shapes.OVAL, {
        x: 0.5, y: y + 0.04, w: 0.36, h: 0.36,
        fill: { color: C.teal }, line: { color: C.teal }
      });
      const checkData = await iconPng(FaCheckCircle, "#FFFFFF", 256);
      sl.addImage({ data: checkData, x: 0.55, y: y + 0.07, w: 0.26, h: 0.26 });

      sl.addText(done[i], {
        x: 1.0, y: y, w: 5.8, h: 0.44,
        fontFace: FONT_BODY, fontSize: 13.5, color: C.dark,
        align: "left", valign: "middle", margin: 0
      });
    }

    // Right: status card — h:3.7, content sized to fit
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 7.1, y: 1.1, w: 2.4, h: 3.7,
      fill: { color: C.navy },
      line: { color: C.navy },
      shadow: { type: "outer", blur: 12, offset: 3, angle: 135, color: "000000", opacity: 0.25 }
    });
    sl.addText("STATUS", {
      x: 7.1, y: 1.25, w: 2.4, h: 0.35,
      fontFace: FONT_BODY, fontSize: 10, color: C.teal,
      bold: true, align: "center", charSpacing: 2, margin: 0
    });
    sl.addText("Completed", {
      x: 7.1, y: 1.58, w: 2.4, h: 0.5,
      fontFace: FONT_TITLE, fontSize: 18, color: C.teal,
      bold: true, align: "center", margin: 0
    });

    const stats = [
      { val: "4,900+", lbl: "log files" },
      { val: "6",      lbl: "dashboard tabs" },
      { val: "0 PII",  lbl: "exposed" },
      { val: "5 min",  lbl: "refresh cycle" },
    ];
    for (let i = 0; i < stats.length; i++) {
      const sy = 2.25 + i * 0.61;
      sl.addText(stats[i].val, {
        x: 7.1, y: sy, w: 2.4, h: 0.32,
        fontFace: FONT_TITLE, fontSize: 20, color: C.teal,
        bold: true, align: "center", margin: 0
      });
      sl.addText(stats[i].lbl, {
        x: 7.1, y: sy + 0.31, w: 2.4, h: 0.25,
        fontFace: FONT_BODY, fontSize: 11, color: "94A3B8",
        align: "center", margin: 0
      });
    }
  }

  // ── Slide 6: Dashboard Preview ────────────────────────────────────────────
  {
    const sl = pres.addSlide();
    sl.background = { color: C.white };

    sl.addText("The dashboard: 6 views", {
      x: 0.5, y: 0.3, w: 9, h: 0.65,
      fontFace: FONT_TITLE, fontSize: 34, color: C.navy,
      bold: true, align: "left", margin: 0
    });

    const tabs = [
      { name: "Overview",          desc: "Total spend, requests, tokens and error rate at a glance" },
      { name: "Cost Explorer",     desc: "Spend by model, team and user to break down the bill" },
      { name: "Time Intelligence", desc: "Hourly and daily patterns showing when researchers are most active" },
      { name: "Users",             desc: "Per-user spend and activity (anonymized: user_001, user_002, ...)" },
      { name: "Sessions",          desc: "Multi-turn conversations grouped by session ID" },
      { name: "Ask the Data",      desc: "Natural language Q&A powered by Claude" },
    ];

    // 3 left, 3 right — balanced columns
    const cols = [
      [0, 1, 2],
      [3, 4, 5],
    ];
    const colX    = [0.5, 5.3];
    const rowH    = 1.05;
    const startY  = 1.2;

    for (let c = 0; c < 2; c++) {
      for (let r = 0; r < cols[c].length; r++) {
        const idx = cols[c][r];
        const { name, desc } = tabs[idx];
        const x = colX[c];
        const y = startY + r * rowH;

        // Number badge
        sl.addShape(pres.shapes.RECTANGLE, {
          x, y: y + 0.12, w: 0.36, h: 0.36,
          fill: { color: (c === 0 ? C.blue : C.teal) },
          line: { color: (c === 0 ? C.blue : C.teal) }
        });
        sl.addText(String(idx + 1), {
          x, y: y + 0.12, w: 0.36, h: 0.36,
          fontFace: FONT_BODY, fontSize: 12, color: C.white,
          bold: true, align: "center", valign: "middle", margin: 0
        });

        sl.addText(name, {
          x: x + 0.45, y: y + 0.08, w: 4.3, h: 0.3,
          fontFace: FONT_TITLE, fontSize: 13, color: C.navy,
          bold: true, align: "left", margin: 0
        });
        sl.addText(desc, {
          x: x + 0.45, y: y + 0.38, w: 4.3, h: 0.42,
          fontFace: FONT_BODY, fontSize: 11.5, color: C.mid,
          align: "left", margin: 0
        });
      }
    }

    // URL footer
    sl.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 5.22, w: 10, h: 0.4,
      fill: { color: C.navy }, line: { color: C.navy }
    });
    sl.addText("🔗  llmaven-prod-streamlit.azurewebsites.net", {
      x: 0.5, y: 5.25, w: 9, h: 0.32,
      fontFace: FONT_BODY, fontSize: 12, color: "94A3B8",
      align: "center", margin: 0
    });
  }

  // ── Slide 7: What's Next ──────────────────────────────────────────────────
  {
    const sl = pres.addSlide();
    sl.background = { color: C.navy };

    // Dot grid decoration — far right only, away from title text
    const dotColor = "1E3A5F";
    for (let col = 0; col < 4; col++) {
      for (let row = 0; row < 3; row++) {
        sl.addShape(pres.shapes.OVAL, {
          x: 7.0 + col * 0.55, y: 0.5 + row * 0.5, w: 0.1, h: 0.1,
          fill: { color: dotColor }, line: { color: dotColor }
        });
      }
    }

    sl.addText("DIRECTION", {
      x: 0.5, y: 0.55, w: 9, h: 0.35,
      fontFace: FONT_BODY, fontSize: 11, color: C.teal,
      bold: true, charSpacing: 4, align: "left", margin: 0
    });
    sl.addText("What's next", {
      x: 0.5, y: 0.9, w: 9, h: 0.7,
      fontFace: FONT_TITLE, fontSize: 38, color: C.white,
      bold: true, align: "left", margin: 0
    });

    const nexts = [
      { icon: FaDatabase,    color: C.teal, title: "Historical data ingestion",
        body: "Full historical data (80-90 days) being loaded; dashboard will show the complete picture" },
      { icon: FaBrain,       color: C.blue, title: "Fine-tuning dataset generation",
        body: "Export anonymized session data in training format for model fine-tuning" },
      { icon: FaTools,       color: C.teal, title: "Tool and MCP usage evaluation",
        body: "Analyze which tools, skills, and MCP servers researchers rely on most" },
      { icon: MdQueryStats,  color: C.blue, title: "Programmatic access",
        body: "Query API so teams can pull usage data into notebooks and reports" },
    ];

    const nextX  = [0.4, 5.2];
    const nextY0 = 1.65;
    const nextH  = 1.55;  // equal height all cards
    const nextGap = 0.35; // larger gap between rows for breathing room

    for (let i = 0; i < nexts.length; i++) {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const x = nextX[col];
      const y = nextY0 + row * (nextH + nextGap);
      const { icon, color, title, body } = nexts[i];

      sl.addShape(pres.shapes.RECTANGLE, {
        x, y, w: 4.35, h: nextH,
        fill: { color: "1E293B" },
        line: { color: "334155", width: 0.75 },
        shadow: { type: "outer", blur: 8, offset: 2, angle: 135, color: "000000", opacity: 0.4 }
      });

      sl.addShape(pres.shapes.OVAL, {
        x: x + 0.18, y: y + 0.22, w: 0.52, h: 0.52,
        fill: { color }, line: { color }
      });
      const iconData = await iconPng(icon, "#FFFFFF", 256);
      sl.addImage({ data: iconData, x: x + 0.24, y: y + 0.28, w: 0.4, h: 0.4 });

      sl.addText(title, {
        x: x + 0.82, y: y + 0.22, w: 3.45, h: 0.42,
        fontFace: FONT_TITLE, fontSize: 14, color: C.white,
        bold: true, align: "left", margin: 0
      });
      sl.addText(body, {
        x: x + 0.18, y: y + 0.82, w: 4.05, h: 0.65,
        fontFace: FONT_BODY, fontSize: 11.5, color: "CBD5E1",
        align: "left", margin: 0
      });
    }
  }

  // ── Write ────────────────────────────────────────────────────────────────
  const outPath = "/Users/a91885/Desktop/Kyron Medical/llmaven/slides/LLMoxie_Pipeline.pptx";
  await pres.writeFile({ fileName: outPath });
  console.log("✅  Saved:", outPath);
}

build().catch(err => { console.error(err); process.exit(1); });
