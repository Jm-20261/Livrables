# tests/test_integration_mongo.py
import os
import pytest
from pymongo import MongoClient
from dotenv import load_dotenv

pytestmark = pytest.mark.integration


def test_mongo_contains_data_record_id_and_index():
    # 1) Charger les variables du fichier .env (en local)
    load_dotenv()

    db_name = os.getenv("MONGO_DB", "medical_db")
    app_user = os.getenv("MONGO_APP_USER", "app_user")
    app_password = os.getenv("MONGO_APP_PASSWORD", "change_me_app")

    # 2) Connexion à Mongo exposé sur localhost par docker-compose
    mongo_uri = f"mongodb://{app_user}:{app_password}@localhost:27017/{db_name}?authSource={db_name}"

    client = MongoClient(mongo_uri)
    coll = client[db_name]["admissions"]

    # 3) Vérifier qu'il y a des données
    count = coll.count_documents({})
    assert count > 0, "Aucun document trouvé dans MongoDB (migration non exécutée ?)"

    # 4) Vérifier la présence de record_id
    doc = coll.find_one({})
    assert doc is not None
    assert "record_id" in doc, "record_id manquant dans un document"

    # 5) Vérifier l'index unique sur record_id
    indexes = coll.index_information()
    assert "uniq_record_id" in indexes, "Index uniq_record_id absent"