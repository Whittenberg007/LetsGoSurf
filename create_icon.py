"""Generate a surf wave icon using the Windows Segoe UI Emoji font."""
from PIL import Image, ImageDraw, ImageFont
import os

SIZE = 256
# Render the wave emoji at a large size then resize for the ICO
# Segoe UI Emoji renders at fixed pixel sizes (commonly up to 109px for the color bitmaps)
RENDER_SIZE = 220

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Load Segoe UI Emoji
font_path = "C:/Windows/Fonts/seguiemj.ttf"
try:
    font = ImageFont.truetype(font_path, RENDER_SIZE)
except Exception as e:
    print(f"Failed to load emoji font: {e}")
    raise

# The wave emoji 🌊 = U+1F30A
wave = "\U0001F30A"

# Get the bounding box to center it
bbox = draw.textbbox((0, 0), wave, font=font, embedded_color=True)
text_w = bbox[2] - bbox[0]
text_h = bbox[3] - bbox[1]
x = (SIZE - text_w) // 2 - bbox[0]
y = (SIZE - text_h) // 2 - bbox[1]

# Draw the emoji in color
draw.text((x, y), wave, font=font, embedded_color=True)

# Save as multi-size ICO
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "letsgosurf.ico")
img.save(out_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(f"Saved icon: {out_path}")

preview_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "letsgosurf_preview.png")
img.save(preview_path, format="PNG")
print(f"Saved preview: {preview_path}")
