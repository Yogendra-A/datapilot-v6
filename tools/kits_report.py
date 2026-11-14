"""
Find out exactly how AgentTune and AuditKIT were used in a Colab notebook.

    python kits_report.py my_notebook.ipynb

Prints a short report (also saved to kits_report.txt). Paste the report into the chat.
"""
import json
import re
import sys

if len(sys.argv) < 2:
    sys.exit("usage: python kits_report.py notebook.ipynb")

nb = json.load(open(sys.argv[1], encoding="utf-8"))
cells = nb.get("cells", [])
KITS = ["agenttune", "auditkit"]
IMPORT_RE = re.compile(r"^\s*(?:from|import)\s+(agenttune|auditkit)[\w\.]*(?:\s+import\s+(.+))?", re.I | re.M)
PIP_RE = re.compile(r"pip\s+install[^\n]*(agenttune|auditkit)[^\n]*", re.I)
SCORE_RE = re.compile(r"(accuracy|score|success|pass rate|reward|f1|exact match|latency)", re.I)


def src(c):
    s = c.get("source", "")
    return "".join(s) if isinstance(s, list) else s


def out_text(c):
    parts = []
    for o in c.get("outputs", []):
        if "text" in o:
            t = o["text"]
            parts.append("".join(t) if isinstance(t, list) else t)
        elif "data" in o and "text/plain" in o["data"]:
            t = o["data"]["text/plain"]
            parts.append("".join(t) if isinstance(t, list) else t)
    return "\n".join(parts)


lines = []
P = lines.append
P(f"notebook: {sys.argv[1]} | cells: {len(cells)}")

summary = {k: {"import_cells": [], "names": set(), "mention_cells": []} for k in KITS}
pips = []
for i, c in enumerate(cells):
    s = src(c)
    for m in IMPORT_RE.finditer(s):
        k = m.group(1).lower()
        summary[k]["import_cells"].append(i)
        if m.group(2):
            summary[k]["names"].update(n.strip() for n in m.group(2).split(","))
    for k in KITS:
        if k in s.lower() or k in out_text(c).lower():
            summary[k]["mention_cells"].append(i)
    for m in PIP_RE.finditer(s):
        pips.append((i, m.group(0).strip()[:160]))

P("\n== SUMMARY ==")
for k in KITS:
    d = summary[k]
    P(f"{k}: imported in cells {d['import_cells'][:15]} | names imported: {sorted(d['names'])[:20]} | "
      f"mentioned in {len(d['mention_cells'])} cells")
P("pip install lines: " + (str(pips[:6]) if pips else "none"))

# attribute / call usage like agenttune.something(...)
P("\n== API USED (module.attribute) ==")
for k in KITS:
    found = {}
    for c in cells:
        for m in re.finditer(rf"\b{k}(?:\.\w+)+", src(c), re.I):
            found[m.group(0)] = found.get(m.group(0), 0) + 1
    P(f"{k}: " + (", ".join(f"{a} x{n}" for a, n in sorted(found.items(), key=lambda x: -x[1])[:15]) or "none"))

# show the cells that import a kit (source head + output head)
P("\n== CELLS THAT IMPORT A KIT (first 8) ==")
shown = sorted({i for k in KITS for i in summary[k]["import_cells"]})[:8]
for i in shown:
    s = src(cells[i]).splitlines()
    P(f"\n--- cell {i} source (first 18 lines) ---")
    for ln in s[:18]:
        P("  " + ln[:150])
    o = out_text(cells[i]).strip()
    if o:
        P(f"--- cell {i} output (first 500 chars) ---")
        P("  " + o[:500].replace("\n", "\n  "))

# any output near an AuditKIT mention that looks like a score
P("\n== OUTPUTS WITH SCORE-LIKE WORDS IN CELLS MENTIONING AuditKIT (first 6) ==")
count = 0
for i in summary["auditkit"]["mention_cells"]:
    o = out_text(cells[i])
    if SCORE_RE.search(o):
        P(f"\n--- cell {i} ---")
        P("  " + o.strip()[:600].replace("\n", "\n  "))
        count += 1
        if count >= 6:
            break
if count == 0:
    P("none found")

report = "\n".join(lines)
open("kits_report.txt", "w", encoding="utf-8").write(report)
print(report[:9000])
print("\n[saved to kits_report.txt]")