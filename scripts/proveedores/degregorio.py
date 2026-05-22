import re

from .utils import normalizar_texto


PROVEEDOR = {
    "key": "degregorio",
    "name": "DEGREGORIO",
    "cuit": "30701435758",
    "aliases": [
        "DEGREGORIO Servicios de Distribucion",
        "Transportes y Distribuciones Degregorio",
        "Transportes y Distribuciones Degregorio S.R.L.",
    ],
}

ALIAS_DETECCION = [
    "DEGREGORIO",
    "SERVICIOS DE DISTRIBUCION",
    "TRANSPORTES Y DISTRIBUCIONES DEGREGORIO",
    "30701435758",
]

IGNORAR_LINEA = [
    "SUBTOTAL",
    "IIBB",
    "IMP INTERNO",
    "IVA 21%",
    "TOTAL",
    "SON",
    "CAE",
    "FECHA",
    "CLIENTE",
    "CONDICION DE VENTA",
]

LINEA_PRODUCTO_RE = re.compile(
    r"^\s*"
    r"(?P<codigo>\d{5,6})\s+"
    r"(?P<detalle>.+?)\s+"
    r"(?P<cantidad>\d+)\s+"
    r"(?P<precio_unitario>\d+(?:\.\d+)?)\s+"
    r"(?P<descuento>\d+(?:\.\d+)?)\s+"
    r"(?P<total>\d+(?:\.\d+)?)"
    r"\s*$"
)


def normalizar_numero_decimal(valor):
    if valor is None:
        return None

    valor = str(valor).strip()

    if "," in valor and "." in valor:
        valor = valor.replace(",", "")
    elif "," in valor:
        valor = valor.replace(",", ".")

    try:
        return float(valor)
    except ValueError:
        return valor


def es_proveedor(texto):
    texto_normalizado = normalizar_texto(texto)
    solo_digitos = "".join(char for char in str(texto) if char.isdigit())

    return any(alias in texto_normalizado for alias in ALIAS_DETECCION) or (
        PROVEEDOR["cuit"] in solo_digitos
    )


def debe_ignorar_linea(linea):
    linea_normalizada = normalizar_texto(linea)
    return any(texto in linea_normalizada for texto in IGNORAR_LINEA)


def es_linea_producto(linea):
    if debe_ignorar_linea(linea):
        return False

    return LINEA_PRODUCTO_RE.match(linea) is not None


def extraer_productos(texto):
    productos = []

    for linea in texto.splitlines():
        linea = linea.strip()

        if not linea or debe_ignorar_linea(linea):
            continue

        match = LINEA_PRODUCTO_RE.match(linea)

        if match is None:
            continue

        total = normalizar_numero_decimal(match.group("total"))

        productos.append(
            {
                "codigo_proveedor": match.group("codigo"),
                "detalle": " ".join(match.group("detalle").split()),
                "cantidad": normalizar_numero_decimal(match.group("cantidad")),
                "precio_unitario": normalizar_numero_decimal(
                    match.group("precio_unitario")
                ),
                "descuento": normalizar_numero_decimal(match.group("descuento")),
                "total_neto": total,
                "i_internos": 0,
                "iva": 0,
                "total": total,
            }
        )

    return productos
