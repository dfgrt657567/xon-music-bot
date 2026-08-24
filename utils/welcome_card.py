"""
XON Music — Welcome Card Image Generator
Generates a beautiful Discord welcome card matching the XON Official style.
"""
from PIL import Image, ImageDraw, ImageFont
import io
import os
import urllib.request

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

W, H = 900, 500


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/Arial.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _fetch_avatar(url: str, size: int = 90) -> Image.Image:
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
        print(f"[!] Avatar fetch failed: {e}")
        img = Image.new("RGBA", (size, size), (60, 20, 120, 255))
        ImageDraw.Draw(img).ellipse((1, 1, size - 2, size - 2), outline=(180, 120, 255), width=3)
        return img


def _rr(draw: ImageDraw.ImageDraw, xy, r, fill=None, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=r, fill=fill, outline=outline, width=width)


def _glow_orb(img: Image.Image, cx: int, cy: int, r: int, color: tuple):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(5, 0, -1):
        alpha = int(35 * i / 5)
        ri = r * i // 2
        d.ellipse((cx - ri, cy - ri, cx + ri, cy + ri), fill=(*color[:3], alpha))
    img.alpha_composite(layer)


def generate_welcome_card(
    username: str,
    discriminator: str = "0000",
    member_number: int = 1,
    joined_ago: str = "a few seconds ago",
    server_name: str = "XON OFFICIAL",
    avatar_url: str = None,
) -> io.BytesIO:
    # ── Background ────────────────────────────────────────────────────
    card = Image.new("RGBA", (W, H), (6, 2, 18, 255))
    draw = ImageDraw.Draw(card)

    # gradient overlay
    for y in range(H):
        t = y / H
        r = int(8 + 4 * t)
        g = int(3 + 2 * t)
        b = int(22 + 10 * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b, 200))

    # Glow orbs
    _glow_orb(card, 100, 90,  260, (120, 40, 200))
    _glow_orb(card, W - 90, 70, 240, (90, 20, 170))
    _glow_orb(card, W // 2, H - 30, 200, (70, 20, 150))

    draw = ImageDraw.Draw(card)

    # Grid
    for x in range(0, W, 40):
        draw.line([(x, 0), (x, H)], fill=(255, 255, 255, 5))
    for y in range(0, H, 40):
        draw.line([(0, y), (W, y)], fill=(255, 255, 255, 5))

    # ── Fonts ─────────────────────────────────────────────────────────
    fT  = _get_font(54)   # Big title
    fH  = _get_font(27)   # Heading
    fB  = _get_font(19)   # Body
    fS  = _get_font(14)   # Small
    fXS = _get_font(12)   # Extra small

    # ── Top bar: "@user joined the server!" ───────────────────────────
    draw.ellipse((W//2 - 66, 14, W//2 - 44, 36), fill=(88, 101, 242))
    draw.text((W//2 - 40, 15), f"@{username} joined the server!", font=fXS, fill=(200, 170, 255))

    # ── Left XON Logo circle ──────────────────────────────────────────
    lx, ly = 82, 145
    draw.ellipse((lx-70, ly-70, lx+70, ly+70), outline=(100, 40, 180, 180), width=3)
    draw.ellipse((lx-63, ly-63, lx+63, ly+63), fill=(10, 4, 32, 255))
    draw.ellipse((lx-58, ly-58, lx+58, ly+58), outline=(70, 30, 140, 100), width=1)
    draw.text((lx - 26, ly - 22), "XON",      font=fH,  fill=(210, 170, 255))
    draw.text((lx - 30, ly + 8),  "OFFICIAL", font=fXS, fill=(140, 100, 220))

    # ── Avatar overlapping logo ───────────────────────────────────────
    av_size = 86
    if avatar_url:
        avatar = _fetch_avatar(avatar_url, av_size)
        card.alpha_composite(avatar, (lx - av_size//2, ly - av_size//2))
        # Ring around avatar
        draw = ImageDraw.Draw(card)
        draw.ellipse((lx - av_size//2 - 3, ly - av_size//2 - 3,
                      lx + av_size//2 + 3, ly + av_size//2 + 3),
                     outline=(139, 92, 246), width=3)

    draw = ImageDraw.Draw(card)

    # ── Center: WELCOME text ──────────────────────────────────────────
    tx = 185
    draw.text((tx, 62),  "👋 WELCOME,",   font=fT, fill=(255, 255, 255))
    draw.text((tx, 118), f"@{username}!", font=fT, fill=(180, 110, 255))

    draw.text((tx, 185), "Glad to have you here! You're now part of", font=fB, fill=(160, 140, 200))
    draw.text((tx, 207), f"{server_name}!", font=fB, fill=(200, 140, 255))

    # Divider
    dy = 237
    draw.line([(tx, dy), (tx + 370, dy)], fill=(100, 50, 200, 100), width=1)
    draw.text((tx + 175, dy - 9), "✕", font=fS, fill=(139, 92, 246))

    # ── Right: Big XON text ───────────────────────────────────────────
    fBIG = _get_font(90)
    bx = 648
    # Shadow layers
    for i in range(5, 0, -1):
        draw.text((bx + i, 55 + i), "XON", font=fBIG, fill=(80, 10, 160, 60))
    draw.text((bx, 55), "XON", font=fBIG, fill=(200, 140, 255))
    draw.text((bx + 8, 152), "OFFICIAL", font=fB, fill=(150, 90, 230))

    # ── Info cards ────────────────────────────────────────────────────
    n = member_number
    if n % 100 in (11, 12, 13):
        suf = "th"
    elif n % 10 == 1: suf = "st"
    elif n % 10 == 2: suf = "nd"
    elif n % 10 == 3: suf = "rd"
    else: suf = "th"

    cards_data = [
        ("👤", "MEMBER",         f"{username}#{discriminator}"),
        ("📅", "JOINED DISCORD", joined_ago),
        ("🏅", "YOU ARE",        f"#{n:03d} member ({n}{suf})"),
    ]
    cw, ch_h = 228, 68
    cy_cards = 256
    for i, (ico, lbl, val) in enumerate(cards_data):
        cx2 = tx + i * (cw + 12)
        _rr(draw, (cx2, cy_cards, cx2 + cw, cy_cards + ch_h),
            r=10, fill=(18, 8, 44, 220), outline=(80, 40, 160, 160), width=1)
        draw.text((cx2 + 10, cy_cards + 7),  f"{ico} {lbl}", font=fXS, fill=(150, 110, 230))
        draw.text((cx2 + 10, cy_cards + 28), val,            font=fS,  fill=(235, 225, 255))

    # ── Server Rules box ──────────────────────────────────────────────
    ry = 343
    _rr(draw, (tx - 4, ry, W - 28, ry + 130), r=12,
        fill=(12, 6, 36, 210), outline=(55, 25, 115, 140), width=1)

    draw.text((tx + 4, ry + 7), "📋 SERVER RULES", font=fH, fill=(255, 255, 255))
    draw.line([(tx + 192, ry + 10), (tx + 193, ry + 34)], fill=(80, 40, 160, 150), width=1)
    draw.text((tx + 200, ry + 7), "Please read the rules and enjoy your stay! 🎵",
              font=fXS, fill=(140, 110, 200))

    rules = [
        ("🛡", "BE RESPECTFUL",  (139, 92,  246)),
        ("💬", "NO SPAM",        (6,  182, 212)),
        ("🚫", "NO TOXICITY",    (239, 68,  68)),
        ("#",  "STAY ON TOPIC",  (34,  197,  94)),
        ("🔒", "FOLLOW RULES",   (245, 158,  11)),
        ("⚡", "HAVE FUN",       (167, 139, 250)),
    ]
    rw = 88
    rx0 = tx + 4
    ry0 = ry + 44
    for i, (ico, nm, col) in enumerate(rules):
        rxr = rx0 + i * (rw + 5)
        _rr(draw, (rxr, ry0, rxr + rw, ry0 + 74), r=8,
            fill=(18, 8, 50, 200), outline=(*col, 130), width=1)
        draw.text((rxr + rw - 18, ry0 + 4), f"0{i+1}", font=fXS, fill=(*col, 110))
        draw.text((rxr + 26, ry0 + 14),     ico,       font=fH,  fill=col)
        # Wrap rule name
        words = nm.split()
        line1 = " ".join(words[:2]) if len(words) > 2 else nm
        line2 = " ".join(words[2:]) if len(words) > 2 else ""
        draw.text((rxr + 3, ry0 + 46), line1, font=fXS, fill=col)
        if line2:
            draw.text((rxr + 3, ry0 + 58), line2, font=fXS, fill=col)

    # ── Bottom banner ─────────────────────────────────────────────────
    bby = H - 42
    _rr(draw, (0, bby - 2, W//2 + 40, H), r=0, fill=(8, 4, 28, 230))
    draw.text((18, bby),      "BE ACTIVE, HAVE FUN AND MAKE NEW FRIENDS!", font=fS,  fill=(255, 255, 255))
    draw.text((18, bby + 18), "We hope you ",   font=fS, fill=(160, 140, 200))
    draw.text((18 + 84, bby + 18), "enjoy",    font=fS, fill=(200, 130, 255))
    draw.text((18 + 126, bby + 18), " your stay. 💜", font=fS, fill=(160, 140, 200))

    draw.text((W//2 + 50, bby - 4), "Let's build an",       font=fB, fill=(200, 150, 255))
    draw.text((W//2 + 50, bby + 14), "amazing community!",  font=fH, fill=(215, 130, 255))

    # ── Border ────────────────────────────────────────────────────────
    draw.rounded_rectangle((0, 0, W - 1, H - 1), radius=16, outline=(90, 40, 190, 180), width=2)

    # ── Export ───────────────────────────────────────────────────────
    buf = io.BytesIO()
    card.convert("RGB").save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf
