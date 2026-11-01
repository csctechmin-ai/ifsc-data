import json, os, re, sys, urllib.request, xml.etree.ElementTree as ET
CHANNELS = [
    ("UCq_FewAXJeLyneob8EOHyFw", "Wellora Living", "@WelloraLivingT"),
    ("UCa_Vnyt5BaSjU1BV42iaENg", "Finance Deep Dive", "@FinanceDeepDiveind"),
    ("UCGWIdAs_q-1rqKNvU5bYzPA", "MelodyVerse AI", "@MelodyVerseAI-v7y"),
]
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
      "m": "http://search.yahoo.com/mrss/"}
out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
local = sys.argv[2] if len(sys.argv) > 2 else None
videos, ok = [], 0
for cid, name, handle in CHANNELS:
    try:
        if local:
            xml = open(os.path.join(local, cid + ".xml"), "rb").read()
        else:
            req = urllib.request.Request("https://www.youtube.com/feeds/videos.xml?channel_id=" + cid,
                                         headers={"User-Agent": "Mozilla/5.0 ifsctracker-videos"})
            xml = urllib.request.urlopen(req, timeout=30).read()
        root = ET.fromstring(xml); ok += 1
    except Exception as e:
        print("feed failed:", name, e); continue
    for en in root.findall("a:entry", NS):
        vid = (en.findtext("yt:videoId", "", NS) or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid): continue
        link = en.find("a:link", NS)
        href = link.get("href", "") if link is not None else ""
        videos.append({
            "id": vid,
            "title": re.sub(r"\s+", " ", en.findtext("a:title", "", NS)).strip()[:200],
            "published": en.findtext("a:published", "", NS),
            "channel": name, "handle": handle,
            "short": "/shorts/" in href,
            "desc": re.sub(r"\s+", " ", en.findtext("m:group/m:description", "", NS) or "").strip()[:220],
        })
if ok == 0:
    sys.exit("no feeds could be read; keeping the old file")
videos.sort(key=lambda v: v["published"], reverse=True)
os.makedirs(os.path.join(out_dir, "media"), exist_ok=True)
with open(os.path.join(out_dir, "media", "videos.json"), "w", encoding="utf-8") as f:
    json.dump({"channels": [{"name": n, "handle": h} for _, n, h in CHANNELS], "videos": videos[:30]},
              f, ensure_ascii=False, separators=(",", ":"))
print(len(videos), "videos from", ok, "channels")
