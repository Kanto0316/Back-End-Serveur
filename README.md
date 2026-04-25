# Back-End-Serveur (Node.js + Express)

API backend prête pour Render pour convertir un fichier Excel (`.xlsx`/`.xls`) en JSON téléchargeable.

## Stack

- Node.js
- Express
- multer
- xlsx
- cors

## Endpoint principal

### `POST /api/excel-to-json`

- Upload attendu via `multipart/form-data`
- Champ fichier : **`file`**
- Taille max : **5MB**
- Extensions autorisées : **.xlsx** et **.xls**

### Comportement

1. Reçoit le fichier Excel
2. Lit uniquement la première feuille
3. Cherche les colonnes :
   - `code` / `Code` / `CODE`
   - `Désignation` / `Designation` / `designation`
4. Nettoie les valeurs :
   - conversion en string
   - `trim()`
   - ignore les lignes totalement vides
5. Retourne un fichier JSON téléchargeable :
   - `Content-Type: application/json`
   - `Content-Disposition: attachment; filename="suggestions.json"`

Format retourné :

```json
[
  {
    "code": "ABC123",
    "designation": "Produit exemple"
  }
]
```

## Endpoints utilitaires

- `GET /health` → `{ "status": "ok" }`

## Gestion d'erreurs

- `400` : fichier absent, extension invalide, fichier trop volumineux, colonnes manquantes, Excel vide
- `500` : erreur interne serveur

Format erreur :

```json
{ "error": "message clair" }
```

## CORS

- Autorise automatiquement :
  - Origines `*.github.io`
  - `http://localhost...`
- Vous pouvez fixer une origine explicite via `FRONTEND_ORIGIN`.

## Lancement local

```bash
npm install
npm start
```

Par défaut : port `10000`, ou `process.env.PORT` (compatible Render).

## Déploiement Render

- Runtime : **Node**
- Build Command :
  ```bash
  npm install
  ```
- Start Command :
  ```bash
  npm start
  ```
