#!/bin/sh
set -e

echo "Attente de MongoDB..."

python - <<'PY'
import os
import time
from pymongo import MongoClient

uri = os.getenv("MONGO_URI")
if not uri:
    raise ValueError("MONGO_URI manquant dans les variables d'environnement")

db_name = os.getenv("MONGO_DB", "medical_db")

# On essaye plusieurs fois car Mongo peut mettre un peu de temps à être prêt
for attempt in range(1, 31):
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=2000)

        # Ping sur la base applicative (plus sûr que admin)
        client[db_name].command("ping")

        print("MongoDB est prêt ✅")
        break
    except Exception as e:
        print(f"Tentative {attempt}/30 - Mongo pas prêt : {e}")
        time.sleep(2)
else:
    raise RuntimeError("MongoDB n'est pas prêt après plusieurs tentatives")
PY

echo "Lancement de la migration..."
exec "$@"