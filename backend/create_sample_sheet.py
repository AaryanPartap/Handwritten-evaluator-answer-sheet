import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def generate_sample_sheet():
    output_dir = Path(__file__).resolve().parent / "uploads"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "sample_bfs_answer.jpg"

    # Create lined paper
    width, height = 1200, 1500
    img = Image.new("RGB", (width, height), color=(253, 251, 247))
    draw = ImageDraw.Draw(img)

    # Margin line (red/pink)
    draw.line([(120, 0), (120, height)], fill=(235, 180, 180), width=2)

    # Horizontal ruled lines (light cyan/blue)
    line_spacing = 45
    for y in range(120, height - 80, line_spacing):
        draw.line([(0, y), (width, y)], fill=(215, 230, 245), width=1)

    # Draw header text
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    # Text content representing student's answer
    lines = [
        ("Roll No: 21103042", 140, 80, (40, 40, 40)),
        ("Subject: Data Structures & Algorithms", 500, 80, (40, 40, 40)),
        ("Ans 1:", 60, 130, (20, 20, 180)),
        ("Breadth First Search (BFS) is a fundamental graph traversal algorithm.", 140, 130, (15, 30, 120)),
        ("It starts from a chosen root/source node and explores all neighboring vertices", 140, 175, (15, 30, 120)),
        ("at the current depth level before proceeding to vertices at the next depth level.", 140, 220, (15, 30, 120)),
        ("Key Characteristics:", 140, 265, (15, 30, 120)),
        ("1. Data Structure Used: It uses a Queue (First-In, First-Out / FIFO)", 160, 310, (15, 30, 120)),
        ("   to manage vertices that have been discovered but not fully processed.", 160, 355, (15, 30, 120)),
        ("2. Visited Array: Maintains a boolean array to track visited vertices and prevent loops.", 160, 400, (15, 30, 120)),
        ("3. Application: BFS reliably computes the single-source shortest path in unweighted graphs.", 160, 445, (15, 30, 120)),
        ("Complexities:", 140, 490, (15, 30, 120)),
        ("- Time Complexity: O(V + E) where V is the total vertices and E is total edges.", 160, 535, (15, 30, 120)),
        ("- Auxiliary Space: O(V) for queue storage in worst case.", 160, 580, (15, 30, 120))
    ]

    for text, x, y, color in lines:
        draw.text((x, y), text, fill=color, font=font)

    img.save(out_path, "JPEG", quality=95)
    print(f"Sample answer sheet generated at: {out_path}")

if __name__ == "__main__":
    generate_sample_sheet()
