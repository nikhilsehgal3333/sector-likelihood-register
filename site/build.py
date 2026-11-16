"""Build site/index.html from the generated result files. No number is typed by hand.

    py site/build.py
"""
from __future__ import annotations

import csv
import html
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"
REPO = "https://github.com/nikhilsehgal3333/sector-likelihood-register"

# Which generated section belongs to which question.
GROUPS = [
    ("q1", "1. Method", "Which rule gives each sector a likelihood for one protected right, so "
     "that another person can get the same result?", ["E1", "E3", "E4"]),
    ("q2", "2. Data gaps", "How does a register score a sector with few or no documented cases, "
     "without reading silence as low risk?", ["E2", "E5"]),
    ("q3", "3. AI", "Where can AI collect and code the evidence without loss of traceability?",
     ["A", "B"]),
    ("q4", "4. Integration", "How does the sector score combine with the country register and "
     "the company size?", ["E6"]),
]


def inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


def render(markdown: str) -> str:
    """Convert the small markdown subset that the scripts write."""
    out, lines, i = [], markdown.strip().splitlines(), 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            head, body = rows[0], rows[2:]
            out.append("<div class='scroll'><table><thead><tr>"
                       + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
                                 for r in body) + "</tbody></table></div>")
        elif line.startswith("- "):
            items = []
            while i < len(lines) and (lines[i].startswith("- ") or not lines[i].strip()):
                if lines[i].startswith("- "):
                    items.append(lines[i][2:])
                i += 1
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
        else:
            out.append(f"<p>{inline(line)}</p>")
            i += 1
    return "\n".join(out)


def sections(path: Path) -> dict[str, tuple[str, str]]:
    """Split a result file at '## ' headings. Key = first token of the heading without the dot."""
    found = {}
    for block in re.split(r"\n(?=## )", path.read_text(encoding="utf-8")):
        if block.startswith("## "):
            title, _, body = block.partition("\n")
            title = title[3:].strip()
            found[title.split(".")[0]] = (title, body)
    return found


