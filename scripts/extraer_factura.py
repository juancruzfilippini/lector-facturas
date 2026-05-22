import sys

import pdfplumber
import xlwt

from db import find_provider_id, get_connection, get_internal_product_code
from proveedores import coca_cola


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
]


def extraer_texto_pdf(pdf_path):
    texto = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()

            if page_text:
                texto += "\n" + page_text

    return texto


def detectar_proveedor(texto):
    for parser in PARSERS:
        if parser.es_proveedor(texto):
            return parser

    return None


def aplicar_mapeos(productos, proveedor, db_path):
    with get_connection(db_path) as conn:
        provider_id = find_provider_id(conn, proveedor)

        for producto in productos:
            codigo_interno = None

            if provider_id is not None:
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
