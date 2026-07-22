from __future__ import annotations

import sqlalchemy as sa


def orm_schema_gaps(engine, metadata) -> dict[str, object]:
    """Return mapped tables and columns absent from a physical database."""
    inspector = sa.inspect(engine)
    physical_tables = set(inspector.get_table_names())
    mapped_tables = set(metadata.tables)
    missing_columns = {}

    for table_name in sorted(mapped_tables & physical_tables):
        physical_columns = {
            column["name"] for column in inspector.get_columns(table_name)
        }
        mapped_columns = {
            column.name for column in metadata.tables[table_name].columns
        }
        if missing := sorted(mapped_columns - physical_columns):
            missing_columns[table_name] = missing

    return {
        "missing_tables": sorted(mapped_tables - physical_tables),
        "missing_columns": missing_columns,
    }
