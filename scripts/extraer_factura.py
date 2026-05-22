import re
import sys
import unicodedata

import pdfplumber
import xlwt

from db import ensure_provider_id, get_connection, get_internal_product_code
from proveedores import coca_cola, degregorio


COLUMNAS = [
    "codigo_interno",
    "codigo_proveedor",
    "detalle",
    "cantidad",
    "precio_unitario",
    "descuento",
    "total_neto",
    "i_internos",
    "iva",
    "total",
]

PARSERS = [
    coca_cola,
    degregorio,
]

DEGREGORIO_DETECCION_NORMALIZADA = [
    "DEGREGORIO",
    "TRANSPORTES Y DISTRIBUCIONES DEGREGORIO",
]

DEGREGORIO_DETECCION_COMPACTA = [
    "DEGREGORIO",
    "TRANSPORTESYDISTRIBUCIONESDEGREGORIO",
    "30701435758",
    "CUIT30701435758",
    "DEGREG",
]

DEGREGORIO_CABECERAS_COMPACTAS = [
    "CODIGODETALLEBULTOSUNIDSPUNITBONIFIMPORTE",
    "BULTOSUNIDSPUNITBONIFIMPORTE",
]


def extraer_texto_pdf(pdf_path):
    texto = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()

            if page_text:
                texto += "\n" + page_text

    return texto


def normalizar_texto(texto):
    texto = texto or ""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(char for char in texto if not unicodedata.combining(char))
    texto = texto.upper()
    texto = texto.replace("\n", " ")
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def solo_alfanumerico(texto):
    return re.sub(r"[^A-Z0-9]", "", (texto or "").upper())


def es_degregorio(texto, texto_normalizado, texto_compacto):
    if any(
        clave in texto_normalizado for clave in DEGREGORIO_DETECCION_NORMALIZADA
    ) or any(clave in texto_compacto for clave in DEGREGORIO_DETECCION_COMPACTA):
        return True

    tiene_cabecera_degregorio = any(
        cabecera in texto_compacto for cabecera in DEGREGORIO_CABECERAS_COMPACTAS
    )

    if not tiene_cabecera_degregorio:
        return False

    return any(
        producto.get("codigo_proveedor")
        for producto in degregorio.extraer_productos(texto)
    )


def detectar_proveedor(texto):
    texto_normalizado = normalizar_texto(texto)
    texto_compacto = solo_alfanumerico(texto_normalizado)

    for parser in PARSERS:
        if parser is degregorio:
            if es_degregorio(
                texto,
                texto_normalizado,
                texto_compacto,
            ) or parser.es_proveedor(
                texto
            ):
                return degregorio
            continue

        if parser.es_proveedor(texto):
            return parser

    return None


def aplicar_mapeos(productos, proveedor, db_path):
    with get_connection(db_path) as conn:
        provider_id = ensure_provider_id(conn, proveedor)

        for producto in productos:
            codigo_interno = None

            codigo_interno = get_internal_product_code(
                conn,
                provider_id,
                producto["codigo_proveedor"],
            )

            producto["codigo_interno"] = codigo_interno or "SIN_MAPEO"

    return productos


def generar_excel_xls(productos, output_path):
    workbook = xlwt.Workbook(encoding="utf-8")
    sheet = workbook.add_sheet("Productos")

    for col_idx, columna in enumerate(COLUMNAS):
        sheet.write(2, col_idx, columna)

    for row_idx, producto in enumerate(productos, start=3):
        for col_idx, columna in enumerate(COLUMNAS):
            sheet.write(row_idx, col_idx, producto.get(columna, ""))

    workbook.save(output_path)


def main():
    if len(sys.argv) < 3:
        print(
            "Uso: python extraer_factura.py archivo.pdf salida.xls [database.sqlite]",
            file=sys.stderr,
        )
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2]
    db_path = sys.argv[3] if len(sys.argv) >= 4 else None

    try:
        texto = extraer_texto_pdf(pdf_path)
        parser = detectar_proveedor(texto)

        if parser is None:
            texto_normalizado = normalizar_texto(texto)
            texto_compacto = solo_alfanumerico(texto_normalizado)
            print(
                f"DEBUG proveedor no detectado. Texto extraido: {texto[:1500]}",
                file=sys.stderr,
            )
            print(
                f"DEBUG normalizado: {texto_normalizado[:1500]}",
                file=sys.stderr,
            )
            print(f"DEBUG compacto: {texto_compacto[:1500]}", file=sys.stderr)
            print(
                "No se detecto proveedor para la factura. "
                "Agregue un parser especifico o revise el PDF.",
                file=sys.stderr,
            )
            sys.exit(1)

        productos = parser.extraer_productos(texto)

        if not productos:
            print("No se detectaron productos en la factura", file=sys.stderr)
            sys.exit(1)

        try:
            productos = aplicar_mapeos(productos, parser.PROVEEDOR, db_path)
        except Exception as db_error:
            print(f"Error de base de datos: {db_error}", file=sys.stderr)
            sys.exit(1)

        generar_excel_xls(productos, output_path)

        print(f"Archivo XLS generado correctamente: {output_path}")
    except Exception as error:
        print(f"Error procesando la factura: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
