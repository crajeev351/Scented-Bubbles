import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

static_img_dir = Path("app/static/images")
static_img_dir.mkdir(parents=True, exist_ok=True)

def create_styled_image(path: Path, size: tuple, bg_color: tuple, text: str, subtext: str = "", accent_color: tuple = (212, 175, 55)):
    img = Image.new("RGB", size, color=bg_color)
    draw = ImageDraw.Draw(img)
    w, h = size

    # Draw luxury border
    border_margin = int(min(w, h) * 0.04)
    draw.rectangle(
        [(border_margin, border_margin), (w - border_margin, h - border_margin)],
        outline=accent_color,
        width=2
    )

    # Draw decorative subtle bubbles/circles
    draw.arc([w * 0.1, h * 0.1, w * 0.3, h * 0.3], 0, 360, fill=(240, 230, 220), width=1)
    draw.arc([w * 0.7, h * 0.6, w * 0.9, h * 0.8], 0, 360, fill=(240, 230, 220), width=1)
    draw.arc([w * 0.8, h * 0.15, w * 0.92, h * 0.27], 0, 360, fill=(240, 230, 220), width=1)

    # Draw simple bottle silhouette in center
    cx, cy = w // 2, h // 2
    bw, bh = int(w * 0.22), int(h * 0.35)
    cap_w, cap_h = int(bw * 0.4), int(bh * 0.18)

    # Bottle body
    draw.rounded_rectangle(
        [(cx - bw // 2, cy - bh // 2 + cap_h), (cx + bw // 2, cy + bh // 2)],
        radius=12,
        outline=accent_color,
        width=2,
        fill=(255, 255, 255)
    )
    # Bottle cap
    draw.rectangle(
        [(cx - cap_w // 2, cy - bh // 2), (cx + cap_w // 2, cy - bh // 2 + cap_h)],
        fill=accent_color
    )

    # Draw Text
    draw.text((cx, cy + bh // 2 + 25), text, fill=(40, 40, 40), anchor="mm")
    if subtext:
        draw.text((cx, cy + bh // 2 + 50), subtext, fill=(110, 110, 110), anchor="mm")

    # Watermark
    draw.text((cx, h - border_margin - 20), "SCENTED BUBBLES", fill=accent_color, anchor="mm")

    img.save(path, "WEBP", quality=90)
    print(f"Generated: {path}")

def generate_banner(path: Path, title: str, subtitle: str, bg_color: tuple):
    w, h = 1200, 480
    img = Image.new("RGB", (w, h), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Gradient-like luxury overlay
    draw.rectangle([(0, 0), (w, h)], outline=(212, 175, 55), width=3)
    # Bubbles
    for r, cx, cy in [(40, 150, 100), (70, 220, 180), (30, 1050, 350), (90, 950, 200), (50, 600, 80)]:
        draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], outline=(235, 215, 180), width=2)

    # Texts
    draw.text((w // 2, h // 2 - 40), "SCENTED BUBBLES", fill=(180, 140, 40), anchor="mm")
    draw.text((w // 2, h // 2 + 10), title, fill=(30, 30, 30), anchor="mm")
    draw.text((w // 2, h // 2 + 60), subtitle, fill=(90, 85, 80), anchor="mm")

    img.save(path, "WEBP", quality=88)
    print(f"Generated Banner: {path}")

def generate_qr(path: Path):
    w, h = 400, 400
    img = Image.new("RGB", (w, h), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Draw QR frame
    draw.rectangle([(20, 20), (w - 20, h - 20)], outline=(30, 30, 30), width=4)
    # Finder corners
    for x, y in [(50, 50), (270, 50), (50, 270)]:
        draw.rectangle([(x, y), (x + 80, y + 80)], outline=(30, 30, 30), width=6)
        draw.rectangle([(x + 20, y + 20), (x + 60, y + 60)], fill=(30, 30, 30))

    # Grid imitation
    for i in range(150, 250, 20):
        for j in range(150, 250, 20):
            if (i + j) % 40 == 0:
                draw.rectangle([(i, j), (i + 14, j + 14)], fill=(30, 30, 30))

    draw.text((w // 2, h - 45), "UPI ID: scentedbubbles@okaxis", fill=(50, 50, 50), anchor="mm")
    draw.text((w // 2, 35), "SCENTED BUBBLES PAY", fill=(212, 175, 55), anchor="mm")
    img.save(path, "PNG")
    print(f"Generated QR: {path}")

# Run generation
create_styled_image(static_img_dir / "placeholder_perfume.webp", (600, 600), (250, 248, 245), "Artisanal Perfume", "Scented Bubbles")
create_styled_image(static_img_dir / "perfume_velvet_oud.webp", (600, 600), (245, 240, 235), "Velvet Oud Royal", "Eau de Parfum", (180, 120, 50))
create_styled_image(static_img_dir / "perfume_coastal_breeze.webp", (600, 600), (240, 246, 250), "Coastal Sea Breeze", "Fresh Aquatic", (70, 140, 180))
create_styled_image(static_img_dir / "perfume_cafe_vanille.webp", (600, 600), (248, 243, 238), "Café Vanille Noir", "Gourmand Spicy", (140, 90, 60))
create_styled_image(static_img_dir / "perfume_iris_musk.webp", (600, 600), (250, 247, 252), "Iris & White Musk", "Floral Powdery", (150, 120, 170))

create_styled_image(static_img_dir / "car_amber_noir.webp", (600, 600), (246, 242, 238), "Amber Noir Car Diffuser", "Wooden Hanging Diffuser", (160, 110, 40))
create_styled_image(static_img_dir / "car_citrus_clip.webp", (600, 600), (252, 250, 240), "Citrus Zest & Eucalyptus", "Vent Clip Fragrance", (190, 150, 30))

create_styled_image(static_img_dir / "placeholder_combo.webp", (600, 600), (248, 246, 242), "Curated Combo Pack", "Fragrance Duo", (200, 160, 60))
create_styled_image(static_img_dir / "combo_royal_duo.webp", (600, 600), (245, 240, 238), "The Royal Duo", "Velvet Oud + Car Diffuser", (180, 120, 50))
create_styled_image(static_img_dir / "combo_fresh_horizons.webp", (600, 600), (240, 248, 248), "Fresh Horizons Set", "Sea Breeze + Citrus Clip", (60, 150, 150))
create_styled_image(static_img_dir / "combo_car_duo.webp", (600, 600), (250, 248, 240), "Connoisseur's Car Duo", "Twin Car Diffusers", (180, 140, 40))

generate_banner(static_img_dir / "banner_hero_1.webp", "ARTISANAL FINE FRAGRANCES", "Handcrafted in Small Batches • Pure Botanical Extracts", (248, 245, 240))
generate_banner(static_img_dir / "banner_hero_2.webp", "CURATED FRAGRANCE COMBOS", "Perfume & Luxury Car Diffusers • Save up to 30%", (244, 247, 245))
generate_banner(static_img_dir / "banner_hero_3.webp", "COMPLIMENTARY SHIPPING", "Free Express Delivery on Orders Over ₹999", (248, 244, 246))
generate_banner(static_img_dir / "placeholder_banner.webp", "SCENTED BUBBLES", "Softness, Freshness and Luxury", (248, 246, 242))

generate_qr(static_img_dir / "placeholder_upi_qr.png")
print("All placeholder images generated successfully!")
