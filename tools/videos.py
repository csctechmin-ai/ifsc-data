"""Reads the YouTube channel feeds and writes media/videos.json for the IFSC Tracker home page.

YouTube's public feed sometimes returns 404 or 5xx for a few hours even though the
channel is fine. So each feed is retried, a channel that still fails keeps the videos
it had in the last good file, and the run only fails when the list has not been
refreshed for STALE_HOURS (a real, lasting problem).
"""
import json, os, re, sys, time, datetime, urllib.request, xml.etree.ElementTree as ET

CHANNELS = [
    ("UCq_FewAXJeLyneob8EOHyFw", "Wellora Living", "@WelloraLivingT"),
    ("UCa_Vnyt5BaSjU1BV42iaENg", "Finance Deep Dive", "@FinanceDeepDiveind"),
    ("UCGWIdAs_q-1rqKNvU5bYzPA", "MelodyVerse AI", "@MelodyVerseAI-v7y"),
]
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
      "m": "http://search.yahoo.com/mrss/"}
TRIES, WAIT = 3, 20          # 3 attempts per feed, 20 s then 40 s apart
STALE_HOURS = 48             # fail the run only if no feed has worked for this long
MAX_VIDEOS = 30

out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
local = sys.argv[2] if len(sys.argv) > 2 else None
path = os.path.join(out_dir, "media", "videos.json")
now = datetime.datetime.now(datetime.timezone.utc)

try:
    old = json.load(open(path, encoding="utf-8"))
except Exception:
    old = {}
old_videos = old.get("videos", []) if isinstance(old.get("videos"), list) else []
old_checked = old.get("checked", {}) if isinstance(old.get("checked"), dict) else {}


def fetch(cid):
    if local:
        return open(os.path.join(local, cid + ".xml"), "rb").read()
    url = "https://www.youtube.com/feeds/videos.xml?channel_id=" + cid
    last = None
    for i in range(TRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; ifsctracker-videos)"})
            return urllib.request.urlopen(req, timeout=30).read()
        except Exception as e:
            last = e
            if i < TRIES - 1:
                time.sleep(WAIT * (i + 1))
    raise last


def parse(xml, name, handle):
    root = ET.fromstring(xml)
    items = []
    for en in root.findall("a:entry", NS):
        vid = (en.findtext("yt:videoId", "", NS) or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid):
            continue
        link = en.find("a:link", NS)
        href = link.get("href", "") if link is not None else ""
        items.append({
            "id": vid,
            "title": re.sub(r"\s+", " ", en.findtext("a:title", "", NS)).strip()[:200],
            "published": en.findtext("a:published", "", NS),
            "channel": name, "handle": handle,
            "short": "/shorts/" in href,
            "desc": re.sub(r"\s+", " ", en.findtext("m:group/m:description", "", NS) or "").strip()[:220],
        })
    return items


import html as _html

def get(url):
    last = None
    for i in range(TRIES):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
                "Accept-Language": "en-IN,en;q=0.9", "Cookie": "CONSENT=YES+1; SOCS=CAI"})
            return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            if i < TRIES - 1:
                time.sleep(WAIT * (i + 1))
    raise last


def page_ids(cid, tab):
    """Video IDs listed on a channel tab, newest first (the order YouTube shows them)."""
    text = get(f"https://www.youtube.com/channel/{cid}/{tab}")
    m = re.search(r"ytInitialData\s*=\s*(\{.*?\});\s*</script>", text, re.S)
    blob = m.group(1) if m else text
    ids = []
    for vid in re.findall(r'"videoId":\s*"([A-Za-z0-9_-]{11})"', blob):
        if vid not in ids:
            ids.append(vid)
    return ids[:15]


def watch_info(vid, cid):
    t = get("https://www.youtube.com/watch?v=" + vid)
    if f'"channelId":"{cid}"' not in t and f'"externalChannelId":"{cid}"' not in t:
        return None, "not from this channel" if '"channelId":"' in t else "video page could not be read (YouTube may be asking to sign in)"
    pub = re.search(r'"(?:uploadDate|publishDate)":"([^"]+)"', t) or re.search(r'itemprop="(?:datePublished|uploadDate)" content="([^"]+)"', t)
    title = re.search(r'<meta name="title" content="([^"]*)"', t) or re.search(r"<title>(.*?)(?: - YouTube)?</title>", t, re.S)
    desc = re.search(r'<meta name="description" content="([^"]*)"', t)
    if not pub or not title:
        return None, "no date or title on the video page"
    p = pub.group(1)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p):
        p += "T00:00:00+00:00"
    try:
        p = datetime.datetime.fromisoformat(p.replace("Z", "+00:00")).astimezone(datetime.timezone.utc).isoformat(timespec="seconds")
    except ValueError:
        pass
    return ({"published": p, "title": re.sub(r"\s+", " ", _html.unescape(title.group(1))).strip()[:200],
            "desc": re.sub(r"\s+", " ", _html.unescape(desc.group(1) if desc else "")).strip()[:220]}, "")


