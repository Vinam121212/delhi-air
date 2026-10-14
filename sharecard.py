"""Instagram/WhatsApp-ready AQI image (1080×1350) drawn with Pillow."""
import io

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1350


def _font(size):
    return ImageFont.load_default(size=size)     # Pillow's bundled scalable font — no downloads needed


def _rgb(hex_colour):
    h = hex_colour.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _text(d, xy, s, size, fill=(255, 255, 255), anchor="la", bold=False):
    d.text(xy, s, font=_font(size), fill=fill, anchor=anchor, stroke_width=1 if bold and size >= 40 else 0, stroke_fill=fill)


def make_card(*, location, place, aqi, standard, category, colour, pm25, cigarettes, main_pollutant, time_str,
              url, station=None, advice=""):
    col = _rgb(colour)
    top, bottom = _mix(col, (8, 14, 40), .55), (6, 10, 28)
    strip = Image.new("RGB", (1, H))                         # vertical gradient, stretched to full width
    for y in range(H):
        strip.putpixel((0, y), _mix(top, bottom, y / H))
    img = strip.resize((W, H))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse((W - 620, -260, W + 240, 600), fill=col + (150,))
    g.ellipse((-300, H - 520, 420, H + 200), fill=(56, 189, 248, 70))
    img = Image.alpha_composite(img.convert("RGBA"), glow.filter(ImageFilter.GaussianBlur(120)))

    # glass panel
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    p = ImageDraw.Draw(panel)
    p.rounded_rectangle((60, 300, W - 60, 1150), radius=60, fill=(255, 255, 255, 34), outline=(255, 255, 255, 90), width=3)
    for i in range(3):                                       # stat tiles (translucent, so drawn on the overlay)
        cx = 120 + 280 * i + 140
        p.rounded_rectangle((cx - 125, 850, cx + 125, 1030), radius=34, fill=(255, 255, 255, 30), outline=(255, 255, 255, 60), width=2)
    img = Image.alpha_composite(img, panel)
    d = ImageDraw.Draw(img)

    # brand
    _text(d, (72, 92), "AQI", 54, bold=True)
    w_aqi = d.textlength("AQI", font=_font(54)) + 4
    _text(d, (72 + w_aqi, 92), "fy", 54, fill=(125, 211, 252))
    w_fy = d.textlength("fy", font=_font(54)) + 2
    _text(d, (72 + w_aqi + w_fy, 92), "Me", 54, fill=(74, 222, 128), bold=True)
    _text(d, (W - 72, 104), time_str, 30, fill=(220, 230, 245), anchor="ra")

    _text(d, (W // 2, 205), location, 64, anchor="mm", bold=True)
    _text(d, (W // 2, 262), place.upper(), 28, fill=(210, 222, 240), anchor="mm")

    # big number + category
    _text(d, (W // 2, 520), f"{aqi:.0f}", 260, fill=col, anchor="mm", bold=True)
    _text(d, (W // 2, 668), f"{standard} AQI", 30, fill=(215, 225, 240), anchor="mm")
    pill_w = d.textlength(category, font=_font(46)) + 90
    d.rounded_rectangle((W // 2 - pill_w / 2, 712, W // 2 + pill_w / 2, 792), radius=40, fill=col)
    _text(d, (W // 2, 752), category, 46, fill=(15, 20, 35), anchor="mm")

    # stats row
    stats = [("PM2.5", f"{pm25:.0f}", "ug/m3"), ("Cigarettes", f"{cigarettes:.1f}", "per day"), ("Main", main_pollutant, "pollutant")]
    for i, (k, v, u) in enumerate(stats):
        cx = 120 + 280 * i + 140
        _text(d, (cx, 892), k.upper(), 26, fill=(205, 218, 238), anchor="mm")
        _text(d, (cx, 952), v, 58, anchor="mm", bold=True)
        _text(d, (cx, 1004), u, 24, fill=(205, 218, 238), anchor="mm")
    if advice:
        _text(d, (W // 2, 1092), advice[:60], 30, fill=(235, 242, 250), anchor="mm")

    if station:
        _text(d, (W // 2, 1200), f"Measured at {station}", 28, fill=(205, 218, 238), anchor="mm")
    _text(d, (W // 2, 1262), "Check your air at", 28, fill=(205, 218, 238), anchor="mm")
    _text(d, (W // 2, 1306), url, 38, fill=(125, 211, 252), anchor="mm")

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()
