# Projet 5 — Migration CSV vers MongoDB (NoSQL)

## Contexte
Ce projet consiste à migrer un dataset médical fourni au format **CSV** vers une base NoSQL (MongoDB).
L’objectif est de livrer une solution **simple à exécuter**, **relançable** (idempotente) et **documentée**, puis de la **conteneuriser** avec Docker.

Dataset utilisé : `healthcare_dataset.csv` (Kaggle — healthcare dataset)

---

## Attendus OpenClassrooms (livrables)
Ce dépôt contient les éléments demandés pour le projet :

- **Script de migration** : import du CSV vers MongoDB (relançable, sans doublons).
- **`requirements.txt`** : dépendances Python nécessaires au script.
- **README** : explication de la logique, schéma des données, exécution locale + Docker, dépannage.
- **Docker** :
  - `docker-compose.yml` : lance MongoDB + exécute la migration
  - `Dockerfile` / `entrypoint.sh` : conteneurisation du script
  - **Volumes** : persistance MongoDB + montage du dossier CSV
- **Sécurité** :
  - authentification MongoDB activée
  - rôles utilisateurs documentés (admin / applicatif / lecture seule)
  - secrets non versionnés via `.env` (modèle fourni : `.env.example`)


---

## Objectifs

### Étape 1 — Script de migration
- Lire un fichier CSV
- Vérifier que le CSV contient les colonnes attendues
- Convertir les types (dates, nombres)
- Insérer les données dans MongoDB
- Éviter les doublons et permettre la relance du script (idempotence)
- Mettre en place des index pertinents

### Étape 2 — Docker
- Conteneuriser MongoDB et la migration
- Exécuter la migration via `docker compose`
- Utiliser des volumes (données MongoDB + dataset CSV)

---

## Concepts MongoDB
- **Base de données** : conteneur logique (ex: `medical_db`)
- **Collection** : ensemble de documents (ex: `admissions`)
- **Document** : une “fiche” JSON/BSON (équivalent d’une ligne, mais flexible)

---

## Schéma des données (collection `admissions`)
Chaque ligne du CSV correspond à une admission / séjour.
Le script stocke chaque ligne sous forme d’un document avec les champs :

- `name` (string)
- `age` (int)
- `gender` (string)
- `blood_type` (string)
- `medical_condition` (string)
- `date_of_admission` (date)
- `doctor` (string)
- `hospital` (string)
- `insurance_provider` (string)
- `billing_amount` (float)
- `room_number` (int)
- `admission_type` (string)
- `discharge_date` (date)
- `medication` (string)
- `test_results` (string)
- `record_id` (string, **unique**) : identifiant calculé à partir des valeurs de la ligne (hash)

---

## Logique de migration

### 1) Lecture + validation
Le script lit le CSV et vérifie la présence des colonnes attendues.
Si une colonne est manquante, le script s’arrête avec une erreur explicite.

### 2) Typage des champs
Le CSV contient souvent des valeurs au format texte.
Le script convertit :
- `Date of Admission`, `Discharge Date` -> `datetime`
- `Age`, `Room Number` -> `int`
- `Billing Amount` -> `float`

### 3) Anti-doublons avec `record_id` + index unique
Le script calcule un champ `record_id` (hash SHA256) basé sur les valeurs de la ligne.
Deux lignes identiques produisent le même `record_id`.
Un **index unique** sur `record_id` empêche l’insertion de doublons.

### 4) Upsert (migration relançable)
Le script utilise des opérations **upsert** :
- si `record_id` n’existe pas -> insertion
- si `record_id` existe -> mise à jour

Ainsi, le script peut être relancé sans dupliquer les données.

### 5) Insertion par lots (bulk)
Les insertions se font par lots (`batch_size`) via `bulk_write` pour de meilleures performances.

---

## Index créés
- `uniq_record_id` (unique) : empêche les doublons et garantit l’idempotence
- `idx_medical_condition` : accélère les recherches par pathologie
- `idx_hospital` : accélère les recherches par hôpital
- `idx_doctor` : accélère les recherches par médecin
- `idx_date_of_admission_desc` : accélère les tris par date d’admission
- `idx_hospital_date` : accélère les requêtes par hôpital + tri date

---

## Authentification et rôles (sécurité)
MongoDB est configuré avec authentification et **3 profils** (principe du moindre privilège) :

### 1) Administrateur (maintenance)
- Utilisateur : `mongo_admin`
- Base d’authentification : `admin`
- Rôle : `root`
- Usage : opérations d’administration uniquement (création d’utilisateurs, maintenance).

### 2) Utilisateur applicatif (migration)
- Utilisateur : `app_user`
- Base d’authentification : `medical_db`
- Rôle : `readWrite` sur `medical_db`
- Usage : utilisé par le conteneur `migrate` pour écrire dans la base.

### 3) Utilisateur lecture seule
- Utilisateur : `read_user`
- Base d’authentification : `medical_db`
- Rôle : `read` sur `medical_db`
- Usage : consultation via MongoDB Compass / BI sans droit d’écriture.

> Important : les scripts d’initialisation `mongo-init/` ne s’exécutent qu’au **premier démarrage** si le volume MongoDB est vide.

---

