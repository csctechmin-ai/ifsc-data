import base64, io, os, re, sys, urllib.request
from PIL import Image, ImageDraw, ImageFont
OUT = sys.argv[1] if len(sys.argv) > 1 else "assets"
SITE = "https://www.ifsctracker.in/"
MARK = "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"
os.makedirs(OUT, exist_ok=True)
mark = Image.open(io.BytesIO(base64.b64decode(MARK))).convert("RGBA")
mark.save(os.path.join(OUT, "mark.png"))
# full logos: copied from the images built into the live theme (header first, footer second)
html = urllib.request.urlopen(urllib.request.Request(SITE, headers={"User-Agent": "Mozilla/5.0 ifsctracker-assets"}), timeout=30).read().decode("utf-8", "replace")
webps = re.findall(r"data:image/webp;base64,([A-Za-z0-9+/=]+)", html)
if len(webps) >= 2:
    for name, b in (("logo.webp", webps[0]), ("logo-white.webp", webps[1])):
        open(os.path.join(OUT, name), "wb").write(base64.b64decode(b))
elif not os.path.exists(os.path.join(OUT, "logo.webp")):
    sys.exit("logo not found on live site")
logo = Image.open(os.path.join(OUT, "logo.webp")).convert("RGBA")
for n in (32, 48, 64):
    mark.resize((n, n), Image.LANCZOS).save(os.path.join(OUT, f"favicon-{n}.png"), optimize=True)
mark.resize((64, 64), Image.LANCZOS).save(os.path.join(OUT, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
def on_white(size, inner):
    c = Image.new("RGB", (size, size), (255, 255, 255)); m = mark.resize((inner, inner), Image.LANCZOS)
    c.paste(m, ((size - inner) // 2, (size - inner) // 2), m); return c
on_white(180, 144).save(os.path.join(OUT, "apple-touch-icon.png"), optimize=True)
on_white(256, 192).save(os.path.join(OUT, "logo-256.png"), optimize=True)
def font(bold, size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else ""),
              "/usr/share/fonts/truetype/liberation/LiberationSans-%s.ttf" % ("Bold" if bold else "Regular")):
        if os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default(size=size)
W, H = 1200, 630
og = Image.new("RGB", (W, H), (19, 49, 47)); d = ImageDraw.Draw(og)
d.rectangle([0, 0, W, 10], fill=(197, 165, 114))
card = Image.new("RGB", (logo.width + 52, logo.height + 28), (255, 255, 255)); card.paste(logo, (26, 14), logo); og.paste(card, (80, 80))
d.text((80, 250), "Bank IFSC Code Finder", font=font(True, 68), fill=(255, 255, 255))
d.text((80, 340), "SBI, HDFC, ICICI, PNB & 1,300+ banks", font=font(False, 40), fill=(197, 165, 114))
d.text((80, 410), "IFSC, MICR, branch address and NEFT / RTGS / IMPS / UPI", font=font(False, 32), fill=(212, 227, 225))
d.text((80, 530), "www.ifsctracker.in", font=font(True, 36), fill=(255, 255, 255))
og.save(os.path.join(OUT, "og-image.jpg"), quality=86, optimize=True, progressive=True)
print("assets:", sorted(os.listdir(OUT)))
