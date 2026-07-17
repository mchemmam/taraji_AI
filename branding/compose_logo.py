"""Compose the Taraji Press badge from the standalone Walidha cutout.

Layout follows the Taraji Analytics badge system: yellow disc, arced gold
uppercase name on top, arced subtitle on the bottom, thin red arc accents.
Everything is kept inside the inscribed circle so Facebook/Telegram circular
crops lose nothing. Renders a white-background and a black-background variant;
on black, the character gets a white keyline where he sticks out past the disc
so his dark hair/shoes don't merge into the background.
"""
import math
from collections import Counter
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

MASCOT = "/Users/mchemmam/Desktop/Projects/Taraji Analytics/Logo/New/Gemini_Generated_Image_ymyrukymyrukymyr-Photoroom.png"
FONT = "/Users/mchemmam/Desktop/Projects/GIT/tarajianalytics/brand/fonts/Oswald-Bold.ttf"
OUT = "/private/tmp/claude-501/-Users-mchemmam-Desktop-Projects-GIT-taraji-AI-taraji-AI/ad33d97c-8e4c-4916-a951-966c205c09f5/scratchpad"

S = 1024
CX, CY = S // 2, S // 2
GOLD = (196, 148, 20)
BLACK = (26, 26, 26)

# ---------- load mascot, ensure transparency, crop to content ----------
m = Image.open(MASCOT).convert("RGBA")
if m.getchannel("A").getextrema()[0] == 255:  # no real alpha -> key out near-white
    px = m.load()
    for y in range(m.height):
        for x in range(m.width):
            r, g, b, a = px[x, y]
            if r > 242 and g > 242 and b > 242:
                px[x, y] = (r, g, b, 0)
m = m.crop(m.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox())

# ---------- sample brand colors from the art ----------
reds, yellows = Counter(), Counter()
small = m.resize((200, int(200 * m.height / m.width)))
for r, g, b, a in small.getdata():
    if a < 200:
        continue
    if r > 180 and g < 90 and b < 90:
        reds[(r, g, b)] += 1
    elif r > 200 and g > 150 and b < 90:
        yellows[(r, g, b)] += 1
RED = reds.most_common(1)[0][0]
YELLOW = yellows.most_common(1)[0][0]
print("sampled RED", RED, "YELLOW", YELLOW)


def arc_text(canvas, text, radius, font, fill, top=True):
    probe = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    widths = [probe.textlength(c, font=font) for c in text]
    gap = font.size * 0.22
    a = (-math.pi / 2 if top else math.pi / 2)
    a -= (sum(widths) + gap * (len(text) - 1)) / radius / 2 * (1 if top else -1)
    step_sign = 1 if top else -1
    for ch, w in zip(text, widths):
        half = (w + gap) / 2 / radius * step_sign
        a += half
        x = CX + radius * math.cos(a)
        y = CY + radius * math.sin(a)
        deg = math.degrees(a)
        rot = -(deg + 90) if top else -(deg - 90)
        glyph_img = Image.new("RGBA", (int(w) + 24, font.size + 28), (0, 0, 0, 0))
        ImageDraw.Draw(glyph_img).text((12, 8), ch, font=font, fill=fill)
        glyph_img = glyph_img.rotate(rot, expand=True, resample=Image.BICUBIC)
        canvas.alpha_composite(glyph_img, (int(x - glyph_img.width / 2), int(y - glyph_img.height / 2)))
        a += half


DISC_R = 336
MH = 650
MASCOT_TOP = CY - DISC_R + 24

disc_mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(disc_mask).ellipse([CX - DISC_R, CY - DISC_R, CX + DISC_R, CY + DISC_R], fill=255)
outside_disc = ImageOps.invert(disc_mask)


