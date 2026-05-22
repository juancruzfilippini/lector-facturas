import re

from .utils import normalizar_numero


PROVEEDOR = {
    "key": "generico",
    "name": "Proveedor generico",
    "cuit": None,
    "aliases": [],
}


def es_proveedor(_texto):
    return False


def extraer_productos(texto):
    productos = []

    for linea in texto.splitlines():
        linea = linea.strip()

        if not re.match(r"^\d{6}\s+", linea):
            continue

        partes = linea.split()

        if len(partes) < 9:
            continue

        valores = partes[-7:]
        productos.append(
            {
                "codigo_proveedor": partes[0],
                "detalle": " ".join(partes[1:-7]),
                "cantidad": normalizar_numero(valores[0]),
                "precio_unitario": normalizar_numero(valores[1]),
                "descuento": normalizar_numero(valores[2]),
                "total_neto": normalizar_numero(valores[3]),
                "i_internos": normalizar_numero(valores[4]),
                "iva": normalizar_numero(valores[5]),
                "total": normalizar_numero(valores[6]),
            }
        )

    return productos
