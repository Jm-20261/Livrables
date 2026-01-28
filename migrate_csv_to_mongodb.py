import argparse
import hashlib
import logging
import os

import pandas as pd
from pymongo import MongoClient, UpdateOne, ASCENDING, DESCENDING


logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

# Définit les colonnes attendues dans le dataset
EXPECTED_COLUMNS = [
    "Name", "Age", "Gender", "Blood Type", "Medical Condition",
    "Date of Admission", "Doctor", "Hospital", "Insurance Provider",
    "Billing Amount", "Room Number", "Admission Type", "Discharge Date",
    "Medication", "Test Results"
]

# Définit la table de renommage des colonnes en snake_case pour une meilleure lisibilité
RENAME_MAP = {
    "Name": "name",
    "Age": "age",
    "Gender": "gender",
    "Blood Type": "blood_type",
    "Medical Condition": "medical_condition",
    "Date of Admission": "date_of_admission",
    "Doctor": "doctor",
    "Hospital": "hospital",
    "Insurance Provider": "insurance_provider",
    "Billing Amount": "billing_amount",
    "Room Number": "room_number",
    "Admission Type": "admission_type",
    "Discharge Date": "discharge_date",
    "Medication": "medication",
    "Test Results": "test_results",
}


def compute_record_id(doc: dict, keys: list[str]) -> str:
    """
    Crée un identifiant stable pour une ligne.
    Deux lignes identiques produisent le même record_id.
    """
    raw = "|".join("" if doc.get(k) is None else str(doc.get(k)).strip() for k in keys)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_csv(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    missing_cols = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Colonnes manquantes dans le CSV: {missing_cols}")

    duplicate_rows = int(df.duplicated().sum())
    logging.info(f"CSV chargé: {len(df)} lignes | doublons exacts détectés: {duplicate_rows}")
    return df


def cast_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convertit les types afin que MongoDB stocke des valeurs exploitables :
    - dates: datetime
    - nombres: int/float
    """
    df = df.copy()

    # Convertit les colonnes de dates en datetime
    df["Date of Admission"] = pd.to_datetime(df["Date of Admission"], errors="coerce")
    df["Discharge Date"] = pd.to_datetime(df["Discharge Date"], errors="coerce")

    # Convertit les colonnes numériques en int/float
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce").astype("Int64")
    df["Room Number"] = pd.to_numeric(df["Room Number"], errors="coerce").astype("Int64")
    df["Billing Amount"] = pd.to_numeric(df["Billing Amount"], errors="coerce")

    # Nettoie légèrement les colonnes texte (suppression des espaces en début/fin)
    for col in ["Name", "Doctor", "Hospital", "Insurance Provider", "Medical Condition", "Medication"]:
        df[col] = df[col].astype(str).str.strip()

    return df


def connect_mongo(uri: str, db_name: str, collection_name: str):
    # Établit la connexion à MongoDB et retourne la collection cible
    client = MongoClient(uri)
    coll = client[db_name][collection_name]
    return client, coll


def ensure_indexes(coll):
    """
    Crée les index nécessaires :
    - un index unique sur record_id pour empêcher les doublons et rendre la migration relançable
    - des index supplémentaires pour accélérer les recherches fréquentes
    """
    coll.create_index([("record_id", ASCENDING)], unique=True, name="uniq_record_id")
    coll.create_index([("medical_condition", ASCENDING)], name="idx_medical_condition")
    coll.create_index([("hospital", ASCENDING)], name="idx_hospital")
    coll.create_index([("doctor", ASCENDING)], name="idx_doctor")
    coll.create_index([("date_of_admission", DESCENDING)], name="idx_date_of_admission_desc")
    coll.create_index([("hospital", ASCENDING), ("date_of_admission", DESCENDING)], name="idx_hospital_date")


def migrate_dataframe_to_mongo(df: pd.DataFrame, coll, batch_size: int = 5000):
    """
    Transforme les lignes du CSV en documents MongoDB et les écrit en base par lots.
    Utilise upsert pour éviter les doublons et permettre la relance du script.
    """
    # Renomme les colonnes selon la table RENAME_MAP
    df2 = df.rename(columns=RENAME_MAP)

    # Remplace les NaN/NaT par None pour une meilleure compatibilité MongoDB
    df2 = df2.where(pd.notnull(df2), None)

    # Transforme le DataFrame en liste de dictionnaires (1 dictionnaire = 1 document)
    records = df2.to_dict(orient="records")
    if not records:
        logging.warning("Aucune donnée à migrer.")
        return

    # Définit l’ordre des clés utilisé pour calculer record_id de manière stable
    record_keys = list(df2.columns)

    total = len(records)
    logging.info(f"Début migration: {total} enregistrements (batch_size={batch_size})")

    # Traite les enregistrements par lots afin d’améliorer les performances
    for start in range(0, total, batch_size):
        chunk = records[start:start + batch_size]
        ops = []

        # Construit les opérations MongoDB (upsert) pour chaque document du lot
        for doc in chunk:
            doc["record_id"] = compute_record_id(doc, record_keys)
            ops.append(
                UpdateOne(
                    {"record_id": doc["record_id"]},
                    {"$set": doc},
                    upsert=True
                )
            )

        # Exécute les opérations en bulk pour accélérer l’insertion/mise à jour
        res = coll.bulk_write(ops, ordered=False)
        logging.info(
            f"Batch {start//batch_size + 1}: upserts={res.upserted_count} matched={res.matched_count} modified={res.modified_count}"
        )

    logging.info("Migration terminée.")


def main():
    parser = argparse.ArgumentParser(description="Migration CSV -> MongoDB (dataset healthcare)")
    parser.add_argument("--csv", required=True, help="Chemin du fichier CSV")
    parser.add_argument("--mongo-uri", default=os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    parser.add_argument("--db", default=os.getenv("MONGO_DB", "medical_db"))
    parser.add_argument("--collection", default=os.getenv("MONGO_COLLECTION", "admissions"))
    parser.add_argument("--batch-size", type=int, default=5000, help="Taille des lots pour bulk_write")
    args = parser.parse_args()

    df = load_csv(args.csv)
    df = cast_types(df)

    client, coll = connect_mongo(args.mongo_uri, args.db, args.collection)
    ensure_indexes(coll)

    before = coll.count_documents({})
    logging.info(f"Documents avant migration: {before}")

    migrate_dataframe_to_mongo(df, coll, batch_size=args.batch_size)

    after = coll.count_documents({})
    logging.info(f"Documents après migration: {after}")

    client.close()
    logging.info("Fin.")


if __name__ == "__main__":
    main()