## Fichiers importants du projet
- `migrate_csv_to_mongodb.py` : script de migration CSV -> MongoDB
- `requirements.txt` : dépendances Python
- `docker-compose.yml` : orchestration MongoDB + migration
- `Dockerfile` : image du conteneur de migration
- `entrypoint.sh` : point d’entrée (si utilisé)
- `mongo-init/01-create-users.js` : création des utilisateurs MongoDB (app + read-only)
- `.env.example` : modèle de configuration (sans secrets)
- `.env` : configuration locale (non versionnée)

---

## Prérequis
- Python 3.10+ (optionnel si exécution sans Docker)
- Docker Desktop installé et lancé
- MongoDB Compass (optionnel, utile pour visualiser)

---

## Étape 1 — Exécution sans Docker (local)

### 1) Créer un environnement virtuel
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Installer les dépendances
```bash
pip install -r requirements.txt
```

### 3) Lancer MongoDB (local)
MongoDB doit être démarré et accessible sur :
```text
mongodb://localhost:27017
```

### 4) Exécuter le script de migration (local)
Placer le fichier CSV dans `data/healthcare_dataset.csv` puis exécuter :
```bash
python migrate_csv_to_mongodb.py --csv data/healthcare_dataset.csv
```

Paramètres disponibles :
- `--mongo-uri` : URI MongoDB (défaut `mongodb://localhost:27017`)
- `--db` : base MongoDB (défaut `medical_db`)
- `--collection` : collection (défaut `admissions`)
- `--batch-size` : taille des lots (défaut `5000`)

Exemple complet :
```bash
python migrate_csv_to_mongodb.py \
  --csv data/healthcare_dataset.csv \
  --mongo-uri mongodb://localhost:27017 \
  --db medical_db \
  --collection admissions \
  --batch-size 5000
```

### 5) Vérification rapide
Après migration, le dataset dédoublonné contient environ **54 966** documents.

---

## Étape 2 — Exécution avec Docker Compose

### Configuration (variables d’environnement)
Créer un fichier `.env` à la racine (ne pas le versionner) en s’appuyant sur `.env.example`.

Exemple `.env` :
```env
MONGO_DB=medical_db

MONGO_ROOT_USER=mongo_admin
MONGO_ROOT_PASSWORD=change_me_admin

MONGO_APP_USER=app_user
MONGO_APP_PASSWORD=change_me_app

MONGO_READ_USER=read_user
MONGO_READ_PASSWORD=change_me_read
```

Le fichier `.env` est ignoré par Git via `.gitignore` (seuls `.env.example` et le code sont versionnés).

### 1) Démarrer MongoDB + lancer la migration
Depuis la racine du projet :
```bash
docker compose up --build
```

- Le service `mongo` démarre MongoDB avec authentification
- Le service `migrate` exécute la migration puis se termine automatiquement

### 2) Vérifier l’état des conteneurs
```bash
docker compose ps
```

Attendu :
- `mongo` : Up (healthy)
- `migrate` : Exited (0) une fois la migration terminée

### 3) Logs
Logs migration :
```bash
docker compose logs -f migrate
```

Logs MongoDB :
```bash
docker compose logs -f mongo
```

### 4) Arrêter
```bash
docker compose down
```

### 5) Réinitialiser complètement la base (⚠️ supprime les données)
Comme `mongo-init/` ne s’exécute qu’au premier démarrage, il faut supprimer le volume si l’on change les utilisateurs/mots de passe :
```bash
docker compose down -v
docker compose up --build
```
---

## Tests (unitaires + intégration)

Il y a **5 tests au total** :
- **4 tests unitaires** (rapides, sans MongoDB)
- **1 test d’intégration** (vérifie les données dans MongoDB après migration)

L’objectif des tests est de prouver que :
- le CSV contient bien les **colonnes attendues**
- le calcul de `record_id` est **stable** (même ligne → même id, ligne différente → id différent)
- la migration a bien **inséré des données** dans MongoDB
- l’index unique sur `record_id` est bien créé

> Les tests sont exécutés avec **pytest**.

## Lancer les test

python -m pytest -q

---

## Connexion MongoDB Compass (avec authentification)
Recommandation : utiliser `127.0.0.1` et `directConnection=true` pour éviter les soucis `localhost/IPv6`.

### Lecture seule
```text
mongodb://read_user:<MOT_DE_PASSE>@127.0.0.1:27017/medical_db?authSource=medical_db&directConnection=true
```

### Lecture/écriture (migration)
```text
mongodb://app_user:<MOT_DE_PASSE>@127.0.0.1:27017/medical_db?authSource=medical_db&directConnection=true
```

### Admin
```text
mongodb://mongo_admin:<MOT_DE_PASSE>@127.0.0.1:27017/admin?authSource=admin&directConnection=true
```

---

## Dépannage (Troubleshooting)

### La base / les utilisateurs ne se créent pas
Les scripts `mongo-init/` ne s’exécutent qu’au premier démarrage si le volume est vide.  
Solution :
```bash
docker compose down -v
docker compose up --build
```

### Erreur de montage `mongo-init` (not a directory)
Vérifier que `mongo-init` est bien un dossier et contient `01-create-users.js`.

### Compass ne voit pas `medical_db`
- Vérifier que la connexion Compass utilise `127.0.0.1:27017`
- Ajouter `directConnection=true`
- Vérifier que le port est exposé :
```bash
docker compose ps
```
