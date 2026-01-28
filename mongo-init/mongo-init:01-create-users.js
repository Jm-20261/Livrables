// Exécuté automatiquement au 1er démarrage si /data/db est vide

const dbName = process.env.MONGO_INITDB_DATABASE || "medical_db";

const appUser = process.env.MONGO_APP_USER || "app_user";
const appPwd  = process.env.MONGO_APP_PASSWORD || "change_me";

const readUser = process.env.MONGO_READ_USER || "read_user";
const readPwd  = process.env.MONGO_READ_PASSWORD || "change_me";

db = db.getSiblingDB(dbName);

// User applicatif: lecture/écriture sur medical_db
db.createUser({
  user: appUser,
  pwd: appPwd,
  roles: [{ role: "readWrite", db: dbName }]
});

// User lecture seule: lecture sur medical_db
db.createUser({
  user: readUser,
  pwd: readPwd,
  roles: [{ role: "read", db: dbName }]
});