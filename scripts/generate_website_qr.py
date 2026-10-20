#!/usr/bin/env python3
"""
Generate high-resolution QR codes for scentedbubble.in
Produces:
1. Standard High-Res PNG (1200x1200px)
2. Transparent Background PNG (1200x1200px)
3. Infinite Resolution Vector SVG
4. Luxury Noir & Gold Packaging Insert Card (1200x1600px)
5. Luxury Champagne Ivory Card (1200x1600px)
6. Square Packaging Sticker Badge (800x800px)
"""

import os
from pathlib import Path
import qrcode
import qrcode.image.svg
from PIL import Image, ImageDraw, ImageFont

TARGET_URL = "https://scentedbubble.in"
DISPLAY_URL = "scentedbubble.in"
BRAND_NAME = "SCENTED BUBBLES"
BRAND_TAGLINE = "ARTISANAL LUXURY FRAGRANCES"
CALL_TO_ACTION = "SCAN TO EXPLORE & SHOP"
SUB_TEXT = "Perfumes • Car Diffusers • Luxury Combos"

# Output directories
ROOT_DIR = Path(__file__).resolve().parent.parent
WEBSITE_QR_DIR = ROOT_DIR / "website_qr"
WEBSITE_QR_DIR.mkdir(parents=True, exist_ok=True)
STATIC_QR_DIR = ROOT_DIR / "app" / "static" / "images" / "qr"
STATIC_QR_DIR.mkdir(parents=True, exist_ok=True)

# Font helper
def get_font(name_or_style: str, size: int):
    candidates = []
    if name_or_style == "serif_bold":
        candidates = ["C:/Windows/Fonts/georgiab.ttf", "C:/Windows/Fonts/timesbd.ttf"]
    elif name_or_style == "serif":
        candidates = ["C:/Windows/Fonts/georgia.ttf", "C:/Windows/Fonts/times.ttf"]
    elif name_or_style == "sans_bold":
        candidates = ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/calibrib.ttf"]
    elif name_or_style == "sans":
        candidates = ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/calibri.ttf"]
    
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def generate_standard_qr(output_path: Path, box_size=30, border=4):
    """Generate high-resolution 300 DPI clean black & white QR code."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(TARGET_URL)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#141312", back_color="#FFFFFF").convert("RGB")
    img.save(output_path, "PNG", dpi=(300, 300))
    print(f"Generated: {output_path} ({img.size[0]}x{img.size[1]})")
    return img

def generate_transparent_qr(output_path: Path, box_size=30, border=4):
    """Generate transparent background QR code for designers (Photoshop/Canva/Figma)."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=box_size,
        border=border,
    )
    qr.add_data(TARGET_URL)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    mod_count = len(matrix)
    total_size = (mod_count + border * 2) * box_size
    img = Image.new("RGBA", (total_size, total_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for r in range(mod_count):
        for c in range(mod_count):
            if matrix[r][c]:
                x0 = (c + border) * box_size
                y0 = (r + border) * box_size
                x1 = x0 + box_size
                y1 = y0 + box_size
                draw.rectangle([x0, y0, x1, y1], fill=(20, 19, 18, 255))
    img.save(output_path, "PNG", dpi=(300, 300))
    print(f"Generated: {output_path} ({img.size[0]}x{img.size[1]})")
    return img

def generate_vector_svg(output_path: Path):
    """Generate infinite resolution SVG vector QR code."""
    factory = qrcode.image.svg.SvgPathImage
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
        image_factory=factory
    )
    qr.add_data(TARGET_URL)
    qr.make(fit=True)
    svg_img = qr.make_image()
    svg_img.save(output_path)
    print(f"Generated Vector SVG: {output_path}")

def draw_bubble_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, color: tuple):
    """Draw the signature Scented Bubbles emblem."""
    # Main ring
    draw.ellipse([(cx - radius, cy - radius), (cx + radius, cy + radius)], outline=color, width=3)
    # Highlight arc
    r_in = int(radius * 0.7)
    draw.arc([(cx - r_in, cy - r_in), (cx + r_in, cy + r_in)], start=200, end=290, fill=color, width=3)
    # Floating satellite bubble 1
    sb1_r = int(radius * 0.22)
    sb1_cx = cx + int(radius * 0.58)
    sb1_cy = cy - int(radius * 0.52)
    draw.ellipse([(sb1_cx - sb1_r, sb1_cy - sb1_r), (sb1_cx + sb1_r, sb1_cy + sb1_r)], fill=color)
    # Floating satellite bubble 2
    sb2_r = int(radius * 0.16)
    sb2_cx = cx - int(radius * 0.55)
    sb2_cy = cy + int(radius * 0.45)
    draw.ellipse([(sb2_cx - sb2_r, sb2_cy - sb2_r), (sb2_cx + sb2_r, sb2_cy + sb2_r)], fill=color)

