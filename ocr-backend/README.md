# Backend OCR — Suivi Matériel

Service d'analyse **sans stockage** : il authentifie l'appelant avec Firebase Admin, prétraite l'image en mémoire, exécute Tesseract (`fra+eng`) et retourne uniquement les codes et désignations suffisamment fiables. Il n'accède ni à Firestore ni à un SDK Firebase client.

## Installation locale

Prérequis : Python 3.12, Tesseract et les paquets de langues français/anglais.

```bash
cd ocr-backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export FIREBASE_PROJECT_ID="mon-projet"
export FIREBASE_SERVICE_ACCOUNT='{"type":"service_account", ...}'
uvicorn app.main:app --reload
```

Variables Render attendues :

- `FIREBASE_PROJECT_ID` : ID du projet Firebase utilisé par le frontend (et non son nom d'affichage) ;
- `FIREBASE_SERVICE_ACCOUNT` : JSON complet du compte de service sur une seule ligne. Son champ `project_id` doit être identique à `FIREBASE_PROJECT_ID`. Ne jamais enregistrer ce JSON dans Git.

Si `FIREBASE_SERVICE_ACCOUNT` est absente, Firebase Admin utilise les Application Default Credentials ; dans ce cas `FIREBASE_PROJECT_ID` reste obligatoire. Paramètres optionnels : `MAX_IMAGE_BYTES` (10 Mio), `MAX_IMAGE_DIMENSION` (2400 px), `OCR_RATE_LIMIT_PER_MINUTE` (30).

Les refus d'authentification sont classés sans journaliser le token, l'en-tête Authorization ou le compte de service : `TOKEN_MISSING`, `TOKEN_EXPIRED`, `TOKEN_INVALID`, `TOKEN_WRONG_PROJECT`, `SERVER_AUTH_CONFIG_ERROR`. Un utilisateur authentifié sans la custom claim requise reçoit `403 OCR_FORBIDDEN`.

Pour accorder l'accès, définir la custom claim booléenne `ocrAdmin: true` côté administration Firebase. Les rôles, e-mails et paramètres d'administration transmis par le client sont ignorés.

## Appel API

```bash
curl -X POST http://localhost:8000/v1/ocr/articles \
  -H "Authorization: Bearer $FIREBASE_ID_TOKEN" \
  -F "image=@liste.jpg"
```

Réponse :

```json
{
  "schemaVersion": "1.0",
  "articles": [
    {
      "code": "200LDV102350STD",
      "designation": "INTERMEDIAIRE INOX AUTO M12 INOX A2",
      "confidence": 0.92
    }
  ],
  "warnings": []
}
```

Les images JPG/JPEG, PNG et WebP sont acceptées. Elles sont décodées et traitées exclusivement en mémoire, puis les buffers sont libérés. Le texte OCR et le document ne sont jamais journalisés.

## Déploiement sur Render

1. Créer un **Web Service** depuis le dépôt.
2. Choisir l'environnement **Docker** et `ocr-backend/Dockerfile` comme chemin du Dockerfile (ou définir `ocr-backend` comme Root Directory).
3. Ajouter les variables secrètes `FIREBASE_PROJECT_ID` et `FIREBASE_SERVICE_ACCOUNT`.
4. Déployer. Le conteneur écoute automatiquement la variable `PORT` fournie par Render.

Le service renvoie des erreurs structurées avec `code`, `message` et `requestId`. Les statuts documentés sont 400, 401, 403, 413, 415, 422, 429 et 500.

## Tests

```bash
cd ocr-backend
pytest -q
```

Le contrat `OcrProvider` isole le moteur OCR afin de remplacer ultérieurement Tesseract par Google Vision, Document AI ou un autre fournisseur.
