"""One-time script to generate a surf wave icon for the desktop shortcut."""
from PIL import Image, ImageDraw
import math
import os

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Sky/background gradient (teal to deep blue)
for y in range(SIZE):
    t = y / SIZE
    r = int(14 + (4 - 14) * t)
    g = int(165 + (30 - 165) * t)
    b = int(233 + (120 - 233) * t)
    draw.line([(0, y), (SIZE, y)], fill=(r, g, b, 255))

# Rounded square mask (app icon style)
mask = Image.new("L", (SIZE, SIZE), 0)
mask_draw = ImageDraw.Draw(mask)
radius = 48
mask_draw.rounded_rectangle([(0, 0), (SIZE, SIZE)], radius=radius, fill=255)

# Sun circle
sun_center = (190, 80)
sun_radius = 28
draw.ellipse(
    [sun_center[0] - sun_radius, sun_center[1] - sun_radius,
     sun_center[0] + sun_radius, sun_center[1] + sun_radius],
    fill=(255, 220, 100, 255),
)

# Main breaking wave - curl shape
wave_color = (255, 255, 255, 255)
wave_dark = (30, 100, 180, 255)
wave_mid = (80, 170, 220, 255)

# Draw wave body (big arc from left sweeping up and over)
# Use polygon points to approximate a wave curl
wave_points = []
# Top of wave (curl)
for i in range(50):
    t = i / 49
    x = 40 + t * 180
    y = 170 - math.sin(t * math.pi) * 90
    wave_points.append((x, y))
# Inside of curl (bottom edge back to start)
for i in range(50):
    t = i / 49
    x = 220 - t * 180
    # Curved underside
    y = 180 + math.sin(t * math.pi) * 20
    wave_points.append((x, y))

draw.polygon(wave_points, fill=wave_mid)

# Wave crest/foam (white band on top)
crest_points = []
for i in range(50):
    t = i / 49
    x = 40 + t * 180
    y = 170 - math.sin(t * math.pi) * 90
    crest_points.append((x, y))
for i in range(50):
    t = (49 - i) / 49
    x = 40 + t * 180
    y = 170 - math.sin(t * math.pi) * 90 + 18
    crest_points.append((x, y))

draw.polygon(crest_points, fill=wave_color)

# Inner curl shadow (darker blue inside the barrel)
curl_points = []
for i in range(30):
    t = i / 29
    x = 90 + t * 100
    y = 150 - math.sin(t * math.pi) * 40
    curl_points.append((x, y))
for i in range(30):
    t = (29 - i) / 29
    x = 90 + t * 100
    y = 165 - math.sin(t * math.pi) * 30
    curl_points.append((x, y))

draw.polygon(curl_points, fill=wave_dark)

# Water foreground (base ocean line)
draw.rectangle([(0, 200), (SIZE, SIZE)], fill=(20, 90, 160, 255))

# Foam splashes under wave
for cx, cy, r in [(60, 205, 6), (100, 215, 5), (150, 210, 7), (200, 220, 5), (230, 215, 6)]:
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 255))

# Apply rounded-corner mask
img.putalpha(mask)

# Save as ICO with multiple sizes for Windows
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "letsgosurf.ico")
img.save(out_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(f"Saved icon: {out_path}")
