"""Re-arrange 5x3 canvases (15 cells) into 2-column layout by cropping cells."""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import glob

BASE = Path(__file__).resolve().parent.parent  # Test/
CANVAS_DIR = BASE / "compare_same_test" / "canvases"
OUT_DIR = BASE / "compare_same_test" / "canvases_2col"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Also re-do master_canvas
MASTER = BASE / "compare_same_test" / "master_canvas.jpg"

ORIG_COLS = 5
ORIG_ROWS = 3
NEW_COLS = 2

# Labels in order (5x3 grid, left-to-right top-to-bottom)
LABELS = [
    "Ground Truth",
    "combined_y26l_123", "combined_y26l_42", "combined_yv9c_123", "combined_yv9c_42",
    "damimas_y26l_123", "damimas_y26l_42", "damimas_yv9c_123", "damimas_yv9c_42",
    "lonsum_y26l_123", "lonsum_y26l_42", "lonsum_yv9c_123", "lonsum_yv9c_42",
    "legacy_yv9c_640", "legacy_y26l_1280_damimas",
]

PAD = 4
LABEL_H = 36


def try_font(size=24):
    for name in ["arial.ttf", "Arial.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def extract_cells(img):
    """Extract individual cells from a 5x3 grid image."""
    w, h = img.size
    # The canvas has labels on top of each cell, estimate cell dimensions
    cell_w = w // ORIG_COLS
    cell_h = h // ORIG_ROWS

    cells = []
    for row in range(ORIG_ROWS):
        for col in range(ORIG_COLS):
            x1 = col * cell_w
            y1 = row * cell_h
            x2 = x1 + cell_w
            y2 = y1 + cell_h
            cell = img.crop((x1, y1, x2, y2))
            cells.append(cell)
    return cells, cell_w, cell_h


def build_2col(cells, cell_w, cell_h, font):
    """Build a 2-column grid from extracted cells with new labels."""
    n = len(cells)
    rows = (n + NEW_COLS - 1) // NEW_COLS

    new_cell_h = cell_h  # keep original cell height (already includes label)
    grid_w = NEW_COLS * cell_w + (NEW_COLS - 1) * PAD
    grid_h = rows * new_cell_h + (rows - 1) * PAD

    canvas = Image.new("RGB", (grid_w, grid_h), (0, 0, 0))

    for i, cell in enumerate(cells):
        col = i % NEW_COLS
        row = i // NEW_COLS
        x = col * (cell_w + PAD)
        y = row * (new_cell_h + PAD)
        canvas.paste(cell, (x, y))

    return canvas


def process_canvas(path, font):
    img = Image.open(path).convert("RGB")
    cells, cw, ch = extract_cells(img)
    result = build_2col(cells, cw, ch, font)
    out_path = OUT_DIR / path.name
    result.save(out_path, quality=92)
    print(f"  {path.name} -> {result.size[0]}x{result.size[1]}")


if __name__ == "__main__":
    font = try_font()

    # Process individual canvases
    canvases = sorted(CANVAS_DIR.glob("canvas_*.jpg"))
    print(f"Found {len(canvases)} canvases")
    for c in canvases:
        process_canvas(c, font)

    # Process master canvas too
    if MASTER.exists():
        img = Image.open(MASTER).convert("RGB")
        # Master canvas is 8 rows of 5x3 grids stacked vertically
        # Each sub-grid is for one test image
        w, h = img.size
        sub_h = h // 8  # 8 test images
        print(f"\nMaster canvas: {w}x{h}, sub_h={sub_h}")

        all_subs = []
        for i in range(8):
            sub = img.crop((0, i * sub_h, w, (i + 1) * sub_h))
            cells, cw, ch = extract_cells(sub)
            result = build_2col(cells, cw, ch, font)
            all_subs.append(result)

        # Stack all sub-canvases vertically
        total_w = max(s.size[0] for s in all_subs)
        total_h = sum(s.size[1] for s in all_subs) + (len(all_subs) - 1) * 8
        master_out = Image.new("RGB", (total_w, total_h), (0, 0, 0))
        y_off = 0
        for s in all_subs:
            master_out.paste(s, (0, y_off))
            y_off += s.size[1] + 8

        out_path = OUT_DIR / "master_canvas_2col.jpg"
        master_out.save(out_path, quality=92)
        print(f"  master -> {total_w}x{total_h}")

    print("\nDone!")
