"""Facebook cover photo for the Taraji Press page.

A calm, airy "news-wire" banner in the Taraji Analytics badge system
(yellow disc, gold Oswald type, EST red accents). Left: the Taraji Press
badge. Right: wordmark + tagline, a small "a Taraji Analytics product"
lockup, and a light 4-step flow -- search every 15 min, collect, filter,
publish to Facebook + Telegram. No boxes; steps sit on a thin connecting
line so the layout can breathe.

Rendered at 3x (Facebook cover is 851x315) and downscaled for crisp type.
"""
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

PRESS = "/Users/mchemmam/Desktop/Projects/GIT/taraji_AI/taraji_AI/branding/taraji_press_transparent.png"
ANALYTICS = "/Users/mchemmam/Desktop/Projects/GIT/tarajianalytics/brand/taraji_logo.png"
FDIR = "/Users/mchemmam/Desktop/Projects/GIT/tarajianalytics/brand/fonts"
OUT = "/Users/mchemmam/Desktop/Projects/GIT/taraji_AI/taraji_AI/branding/taraji_press_fb_cover.png"

W, H = 851, 315
K = 3  # supersample

BG      = (13, 13, 16)
GOLD    = (196, 148, 20)
GOLDLT  = (224, 180, 54)
YELLOW  = (245, 205, 39)
RED     = (224, 39, 37)
WHITE   = (244, 244, 246)
GRAY    = (158, 158, 166)
FB_BLUE = (24, 119, 242)
TG_BLUE = (41, 171, 226)


def u(v):
    return int(round(v * K))


def font(name, size):
    return ImageFont.truetype(f"{FDIR}/{name}", u(size))


OSWALD_B  = "Oswald-Bold.ttf"
OSWALD_SB = "Oswald-SemiBold.ttf"
OSWALD_M  = "Oswald-Medium.ttf"
INTER_SB  = "Inter-SemiBold.ttf"
INTER_M   = "Inter-Medium.ttf"


def fit(img, box):
    r = min(box / img.width, box / img.height)
    return img.resize((max(1, int(img.width * r)), max(1, int(img.height * r))), Image.LANCZOS)


def tracked(d, xy, text, fnt, fill, spacing, center=False):
    sp = u(spacing)
    widths = [d.textlength(c, font=fnt) for c in text]
    total = sum(widths) + sp * (len(text) - 1)
    x, y = (xy[0] - total / 2, xy[1]) if center else xy
    for c, w in zip(text, widths):
        d.text((x, y), c, font=fnt, fill=fill)
        x += w + sp
    return total / K


def w_tracked(d, text, fnt, spacing):
    sp = u(spacing)
    return (sum(d.textlength(c, font=fnt) for c in text) + sp * (len(text) - 1)) / K


# ---------- white line-glyph icons inside a gold disc ----------
def icon_search(d, cx, cy, r):
    lw = max(2, u(r * 0.14))
    rr = u(r * 0.58)
    ox, oy = u(cx - r * 0.16), u(cy - r * 0.16)
    d.ellipse([ox - rr, oy - rr, ox + rr, oy + rr], outline=WHITE, width=lw)
    a = math.radians(45)
    d.line([ox + rr * math.cos(a), oy + rr * math.sin(a), u(cx + r * 0.6), u(cy + r * 0.6)],
           fill=WHITE, width=int(lw * 1.4))


def icon_collect(d, cx, cy, r):
    lw = max(2, u(r * 0.14))
    d.line([u(cx - r * 0.55), u(cy + r * 0.5), u(cx + r * 0.55), u(cy + r * 0.5)], fill=WHITE, width=lw)
    d.line([u(cx - r * 0.55), u(cy + r * 0.15), u(cx - r * 0.55), u(cy + r * 0.5)], fill=WHITE, width=lw)
    d.line([u(cx + r * 0.55), u(cy + r * 0.15), u(cx + r * 0.55), u(cy + r * 0.5)], fill=WHITE, width=lw)
    d.line([u(cx), u(cy - r * 0.55), u(cx), u(cy + r * 0.12)], fill=WHITE, width=lw)
    d.line([u(cx - r * 0.3), u(cy - r * 0.14), u(cx), u(cy + r * 0.14)], fill=WHITE, width=lw)
    d.line([u(cx + r * 0.3), u(cy - r * 0.14), u(cx), u(cy + r * 0.14)], fill=WHITE, width=lw)


