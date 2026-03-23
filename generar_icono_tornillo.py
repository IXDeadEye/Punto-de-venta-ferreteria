from PIL import Image, ImageDraw

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Fondo circular suave
margin = 10
draw.ellipse((margin, margin, SIZE - margin, SIZE - margin), fill=(235, 242, 248, 255))

# Cuerpo del tornillo (ligero diagonal)
body = [(84, 88), (150, 54), (188, 130), (122, 164)]
draw.polygon(body, fill=(180, 188, 198, 255), outline=(110, 118, 128, 255))

# Cabeza del tornillo
draw.ellipse((48, 72, 124, 148), fill=(205, 214, 225, 255), outline=(120, 128, 138, 255), width=3)

# Ranura de la cabeza
draw.line((64, 109, 108, 109), fill=(115, 123, 133, 255), width=7)
draw.line((86, 87, 86, 131), fill=(115, 123, 133, 255), width=7)

# Rosca del tornillo
thread_color = (132, 140, 150, 255)
for step in range(0, 7):
    x1 = 122 + step * 10
    y1 = 164 - step * 15
    x2 = x1 + 24
    y2 = y1 - 8
    draw.line((x1, y1, x2, y2), fill=thread_color, width=4)

# Brillo
draw.polygon([(95, 88), (132, 70), (144, 94), (108, 112)], fill=(245, 248, 252, 140))

icon_path = "PDV/tornillo_icon.ico"
img.save(icon_path, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(f"Icono generado: {icon_path}")
