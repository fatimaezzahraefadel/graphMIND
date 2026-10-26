# GraphMind — Plateforme d'analytique sur graphe de connaissances

## Prérequis
- Python 3.11 (obligatoire — voir `.python-version`)
- Docker Desktop ≥ 4.x
- pyenv (recommandé) ou installer Python 3.11 manuellement

## Installation

### 1. Cloner le dépôt
```bash
git clone <url>
cd GraphMind
```

### 2. Créer le venv Python 3.11
```bash
# Avec pyenv
pyenv install 3.11.9
pyenv local 3.11.9

# Créer et activer le venv
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate
```

### 3. Installer les dépendances
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Copier et configurer les variables d'environnement
```bash
cp .env.example .env
# Éditer .env avec vos valeurs
```

### 5. Lancer les tests
```bash
pytest tests/phase1_ingestion/ -v
```

## Architecture
Voir `.kiro/specs/ai-knowledge-graph-analytics/design.md`

## Note Dockerfile
Toutes les images Docker de ce projet utilisent `python:3.11-slim` comme image de base.
