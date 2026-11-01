import csv, json, os, re, sys, shutil, datetime
src, names_file, out = sys.argv[1], sys.argv[2], sys.argv[3]
CHUNK, PACK = 2000, 2500
FIX = {"MADHY PRADESH": "MADHYA PRADESH", "UTTARKHAND": "UTTARAKHAND", "ODHISA": "ODISHA",
       "DADAR AND NAGAR HAVELI": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
       "LUDHIANA": "PUNJAB", "DAKSHIN KANNAD": "KARNATAKA", "": "OTHER"}
names = json.load(open(names_file, encoding="utf-8"))
c = lambda s: re.sub(r"\s+", " ", (s or "").strip())
tf = lambda v: 1 if str(v).strip().lower() == "true" else 0
slug = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "na"
rows = []
for r in csv.DictReader(open(src, encoding="utf-8")):
    code = c(r["IFSC"]).upper()
    if not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", code): continue
    st = c(r["STATE"]).upper(); st = FIX.get(st, st)
    rows.append(dict(ifsc=code, bank=c(r["BANK"]) or names.get(code[:4]) or code[:4], branch=c(r["BRANCH"]).upper(),
        centre=c(r["CENTRE"]), district=c(r["DISTRICT"]).upper() or c(r["CITY"]).upper() or "OTHER", state=st,
        address=c(r["ADDRESS"]), contact=c(r["CONTACT"]), city=c(r["CITY"]), micr=c(r["MICR"]), swift=c(r["SWIFT"]),
        imps=tf(r["IMPS"]), rtgs=tf(r["RTGS"]), neft=tf(r["NEFT"]), upi=tf(r["UPI"])))
rows.sort(key=lambda r: r["ifsc"])
by = {}
for r in rows: by.setdefault(r["bank"], []).append(r)
banks = sorted(by, key=lambda b: (-len(by[b]), b.lower()))
bid = {b: i for i, b in enumerate(banks)}
slugs, used = {}, set()
for b in banks:
    s = slug(b); base, n = s, 2
    while s in used: s = f"{base}-{n}"; n += 1
    used.add(s); slugs[b] = s
D = os.path.join(out, "data")
shutil.rmtree(D, ignore_errors=True); os.makedirs(D + "/r"); os.makedirs(D + "/b")
def dump(p, o): json.dump(o, open(p, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
F = ["ifsc", "bank", "branch", "centre", "district", "state", "address", "contact", "city", "micr", "swift", "imps", "rtgs", "neft", "upi"]
starts = []
for i in range(0, len(rows), CHUNK):
    part = rows[i:i + CHUNK]; starts.append(part[0]["ifsc"])
    dump(f"{D}/r/{len(starts)-1}.json", [[bid[r[k]] if k == "bank" else r[k] for k in F] for r in part])
units = []
for b in banks:
    t = {}
    for r in by[b]: t.setdefault(r["state"], {}).setdefault(r["district"], []).append([r["branch"], r["ifsc"], r["city"]])
    for s in t.values():
        for d in s.values(): d.sort()
    if len(by[b]) > PACK: units += [(b, s, dd, sum(map(len, dd.values()))) for s, dd in t.items()]
    else: units.append((b, None, t, len(by[b])))
files, cur, n, loc = [], {}, 0, {}
for b, s, p, k in units:
    if cur and n + k > PACK: files.append(cur); cur, n = {}, 0
    cur[str(bid[b]) if s is None else f"{bid[b]}|{s}"] = p; n += k; loc[(b, s)] = len(files)
if cur: files.append(cur)
for i, f in enumerate(files): dump(f"{D}/b/{i}.json", f)
out_banks = []
for b in banks:
    sts = sorted({r["state"] for r in by[b]})
    e = {"n": b, "s": slugs[b], "c": len(by[b]), "k": by[b][0]["ifsc"][:4]}
    if (b, None) in loc: e["f"] = loc[(b, None)]
    else: e["sf"] = {s: loc[(b, s)] for s in sts}
    e["st"] = {s: sum(1 for r in by[b] if r["state"] == s) for s in sts}
    out_banks.append(e)
dump(f"{D}/banks.json", out_banks)
dump(f"{D}/meta.json", {"count": len(rows), "banks": len(banks), "starts": starts, "updated": datetime.date.today().isoformat()})
print(len(rows), "codes,", len(banks), "banks,", len(starts), "+", len(files), "files")
