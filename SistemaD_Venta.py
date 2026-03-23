import sys
import json
import shutil
from datetime import datetime
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

from PyQt5.QtGui import QDoubleValidator, QIntValidator, QColor
from PyQt5.QtWidgets import (
	QApplication,
	QComboBox,
	QDialog,
	QFrame,
	QGridLayout,
	QGroupBox,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QMainWindow,
	QMessageBox,
	QPushButton,
	QTableWidget,
	QTableWidgetItem,
	QVBoxLayout,
	QWidget,
)
from PyQt5.QtCore import Qt


@dataclass
class Producto:
	codigo: str
	nombre: str
	categoria: str
	precio: float
	stock: int


@dataclass
class ItemCarrito:
	producto: Producto
	codigo: str
	nombre: str
	precio: float
	cantidad: int


class VentanaReportes(QDialog):
	def __init__(self, historial_ventas: List[Dict], historial_cortes: List[Dict], parent: Optional[QWidget] = None) -> None:
		super().__init__(parent)
		self.setWindowTitle("Reporte de Ventas")
		self.resize(860, 440)

		layout = QVBoxLayout(self)
		tabla = QTableWidget(0, 6)
		tabla.setHorizontalHeaderLabels(["Código", "Nombre de Producto", "Precio", "Cantidad", "Forma de Pago", "Fecha y Hora"])
		tabla.setEditTriggers(QTableWidget.NoEditTriggers)
		tabla.setSelectionBehavior(QTableWidget.SelectRows)
		tabla.verticalHeader().setVisible(False)
		tabla.horizontalHeader().setStretchLastSection(True)
		tabla.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

		ventas_ordenadas = sorted(
			historial_ventas,
			key=lambda v: str(v.get("fecha_hora", "")),
		)

		cierres_por_fecha_hora: Dict[str, Dict] = {}
		for corte in historial_cortes:
			fecha_hora_cierre = str(corte.get("fecha_hora_cierre", "")).strip()
			if fecha_hora_cierre:
				cierres_por_fecha_hora[fecha_hora_cierre] = corte

		conteo_ventas_por_cierre: Dict[str, int] = {}
		for venta in ventas_ordenadas:
			if not bool(venta.get("cerrada", False)):
				continue
			fecha_hora_cierre = str(venta.get("fecha_hora_cierre", "")).strip()
			if not fecha_hora_cierre:
				continue
			conteo_ventas_por_cierre[fecha_hora_cierre] = conteo_ventas_por_cierre.get(fecha_hora_cierre, 0) + 1

		for venta in ventas_ordenadas:
			fila = tabla.rowCount()
			tabla.insertRow(fila)
			tabla.setItem(fila, 0, QTableWidgetItem(str(venta.get("codigo", ""))))
			tabla.setItem(fila, 1, QTableWidgetItem(str(venta.get("nombre", ""))))
			precio_unitario = float(venta.get("precio_unitario", 0.0))
			tabla.setItem(fila, 2, QTableWidgetItem(f"${precio_unitario:,.2f}"))
			tabla.setItem(fila, 3, QTableWidgetItem(str(venta.get("cantidad", 0))))
			tabla.setItem(fila, 4, QTableWidgetItem(str(venta.get("forma_pago", ""))))
			tabla.setItem(fila, 5, QTableWidgetItem(str(venta.get("fecha_hora", ""))))

			if not bool(venta.get("cerrada", False)):
				continue

			fecha_hora_cierre = str(venta.get("fecha_hora_cierre", "")).strip()
			if not fecha_hora_cierre or fecha_hora_cierre not in conteo_ventas_por_cierre:
				continue

			conteo_ventas_por_cierre[fecha_hora_cierre] -= 1
			if conteo_ventas_por_cierre[fecha_hora_cierre] > 0:
				continue

			corte = cierres_por_fecha_hora.get(fecha_hora_cierre)
			total_corte = float(corte.get("total_ventas", 0.0)) if corte else 0.0
			fecha_corte = str(corte.get("fecha_operacion", "")) if corte else ""

			fila_cierre = tabla.rowCount()
			tabla.insertRow(fila_cierre)
			tabla.setSpan(fila_cierre, 0, 1, 6)
			descripcion_cierre = (
				f"CIERRE DE CAJA {fecha_corte} - ${total_corte:,.2f}" if fecha_corte else f"CIERRE DE CAJA - ${total_corte:,.2f}"
			)
			item_cierre = QTableWidgetItem(descripcion_cierre)
			item_cierre.setTextAlignment(Qt.AlignCenter)
			tabla.setItem(fila_cierre, 0, item_cierre)

		layout.addWidget(tabla)


