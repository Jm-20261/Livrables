import pandas as pd
import pytest

from migrate_csv_to_mongodb import EXPECTED_COLUMNS, load_csv, compute_record_id


def _dummy_value_for_column(col_name: str):
    """Retourne une valeur simple selon le nom de colonne."""
    name = col_name.lower()
    if "date" in name:
        return "2022-01-01"
    if "amount" in name or "billing" in name:
        return "123.45"
    if "age" in name or "number" in name or "room" in name:
        return "1"
    return "test"


def test_load_csv_ok_columns_and_row_count(tmp_path):
    """
    - le CSV contient toutes les colonnes attendues
    - load_csv lit bien le fichier
    - le nombre de lignes est correct
    """
    rows = []
    for i in range(3):
        row = {col: _dummy_value_for_column(col) for col in EXPECTED_COLUMNS}
        row[EXPECTED_COLUMNS[0]] = f"row_{i}"  # différencier les lignes
        rows.append(row)

    df = pd.DataFrame(rows)
    csv_path = tmp_path / "ok.csv"
    df.to_csv(csv_path, index=False)

    loaded = load_csv(str(csv_path))

    assert len(loaded) == 3
    assert set(EXPECTED_COLUMNS).issubset(set(loaded.columns))


def test_load_csv_raises_if_missing_expected_column(tmp_path):
    """
    - si une colonne attendue manque, load_csv doit lever une erreur
    """
    cols = list(EXPECTED_COLUMNS)
    cols.pop()  # on retire 1 colonne attendue

    df = pd.DataFrame([{col: _dummy_value_for_column(col) for col in cols}])
    csv_path = tmp_path / "bad.csv"
    df.to_csv(csv_path, index=False)

    with pytest.raises(Exception) as exc:
        load_csv(str(csv_path))

    msg = str(exc.value).lower()
    assert "missing" in msg or "manquant" in msg or "column" in msg


def test_compute_record_id_is_stable():
    """
    - même ligne => même record_id
    """
    row = {col: _dummy_value_for_column(col) for col in EXPECTED_COLUMNS}

    # ✅ compute_record_id attend aussi "keys"
    id1 = compute_record_id(row, EXPECTED_COLUMNS)
    id2 = compute_record_id(row, EXPECTED_COLUMNS)

    assert id1 == id2
    assert isinstance(id1, str)
    assert len(id1) > 10


def test_compute_record_id_is_different_for_different_rows():
    """
    - si on change la donnée, record_id doit changer
    """
    row1 = {col: _dummy_value_for_column(col) for col in EXPECTED_COLUMNS}
    row2 = {col: _dummy_value_for_column(col) for col in EXPECTED_COLUMNS}

    row2[EXPECTED_COLUMNS[0]] = "different_value"

    id1 = compute_record_id(row1, EXPECTED_COLUMNS)
    id2 = compute_record_id(row2, EXPECTED_COLUMNS)

    assert id1 != id2