MAX_LOOKUPS = 12             # new videos looked up per run (each needs one page fetch)
videos, ok, failed, checked = [], 0, [], dict(old_checked)
known = {v["id"]: v for v in old_videos if isinstance(v, dict) and v.get("id")}
lookups = 0
for cid, name, handle in CHANNELS:
    items, worked = [], False
    try:
        items = parse(fetch(cid), name, handle)
        worked = True
        print(f"{name}: feed has {len(items)} videos, newest {max((v['published'] for v in items), default='-')[:10]}")
    except Exception as e:
        print(f"::warning::YouTube feed for {name} could not be read ({e})")
    if not local:
        # The public feed is sometimes days or weeks behind, so also read the channel's own pages.
        have = {v["id"] for v in items}
        for tab in ("videos", "shorts", "streams"):
            try:
                ids = page_ids(cid, tab)
            except Exception as e:
                print(f"{name}: could not read the {tab} page ({e})"); continue
            worked = worked or bool(ids)
            new = [i for i in ids if i not in have]
            print(f"{name}: {tab} page lists {len(ids)} videos, {len(new)} not in the feed")
            for vid in new:
                have.add(vid)
                if vid in known:
                    items.append(dict(known[vid], short=known[vid].get("short") or tab == "shorts")); continue
                if lookups >= MAX_LOOKUPS:
                    continue
                lookups += 1
                try:
                    info, why = watch_info(vid, cid)
                except Exception as e:
                    info, why = None, str(e)
                if not info:
                    print(f"{name}: skipped video {vid} ({why})")
                else:
                    items.append({"id": vid, "channel": name, "handle": handle, "short": tab == "shorts", **info})
                    print(f"{name}: added {info['published'][:10]} {info['title'][:60]}")
    if worked:
        ok += 1
        checked[handle] = now.isoformat(timespec="seconds")
        videos += items
    else:
        failed.append(name)
        kept = [v for v in old_videos if isinstance(v, dict) and v.get("handle") == handle]
        videos += kept
        print(f"::warning::No source for {name} could be read; kept its {len(kept)} earlier videos")

if ok == 0:
    # Nothing new could be read. Keep the old file unchanged.
    last = max((checked.get(h, "") for _, _, h in CHANNELS), default="")
    try:
        age = (now - datetime.datetime.fromisoformat(last)).total_seconds() / 3600
    except Exception:
        age = None
    if age is not None and age < STALE_HOURS:
        print(f"::notice::YouTube feeds are temporarily unavailable; keeping the current list (last refreshed {age:.0f} hours ago)")
        sys.exit(0)
    if age is None and old_videos:
        # Older files have no "checked" time yet: give YouTube the benefit of the doubt once.
        print("::notice::YouTube feeds are temporarily unavailable; keeping the current list")
        sys.exit(0)
    sys.exit(f"::error::No YouTube feed has worked for over {STALE_HOURS} hours. Check the channel IDs in tools/videos.py.")

seen, unique = set(), []
for v in sorted(videos, key=lambda v: v.get("published", ""), reverse=True):
    if v["id"] in seen:
        continue
    seen.add(v["id"]); unique.append(v)

data = {"channels": [{"name": n, "handle": h} for _, n, h in CHANNELS], "videos": unique[:MAX_VIDEOS], "checked": checked}
# Only rewrite the file when the videos change, so the timestamps alone don't make a commit every run.
if old.get("videos") == data["videos"] and old.get("channels") == data["channels"] and "checked" in old:
    stale_marks = any((now - datetime.datetime.fromisoformat(old_checked.get(h, "1970-01-01T00:00:00+00:00"))).total_seconds() > 86400
                      for _, _, h in CHANNELS if h in checked and h in old_checked)
    if not stale_marks:
        print(len(unique), "videos from", ok, "channels (no change)")
        sys.exit(0)
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
print(len(unique), "videos from", ok, "channels" + (f"; kept earlier videos for {', '.join(failed)}" if failed else ""))
