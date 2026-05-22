import sys
import re
import pdfplumber
import pandas as pd


def normalizar_numero(valor):
    """
    Convierte números argentinos tipo 21,00 o 386688,87 a float.
    """
    if valor is None:
        return None

    valor = str(valor).strip()
    valor = valor.replace(".", "")
    valor = valor.replace(",", ".")

    try:
        return float(valor)
    except ValueError:
        return valor


def extraer_texto_pdf(pdf_path):
    texto = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()

            if page_text:
                texto += "\n" + page_text

    return texto


def extraer_productos_generico(texto):
    productos = []

    lineas = texto.splitlines()

    for linea in lineas:
        linea = linea.strip()

        # Detecta líneas que comienzan con código de producto de 6 dígitos.
        # Ejemplo:
        # 100412 COCA COLA PET 2500X6 RED 21,00 21974,63 ...
        if not re.match(r"^\d{6}\s+", linea):
            continue

        partes = linea.split()

        if len(partes) < 9:
            continue

        codigo = partes[0]

        # Últimas 7 columnas numéricas:
        # cantidad, precio unitario, descuento, total neto, internos, iva, total
        valores = partes[-7:]
        detalle = " ".join(partes[1:-7])

        producto = {
            "codigo": codigo,
            "detalle": detalle,
            "cantidad": normalizar_numero(valores[0]),
            "precio_unitario": normalizar_numero(valores[1]),
            "descuento": normalizar_numero(valores[2]),
            "total_neto": normalizar_numero(valores[3]),
            "i_internos": normalizar_numero(valores[4]),
            "iva": normalizar_numero(valores[5]),
            "total": normalizar_numero(valores[6]),
        }

        productos.append(producto)

    return productos


def generar_excel(productos, output_path):
    df = pd.DataFrame(productos)

    columnas = [
        "codigo",
        "detalle",
        "cantidad",
        "precio_unitario",
        "descuento",
        "total_neto",
        "i_internos",
        "iva",
        "total",
    ]

    if df.empty:
        df = pd.DataFrame(columns=columnas)
    else:
        df = df[columnas]

    df.to_excel(output_path, index=False)


def main():
    if len(sys.argv) < 3:
        print("Uso: python extraer_factura.py archivo.pdf salida.xlsx", file=sys.stderr)
        sys.exit(1)

    pdf_path = sys.argv[1]
    output_path = sys.argv[2]

    texto = extraer_texto_pdf(pdf_path)
    productos = extraer_productos_generico(texto)

    if not productos:
        print("No se encontraron productos en la factura", file=sys.stderr)
        sys.exit(1)

    generar_excel(productos, output_path)

    print(f"Excel generado correctamente: {output_path}")


if __name__ == "__main__":
    main()