def icon_filter(d, cx, cy, r):
    pts = [(cx - r * 0.6, cy - r * 0.5), (cx + r * 0.6, cy - r * 0.5),
           (cx + r * 0.13, cy + r * 0.02), (cx + r * 0.13, cy + r * 0.58),
           (cx - r * 0.13, cy + r * 0.32), (cx - r * 0.13, cy + r * 0.02)]
    d.polygon([(u(x), u(y)) for x, y in pts], fill=WHITE)


def icon_publish(d, cx, cy, r):
    pts = [(cx - r * 0.62, cy - r * 0.58), (cx + r * 0.62, cy),
           (cx - r * 0.62, cy + r * 0.58), (cx - r * 0.28, cy)]
    d.polygon([(u(x), u(y)) for x, y in pts], fill=WHITE)
    d.line([u(cx - r * 0.28), u(cy), u(cx + r * 0.62), u(cy)], fill=YELLOW, width=max(2, u(r * 0.1)))


ICONS = [icon_search, icon_collect, icon_filter, icon_publish]


def platform_badge(d, cx, cy, bsz, color, kind):
    d.rounded_rectangle([u(cx - bsz / 2), u(cy - bsz / 2), u(cx + bsz / 2), u(cy + bsz / 2)],
                        radius=u(bsz * 0.26), fill=color)
    if kind == "fb":
        ff = font(INTER_SB, bsz * 0.92)
        w = d.textlength("f", font=ff)
        d.text((u(cx) - w / 2, u(cy) - u(bsz * 0.6)), "f", font=ff, fill=WHITE)
    else:
        r = bsz * 0.3
        pts = [(cx - r, cy + r * 0.05), (cx + r, cy - r * 0.82),
               (cx + r * 0.05, cy + r * 0.88), (cx - r * 0.22, cy + r * 0.16)]
        d.polygon([(u(x), u(y)) for x, y in pts], fill=WHITE)


# ============================ build ============================
img = Image.new("RGB", (W * K, H * K), BG)

# soft warm glow behind the badge (left), subtle
glow = Image.new("L", (W * K, H * K), 0)
ImageDraw.Draw(glow).ellipse([u(-140), u(-40), u(300), u(360)], fill=60)
glow = glow.filter(ImageFilter.GaussianBlur(u(90)))
img.paste(Image.new("RGB", (W * K, H * K), (44, 36, 12)), (0, 0), glow)

d = ImageDraw.Draw(img)
# minimal thin frame: red hairline edge + gold rule
d.rectangle([0, 0, W * K, u(2)], fill=RED)
d.rectangle([0, u(2), W * K, u(4)], fill=GOLD)
d.rectangle([0, H * K - u(2), W * K, H * K], fill=RED)
d.rectangle([0, H * K - u(4), W * K, H * K - u(2)], fill=GOLD)

