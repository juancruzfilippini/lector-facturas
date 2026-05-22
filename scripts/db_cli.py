import json
import sys

from db import (
    create_product_mapping,
    create_provider,
    get_connection,
    json_dumps,
    list_product_mappings,
    list_providers,
)


def read_payload():
    raw_payload = sys.stdin.read().strip()

    if not raw_payload:
        return {}

    return json.loads(raw_payload)


def main():
    if len(sys.argv) < 3:
        print(
            json_dumps(
                {
                    "ok": False,
                    "error": "Uso: python db_cli.py accion database.sqlite",
                }
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    action = sys.argv[1]
    db_path = sys.argv[2]
    payload = read_payload()

    try:
        with get_connection(db_path) as conn:
            if action == "list_providers":
                data = list_providers(conn)
            elif action == "create_provider":
                data = create_provider(
                    conn,
                    payload.get("name"),
                    payload.get("cuit"),
                )
            elif action == "list_product_mappings":
                data = list_product_mappings(conn)
            elif action == "create_product_mapping":
                data = create_product_mapping(
                    conn,
                    payload.get("provider_id"),
                    payload.get("provider_product_code"),
                    payload.get("provider_product_description"),
                    payload.get("internal_product_code"),
                )
            else:
                raise ValueError(f"Accion de base de datos no soportada: {action}")

        print(json_dumps({"ok": True, "data": data}))
    except Exception as error:
        print(json_dumps({"ok": False, "error": str(error)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
