CREATE TABLE IF NOT EXISTS filieres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    code TEXT NOT NULL,
    niveau TEXT NOT NULL,
    UNIQUE(code, niveau)
);

CREATE TABLE IF NOT EXISTS modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    id_filiere INTEGER,
    semestre TEXT NOT NULL,
    bloc_competence TEXT,
    volume_heures INTEGER NOT NULL,
    credits INTEGER,
    FOREIGN KEY (id_filiere) REFERENCES filieres(id)
);

CREATE TABLE IF NOT EXISTS etudiants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_inscriptionsessionprogramme INTEGER UNIQUE NOT NULL,
    nom TEXT NOT NULL,
    prenom TEXT NOT NULL,
    email TEXT UNIQUE,
    id_filiere INTEGER,
    cursus TEXT,
    session_programme TEXT,
    FOREIGN KEY (id_filiere) REFERENCES filieres(id)
);

CREATE TABLE IF NOT EXISTS absences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_absence_konosys TEXT UNIQUE NOT NULL,
    id_etudiant INTEGER NOT NULL,
    id_module INTEGER,
    module_nom TEXT NOT NULL,
    date_absence DATE NOT NULL,
    seance TEXT,
    heure TEXT,
    duree_heures REAL NOT NULL,
    justifiee BOOLEAN NOT NULL,
    motif TEXT,
    FOREIGN KEY (id_etudiant) REFERENCES etudiants(id),
    FOREIGN KEY (id_module) REFERENCES modules(id)
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_etudiant INTEGER UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    created_at DATETIME,
    last_login DATETIME,
    FOREIGN KEY (id_etudiant) REFERENCES etudiants(id)
);

CREATE TABLE IF NOT EXISTS alertes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_etudiant INTEGER NOT NULL,
    id_module INTEGER NOT NULL,
    statut TEXT NOT NULL,
    taux_nj REAL NOT NULL,
    taux_total REAL NOT NULL,
    avert_envoye BOOLEAN DEFAULT 0,
    exclu_envoye BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(id_etudiant, id_module),
    FOREIGN KEY (id_etudiant) REFERENCES etudiants(id),
    FOREIGN KEY (id_module) REFERENCES modules(id)
);

CREATE TABLE IF NOT EXISTS emails_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_alerte INTEGER,
    destinataire TEXT NOT NULL,
    sujet TEXT,
    type_email TEXT,
    envoye BOOLEAN DEFAULT 0,
    envoye_le DATETIME,
    FOREIGN KEY (id_alerte) REFERENCES alertes(id)
);

CREATE INDEX IF NOT EXISTS idx_absences_etudiant ON absences(id_etudiant);
CREATE INDEX IF NOT EXISTS idx_absences_module ON absences(id_module);
CREATE INDEX IF NOT EXISTS idx_alertes_etudiant ON alertes(id_etudiant);