# ---------- left: Taraji Press badge, vertically centered ----------
press = fit(Image.open(PRESS).convert("RGBA"), u(158))
img.paste(press, (u(34), u(H / 2) - press.height // 2), press)
d = ImageDraw.Draw(img)

RX = 232          # right-content left edge
RR = W - 40       # right-content right edge

# ---------- top-right: "a Taraji Analytics product" lockup ----------
al = fit(Image.open(ANALYTICS).convert("RGBA"), u(52))
lk1, lk2 = "A TARAJI ANALYTICS", "PRODUCT"
f_lk1 = font(OSWALD_M, 13)
f_lk2 = font(OSWALD_B, 15)
lk_tw = max(w_tracked(d, lk1, f_lk1, 1.2), w_tracked(d, lk2, f_lk2, 1.2))
lk_x = RR - lk_tw
al_x = lk_x - 10 - 52
img.paste(al, (u(al_x), u(40)), al)
d = ImageDraw.Draw(img)
tracked(d, (u(lk_x), u(44)), lk1, f_lk1, GRAY, 1.2)
tracked(d, (u(lk_x), u(64)), lk2, f_lk2, GOLDLT, 1.2)

# ---------- wordmark + tagline ----------
tracked(d, (u(RX), u(42)), "TARAJI PRESS", font(OSWALD_B, 43), YELLOW, 1.5)
tracked(d, (u(RX + 3), u(97)), "AUTOMATED EST NEWS WIRE", font(OSWALD_M, 15.5), GRAY, 4.2)

# ---------- thin divider ----------
d.line([u(RX), u(140), u(RR), u(140)], fill=(52, 52, 60), width=max(1, u(1)))
tracked(d, (u(RX), u(150), ), "HOW IT WORKS", font(OSWALD_SB, 12.5), GOLD, 4.0)

# ---------- light 4-step flow (discs on a connecting line) ----------
steps = [
    ("SEARCH", "every 15 min", False),
    ("COLLECT", "gather articles", False),
    ("FILTER", "verify & rank", False),
    ("PUBLISH", None, True),
]
n = len(steps)
disc_r = 19
row_y = 205
cxs = [RX + (RR - RX) * (i + 0.5) / n for i in range(n)]

# connecting line first (behind discs)
d.line([u(cxs[0]), u(row_y), u(cxs[-1]), u(row_y)], fill=(74, 66, 42), width=max(1, u(1.5)))

f_title = font(OSWALD_SB, 18)
f_sub = font(INTER_M, 11.5)
for i, (title, sub, is_pub) in enumerate(steps):
    cx = cxs[i]
    # small arrowhead midway to next node
    if i < n - 1:
        mx = (cxs[i] + cxs[i + 1]) / 2
        d.polygon([(u(mx + 5), u(row_y)), (u(mx - 2), u(row_y - 4)), (u(mx - 2), u(row_y + 4))], fill=GOLDLT)
    # gold disc + icon
    d.ellipse([u(cx - disc_r), u(row_y - disc_r), u(cx + disc_r), u(row_y + disc_r)], fill=YELLOW)
    d.ellipse([u(cx - disc_r), u(row_y - disc_r), u(cx + disc_r), u(row_y + disc_r)], outline=GOLD, width=u(1.5))
    ICONS[i](d, cx, row_y, disc_r * 0.7)
    # step-number chip
    bx, by, br = cx + disc_r * 0.8, row_y - disc_r * 0.8, 8
    d.ellipse([u(bx - br), u(by - br), u(bx + br), u(by + br)], fill=RED, outline=BG, width=u(1.5))
    nf = font(OSWALD_B, 11)
    nw = d.textlength(str(i + 1), font=nf)
    d.text((u(bx) - nw / 2, u(by) - u(8)), str(i + 1), font=nf, fill=WHITE)
    # title
    tracked(d, (u(cx), u(row_y + 30)), title, f_title, WHITE, 0.5, center=True)
    # subtitle OR platform badges
    if is_pub:
        platform_badge(d, cx - 13, row_y + 62, 19, FB_BLUE, "fb")
        platform_badge(d, cx + 13, row_y + 62, 19, TG_BLUE, "tg")
    else:
        sw = d.textlength(sub, font=f_sub)
        d.text((u(cx) - sw / 2, u(row_y + 55)), sub, font=f_sub, fill=GRAY)

# ---------- downscale ----------
final = img.resize((W, H), Image.LANCZOS)
final.save(OUT)
img.resize((W * 2, H * 2), Image.LANCZOS).save(OUT.replace(".png", "_2x.png"))
print("saved", OUT, final.size)
