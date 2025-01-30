import os
from django.db import migrations
from django.db.utils import ProgrammingError
def safe_run_sql(sql_files):
    """
    Safely create migrations.RunSQL operations from a list of SQL file paths.
    Handles FileNotFoundError for missing files and lets ProgrammingError surface naturally.
    """
    operations = []
    for file_path in sql_files:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"SQL file not found: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as sql_file:
                sql = sql_file.read()
            operations.append(migrations.RunSQL(sql=sql, reverse_sql=None))
        except ProgrammingError as pe:
            raise ProgrammingError(
                f"SQL syntax error in file {file_path}: {pe}"
            ) from pe
        except Exception as e:
            raise RuntimeError(
                f"Unexpected error in file {file_path}: {e}"
            ) from e
    return operations
