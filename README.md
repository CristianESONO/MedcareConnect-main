# MedCare Connect

MedCare Connect est une plateforme de services de santé qui permet de trouver des services et des professionnels de santé, de gérer les demandes des patients et d’accompagner les établissements et les praticiens.

## Architecture

- **Backend Django** (`backend/`) : authentification et sessions, autorisations, règles métier, points de terminaison d’API, interface d’administration Django et pages qui n’ont pas encore été migrées vers React.
- **Frontend React** (`frontend/`) : application monopage adaptative, développée avec React, TypeScript, Vite, Tailwind CSS et React Router.
- **Déploiement du frontend** : Vite génère l’application dans `backend/static/react/`. Django sert le point d’entrée React pour les routes migrées ; Django et WhiteNoise/Nginx servent les ressources statiques.
- **Ressources et données partagées** : les ressources statiques de Django se trouvent dans `backend/static/`, les fichiers téléversés dans `media/` et la documentation de référence du projet et du catalogue dans `documents/`.
- **Déploiement** : en production, Django/Gunicorn peut être exécuté derrière Nginx installé sur le système, ou via le Dockerfile et la configuration Docker Compose fournis.

React ne remplace ni l’authentification ni la logique métier de Django. Le navigateur utilise les API de Django et les cookies de session ; certaines routes qui n’ont pas encore été migrées utilisent toujours les modèles Django.

## Prérequis

- Python 3.12 (l’image Docker utilise Python 3.12)
- Node.js 22.12 ou version ultérieure et npm (la compilation Docker utilise Node.js 22)
- Git
- SQLite pour le développement local ou PostgreSQL pour la production

## Développement local

Exécutez ces commandes depuis la racine du dépôt.

### 1. Configurer Django

**Windows PowerShell**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python backend/manage.py migrate
python backend/manage.py runserver
```

**Linux/macOS**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python backend/manage.py migrate
python backend/manage.py runserver
```

Django est accessible à l’adresse `http://127.0.0.1:8000`.

### 2. Lancer React en mode développement

Dans un deuxième terminal :

```bash
npm ci --prefix frontend
npm run dev --prefix frontend
```

Ouvrez `http://localhost:5173`. Vite redirige les routes du backend et les API vers Django sur le port 8000.

### 3. Compiler React pour Django

```bash
npm ci --prefix frontend
npm run build --prefix frontend
python backend/manage.py collectstatic --noinput
```

Le point d’entrée compilé doit se trouver dans `backend/static/react/index.html` ; les ressources de Vite sont générées à côté. Django rassemble les ressources de production dans `staticfiles/`.

## Configuration

Django lit les variables d’environnement dans le fichier `.env` à la racine du dépôt si elles n’ont pas déjà été définies par le gestionnaire de processus. Ne validez pas le fichier `.env` et ne stockez pas d’identifiants de production dans le dépôt.

En production, configurez au minimum :

```dotenv
DEBUG=False
SECRET_KEY=<generate-a-unique-secret>
ALLOWED_HOSTS=app.example.com
CSRF_TRUSTED_ORIGINS=https://app.example.com
HTTPS_ENABLED=True
TRUST_PROXY_HEADERS=True
```

Générez localement un secret sur le serveur :

```bash
python -c 'import secrets; print(secrets.token_urlsafe(64))'
```

Par défaut, Django utilise SQLite à la racine du dépôt. Pour utiliser PostgreSQL, définissez `DATABASE_URL` avec une valeur commençant par `postgres`, puis configurez `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` et `POSTGRES_PORT`. Assurez-vous que seuls les comptes nécessaires au service peuvent lire les fichiers d’environnement de production.

## Tests et vérifications

```bash
python backend/manage.py check
python backend/manage.py test
npm run build --prefix frontend
npm run lint --prefix frontend
```

Les dépendances facultatives pour les tests de navigateur et l’assurance qualité sont répertoriées dans `backend/requirements-dev.txt`.

## Déploiement en production

Sur un serveur utilisant systemd/Gunicorn, mettez le code à jour, compilez React, puis exécutez le script de déploiement :

```bash
cd /usr/local/etc/MedcareConnect
git pull --ff-only origin main
npm ci --prefix frontend
npm run build --prefix frontend
bash backend/scripts/deploy_server_update.sh
```

Le script installe les dépendances Python, applique les migrations, collecte les fichiers statiques, synchronise le catalogue de services de référence et redémarre le service systemd `medcareconnect`. Compilez React avant de l’exécuter afin que l’application Django déployée utilise la version correspondante du frontend.

Comme le paquet du projet Django se trouve dans `backend/`, l’unité systemd doit utiliser ce répertoire comme répertoire de travail. Par exemple, un fichier de surcharge pour `/usr/local/etc/MedcareConnect` peut contenir :

```ini
[Service]
WorkingDirectory=/usr/local/etc/MedcareConnect/backend
Environment="PYTHONPATH=/usr/local/etc/MedcareConnect/backend"
```

Après avoir modifié une unité ou un fichier de surcharge, exécutez `systemctl daemon-reload`, puis redémarrez le service. Configurez Nginx pour qu’il redirige les routes de l’application vers Gunicorn et serve `/static/` depuis le répertoire indiqué par `STATIC_ROOT` (`staticfiles/`). Veillez à configurer HTTPS et les en-têtes de proxy transférés pour le domaine de production.

Avec Docker :

```bash
docker compose up -d --build
```

Docker compile React dans le cadre du Dockerfile et collecte les ressources statiques au démarrage du conteneur web. Configurez le fichier d’environnement attendu par `docker-compose.yml` avant de démarrer l’ensemble des services.

## Organisation du dépôt

```text
backend/       Projet Django, applications, migrations, tests, scripts et ressources statiques Django
frontend/      Application monopage React + TypeScript et configuration Vite
nginx/         Configuration Nginx pour le déploiement Docker
documents/     Documents de référence et documentation du projet
media/         Fichiers téléversés par les utilisateurs
```
