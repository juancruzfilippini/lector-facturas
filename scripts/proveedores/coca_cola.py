import re

from .utils import normalizar_numero, normalizar_texto


PROVEEDOR = {
    "key": "coca_cola",
    "name": "Coca Cola / Embotelladora del Atlantico",
    "cuit": "30529135944",
    "aliases": [
        "Coca Cola",
        "Embotelladora del Atlantico",
        "Embotelladora del Atl",
    ],
}

ALIAS_DETECCION = [
    "COCA COLA",
    "EMBOTELLADORA DEL ATL",
    "30529135944",
]


def es_proveedor(texto):
    texto_normalizado = normalizar_texto(texto)
    solo_digitos = "".join(char for char in str(texto) if char.isdigit())

    return any(alias in texto_normalizado for alias in ALIAS_DETECCION) or (
        PROVEEDOR["cuit"] in solo_digitos
    )


def es_linea_producto(linea):
    return re.match(r"^\d{6}\s+", linea) is not None


def extraer_productos(texto):
    productos = []

    for linea in texto.splitlines():
        linea = linea.strip()

        if not es_linea_producto(linea):
            continue

        partes = linea.split()

        if len(partes) < 9:
            continue

        valores = partes[-7:]
        detalle = " ".join(partes[1:-7])

        productos.append(
            {
                "codigo_proveedor": partes[0],
                "detalle": detalle,
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
