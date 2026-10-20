# Scented Bubbles — Website QR Codes

All QR code assets in this folder point directly to:
👉 **`https://scentedbubble.in`**

Generated with Error Correction Level H (~30% redundancy) for high scan reliability on all Android & iOS devices, even when printed on textured packaging, stickers, or cards.

---

## Files in this Directory

| File Name | Format | Resolution / Size | Recommended Use |
|---|---|---|---|
| `scentedbubble_qr.png` | PNG (300 DPI) | 1110 × 1110 px | High-contrast standard QR for general digital & print use |
| `scentedbubble_qr.svg` | Vector SVG | Infinite (Scalable) | Professional print shops (boxes, banners, brochures, labels) |
| `scentedbubble_qr_transparent.png` | Transparent PNG | 1350 × 1350 px | Graphic design (drag into Canva, Photoshop, Illustrator, Figma) |
| `scentedbubble_qr_luxury_card_noir.png` | PNG (300 DPI) | 1200 × 1600 px | Dark luxury unboxing card / product package insert / thank-you card |
| `scentedbubble_qr_luxury_card_ivory.png` | PNG (300 DPI) | 1200 × 1600 px | Minimalist champagne ivory packaging card |
| `scentedbubble_qr_badge.png` | PNG (300 DPI) | 800 × 800 px | Square sticker / display badge with gold rim & website link pill |

---

## Regeneration

To regenerate or modify these assets at any time, run:
```bash
python scripts/generate_website_qr.py
```
This updates both this `website_qr/` folder and `app/static/images/qr/`.
