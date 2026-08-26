"""
XON Music — Welcome Card Image Generator v2
Beautiful welcome card — no emoji rendering issues.
Uses shapes and text labels instead of emoji characters.
"""
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.request
import math

W, H = 960, 560


def _get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/Arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _fetch_avatar(url: str, size: int = 90) -> Image.Image | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as res:
            data = res.read()
        img = Image.open(io.BytesIO(data)).convert("RGBA").resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
        out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        out.paste(img, mask=mask)
        return out
    except Exception as e:
        print(f"[!] Avatar fetch: {e}")
        return None


def _rr(draw, xy, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def _glow(img: Image.Image, cx, cy, r, color):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(6, 0, -1):
        a = int(30 * i / 6)
        ri = r * i // 3
        d.ellipse((cx - ri, cy - ri, cx + ri, cy + ri), fill=(*color[:3], a))
    img.alpha_composite(layer)


def _draw_star(draw, cx, cy, r, color):
    pts = []
    for i in range(5):
        angle = math.radians(i * 72 - 90)
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        angle2 = math.radians(i * 72 - 90 + 36)
        pts.append((cx + r * 0.4 * math.cos(angle2), cy + r * 0.4 * math.sin(angle2)))
    draw.polygon(pts, fill=color)


def generate_welcome_card(
    username: str,
    discriminator: str = "0000",
    member_number: int = 1,
    joined_ago: str = "a few seconds ago",
    server_name: str = "XON OFFICIAL",
    avatar_url: str = None,
) -> io.BytesIO:

    # ── Canvas ────────────────────────────────────────────────────────
    card = Image.new("RGBA", (W, H), (5, 2, 16, 255))

    # Gradient bg
    grad = ImageDraw.Draw(card)
    for y in range(H):
        t = y / H
        grad.line([(0, y), (W, y)], fill=(int(8+4*t), int(3+1*t), int(22+8*t), 255))

    # Glow orbs
    _glow(card, 110, 100, 320, (110, 30, 200))
    _glow(card, W - 110, 80,  300, (80,  15, 170))
    _glow(card, W // 2, H - 40, 260, (60, 15, 140))

    draw = ImageDraw.Draw(card)

    # Subtle grid
    for x in range(0, W, 45):
        draw.line([(x, 0), (x, H)], fill=(255, 255, 255, 6))
    for y in range(0, H, 45):
        draw.line([(0, y), (W, y)], fill=(255, 255, 255, 6))

    # ── Fonts ─────────────────────────────────────────────────────────
    fXL  = _get_font(58)
    fL   = _get_font(32)
    fM   = _get_font(21)
    fS   = _get_font(15)
    fXS  = _get_font(12)

    # ── TOP BAR: "user joined the server!" ───────────────────────────
    draw.ellipse((W//2 - 72, 13, W//2 - 52, 33), fill=(88, 101, 242))
    draw.text((W//2 - 47, 14), f"@{username}  joined the server!", font=fXS, fill=(190, 160, 255))

    # ── LEFT: XON Circle logo ────────────────────────────────────────
    lx, ly = 88, 150
    # Outer glow ring
    for i in range(3):
        draw.ellipse((lx-72-i*2, ly-72-i*2, lx+72+i*2, ly+72+i*2),
                     outline=(100, 40, 200, 60 - i*20), width=2)
    draw.ellipse((lx-70, ly-70, lx+70, ly+70), outline=(120, 55, 220, 200), width=3)
    draw.ellipse((lx-64, ly-64, lx+64, ly+64), fill=(10, 4, 35, 255))

    # XON text inside circle
    draw.text((lx - 30, ly - 24), "XON",      font=fL,  fill=(210, 170, 255))
    draw.text((lx - 33, ly + 10), "OFFICIAL", font=fXS, fill=(140, 100, 210))

    # ── AVATAR over logo ──────────────────────────────────────────────
    av_size = 88
    if avatar_url:
        avatar = _fetch_avatar(avatar_url, av_size)
        if avatar:
            card.alpha_composite(avatar, (lx - av_size//2, ly - av_size//2))
            draw = ImageDraw.Draw(card)
            # Glow ring around avatar
            for i in range(3):
                draw.ellipse((lx - av_size//2 - 4 - i, ly - av_size//2 - 4 - i,
                              lx + av_size//2 + 4 + i, ly + av_size//2 + 4 + i),
                             outline=(139, 92, 246, 150 - i*40), width=2)
            draw.ellipse((lx - av_size//2 - 3, ly - av_size//2 - 3,
                          lx + av_size//2 + 3, ly + av_size//2 + 3),
                         outline=(180, 130, 255), width=3)

    draw = ImageDraw.Draw(card)

    # ── CENTER: Welcome text ──────────────────────────────────────────
    tx = 190
    draw.text((tx,  58), "WELCOME,",    font=fXL, fill=(255, 255, 255))
    draw.text((tx, 118), f"@{username}!", font=fXL, fill=(175, 105, 255))

    draw.text((tx, 192), "Glad to have you here! You're now part of", font=fM, fill=(155, 135, 200))
    draw.text((tx, 218), f"{server_name}!", font=fM, fill=(200, 140, 255))

    # Divider line
    dy = 249
    draw.line([(tx, dy), (tx + 375, dy)], fill=(100, 50, 200, 90), width=1)
    # X in center of divider
    xc = tx + 188
    draw.line([(xc-6, dy-6), (xc+6, dy+6)], fill=(139, 92, 246), width=2)
    draw.line([(xc+6, dy-6), (xc-6, dy+6)], fill=(139, 92, 246), width=2)

    # ── RIGHT: Big XON text ───────────────────────────────────────────
    fBIG = _get_font(96)
    bx = 638
    # Glow shadow layers
    for i in range(6, 0, -1):
        draw.text((bx + i, 52 + i), "XON", font=fBIG, fill=(80, 10, 160, 40))
    draw.text((bx, 52), "XON", font=fBIG, fill=(195, 130, 255))
    draw.text((bx + 12, 158), "OFFICIAL", font=fM, fill=(145, 85, 225))

    # ── INFO CARDS ───────────────────────────────────────────────────
    n = member_number
    if n % 100 in (11, 12, 13): suf = "th"
    elif n % 10 == 1:  suf = "st"
    elif n % 10 == 2:  suf = "nd"
    elif n % 10 == 3:  suf = "rd"
    else: suf = "th"

    cards_data = [
        ((100, 80, 220), "MEMBER",         f"{username}#{discriminator}"),
        ((6,  182, 212), "JOINED DISCORD", joined_ago),
        ((245,158,  11), "YOU ARE",        f"#{n:03d} member ({n}{suf})"),
    ]
    cw, ch2 = 230, 72
    cy_c = 262
    for i, (col, lbl, val) in enumerate(cards_data):
        cx2 = tx + i * (cw + 14)
        _rr(draw, (cx2, cy_c, cx2 + cw, cy_c + ch2), r=10,
            fill=(16, 7, 42, 220), outline=(*col, 160), width=1)
        # Colored accent line at top of card
        _rr(draw, (cx2, cy_c, cx2 + cw, cy_c + 3), r=2, fill=(*col, 180))
        # Icon circle
        draw.ellipse((cx2+10, cy_c+12, cx2+28, cy_c+30), fill=(*col, 40), outline=(*col, 120), width=1)
        draw.text((cx2 + 14, cy_c + 13), "i", font=fXS, fill=col)
        draw.text((cx2 + 34, cy_c + 12), lbl, font=fXS, fill=(*col,))
        draw.text((cx2 + 10, cy_c + 35), val, font=fS,  fill=(235, 220, 255))

    # ── SERVER RULES BOX ─────────────────────────────────────────────
    ry = 358
    _rr(draw, (tx - 4, ry, W - 22, ry + 140), r=12,
        fill=(11, 5, 34, 215), outline=(60, 28, 120, 140), width=1)

    # "SERVER RULES" header
    draw.text((tx + 4, ry + 8), "SERVER RULES", font=fL, fill=(255, 255, 255))
    draw.line([(tx + 200, ry + 10), (tx + 200, ry + 38)], fill=(80, 40, 150, 150), width=1)
    draw.text((tx + 208, ry + 9), "Please read the rules and enjoy your stay!", font=fXS, fill=(130, 105, 195))

    rules = [
        ("01", "BE RESPECTFUL",  (139, 92,  246)),
        ("02", "NO SPAM",        (6,  182,  212)),
        ("03", "NO TOXICITY",    (239, 68,   68)),
        ("04", "STAY ON TOPIC",  (34,  197,  94)),
        ("05", "FOLLOW RULES",   (245, 158,  11)),
        ("06", "HAVE FUN",       (167, 139, 250)),
    ]
    rw = 97
    rx0 = tx + 4
    ry0 = ry + 52
    for i, (num, nm, col) in enumerate(rules):
        rxr = rx0 + i * (rw + 5)
        _rr(draw, (rxr, ry0, rxr + rw, ry0 + 76), r=8,
            fill=(16, 7, 48, 210), outline=(*col, 130), width=1)
        # Number top-right
        draw.text((rxr + rw - 20, ry0 + 4), num, font=fXS, fill=(*col, 120))
        # Colored icon shape (small filled shape)
        icon_cx = rxr + rw//2
        icon_cy = ry0 + 26
        draw.ellipse((icon_cx - 12, icon_cy - 12, icon_cx + 12, icon_cy + 12),
                     fill=(*col, 35), outline=(*col, 160), width=2)
        # Rule label — split into lines
        words = nm.split()
        if len(words) == 1:
            lines = [words[0]]
        elif len(words) == 2:
            lines = words
        else:
            lines = [" ".join(words[:2]), " ".join(words[2:])]
        for j, line in enumerate(lines[:2]):
            tw_bbox = draw.textbbox((0, 0), line, font=fXS)
            tw = tw_bbox[2] - tw_bbox[0]
            draw.text((rxr + (rw - tw)//2, ry0 + 46 + j * 14), line, font=fXS, fill=col)

    # ── BOTTOM BANNER ─────────────────────────────────────────────────
    bby = H - 52
    draw.rectangle([(0, bby - 4), (W//2 + 60, H)], fill=(7, 3, 22, 235))
    draw.text((18, bby),      "BE ACTIVE, HAVE FUN AND MAKE NEW FRIENDS!", font=fS,  fill=(255, 255, 255))
    draw.text((18, bby + 20), "We hope you  enjoy  your stay.",             font=fS,  fill=(155, 130, 200))
    # Highlight "enjoy"
    bbox_we = draw.textbbox((18, bby+20), "We hope you  ", font=fS)
    ex = 18 + (bbox_we[2] - bbox_we[0])
    draw.text((ex, bby + 20), "enjoy", font=fS, fill=(200, 130, 255))

    draw.text((W//2 + 70, bby - 2),  "Let's build an",      font=fM, fill=(200, 150, 255))
    draw.text((W//2 + 70, bby + 20), "amazing community!",  font=fL, fill=(215, 125, 255))

    # Heart
    draw.text((W - 32, H - 26), "<3", font=fXS, fill=(200, 100, 255))

    # ── OUTER BORDER GLOW ────────────────────────────────────────────
    for i in range(3):
        draw.rounded_rectangle((i, i, W - 1 - i, H - 1 - i),
                                radius=16 - i*2,
                                outline=(90 - i*20, 35, 190 - i*20, 150 - i*40),
                                width=1)

    # ── EXPORT ───────────────────────────────────────────────────────
    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