def build_chars(half_w: int, bot_frac: float, waist_up: bool) -> Image.Image:
    """Mascot + newspaper layer. waist_up crops the mascot's legs so they end
    behind the paper and nothing extends past the disc."""
    chars = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mm = m.resize((int(m.width * MH / m.height), MH), Image.LANCZOS)
    bot_y = MASCOT_TOP + int(MH * bot_frac)
    if waist_up:
        mm = mm.crop((0, 0, mm.width, bot_y + 30 - MASCOT_TOP))
    chars.alpha_composite(mm, (CX - mm.width // 2, MASCOT_TOP))

    pd = ImageDraw.Draw(chars)
    top_y, mid_x = MASCOT_TOP + int(MH * 0.52), CX
    sag = 26
    left_pg = [(mid_x - half_w, top_y + 18), (mid_x, top_y + sag), (mid_x, bot_y + sag), (mid_x - half_w + 10, bot_y + 40)]
    right_pg = [(mid_x, top_y + sag), (mid_x + half_w, top_y + 18), (mid_x + half_w - 10, bot_y + 40), (mid_x, bot_y + sag)]
    for pg in (left_pg, right_pg):
        pd.polygon(pg, fill=(252, 250, 244, 255), outline=BLACK + (255,))
    pd.line([(mid_x, top_y + sag), (mid_x, bot_y + sag)], fill=BLACK + (255,), width=7)
    for pg_sign in (-1, 1):
        x0 = mid_x + pg_sign * 28
        x1 = mid_x + pg_sign * (half_w - 30)
        pd.rectangle([min(x0, x1), top_y + 44, max(x0, x1), top_y + 66], fill=RED + (255,))
        for i in range(4):
            yy = top_y + 92 + i * 30
            pd.line([(min(x0, x1), yy), (max(x0, x1), yy)], fill=(120, 118, 112, 255), width=9)
    return chars


def build(dark: bool, chars: Image.Image) -> Image.Image:
    halo_mask = chars.getchannel("A").point(lambda v: 255 if v > 40 else 0).filter(ImageFilter.MaxFilter(19))
    halo_mask = Image.composite(halo_mask, Image.new("L", (S, S), 0), outside_disc)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([CX - DISC_R, CY - DISC_R, CX + DISC_R, CY + DISC_R], fill=YELLOW + (255,))
    d.ellipse([CX - DISC_R, CY - DISC_R, CX + DISC_R, CY + DISC_R], outline=GOLD + (255,), width=6)
    if dark:  # white keyline where the character leaves the disc
        img.paste((255, 255, 255, 255), (0, 0), halo_mask)
    img.alpha_composite(chars)
    arc_text(img, "TARAJI PRESS", 420, ImageFont.truetype(FONT, 108), GOLD + (255,), top=True)
    arc_text(img, "EST NEWS", 420, ImageFont.truetype(FONT, 66), GOLD + (255,), top=False)
    d2 = ImageDraw.Draw(img)
    for a0, a1 in ((155, 205), (-25, 25)):
        d2.arc([CX - 468, CY - 468, CX + 468, CY + 468], a0, a1, fill=RED + (255,), width=10)
    bg = Image.new("RGBA", (S, S), (12, 12, 12, 255) if dark else (255, 255, 255, 255))
    bg.alpha_composite(img)
    return bg.convert("RGB"), img


chars_full = build_chars(half_w=208, bot_frac=0.88, waist_up=False)
chars_contained = build_chars(half_w=186, bot_frac=0.84, waist_up=True)
white, art = build(dark=False, chars=chars_full)
blackv, _ = build(dark=True, chars=chars_full)
black_contained, _ = build(dark=True, chars=chars_contained)
white.save(f"{OUT}/taraji_press_white.png")
blackv.save(f"{OUT}/taraji_press_black.png")
black_contained.save(f"{OUT}/taraji_press_black_contained.png")
art.save(f"{OUT}/taraji_press_transparent.png")

# ---------- comparison sheet: variants + circular crops + tiny sizes ----------
mask = Image.new("L", (S, S), 0)
ImageDraw.Draw(mask).ellipse([0, 0, S, S], fill=255)
sheet = Image.new("RGB", (1730, 1000), (120, 120, 120))
for col, ver in enumerate((white, blackv, black_contained)):
    sheet.paste(ver.resize((512, 512), Image.LANCZOS), (40 + col * 570, 30))
    circ = ver.copy()
    circ.putalpha(mask)
    big = circ.resize((330, 330), Image.LANCZOS)
    sheet.paste(big, (40 + col * 570, 580), big)
    for size, x in ((80, 420), (40, 520)):
        tiny = circ.resize((size, size), Image.LANCZOS)
        sheet.paste(tiny, (x + col * 570, 600), tiny)
sheet.save(f"{OUT}/taraji_press_preview.png")
print("done")
