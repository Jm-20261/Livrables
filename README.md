# Projet 5 — Migration CSV vers MongoDB (NoSQL)

## Contexte
Ce projet consiste à migrer un dataset médical fourni au format CSV vers une base de données NoSQL (MongoDB).
L’objectif est d’obtenir un script simple à exécuter, relançable, et qui stocke les données avec des types cohérents.

Dataset utilisé : `healthcare_dataset.csv` (Kaggle - healthcare dataset)

---

## Objectifs de l’étape 1
- Lire un fichier CSV
- Vérifier que le CSV contient les colonnes attendues
- Convertir les types (dates, nombres)
- Insérer les données dans MongoDB
- Éviter les doublons et permettre la relance du script (idempotence)
- Mettre en place des index pertinents

---

## Concepts MongoDB (rappel)
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
- `record_id` (string, unique) : identifiant calculé à partir des valeurs de la ligne

---

## Logique de migration

### 1) Lecture + validation
Le script lit le CSV et vérifie la présence des colonnes attendues.
Si une colonne est manquante, le script s’arrête avec une erreur explicite.

### 2) Typage des champs
Le CSV contient souvent des valeurs au format texte.
Le script convertit :
- `Date of Admission`, `Discharge Date` -> `datetime`
- `Age`, `Room Number` -> entiers
- `Billing Amount` -> float

Cela permet ensuite des filtres, tris et agrégations fiables en base.

### 3) Anti-doublons avec `record_id` + index unique
Le dataset peut contenir des doublons exacts.
Le script calcule un champ `record_id` (hash SHA256) basé sur les valeurs de la ligne :
- deux lignes identiques produisent le même `record_id`

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

## Prérequis
- Python 3.10+ (recommandé)
- MongoDB en local (ou accessible via une URI)
- MongoDB Compass (optionnel, utile pour visualiser)

---

## Installation

### 1) Créer un environnement virtuel
```bash
python -m venv .venv
source .venv/bin/activate

### 2) Installer les dépendances
pip install -r requirements.txt