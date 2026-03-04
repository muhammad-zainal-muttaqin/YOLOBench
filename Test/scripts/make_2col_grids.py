"""Generate 2-column grid comparison images from individual val folders."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DETECT = BASE / "runs" / "detect"
OUT = BASE / "runs" / "compare_2col"
OUT.mkdir(parents=True, exist_ok=True)

MODELS = [
    ("val",   "combined_y26l_123"),
    ("val2",  "combined_y26l_42"),
    ("val3",  "combined_yv9c_123"),
    ("val4",  "combined_yv9c_42"),
    ("val5",  "damimas_y26l_123"),
    ("val6",  "damimas_y26l_42"),
    ("val7",  "damimas_yv9c_123"),
    ("val8",  "damimas_yv9c_42"),
    ("val9",  "lonsum_y26l_123"),
    ("val10", "lonsum_y26l_42"),
    ("val11", "lonsum_yv9c_123"),
    ("val12", "lonsum_yv9c_42"),
    ("val13", "legacy_yv9c_640"),
    ("val14", "legacy_y26l_1280_damimas"),
]

IMAGE_TYPES = [
    "confusion_matrix_normalized.png",
    "BoxF1_curve.png",
    "BoxPR_curve.png",
    "BoxP_curve.png",
    "BoxR_curve.png",
    "val_batch0_pred.jpg",
    "val_batch1_pred.jpg",
    "val_batch2_pred.jpg",
]

COLS = 2
LABEL_H = 40
PAD = 4


def try_font(size=28):
    for name in ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def make_grid(image_type):
    font = try_font(28)
    entries = []
    for folder, label in MODELS:
        p = DETECT / folder / image_type
        if p.exists():
            entries.append((label, Image.open(p).convert("RGB")))
        else:
            print(f"  SKIP {folder}/{image_type}")
    if not entries:
        return

    w0, h0 = entries[0][1].size
    cell_w, cell_h = w0, h0 + LABEL_H
    rows = (len(entries) + COLS - 1) // COLS
    grid_w = COLS * cell_w + (COLS - 1) * PAD
    grid_h = rows * cell_h + (rows - 1) * PAD
    canvas = Image.new("RGB", (grid_w, grid_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    for i, (label, img) in enumerate(entries):
        col, row = i % COLS, i // COLS
        x = col * (cell_w + PAD)
        y = row * (cell_h + PAD)
        if img.size != (w0, h0):
            img = img.resize((w0, h0), Image.LANCZOS)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        draw.text((x + (cell_w - tw) // 2, y + 4), label, fill=(0, 0, 0), font=font)
        canvas.paste(img, (x, y + LABEL_H))

    out_path = OUT / f"grid2_{image_type}"
    canvas.save(out_path, quality=92)
    print(f"  -> {out_path.name} ({grid_w}x{grid_h})")


if __name__ == "__main__":
    print(f"Output: {OUT}")
    for img_type in IMAGE_TYPES:
        print(f"Processing {img_type}...")
        make_grid(img_type)
    print("Done!")
