# Attendance Backend

API de gestion de présence avec géolocalisation utilisant FastAPI et PostGIS.

## Fonctionnalités

- **Étudiants** : Gestion des étudiants avec import CSV
- **Géofences** : Gestion des zones géographiques avec PostGIS
- **Fenêtres horaires** : Configuration des créneaux de présence
- **Vérification de présence** : Validation automatique basée sur la localisation et l'horaire
- **Audit** : Enregistrement des événements et décisions

## Démarrage rapide

```bash
# Copier le fichier d'environnement
cp .env.example .env

# Modifier les paramètres dans .env si nécessaire
# (ADMIN_USER, ADMIN_PASS, JWT_SECRET_KEY)

# Démarrer les services
docker compose up -d

# Vérifier que l'API fonctionne
curl http://localhost:8000/

# Tester l'authentification (optionnel)
python test_auth.py
```

## Endpoints

### Authentification
- `POST /auth/login` - Connexion avec JWT (admin/admin123 par défaut)

### Étudiants
- `GET /students` - Lister les étudiants (avec pagination et recherche) 🔓
- `POST /students` - Créer un étudiant 🔒
- `GET /students/{id}` - Récupérer un étudiant par ID 🔓
- `PUT /students/{id}` - Mettre à jour un étudiant 🔒
- `DELETE /students/{id}` - Supprimer un étudiant (suppression logique) 🔒
- `POST /students/import` - Importer des étudiants depuis un CSV 🔒

### Géofences
- `POST /geofence` - Créer/modifier une géofence (GeoJSON) 🔒
- `GET /geofence` - Lister les géofences 🔓

### Fenêtres horaires
- `POST /time-windows` - Remplacer toutes les fenêtres horaires 🔒
- `GET /time-windows` - Lister les fenêtres horaires 🔓

### Présence
- `POST /presence/check` - Vérifier la présence d'un étudiant 🔓

### Événements
- `GET /events` - Lister les événements avec filtres (matricule, dates) 🔒
- `GET /events/{id}` - Récupérer un événement par ID 🔒
- `GET /stats/daily` - Statistiques quotidiennes par date 🔒

**Légende :** 🔓 Public | 🔒 Authentification requise

## Exemple d'utilisation

### Authentification

#### Se connecter et obtenir un token JWT
```bash
# Connexion (admin/admin123 par défaut)
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

**Réponse :**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Utiliser le token pour les requêtes protégées
```bash
# Ajouter le token dans l'en-tête Authorization
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:8000/events"
```

#### Gestion des erreurs d'authentification

**Token manquant ou invalide :**
```json
{
  "detail": "Could not validate credentials"
}
```

**Identifiants incorrects :**
```json
{
  "detail": "Nom d'utilisateur ou mot de passe incorrect"
}
```

**Token expiré :**
```json
{
  "detail": "Could not validate credentials"
}
```

### Gestion des étudiants

#### Créer un étudiant (authentification requise)
```bash
# D'abord, obtenir un token JWT
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | \
  python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Créer un étudiant avec le token
curl -X POST "http://localhost:8000/students" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "matricule": "STU001",
    "nom": "Dupont",
    "prenom": "Jean",
    "is_active": true
  }'
```

#### Lister les étudiants avec pagination
```bash
curl "http://localhost:8000/students?q=Dupont&limit=10&offset=0"
```

#### Importer des étudiants depuis un CSV (authentification requise)
```bash
# Obtenir un token JWT
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | \
  python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Importer le CSV avec le token
curl -X POST "http://localhost:8000/students/import" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@students.csv"
```

**Format du fichier CSV :**
```csv
matricule,nom,prenom
STU001,Dupont,Jean
STU002,Martin,Marie
STU003,Bernard,Pierre
```

### Vérifier la présence
```bash
curl -X POST "http://localhost:8000/presence/check" \
  -H "Content-Type: application/json" \
  -d '{
    "matricule": "STU001",
    "lat": 48.8566,
    "lon": 2.3522,
    "accuracy": 10.0,
    "method": "auto"
  }'
```

### Gestion des événements

#### Lister les événements d'un étudiant (authentification requise)
```bash
# Obtenir un token JWT
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | \
  python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Lister les événements avec le token
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/events?matricule=STU001&from=2023-01-01T00:00:00&to=2023-01-31T23:59:59"
```

#### Récupérer un événement par ID (authentification requise)
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/events/1"
```

#### Statistiques quotidiennes (authentification requise)
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/stats/daily?date=2023-01-15"
```

**Réponse des statistiques :**
```json
{
  "date": "2023-01-15",
  "total_events": 25,
  "present_count": 20,
  "late_count": 3,
  "absent_count": 1,
  "outside_count": 1,
  "manual_count": 5,
  "auto_count": 20
}
```

### Créer une géofence (authentification requise)
```bash
# Obtenir un token JWT
TOKEN=$(curl -s -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | \
  python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Créer une géofence avec le token
curl -X POST "http://localhost:8000/geofence" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Campus Principal",
    "polygon": {
      "type": "Polygon",
      "coordinates": [[[2.3522, 48.8566], [2.3522, 48.8576], [2.3532, 48.8576], [2.3532, 48.8566], [2.3522, 48.8566]]]
    },
    "margin_m": 50
  }'
```

## Configuration

### Variables d'environnement

Créer un fichier `.env` basé sur `.env.example` :

```bash
# Base de données
DATABASE_URL=postgresql://attendance_user:attendance_pass@localhost:5432/attendance

# JWT (changer en production)
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Utilisateur admin
ADMIN_USER=admin
ADMIN_PASS=admin123
```

## Architecture

- **Base de données** : PostgreSQL avec PostGIS
- **API** : FastAPI avec SQLAlchemy
- **Authentification** : JWT (HS256) avec 30 minutes d'expiration
- **Géolocalisation** : PostGIS pour les opérations spatiales
- **Conteneurisation** : Docker Compose

## Règles de présence

1. Vérifier si une fenêtre horaire est active
2. Vérifier si le point est dans la géofence (ST_Contains)
3. Si dans la géofence → "present"
4. Si hors géofence + méthode manuelle → "late"
5. Sinon → "outside"

## Statuts d'événements

- **present** : Étudiant présent dans la géofence
- **late** : Étudiant en retard (vérification manuelle)
- **absent** : Étudiant absent (hors fenêtre horaire)
- **outside** : Étudiant hors géofence

