import unicodedata


def normalizar_numero(valor):
    """Convierte numeros argentinos tipo 21,00 o 386.688,87 a float."""
    if valor is None:
        return None

    valor = str(valor).strip()
    valor = valor.replace(".", "")
    valor = valor.replace(",", ".")

    try:
        return float(valor)
    except ValueError:
        return valor


def normalizar_texto(valor):
    if valor is None:
        return ""

    normalized = unicodedata.normalize("NFKD", str(valor))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.upper().split())