def generate_luxury_card(output_path: Path, theme="noir"):
    """
    Generate luxury 1200x1600 card (postcard / packaging insert / thank-you card).
    Themes: 'noir' (Dark Luxury Obsidian) or 'ivory' (Champagne Light).
    """
    w, h = 1200, 1600

    if theme == "noir":
        bg_color = (18, 18, 18)
        gold_primary = (212, 175, 85)     # #D4AF55
        gold_bright = (235, 205, 125)     # #EBCD7D
        gold_muted = (175, 140, 75)       # #AF8C4B
        text_light = (245, 243, 238)
        text_muted = (180, 175, 168)
        card_inner_bg = (26, 26, 26)
        qr_bg = (255, 255, 255)
    else:  # ivory
        bg_color = (250, 248, 244)
        gold_primary = (197, 160, 89)     # #C5A059
        gold_bright = (172, 135, 65)      # #AC8741
        gold_muted = (160, 130, 75)
        text_light = (25, 24, 22)
        text_muted = (110, 105, 98)
        card_inner_bg = (255, 255, 255)
        qr_bg = (255, 255, 255)

    img = Image.new("RGB", (w, h), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Luxury Double Border
    m1 = 40
    m2 = 50
    draw.rectangle([(m1, m1), (w - m1, h - m1)], outline=gold_muted, width=2)
    draw.rectangle([(m2, m2), (w - m2, h - m2)], outline=gold_primary, width=1)

    # Decorative Corner Ornaments
    corner_len = 35
    for cx, cy in [(m1, m1), (w - m1, m1), (m1, h - m1), (w - m1, h - m1)]:
        dx = 1 if cx == m1 else -1
        dy = 1 if cy == m1 else -1
        draw.line([(cx, cy), (cx + dx * corner_len, cy)], fill=gold_bright, width=3)
        draw.line([(cx, cy), (cx, cy + dy * corner_len)], fill=gold_bright, width=3)

    # Fonts
    font_brand = get_font("serif_bold", 48)
    font_tagline = get_font("sans", 20)
    font_cta = get_font("sans_bold", 28)
    font_url = get_font("serif_bold", 38)
    font_sub = get_font("sans", 22)
    font_badge = get_font("sans_bold", 18)

    # 1. Header Emblem & Brand
    emblem_y = 180
    draw_bubble_icon(draw, w // 2, emblem_y, 40, gold_bright)

    brand_y = emblem_y + 85
    draw.text((w // 2, brand_y), BRAND_NAME, font=font_brand, fill=gold_bright, anchor="mm")

    tagline_y = brand_y + 48
    draw.text((w // 2, tagline_y), BRAND_TAGLINE, font=font_tagline, fill=text_muted, anchor="mm")

    # Thin decorative divider line with center diamond
    div_y = tagline_y + 45
    div_half_w = 200
    draw.line([(w // 2 - div_half_w, div_y), (w // 2 - 25, div_y)], fill=gold_muted, width=1)
    draw.line([(w // 2 + 25, div_y), (w // 2 + div_half_w, div_y)], fill=gold_muted, width=1)
    # Center diamond
    draw.polygon([
        (w // 2, div_y - 6),
        (w // 2 + 6, div_y),
        (w // 2, div_y + 6),
        (w // 2 - 6, div_y)
    ], fill=gold_bright)

    # 2. QR Code Box
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=18,
        border=3,
    )
    qr.add_data(TARGET_URL)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#141312", back_color="#FFFFFF").convert("RGB")

    # Desired QR size on card
    qr_display_size = 560
    qr_img = qr_img.resize((qr_display_size, qr_display_size), Image.Resampling.LANCZOS)

    # QR Card Container Box
    box_pad = 28
    box_w = qr_display_size + box_pad * 2
    box_h = qr_display_size + box_pad * 2
    box_x = (w - box_w) // 2
    box_y = div_y + 55

    # Card container shadow / border
    draw.rounded_rectangle(
        [(box_x - 3, box_y - 3), (box_x + box_w + 3, box_y + box_h + 3)],
        radius=26,
        outline=gold_muted,
        width=1
    )
    draw.rounded_rectangle(
        [(box_x, box_y), (box_x + box_w, box_y + box_h)],
        radius=24,
        fill=qr_bg,
        outline=gold_primary,
        width=3
    )

    # Paste QR Code
    img.paste(qr_img, (box_x + box_pad, box_y + box_pad))

    # 3. Call to Action Pill / Text
    cta_y = box_y + box_h + 65
    draw.text((w // 2, cta_y), CALL_TO_ACTION, font=font_cta, fill=gold_bright, anchor="mm")

    # URL Button Pill
    pill_w = 480
    pill_h = 74
    pill_x = (w - pill_w) // 2
    pill_y = cta_y + 40

    if theme == "noir":
        draw.rounded_rectangle(
            [(pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h)],
            radius=pill_h // 2,
            fill=(30, 28, 24),
            outline=gold_primary,
            width=2
        )
        url_text_color = gold_bright
    else:
        draw.rounded_rectangle(
            [(pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h)],
            radius=pill_h // 2,
            fill=(245, 240, 230),
            outline=gold_primary,
            width=2
        )
        url_text_color = gold_bright

    draw.text((w // 2, pill_y + pill_h // 2), DISPLAY_URL, font=font_url, fill=url_text_color, anchor="mm")

    # 4. Footer info
    footer_y = pill_y + pill_h + 58
    draw.text((w // 2, footer_y), SUB_TEXT, font=font_sub, fill=text_muted, anchor="mm")

    guarantee_y = footer_y + 42
    draw.text((w // 2, guarantee_y), "Crafted with Botanical Essences • Free Shipping over ₹999", font=font_tagline, fill=gold_muted, anchor="mm")

    bottom_note_y = guarantee_y + 36
    draw.text((w // 2, bottom_note_y), "Handcrafted in Small Batches • Experience Pure Luxury", font=get_font("sans", 16), fill=text_muted, anchor="mm")

    img.save(output_path, "PNG", dpi=(300, 300))
    print(f"Generated Luxury Card ({theme}): {output_path}")
    return img

def generate_square_badge(output_path: Path):
    """Generate compact 800x800 square badge with gold frame, ideal for stickers or web display."""
    size = 800
    img = Image.new("RGB", (size, size), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Frame
    gold = (197, 160, 89)
    draw.rounded_rectangle([(16, 16), (size - 16, size - 16)], radius=28, outline=gold, width=4)
    draw.rounded_rectangle([(24, 24), (size - 24, size - 24)], radius=22, outline=(230, 220, 205), width=1)

    # Top Brand Header
    font_top = get_font("serif_bold", 30)
    font_sub = get_font("sans", 16)
    font_bottom = get_font("sans_bold", 24)

    draw.text((size // 2, 60), BRAND_NAME, font=font_top, fill=(20, 19, 18), anchor="mm")
    draw.text((size // 2, 95), "SCAN TO VISIT STORE", font=font_sub, fill=gold, anchor="mm")

    # QR Code
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=14,
        border=2,
    )
    qr.add_data(TARGET_URL)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#141312", back_color="#FFFFFF").convert("RGB")
    qr_size = 500
    qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
    img.paste(qr_img, ((size - qr_size) // 2, 130))

    # Bottom Pill
    pill_w = 400
    pill_h = 56
    pill_x = (size - pill_w) // 2
    pill_y = size - 100
    draw.rounded_rectangle([(pill_x, pill_y), (pill_x + pill_w, pill_y + pill_h)], radius=28, fill=(20, 19, 18))
    draw.text((size // 2, pill_y + pill_h // 2), DISPLAY_URL, font=font_bottom, fill=(255, 255, 255), anchor="mm")

    img.save(output_path, "PNG", dpi=(300, 300))
    print(f"Generated Square Badge: {output_path}")
    return img

def main():
    print(f"Generating QR Codes for: {TARGET_URL} ...")

    # Destination paths in website_qr folder for organized access
    files_to_generate = [
        # 1. Standard Crisp PNG
        (WEBSITE_QR_DIR / "scentedbubble_qr.png", lambda p: generate_standard_qr(p, box_size=30, border=4)),
        # 2. Transparent Background PNG
        (WEBSITE_QR_DIR / "scentedbubble_qr_transparent.png", lambda p: generate_transparent_qr(p, box_size=30, border=4)),
        # 3. Vector SVG
        (WEBSITE_QR_DIR / "scentedbubble_qr.svg", lambda p: generate_vector_svg(p)),
        # 4. Luxury Noir Card
        (WEBSITE_QR_DIR / "scentedbubble_qr_luxury_card_noir.png", lambda p: generate_luxury_card(p, theme="noir")),
        # 5. Luxury Ivory Card
        (WEBSITE_QR_DIR / "scentedbubble_qr_luxury_card_ivory.png", lambda p: generate_luxury_card(p, theme="ivory")),
        # 6. Square Sticker / Badge
        (WEBSITE_QR_DIR / "scentedbubble_qr_badge.png", lambda p: generate_square_badge(p)),
    ]

    for path, generator in files_to_generate:
        generator(path)
        # Also mirror to static images folder for web use
        static_copy = STATIC_QR_DIR / path.name
        if path.suffix.lower() == ".svg":
            with open(path, "r", encoding="utf-8") as f_in, open(static_copy, "w", encoding="utf-8") as f_out:
                f_out.write(f_in.read())
        else:
            with open(path, "rb") as f_in, open(static_copy, "wb") as f_out:
                f_out.write(f_in.read())
        print(f"Mirrored to static: {static_copy}")

    print("\nAll QR code assets generated successfully!")

if __name__ == "__main__":
    main()
