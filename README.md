# Lector de facturas PDF

Backend Node.js con Express para procesar facturas PDF, ejecutar un extractor Python y descargar un Excel `.xls` real compatible con sistemas antiguos.

## Instalacion Node

```powershell
npm install
```

## Entorno Python

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

El proyecto usa `xlwt` para generar archivos `.xls` reales en formato BIFF8. No se genera `.xlsx` ni se renombra un `.xlsx` como `.xls`.

## Ejecucion

```powershell
npm run dev
```

Luego abrir:

```text
http://localhost:3000
```

## Uso del frontend

La pantalla principal permite:

- seleccionar una factura PDF;
- procesarla con el endpoint `POST /procesar-factura`;
- descargar el archivo `factura_procesada.xls`;
- ver estados de procesamiento;
- crear proveedores;
- crear mapeos de productos;
- listar proveedores y mapeos existentes.

## Proveedores

Los proveedores se guardan desde el formulario de proveedores o desde el endpoint:

```http
POST /api/providers
Content-Type: application/json

{
  "name": "Coca Cola",
  "cuit": "30529135944"
}
```

Tambien se pueden listar con:

```http
GET /api/providers
```

## Mapeos

Los mapeos relacionan el codigo de producto del proveedor con el codigo interno propio.

```http
POST /api/product-mappings
Content-Type: application/json

{
  "provider_id": 1,
  "provider_product_code": "100412",
  "provider_product_description": "COCA COLA PET 2500X6 RED",
  "internal_product_code": "MI-CODIGO-INTERNO"
}
```

Tambien se pueden listar con:

```http
GET /api/product-mappings
```

## Procesar factura

El frontend envia el PDF como `factura` al endpoint:

```http
POST /procesar-factura
```

El backend guarda el archivo en `uploads/`, llama a:

```text
.\.venv\Scripts\python.exe scripts\extraer_factura.py
```

y genera el resultado en `outputs/` con extension `.xls`.

El Excel generado tiene:

- fila 1 vacia;
- fila 2 vacia;
- fila 3 con encabezados;
- fila 4 en adelante con productos;
- columna `codigo_interno`;
- valor `SIN_MAPEO` cuando no existe mapeo para ese producto.

## Estructura de proveedores

Los parsers viven en:

```text
scripts/proveedores/
```

Por ahora esta implementado `coca_cola.py`. Para agregar proveedores como Quilmes o Arcor, crear un nuevo modulo en esa carpeta, implementar `es_proveedor(texto)` y `extraer_productos(texto)`, y registrarlo en `scripts/extraer_factura.py`.

## Base de datos

SQLite se guarda en:

```text
database/facturas.sqlite
```

Tablas:

- `providers`
- `product_mappings`

El archivo `.sqlite` esta ignorado por Git.
