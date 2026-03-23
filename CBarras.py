from pathlib import Path

import barcode
from barcode.writer import ImageWriter


def generar_codigo_barras(numero: str, nombre_archivo: str = "codigo_producto") -> Path:
	numero_limpio = numero.strip()
	if not numero_limpio.isdigit() or len(numero_limpio) != 12:
		raise ValueError("El código EAN-13 debe tener exactamente 12 dígitos numéricos.")

	codigo = barcode.get("ean13", numero_limpio, writer=ImageWriter())
	ruta_base = Path(__file__).with_name(nombre_archivo)
	ruta_generada = codigo.save(str(ruta_base))
	return Path(ruta_generada)


def main() -> None:
	numero = input("Ingresa los 12 dígitos del producto: ").strip()
	nombre = input("Nombre del archivo (sin extensión, Enter = codigo_producto): ").strip() or "codigo_producto"

	try:
		ruta_imagen = generar_codigo_barras(numero, nombre)
	except ValueError as error:
		print(f"Error: {error}")
		return

	print(f"Imagen generada correctamente: {ruta_imagen}")


if __name__ == "__main__":
	main()