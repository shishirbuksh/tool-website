import yaml, re
from pathlib import Path

d = yaml.safe_load(Path("data/blog.yaml").read_text(encoding="utf-8"))["posts"]
print("posts:", len(d))

# 1. Headings per post
hvals = []
for s, v in d.items():
    body = str(v.get("body_html", ""))
    h1 = len(re.findall(r"<h1", body, re.I))
    h2 = len(re.findall(r"<h2", body, re.I))
    h3 = len(re.findall(r"<h3", body, re.I))
    hvals.append((s, h1, h2, h3))
noh2 = [s for s, a, b, c in hvals if b == 0]
h1in = [s for s, a, b, c in hvals if a > 0]
print("posts with H1 inside body (must be 0, template owns H1):", len(h1in), h1in[:5])
print("posts with zero H2:", len(noh2), noh2[:5])
import statistics
print("avg h2:", round(sum(b for _, _, b, _ in hvals) / len(hvals), 1),
      "avg h3:", round(sum(c for _, _, _, c in hvals) / len(hvals), 1))

# 2. FAQs
flens = [len(v.get("faqs") or []) for v in d.values()]
print("avg faqs:", round(sum(flens) / len(flens), 1), "min:", min(flens),
      "posts<3 faqs:", sum(1 for n in flens if n < 3))
qwords, awords = [], []
for v in d.values():
    for f in v.get("faqs") or []:
        qwords.append(len(str(f.get("q", "")).split()))
        awords.append(len(str(f.get("a", "")).split()))
print("faq q avg words:", round(sum(qwords) / len(qwords), 1),
      "| a avg words:", round(sum(awords) / len(awords), 1),
      "| answers<15 words:", sum(1 for n in awords if n < 15))

# 3. Keywords: long-tail check (>=3 words counts as long-tail)
ktot = sum(len(v.get("keywords") or []) for v in d.values())
lt = sum(1 for v in d.values() for k in (v.get("keywords") or []) if len(str(k).split()) >= 4)
print("keywords total:", ktot, "avg/post:", round(ktot / len(d), 1),
      "long-tail(4+ words):", lt, f"({lt / max(ktot,1)*100:.0f}%)")
short_kw = [(s, k) for s, v in d.items() for k in (v.get("keywords") or []) if len(str(k).split()) <= 2]
print("short keywords (<=2 words):", len(short_kw), short_kw[:8])

# 4. AI boilerplate signals
signals = ["delve", "furthermore", "moreover", "in conclusion", "it is important to note",
           "as an ai", "game-changer", "cutting-edge", "revolutionize", "unlock the power",
           "in today's fast-paced", "boasts", "testament to"]
for sig in signals:
    n = sum(1 for v in d.values() if sig in str(v.get("body_html", "")).lower())
    if n:
        print(f"AI-signal '{sig}': {n} posts")
# repeated openers
openers = {}
for v in d.values():
    m = re.search(r"<p>([^<]{10,80})", str(v.get("body_html", "")))
    if m:
        key = m.group(1).strip().lower()[:40]
        openers[key] = openers.get(key, 0) + 1
dup = sorted(((c, k) for k, c in openers.items() if c > 3), reverse=True)
print("repeated openers (>3 posts):", dup[:5])

# 5. Lists
nobul = [s for s, v in d.items()
         if "<ul" not in str(v.get("body_html", "")).lower() and "<ol" not in str(v.get("body_html", "")).lower()]
print("posts with NO bullets/numbered lists:", len(nobul), nobul[:8])

# 6. Simple-English proxy: avg sentence length + long words
sens, longs, words = [], 0, 0
for v in d.values():
    txt = re.sub(r"<[^>]+>", " ", str(v.get("body_html", "")))
    txt = re.sub(r"\s+", " ", txt)
    parts = [p for p in re.split(r"[.!?]", txt) if p.strip()]
    sens += [len(p.split()) for p in parts]
    ww = txt.split()
    words += len(ww)
    longs += sum(1 for w in ww if len(w) > 12)
print("avg sentence words:", round(sum(sens) / len(sens), 1),
      "| sentences>30 words:", sum(1 for n in sens if n > 30),
      "| 12+ char words:", f"{longs / words * 100:.1f}%")

# 7. Meta/title checks
notitle = [s for s, v in d.items() if not v.get("meta_title")]
nodesc = [s for s, v in d.items() if len(str(v.get("description", "")).split()) < 10]
print("missing meta_title:", len(notitle), "| thin description(<10w):", len(nodesc), nodesc[:5])