def main() -> None:
    blocks = {**sections(RESULTS / "RESULTS.md"), **sections(RESULTS / "AI_RESULTS.md")}
    register = list(csv.DictReader(open(RESULTS / "e7_register.csv", encoding="utf-8")))
    visibility = list(csv.DictReader(open(RESULTS / "e2_visibility.csv", encoding="utf-8")))
    data = {
        "register": [[r["nace"], r["label"], int(r["cases_2020_2024"]), float(r["rate_per_100k"]),
                      float(r["rate_low"]), float(r["rate_high"]), int(r["point"]),
                      int(r["point_low"]), int(r["point_high"]), r["confidence"]] for r in register],
        "visibility": [[r["country"], float(r["ratio"])] for r in visibility],
    }
    nav = "".join(f"<a href='#{key}'>{title}</a>" for key, title, _q, _ids in GROUPS)
    body = []
    for key, title, question, ids in GROUPS:
        parts = [f"<section id='{key}'><h2>{title}</h2><p class='question'>{question}</p>"]
        if key == "q2":
            parts.append("<figure><figcaption>Recorded non-fatal accidents for each fatal "
                         "accident, by country (logarithmic axis). If records measured "
                         "occurrence, the bars would be similar.</figcaption>"
                         "<div id='bars'></div></figure>")
        for ident in ids:
            heading, text = blocks[ident]
            parts.append(f"<details open><summary>{inline(heading)}</summary>{render(text)}"
                         "</details>")
        parts.append("</section>")
        body.append("\n".join(parts))
    register_block = blocks["E7"]
    page = (TEMPLATE
            .replace("{{DATE}}", date.today().isoformat())
            .replace("{{REPO}}", REPO)
            .replace("{{NAV}}", nav)
            .replace("{{REGISTER_NOTE}}", render(register_block[1].split("\n\n|")[0]))
            .replace("{{BODY}}", "\n".join(body))
            .replace("{{DATA}}", json.dumps(data, ensure_ascii=False)))
    (ROOT / "site" / "index.html").write_text(page, encoding="utf-8")
    print(f"site/index.html written, {len(page):,} characters")


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sector likelihood register: what does a 1-10 probability mean?</title>
<meta name="description" content="Independent study on public data: how a sector risk register can give a defined 1-10 likelihood for a protected right.">
<style>
:root{--bg:#f7f6f2;--card:#fff;--ink:#1c1f24;--muted:#5b6370;--line:#dcdad2;--accent:#0b5cad;
--soft:#e8f0fa;--p1:#dfe9f3;--p2:#b9d3ea;--p3:#8bb8dc;--p4:#5a97c8;--p5:#3b7bb0;--p6:#2b6398;
--p7:#234f80;--p8:#1d3f69;--p9:#172f52;--p10:#11213c;--warn:#8a5a00;--warnbg:#fff4d6}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--card:#1c2128;--ink:#e8eaed;--muted:#a3abb8;
--line:#2f3640;--accent:#7cb7f2;--soft:#1f2c3b;--warn:#f1c661;--warnbg:#3a2f12}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1040px;margin:0 auto;padding:0 16px 80px}
header{max-width:1040px;margin:0 auto;padding:48px 16px 8px}
h1{font-size:clamp(1.7rem,4vw,2.5rem);line-height:1.15;margin:0 0 12px;letter-spacing:-.01em}
h2{font-size:1.45rem;margin:0 0 4px}
.lead{font-size:1.12rem;max-width:68ch;color:var(--ink)}
.note{background:var(--warnbg);color:var(--warn);border-radius:8px;padding:10px 14px;font-size:.92rem;max-width:80ch}
nav{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);z-index:5}
nav div{max-width:1040px;margin:0 auto;padding:10px 16px;display:flex;gap:18px;overflow-x:auto;white-space:nowrap}
nav a{color:var(--muted);text-decoration:none;font-size:.93rem}
nav a:hover{color:var(--accent)}
section{scroll-margin-top:56px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:24px;margin-top:28px}
.question{color:var(--muted);margin:0 0 16px;max-width:75ch}
.idea{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:16px}
@media (max-width:640px){.idea{grid-template-columns:1fr}}
.idea div{background:var(--soft);border-radius:10px;padding:14px 16px}
.idea b{display:block;margin-bottom:4px}
details{border-top:1px solid var(--line);padding:12px 0}
summary{cursor:pointer;font-weight:600}
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:.9rem;margin:10px 0}
th,td{text-align:left;padding:6px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:.82rem}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
code{background:var(--soft);padding:1px 5px;border-radius:4px;font-size:.88em}
ul{padding-left:20px}li{margin:4px 0}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:14px 0}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:8px;overflow:hidden}
.seg button{border:0;background:transparent;color:var(--ink);padding:8px 14px;font:inherit;cursor:pointer}
.seg button[aria-pressed=true]{background:var(--accent);color:#fff}
input[type=search]{flex:1;min-width:180px;padding:8px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);font:inherit}
.pt{display:inline-block;min-width:30px;text-align:center;border-radius:6px;padding:2px 0;font-weight:700}
.trio{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:12px 0}
.trio>div{border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.trio .big{font-size:2rem;font-weight:800;line-height:1.1}
.trio small{color:var(--muted)}
.conf{font-size:.8rem;padding:1px 8px;border-radius:99px;border:1px solid var(--line);color:var(--muted)}
#regwrap{max-height:520px;overflow:auto;border:1px solid var(--line);border-radius:10px}
#regwrap table{margin:0}#regwrap th{position:sticky;top:0;background:var(--card)}
figure{margin:8px 0 16px}figcaption{color:var(--muted);font-size:.9rem;margin-bottom:8px;max-width:75ch}
.bar{display:grid;grid-template-columns:110px 1fr 56px;gap:8px;align-items:center;font-size:.82rem;margin:2px 0}
.bar i{display:block;height:12px;background:var(--accent);border-radius:3px}
.bar span:last-child{text-align:right;font-variant-numeric:tabular-nums;color:var(--muted)}
footer{color:var(--muted);font-size:.88rem;margin-top:32px}
a{color:var(--accent)}
</style>
</head>
<body>
<header>
<h1>What does a 1-10 "probability" mean in a sector risk register?</h1>
<p class="lead">A sector register for supply chain due diligence must let a user compare sectors on one protected right. A score from 1 to 10 can do that only if the register says what the score measures. This study tests that idea on public data and shows where each step works and where it fails.</p>
<p class="note">Independent study by Nikhil Sehgal. Working draft, built {{DATE}}. It is not a product of Catena-X, BMW Group or Ulm University. It uses public data only. All numbers on this page come from the scripts in the <a href="{{REPO}}">code repository</a>.</p>
</header>
<nav><div><a href="#idea">Core idea</a><a href="#register">Register</a>{{NAV}}<a href="#limits">Limits</a></div></nav>
<main>
<section id="idea">
<h2>Core idea</h2>
<div class="idea">
<div><b>Define the score.</b>Each score needs an event, a unit, a period and a published rule that turns a rate into a point. Without these, the same data give very different scores.</div>
<div><b>Do not count mentions.</b>Recorded and reported cases follow the reporting system. A sector with no reports is not a sector with no risk.</div>
<div><b>Show the uncertainty.</b>Each entry has a range and a confidence grade, so a reader can see if a score comes from much data or from little.</div>
<div><b>Measure the AI.</b>Rules read the fixed parts of a report. A language model reads free text only where rules cannot, and a program tests each quotation.</div>
</div>
</section>

<section id="register">
<h2>A register entry for one right: health and safety</h2>
<p class="question">Select a mapping rule. The rates stay the same. The points change.</p>
<div class="trio" id="trio"></div>
<div class="controls">
<div class="seg" role="group" aria-label="Mapping rule">
<button data-map="log" aria-pressed="true">Fixed log scale</button>
<button data-map="decile" aria-pressed="false">Deciles</button>
<button data-map="linear" aria-pressed="false">Linear</button>
</div>
<input type="search" id="q" placeholder="Search a sector, for example transport" aria-label="Search a sector">
</div>
<p id="mapnote" class="question"></p>
<div id="regwrap"><table><thead><tr><th>NACE</th><th>Sector</th><th class="num">Cases</th><th class="num">Rate per 100,000 (range)</th><th>Point</th><th>Confidence</th></tr></thead><tbody id="reg"></tbody></table></div>
{{REGISTER_NOTE}}
</section>

{{BODY}}

<section id="limits">
<h2>Limits</h2>
<ul>
<li><strong>One right with real rates.</strong> Public rates per NACE division exist for accidents at work. For child labour and forced labour no such rates were found, so the register on this page says nothing about them.</li>
<li><strong>EU data.</strong> The rates describe work in the EU, not global supply chains.</li>
<li><strong>Likelihood only.</strong> Severity is a separate dimension and is not scored.</li>
<li><strong>The four questions are an assumption.</strong> They are the reading of the author from public documents. Nobody at Catena-X, BMW Group or Ulm University confirmed them.</li>
<li><strong>No comparison with other tools.</strong> The scores are not compared with existing sector risk databases or with expert judgement.</li>
<li><strong>Text pipeline.</strong> 14 reports of large German companies for one year, one small language model, and no check of the model output by a person yet.</li>
<li><strong>Stability is not validity.</strong> The tests show that the score is stable over time. They do not show that it is correct.</li>
</ul>
<footer>Data: Eurostat, accidents at work (<code>hsw_n2_01</code>, <code>hsw_n2_02</code>), reuse with attribution. Reports under the German Supply Chain Due Diligence Act are documents of the companies and are not stored in the repository. Code: <a href="{{REPO}}">{{REPO}}</a></footer>
</section>
</main>
<script>
const DATA = {{DATA}};
const rows = DATA.register;
const order = rows.map((r,i)=>i).sort((a,b)=>rows[a][3]-rows[b][3]||rows[a][0].localeCompare(rows[b][0]));
const decile = {}; order.forEach((idx,rank)=>{decile[rows[idx][0]] = 1+Math.floor(10*rank/rows.length)});
const linear = r => Math.max(1, Math.min(10, Math.ceil(10*(1-Math.exp(-r[3]/1e5*250)))));
const point = {log:r=>r[6], decile:r=>decile[r[0]], linear:linear};
const notes = {
 log:"Fixed logarithmic scale: each point is about 3 times the point below. Point 2 starts at 1 in 100,000 workers per year. The scale is a proposal of this study.",
 decile:"Deciles: the sectors are put in order and cut into ten groups of equal size. A sector changes its point when other sectors change.",
 linear:"Linear: 10% steps of the probability that a company with 250 workers has one or more fatal accidents in a year."};
let mode = "log";
const css = getComputedStyle(document.documentElement);
function chip(p){const c=css.getPropertyValue("--p"+p).trim();return `<span class="pt" style="background:${c};color:${p>=4?"#fff":"#11213c"}">${p}</span>`}
function draw(){
 const q = document.getElementById("q").value.trim().toLowerCase();
 const f = point[mode];
 document.getElementById("mapnote").textContent = notes[mode];
 document.getElementById("reg").innerHTML = rows.filter(r=>!q||(r[0]+" "+r[1]).toLowerCase().includes(q)).map(r=>{
  const range = mode==="log" && r[7]!==r[8] ? ` <small>(${r[7]} to ${r[8]})</small>` : "";
  return `<tr><td>${r[0]}</td><td>${r[1]}</td><td class="num">${r[2].toLocaleString("en")}</td><td class="num">${r[3].toFixed(2)} (${r[4].toFixed(2)} to ${r[5].toFixed(2)})</td><td>${chip(f(r))}${range}</td><td><span class="conf">${r[9]}</span></td></tr>`}).join("");
 document.getElementById("trio").innerHTML = ["H49","C22","M70"].map(c=>{const r=rows.find(x=>x[0]===c);
  return `<div><small>${c} ${r[1]}</small><div class="big">${f(r)}</div><small>${r[3].toFixed(2)} fatal accidents per 100,000 workers per year</small></div>`}).join("");
}
document.querySelectorAll(".seg button").forEach(b=>b.addEventListener("click",()=>{mode=b.dataset.map;
 document.querySelectorAll(".seg button").forEach(x=>x.setAttribute("aria-pressed",x===b));draw()}));
document.getElementById("q").addEventListener("input",draw);
draw();
const bars = document.getElementById("bars");
if(bars){const max=Math.log10(Math.max(...DATA.visibility.map(v=>v[1])));
 bars.innerHTML = DATA.visibility.map(v=>`<div class="bar"><span>${v[0]}</span><span><i style="width:${(100*Math.log10(v[1])/max).toFixed(1)}%"></i></span><span>${Math.round(v[1]).toLocaleString("en")}</span></div>`).join("")}
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
