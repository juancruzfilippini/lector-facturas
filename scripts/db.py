import json
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = BASE_DIR / "database" / "facturas.sqlite"


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalize_cuit(value):
    if value is None:
        return ""

    return "".join(char for char in str(value) if char.isdigit())


def normalize_text(value):
    if value is None:
        return ""

    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.lower().split())


def resolve_db_path(db_path=None):
    if db_path:
        return Path(db_path)

    return DEFAULT_DB_PATH


def get_connection(db_path=None):
    path = resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)
    return conn


def init_db(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            cuit TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS product_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider_id INTEGER NOT NULL,
            provider_product_code TEXT NOT NULL,
            provider_product_description TEXT,
            internal_product_code TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (provider_id) REFERENCES providers(id) ON DELETE CASCADE,
            UNIQUE (provider_id, provider_product_code)
        );

        CREATE INDEX IF NOT EXISTS idx_providers_cuit
            ON providers(cuit);

        CREATE INDEX IF NOT EXISTS idx_product_mappings_provider_code
            ON product_mappings(provider_id, provider_product_code);
        """
    )
    conn.commit()


def provider_to_dict(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "cuit": row["cuit"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def mapping_to_dict(row):
    return {
        "id": row["id"],
        "provider_id": row["provider_id"],
        "provider_name": row["provider_name"],
        "provider_product_code": row["provider_product_code"],
        "provider_product_description": row["provider_product_description"],
        "internal_product_code": row["internal_product_code"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_providers(conn):
    rows = conn.execute(
        """
        SELECT id, name, cuit, created_at, updated_at
        FROM providers
        ORDER BY name ASC, id ASC
        """
    ).fetchall()
    return [provider_to_dict(row) for row in rows]


def create_provider(conn, name, cuit=None):
    name = str(name or "").strip()
    cuit = normalize_cuit(cuit) or None

    if not name:
        raise ValueError("El nombre del proveedor es obligatorio")

    current_time = now_iso()
    cursor = conn.execute(
        """
        INSERT INTO providers (name, cuit, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        """,
        (name, cuit, current_time, current_time),
    )
    conn.commit()

    row = conn.execute(
        """
        SELECT id, name, cuit, created_at, updated_at
        FROM providers
        WHERE id = ?
        """,
        (cursor.lastrowid,),
    ).fetchone()
    return provider_to_dict(row)


def list_product_mappings(conn):
    rows = conn.execute(
        """
        SELECT
            pm.id,
            pm.provider_id,
            p.name AS provider_name,
            pm.provider_product_code,
            pm.provider_product_description,
            pm.internal_product_code,
            pm.created_at,
            pm.updated_at
        FROM product_mappings pm
        INNER JOIN providers p ON p.id = pm.provider_id
        ORDER BY p.name ASC, pm.provider_product_code ASC
        """
    ).fetchall()
    return [mapping_to_dict(row) for row in rows]


def create_product_mapping(
    conn,
    provider_id,
    provider_product_code,
    provider_product_description,
    internal_product_code,
):
    provider_id = int(provider_id)
    provider_product_code = str(provider_product_code or "").strip()
    provider_product_description = str(provider_product_description or "").strip()
    internal_product_code = str(internal_product_code or "").strip()

    if not provider_product_code:
        raise ValueError("El codigo de producto del proveedor es obligatorio")

    if not internal_product_code:
        raise ValueError("El codigo interno es obligatorio")

    provider = conn.execute(
        "SELECT id FROM providers WHERE id = ?",
        (provider_id,),
    ).fetchone()

    if provider is None:
        raise ValueError("El proveedor indicado no existe")

    current_time = now_iso()
    conn.execute(
        """
        INSERT INTO product_mappings (
            provider_id,
            provider_product_code,
            provider_product_description,
            internal_product_code,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(provider_id, provider_product_code)
        DO UPDATE SET
            provider_product_description = excluded.provider_product_description,
            internal_product_code = excluded.internal_product_code,
            updated_at = excluded.updated_at
        """,
        (
            provider_id,
            provider_product_code,
            provider_product_description,
            internal_product_code,
            current_time,
            current_time,
        ),
    )
    conn.commit()

    row = conn.execute(
        """
        SELECT
            pm.id,
            pm.provider_id,
            p.name AS provider_name,
            pm.provider_product_code,
            pm.provider_product_description,
            pm.internal_product_code,
            pm.created_at,
            pm.updated_at
        FROM product_mappings pm
        INNER JOIN providers p ON p.id = pm.provider_id
        WHERE pm.provider_id = ?
          AND pm.provider_product_code = ?
        """,
        (provider_id, provider_product_code),
    ).fetchone()
    return mapping_to_dict(row)


def find_provider_id(conn, proveedor):
    provider_cuit = normalize_cuit(proveedor.get("cuit"))
    aliases = [proveedor.get("name"), *proveedor.get("aliases", [])]
    normalized_aliases = [normalize_text(alias) for alias in aliases if alias]

    rows = conn.execute(
        "SELECT id, name, cuit FROM providers ORDER BY id ASC"
    ).fetchall()

    for row in rows:
        if provider_cuit and normalize_cuit(row["cuit"]) == provider_cuit:
            return row["id"]

    for row in rows:
        provider_name = normalize_text(row["name"])
        for alias in normalized_aliases:
            if alias and (alias in provider_name or provider_name in alias):
                return row["id"]

    return None


def ensure_provider_id(conn, proveedor):
    provider_id = find_provider_id(conn, proveedor)

    if provider_id is not None:
        return provider_id

    provider = create_provider(
        conn,
        proveedor.get("name") or proveedor.get("key") or "Proveedor",
        proveedor.get("cuit"),
    )
    return provider["id"]


def get_internal_product_code(conn, provider_id, provider_product_code):
    row = conn.execute(
        """
        SELECT internal_product_code
        FROM product_mappings
        WHERE provider_id = ?
          AND provider_product_code = ?
        """,
        (provider_id, str(provider_product_code).strip()),
    ).fetchone()

    if row is None:
        return None

    return row["internal_product_code"]


def json_dumps(data):
    return json.dumps(data, ensure_ascii=False)
