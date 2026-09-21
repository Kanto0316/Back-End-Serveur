# Backend Suivi Matériel

API Express chargée de supprimer les images Cloudinary du projet **Suivi Matériel**. Elle ne modifie pas encore Firestore et n'intègre pas Firebase Admin SDK.

## Prérequis

- Node.js 20 ou supérieur ;
- un compte Cloudinary avec ses identifiants d'API ;
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

### Supprimer une image

```http
POST /api/cloudinary/delete
Content-Type: application/json

{
  "publicId": "dossier/nom_image"
}
```

Le `publicId` doit contenir uniquement des lettres, chiffres, tirets, underscores et `/`, commencer par un caractère alphanumérique et ne pas dépasser 255 caractères. Une suppression réussie (ou une image déjà absente) renvoie :

```json
{
  "success": true,
  "message": "Image supprimée de Cloudinary"
}
```

La route est limitée à 30 requêtes par adresse IP sur 15 minutes. CORS limite les appels provenant d'un navigateur à `FRONTEND_URL`. **CORS ne remplace pas une authentification** : avant une exposition publique sensible, ajouter la vérification d'un jeton utilisateur (par exemple Firebase Auth) et une autorisation métier.

## Déploiement sur Render

1. Pousser le dépôt sur GitHub, GitLab ou Bitbucket.
2. Dans Render, créer un **Web Service** et sélectionner le dépôt.
3. Définir **Root Directory** sur `Backend`.
4. Utiliser les paramètres suivants :
   - **Runtime** : Node ;
   - **Build Command** : `npm install` ;
   - **Start Command** : `npm start`.
5. Dans **Environment**, ajouter `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` et `FRONTEND_URL`.
6. Déployer puis vérifier l'URL Render avec `GET /`.

Il n'est pas nécessaire de définir `PORT` sur Render : la plateforme l'injecte automatiquement.

## Évolution prévue avec Firestore

Le flux cible pourra être étendu sans exposer les identifiants Cloudinary :

```text
Frontend
   ↓ requête authentifiée (à ajouter)
Backend Render
   ↓ cloudinary.uploader.destroy(publicId)
Cloudinary
   ↓ après confirmation de suppression
Firestore update/delete (Firebase Admin SDK à ajouter ultérieurement)
```

Pour éviter les incohérences futures, la mise à jour Firestore devra être effectuée côté backend uniquement après la réponse confirmant la suppression Cloudinary.
