#!/bin/sh
set -e

echo "Attente de MongoDB..."
python - << 'PY'
import os
import time
from pymongo import MongoClient

uri = os.getenv("MONGO_URI", "mongodb://mongo:27017")
deadline = time.time() + 60

while True:
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
        print("MongoDB est prêt.")
        break
    except Exception as e:
        if time.time() > deadline:
            raise SystemExit(f"MongoDB indisponible après 60s: {e}")
        time.sleep(2)
PY

echo "Lancement de la migration..."
exec "$@"