class VentanaPDV(QMainWindow):
	def __init__(self) -> None:
		super().__init__()
		self.setWindowTitle("Ferretería - Punto de Venta")
		self.resize(1180, 680)

		directorio_datos = self._obtener_directorio_datos()
		self.archivo_productos = directorio_datos / "productos.json"
		self.archivo_ventas = directorio_datos / "ventas.json"
		self.archivo_cortes = directorio_datos / "cortes_caja.json"
		self.productos: List[Producto] = self._cargar_productos_archivo()
		self.historial_ventas: List[Dict] = self._cargar_ventas_archivo()
		self.historial_cortes: List[Dict] = self._cargar_cortes_archivo()
		self.carrito: List[ItemCarrito] = []

		self._construir_ui()
		self.cargar_tabla(self.productos)
		self._actualizar_resumen_ventas()

	def _construir_ui(self) -> None:
		central = QWidget()
		self.setCentralWidget(central)
		principal = QHBoxLayout(central)
		principal.setContentsMargins(12, 12, 12, 12)
		principal.setSpacing(12)

		principal.addWidget(self._panel_productos(), 2)
		principal.addWidget(self._panel_centro(), 1)
		principal.addWidget(self._panel_derecha(), 1)

	def _panel_productos(self) -> QWidget:
		grupo = QGroupBox("Productos")
		layout = QVBoxLayout(grupo)

		busqueda_layout = QHBoxLayout()
		self.input_buscar = QLineEdit()
		self.input_buscar.setPlaceholderText("Buscar por código o nombre...")
		self.btn_buscar = QPushButton("Buscar")
		self.btn_limpiar_busqueda = QPushButton("Limpiar")

		self.btn_buscar.clicked.connect(self.buscar_producto)
		self.btn_limpiar_busqueda.clicked.connect(self.limpiar_busqueda)
		self.input_buscar.returnPressed.connect(self.buscar_producto)

		busqueda_layout.addWidget(self.input_buscar)
		busqueda_layout.addWidget(self.btn_buscar)
		busqueda_layout.addWidget(self.btn_limpiar_busqueda)
		layout.addLayout(busqueda_layout)

		self.tabla = QTableWidget(0, 5)
		self.tabla.setHorizontalHeaderLabels(["Código", "Nombre", "Categoría", "Precio", "Stock"])
		self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
		self.tabla.setSelectionMode(QTableWidget.SingleSelection)
		self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
		self.tabla.verticalHeader().setVisible(False)
		self.tabla.horizontalHeader().setStretchLastSection(True)
		self.tabla.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
		self.tabla.itemSelectionChanged.connect(self.cargar_formulario_desde_seleccion)
		self.tabla.cellDoubleClicked.connect(self.agregar_producto_al_carrito_desde_doble_click)
		layout.addWidget(self.tabla)

		form = QGroupBox("Gestión de Producto")
		form_layout = QGridLayout(form)

		self.input_codigo = QLineEdit()
		self.input_nombre = QLineEdit()
		self.input_categoria = QLineEdit()
		self.input_precio = QLineEdit()
		self.input_stock = QLineEdit()

		self.input_precio.setValidator(QDoubleValidator(0.0, 9999999.99, 2))
		self.input_stock.setValidator(QIntValidator(0, 9999999))

		form_layout.addWidget(QLabel("Código:"), 0, 0)
		form_layout.addWidget(self.input_codigo, 0, 1)
		form_layout.addWidget(QLabel("Nombre:"), 1, 0)
		form_layout.addWidget(self.input_nombre, 1, 1)
		form_layout.addWidget(QLabel("Categoría:"), 2, 0)
		form_layout.addWidget(self.input_categoria, 2, 1)
		form_layout.addWidget(QLabel("Precio:"), 3, 0)
		form_layout.addWidget(self.input_precio, 3, 1)
		form_layout.addWidget(QLabel("Stock:"), 4, 0)
		form_layout.addWidget(self.input_stock, 4, 1)

		layout.addWidget(form)

		botones = QHBoxLayout()
		self.btn_agregar = QPushButton("Agregar")
		self.btn_editar = QPushButton("Editar")
		self.btn_eliminar = QPushButton("Eliminar")
		self.btn_limpiar_form = QPushButton("Limpiar Form")

		self.btn_agregar.clicked.connect(self.agregar_producto)
		self.btn_editar.clicked.connect(self.editar_producto)
		self.btn_eliminar.clicked.connect(self.eliminar_producto)
		self.btn_limpiar_form.clicked.connect(self.limpiar_formulario)

		botones.addWidget(self.btn_agregar)
		botones.addWidget(self.btn_editar)
		botones.addWidget(self.btn_eliminar)
		botones.addWidget(self.btn_limpiar_form)
		layout.addLayout(botones)

		return grupo

	def _panel_centro(self) -> QWidget:
		contenedor = QWidget()
		layout = QVBoxLayout(contenedor)

		scanner = QGroupBox("Scanner de Código de Barras")
		scanner_layout = QHBoxLayout(scanner)
		self.input_scanner = QLineEdit()
		self.input_scanner.setPlaceholderText("Escanea o escribe el código y presiona Enter...")
		self.btn_scanner_agregar = QPushButton("Agregar")
		self.input_scanner.returnPressed.connect(self.agregar_producto_desde_scanner)
		self.btn_scanner_agregar.clicked.connect(self.agregar_producto_desde_scanner)
		scanner_layout.addWidget(self.input_scanner)
		scanner_layout.addWidget(self.btn_scanner_agregar)

		carrito = QGroupBox("Carrito de Compras")
		carrito_layout = QVBoxLayout(carrito)
		self.tabla_carrito = QTableWidget(0, 3)
		self.tabla_carrito.setHorizontalHeaderLabels(["Producto", "Cantidad", "Total"])
		self.tabla_carrito.setEditTriggers(QTableWidget.NoEditTriggers)
		self.tabla_carrito.verticalHeader().setVisible(False)
		self.tabla_carrito.horizontalHeader().setStretchLastSection(True)
		self.tabla_carrito.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
		carrito_layout.addWidget(self.tabla_carrito)

		detalle = QGroupBox("Detalles de Venta")
		detalle_layout = QVBoxLayout(detalle)
		self.lbl_total = QLabel("Total a Pagar: $0.00")
		self.lbl_total.setStyleSheet("font-weight: bold; font-size: 16px;")
		self.lbl_forma_pago = QLabel("Forma de Pago:")
		self.combo_forma_pago = QComboBox()
		self.combo_forma_pago.addItems(["Efectivo", "Tarjeta"])
		forma_pago_layout = QHBoxLayout()
		forma_pago_layout.addWidget(self.lbl_forma_pago)
		forma_pago_layout.addWidget(self.combo_forma_pago)

		self.btn_cobrar = QPushButton("Cobrar")
		self.btn_cancelar = QPushButton("Cancelar")
		self.btn_cobrar.clicked.connect(self.cobrar_venta)
		self.btn_cancelar.clicked.connect(self.cancelar_venta)
		acciones_layout = QHBoxLayout()
		acciones_layout.addWidget(self.btn_cobrar)
		acciones_layout.addWidget(self.btn_cancelar)

		detalle_layout.addWidget(self.lbl_total)
		detalle_layout.addLayout(forma_pago_layout)
		detalle_layout.addLayout(acciones_layout)

		layout.addWidget(scanner)
		layout.addWidget(carrito)
		layout.addWidget(detalle)
		return contenedor

	def _panel_derecha(self) -> QWidget:
		contenedor = QWidget()
		layout = QVBoxLayout(contenedor)

		resumen = QGroupBox("Resumen de Ventas")
		resumen_layout = QVBoxLayout(resumen)
		self.lbl_ventas_dia = QLabel("Ventas del Día:  $0.00")
		self.lbl_productos_vendidos = QLabel("Productos Vendidos:  0")

		resumen_layout.addWidget(self.lbl_ventas_dia)
		resumen_layout.addWidget(self._linea_divisoria())
		resumen_layout.addWidget(self.lbl_productos_vendidos)

		reportes = QGroupBox("Reportes")
		rep_layout = QVBoxLayout(reportes)
		rep_layout.addWidget(QLabel("Historial de productos vendidos"))
		btns = QHBoxLayout()
		self.btn_ver_reportes = QPushButton("Ver Reportes")
		self.btn_configurar = QPushButton("Configurar")
		self.btn_cerrar_caja = QPushButton("Cerrar Caja")
		self.btn_ver_reportes.clicked.connect(self.abrir_ventana_reportes)
		self.btn_cerrar_caja.clicked.connect(self.cerrar_caja)
		btns.addWidget(self.btn_ver_reportes)
		btns.addWidget(self.btn_configurar)
		rep_layout.addLayout(btns)
		rep_layout.addWidget(self.btn_cerrar_caja)

		layout.addWidget(resumen)
		layout.addWidget(reportes)
		layout.addStretch()
		return contenedor

	@staticmethod
	def _linea_divisoria() -> QWidget:
		linea = QFrame()
		linea.setFrameShape(QFrame.HLine)
		linea.setFrameShadow(QFrame.Sunken)
		return linea

	def _obtener_directorio_datos(self) -> Path:
		if getattr(sys, "frozen", False):
			# En ejecutable, guardar datos junto al .exe para portabilidad.
			return Path(sys.executable).resolve().parent
		return Path(__file__).resolve().parent

	def _copiar_recurso_si_no_existe(self, nombre_archivo: str, destino: Path) -> None:
		if destino.exists():
			return

		ruta_base_recursos = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
		ruta_origen = ruta_base_recursos / nombre_archivo
		if not ruta_origen.exists():
			return

		try:
			shutil.copy2(ruta_origen, destino)
		except OSError:
			return

	def cargar_tabla(self, productos: List[Producto]) -> None:
		self.tabla.setRowCount(0)
		for producto in productos:
			fila = self.tabla.rowCount()
			self.tabla.insertRow(fila)
			item_codigo = QTableWidgetItem(producto.codigo)
			item_codigo.setData(Qt.UserRole, producto)
			item_nombre = QTableWidgetItem(producto.nombre)
			item_categoria = QTableWidgetItem(producto.categoria)
			item_precio = QTableWidgetItem(f"${producto.precio:,.2f}")
			item_stock = QTableWidgetItem(str(producto.stock))

			if producto.stock == 0:
				color_fondo = QColor("#f8d7da")
			elif producto.stock == 1:
				color_fondo = QColor("#fff3cd")
			else:
				color_fondo = None

			if color_fondo is not None:
				for item in [item_codigo, item_nombre, item_categoria, item_precio, item_stock]:
					item.setBackground(color_fondo)

			self.tabla.setItem(fila, 0, item_codigo)
			self.tabla.setItem(fila, 1, item_nombre)
			self.tabla.setItem(fila, 2, item_categoria)
			self.tabla.setItem(fila, 3, item_precio)
			self.tabla.setItem(fila, 4, item_stock)

	def _producto_desde_fila_tabla(self, fila: int) -> Optional[Producto]:
		if fila < 0:
			return None

		item_codigo = self.tabla.item(fila, 0)
		if item_codigo is None:
			return None

		producto = item_codigo.data(Qt.UserRole)
		if isinstance(producto, Producto):
			return producto
		return None

	def cargar_formulario_desde_seleccion(self) -> None:
		fila = self.tabla.currentRow()
		producto = self._producto_desde_fila_tabla(fila)
		if producto is None:
			return

		self.input_codigo.setText(producto.codigo)
		self.input_nombre.setText(producto.nombre)
		self.input_categoria.setText(producto.categoria)
		self.input_precio.setText(f"{producto.precio:.2f}")
		self.input_stock.setText(str(producto.stock))

	def agregar_producto(self) -> None:
		datos = self._leer_formulario()
		if datos is None:
			return

		self.productos.append(datos)
		self._guardar_productos_archivo()
		self.cargar_tabla(self.productos)
		self.limpiar_formulario()
		QMessageBox.information(self, "Producto agregado", "Producto agregado correctamente.")

	def editar_producto(self) -> None:
		fila = self.tabla.currentRow()
		producto_original = self._producto_desde_fila_tabla(fila)
		if producto_original is None:
			QMessageBox.warning(self, "Sin selección", "Selecciona un producto para editar.")
			return

		datos_nuevos = self._leer_formulario()
		if datos_nuevos is None:
			return

		producto_original.codigo = datos_nuevos.codigo
		producto_original.nombre = datos_nuevos.nombre
		producto_original.categoria = datos_nuevos.categoria
		producto_original.precio = datos_nuevos.precio
		producto_original.stock = datos_nuevos.stock

		self._guardar_productos_archivo()
		self.cargar_tabla(self.productos)
		self.limpiar_formulario()
		QMessageBox.information(self, "Producto editado", "Producto actualizado correctamente.")

	def eliminar_producto(self) -> None:
		fila = self.tabla.currentRow()
		producto = self._producto_desde_fila_tabla(fila)
		if producto is None:
			QMessageBox.warning(self, "Sin selección", "Selecciona un producto para eliminar.")
			return

		respuesta = QMessageBox.question(
			self,
			"Confirmar eliminación",
			f"¿Eliminar el producto '{producto.nombre}'?",
			QMessageBox.Yes | QMessageBox.No,
			QMessageBox.No,
		)
		if respuesta == QMessageBox.No:
			return

		self.productos.remove(producto)
		self._guardar_productos_archivo()
		self.cargar_tabla(self.productos)
		self.limpiar_formulario()
		QMessageBox.information(self, "Producto eliminado", "Producto eliminado correctamente.")

	def buscar_producto(self) -> None:
		termino = self.input_buscar.text().strip().lower()
		if not termino:
			self.cargar_tabla(self.productos)
			return

		filtrados = [
			p
			for p in self.productos
			if termino in p.codigo.lower() or termino in p.nombre.lower() or termino in p.categoria.lower()
		]
		self.cargar_tabla(filtrados)

	def limpiar_busqueda(self) -> None:
		self.input_buscar.clear()
		self.cargar_tabla(self.productos)

	def limpiar_formulario(self) -> None:
		self.input_codigo.clear()
		self.input_nombre.clear()
		self.input_categoria.clear()
		self.input_precio.clear()
		self.input_stock.clear()
		self.tabla.clearSelection()

	def _leer_formulario(self) -> Optional[Producto]:
		codigo = self.input_codigo.text().strip()
		nombre = self.input_nombre.text().strip()
		categoria = self.input_categoria.text().strip()
		precio_str = self.input_precio.text().strip().replace(",", ".")
		stock_str = self.input_stock.text().strip()

		if not codigo or not nombre or not categoria or not precio_str or not stock_str:
			QMessageBox.warning(self, "Datos incompletos", "Completa todos los campos del formulario.")
			return None

		try:
			precio = float(precio_str)
			stock = int(stock_str)
		except ValueError:
			QMessageBox.warning(self, "Datos inválidos", "Precio o stock no tienen formato válido.")
			return None

		if precio < 0 or stock < 0:
			QMessageBox.warning(self, "Valores inválidos", "Precio y stock deben ser mayores o iguales a 0.")
			return None

		return Producto(codigo=codigo, nombre=nombre, categoria=categoria, precio=precio, stock=stock)

	def agregar_producto_al_carrito_desde_doble_click(self, fila: int, _columna: int) -> None:
		producto = self._producto_desde_fila_tabla(fila)
		if producto is None:
			return
		self._agregar_producto_al_carrito(producto)

	def _agregar_producto_al_carrito(self, producto: Producto) -> None:

		item_carrito = self._buscar_item_carrito_por_producto(producto)
		if item_carrito is None:
			if producto.stock <= 0:
				QMessageBox.warning(self, "Sin stock", "Este producto no tiene stock disponible.")
				return
			self.carrito.append(
				ItemCarrito(
					producto=producto,
					codigo=producto.codigo,
					nombre=producto.nombre,
					precio=producto.precio,
					cantidad=1,
				)
			)
		else:
			if item_carrito.cantidad >= producto.stock:
				QMessageBox.warning(self, "Stock insuficiente", "No puedes agregar más unidades que el stock disponible.")
				return
			item_carrito.cantidad += 1

		self._refrescar_tabla_carrito()
		self._actualizar_totales_venta()

	def _buscar_producto_por_codigo(self, codigo_barras: str) -> Optional[Producto]:
		codigo_objetivo = codigo_barras.strip()
		if not codigo_objetivo:
			return None

		for producto in self.productos:
			if producto.codigo.strip() == codigo_objetivo:
				return producto
		return None

	def agregar_producto_desde_scanner(self) -> None:
		codigo_barras = self.input_scanner.text().strip()
		if not codigo_barras:
			return

		producto = self._buscar_producto_por_codigo(codigo_barras)
		if producto is None:
			QMessageBox.warning(self, "No encontrado", f"No existe un producto con código '{codigo_barras}'.")
			self.input_scanner.selectAll()
			self.input_scanner.setFocus()
			return

		self._agregar_producto_al_carrito(producto)
		self.input_scanner.clear()
		self.input_scanner.setFocus()

	def _buscar_item_carrito_por_producto(self, producto: Producto) -> Optional[ItemCarrito]:
		for item in self.carrito:
			if item.producto is producto:
				return item
		return None

	def _refrescar_tabla_carrito(self) -> None:
		self.tabla_carrito.setRowCount(0)
		for item in self.carrito:
			fila = self.tabla_carrito.rowCount()
			self.tabla_carrito.insertRow(fila)
			self.tabla_carrito.setItem(fila, 0, QTableWidgetItem(item.nombre))
			self.tabla_carrito.setItem(fila, 1, QTableWidgetItem(str(item.cantidad)))
			total_fila = item.precio * item.cantidad
			self.tabla_carrito.setItem(fila, 2, QTableWidgetItem(f"${total_fila:,.2f}"))

	def _actualizar_totales_venta(self) -> None:
		total = self._calcular_total_venta()
		self.lbl_total.setText(f"Total a Pagar: ${total:,.2f}")

	def _calcular_total_venta(self) -> float:
		subtotal = sum(item.precio * item.cantidad for item in self.carrito)
		return subtotal

	def cobrar_venta(self) -> None:
		if not self.carrito:
			QMessageBox.warning(self, "Carrito vacío", "No hay productos en el carrito para cobrar.")
			return

		forma_pago = self.combo_forma_pago.currentText()

		for item in self.carrito:
			producto = item.producto
			if producto.stock < item.cantidad:
				QMessageBox.warning(
					self,
					"Stock insuficiente",
					f"Stock insuficiente para {producto.nombre}. Disponible: {producto.stock}.",
				)
				return

		for item in self.carrito:
			item.producto.stock -= item.cantidad

		momento_venta = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		for item in self.carrito:
			self.historial_ventas.append(
				{
					"codigo": item.codigo,
					"nombre": item.nombre,
					"cantidad": item.cantidad,
					"precio_unitario": item.precio,
					"total": item.precio * item.cantidad,
					"forma_pago": forma_pago,
					"fecha_hora": momento_venta,
				}
			)

		self._guardar_productos_archivo()
		self._guardar_ventas_archivo()
		self.cargar_tabla(self.productos)
		self._actualizar_resumen_ventas()

		total = self._calcular_total_venta()
		QMessageBox.information(
			self,
			"Venta cobrada",
			f"Cobro realizado correctamente.\nForma de pago: {forma_pago}\nTotal: ${total:,.2f}",
		)
		self.carrito.clear()
		self._refrescar_tabla_carrito()
		self._actualizar_totales_venta()

	def cancelar_venta(self) -> None:
		if not self.carrito:
			return

		respuesta = QMessageBox.question(
			self,
			"Cancelar venta",
			"¿Deseas cancelar la venta actual?",
			QMessageBox.Yes | QMessageBox.No,
			QMessageBox.No,
		)
		if respuesta == QMessageBox.No:
			return

		self.carrito.clear()
		self._refrescar_tabla_carrito()
		self._actualizar_totales_venta()

	def _productos_iniciales(self) -> List[Producto]:
		return [
			Producto("1001", "Martillo", "Herramientas", 120.00, 15),
			Producto("2002", "Tornillo 1\"", "Tornillería", 0.50, 200),
			Producto("3005", "Pintura Blanca", "Pinturas", 80.00, 35),
			Producto("4008", "Cable Eléctrico", "Eléctricos", 15.00, 50),
		]

	def _cargar_productos_archivo(self) -> List[Producto]:
		self._copiar_recurso_si_no_existe("productos.json", self.archivo_productos)
		if not self.archivo_productos.exists():
			productos = self._productos_iniciales()
			self.productos = productos
			self._guardar_productos_archivo()
			return productos

		try:
			with self.archivo_productos.open("r", encoding="utf-8") as archivo:
				datos = json.load(archivo)
		except (OSError, json.JSONDecodeError):
			return self._productos_iniciales()

		productos: List[Producto] = []
		for item in datos:
			try:
				productos.append(
					Producto(
						codigo=str(item["codigo"]),
						nombre=str(item["nombre"]),
						categoria=str(item["categoria"]),
						precio=float(item["precio"]),
						stock=int(item["stock"]),
					)
				)
			except (KeyError, TypeError, ValueError):
				continue

		if productos:
			return productos
		return self._productos_iniciales()

	def _guardar_productos_archivo(self) -> None:
		try:
			with self.archivo_productos.open("w", encoding="utf-8") as archivo:
				json.dump([asdict(p) for p in self.productos], archivo, ensure_ascii=False, indent=2)
		except OSError:
			QMessageBox.warning(self, "Error al guardar", "No se pudo guardar el archivo de productos.")

	def _cargar_ventas_archivo(self) -> List[Dict]:
		self._copiar_recurso_si_no_existe("ventas.json", self.archivo_ventas)
		if not self.archivo_ventas.exists():
			return []

		try:
			with self.archivo_ventas.open("r", encoding="utf-8") as archivo:
				datos = json.load(archivo)
				if isinstance(datos, list):
					return datos
		except (OSError, json.JSONDecodeError):
			return []

		return []

	def _guardar_ventas_archivo(self) -> None:
		try:
			with self.archivo_ventas.open("w", encoding="utf-8") as archivo:
				json.dump(self.historial_ventas, archivo, ensure_ascii=False, indent=2)
		except OSError:
			QMessageBox.warning(self, "Error al guardar", "No se pudo guardar el historial de ventas.")

	def _cargar_cortes_archivo(self) -> List[Dict]:
		self._copiar_recurso_si_no_existe("cortes_caja.json", self.archivo_cortes)
		if not self.archivo_cortes.exists():
			return []

		try:
			with self.archivo_cortes.open("r", encoding="utf-8") as archivo:
				datos = json.load(archivo)
				if isinstance(datos, list):
					return datos
		except (OSError, json.JSONDecodeError):
			return []

		return []

	def _guardar_cortes_archivo(self) -> None:
		try:
			with self.archivo_cortes.open("w", encoding="utf-8") as archivo:
				json.dump(self.historial_cortes, archivo, ensure_ascii=False, indent=2)
		except OSError:
			QMessageBox.warning(self, "Error al guardar", "No se pudo guardar el corte de caja.")

	def _actualizar_resumen_ventas(self) -> None:
		hoy = datetime.now().date()
		ventas_hoy = 0.0
		productos_vendidos_hoy = 0

		for venta in self.historial_ventas:
			fecha_hora = str(venta.get("fecha_hora", ""))
			try:
				fecha_venta = datetime.strptime(fecha_hora, "%Y-%m-%d %H:%M:%S").date()
			except ValueError:
				continue

			if fecha_venta == hoy:
				if bool(venta.get("cerrada", False)):
					continue
				productos_vendidos_hoy += int(venta.get("cantidad", 0))
				ventas_hoy += float(venta.get("total", 0.0))

		self.lbl_ventas_dia.setText(f"Ventas del Día:  ${ventas_hoy:,.2f}")
		self.lbl_productos_vendidos.setText(f"Productos Vendidos:  {productos_vendidos_hoy}")

	def abrir_ventana_reportes(self) -> None:
		if not self.historial_ventas:
			QMessageBox.information(self, "Sin datos", "Aún no hay ventas registradas.")
			return

		self.ventana_reportes = VentanaReportes(self.historial_ventas, self.historial_cortes, self)
		self.ventana_reportes.exec_()

	def cerrar_caja(self) -> None:
		hoy = datetime.now().date()
		ventas_abiertas_hoy: List[Dict] = []

		for venta in self.historial_ventas:
			fecha_hora = str(venta.get("fecha_hora", ""))
			try:
				fecha_venta = datetime.strptime(fecha_hora, "%Y-%m-%d %H:%M:%S").date()
			except ValueError:
				continue

			if fecha_venta == hoy and not bool(venta.get("cerrada", False)):
				ventas_abiertas_hoy.append(venta)

		if not ventas_abiertas_hoy:
			QMessageBox.information(self, "Sin ventas", "No hay ventas pendientes para cerrar hoy.")
			return

		respuesta = QMessageBox.question(
			self,
			"Cerrar caja",
			"¿Deseas cerrar la caja del día? Esta acción reiniciará el resumen actual.",
			QMessageBox.Yes | QMessageBox.No,
			QMessageBox.No,
		)
		if respuesta == QMessageBox.No:
			return

		total_dia = sum(float(v.get("total", 0.0)) for v in ventas_abiertas_hoy)
		productos_dia = sum(int(v.get("cantidad", 0)) for v in ventas_abiertas_hoy)
		momento_cierre = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

		self.historial_cortes.append(
			{
				"fecha_operacion": hoy.isoformat(),
				"fecha_hora_cierre": momento_cierre,
				"total_ventas": total_dia,
				"productos_vendidos": productos_dia,
				"ventas": [dict(v) for v in ventas_abiertas_hoy],
			}
		)

		for venta in self.historial_ventas:
			fecha_hora = str(venta.get("fecha_hora", ""))
			try:
				fecha_venta = datetime.strptime(fecha_hora, "%Y-%m-%d %H:%M:%S").date()
			except ValueError:
				continue

			if fecha_venta == hoy and not bool(venta.get("cerrada", False)):
				venta["cerrada"] = True
				venta["fecha_hora_cierre"] = momento_cierre

		self._guardar_ventas_archivo()
		self._guardar_cortes_archivo()
		self._actualizar_resumen_ventas()

		QMessageBox.information(
			self,
			"Caja cerrada",
			f"Caja cerrada correctamente.\nTotal del día: ${total_dia:,.2f}\nProductos vendidos: {productos_dia}",
		)


def main() -> None:
	app = QApplication(sys.argv)
	app.setStyle("Fusion")
	ventana = VentanaPDV()
	ventana.show()
	sys.exit(app.exec_())


if __name__ == "__main__":
	main()
