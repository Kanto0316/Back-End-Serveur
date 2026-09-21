# Backend Suivi Matériel

API Express sécurisée chargée de gérer dans Cloudinary les images associées aux documents **OUT**, et de conserver leurs métadonnées dans Firestore.

## Prérequis

- Node.js 20 ou supérieur ;
- un compte Cloudinary avec ses identifiants d'API ;
- un projet Firebase et un compte de service Firebase Admin ;
- l'URL publique du frontend autorisé.

## Installation locale

```bash
cd Backend
npm install
cp .env.example .env
```

Renseigner ensuite les variables dans `.env`, puis démarrer l'API :

```bash
npm start
```

Le serveur écoute par défaut sur `http://localhost:3000`. Pour le développement local, utiliser par exemple `FRONTEND_URL=http://localhost:5173`.

## Variables d'environnement

| Variable | Obligatoire | Description |
| --- | --- | --- |
| `CLOUDINARY_CLOUD_NAME` | Oui | Nom du cloud Cloudinary |
| `CLOUDINARY_API_KEY` | Oui | Clé API Cloudinary |
| `CLOUDINARY_API_SECRET` | Oui | Secret API Cloudinary, uniquement côté serveur |
| `FRONTEND_URL` | Oui | Origine exacte autorisée par CORS, sans chemin (ex. `https://app.example.com`) |
| `FIREBASE_SERVICE_ACCOUNT` | Selon l'hébergement | JSON complet du compte de service Firebase sur une seule ligne |
| `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY` | Selon l'hébergement | Alternative séparée au JSON ; inutiles avec les identifiants Google par défaut |
| `MAX_IMAGE_SIZE_BYTES` | Non | Taille maximale d'une image, 5 Mio par défaut |
| `PORT` | Non | Port HTTP ; Render fournit automatiquement cette valeur |

Ne jamais commiter le fichier `.env` ni exposer le secret Cloudinary dans le frontend.

## API

### État du service

```http
GET /
```

Réponse :

```json
{
  "status": "API Suivi Matériel active"
}
```

Toutes les routes OUT exigent un jeton Firebase ID (`Authorization: Bearer <token>`), un utilisateur Firebase existant et actif, et le rôle `ADMIN` dans le custom claim Firebase ou dans `USERS/{uid}.role`. Le `userId` fourni doit être celui du jeton.

### Ajouter une image à un OUT

```http
POST /api/out/upload-image
Authorization: Bearer <token>
Content-Type: multipart/form-data

image=<fichier>
outId=<identifiant OUT>
userId=<uid Firebase>
```

JPEG, PNG, WebP et GIF sont acceptés. Le type déclaré et la signature binaire sont contrôlés. Pour éviter de rendre l'ancienne image orpheline, il faut supprimer l'image existante avant de la remplacer.

### Supprimer l'image ou l'OUT

```http
DELETE /api/out/:outId/image
DELETE /api/out/:outId
Authorization: Bearer <token>
Content-Type: application/json

{ "userId": "<uid Firebase>" }
```

`X-User-Id` peut remplacer le corps pour une requête DELETE. La suppression Cloudinary précède toujours la modification ou suppression Firestore. En cas d'échec Cloudinary, le document reste intact et l'erreur est journalisée.

Une réussite renvoie :

```json
{
  "success": true,
  "success": true
}
```

Les routes sont limitées à 30 requêtes par adresse IP sur 15 minutes. CORS limite les navigateurs à `FRONTEND_URL`.

## Déploiement sur Render

1. Pousser le dépôt sur GitHub, GitLab ou Bitbucket.
2. Dans Render, créer un **Web Service** et sélectionner le dépôt.
3. Définir **Root Directory** sur `Backend`.
4. Utiliser les paramètres suivants :
   - **Runtime** : Node ;
   - **Build Command** : `npm install` ;
   - **Start Command** : `npm start`.
5. Dans **Environment**, ajouter les variables Cloudinary, Firebase et `FRONTEND_URL`.
6. Déployer puis vérifier l'URL Render avec `GET /`.

Il n'est pas nécessaire de définir `PORT` sur Render : la plateforme l'injecte automatiquement.

## Flux de suppression

```text
Frontend
   ↓ requête authentifiée Firebase
Backend Render
   ↓ cloudinary.uploader.destroy(publicId)
Cloudinary
   ↓ uniquement après confirmation de suppression
Firestore update/delete
```

Cet ordre empêche la création d'une image Cloudinary orpheline si sa suppression échoue.
