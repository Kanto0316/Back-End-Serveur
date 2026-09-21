# Audit des logs de diagnostic Cloudinary

## Fichiers modifiés

- `Backend/server.js` : ajout des journaux de diagnostic HTTP, CORS et Cloudinary.
- `AUDIT_LOGS_DIAGNOSTIC_CLOUDINARY.md` : documentation des journaux et de la procédure de test.

## Emplacement des logs ajoutés

### Journal HTTP global

Le middleware placé après l'analyse du corps JSON et avant les routes journalise, pour chaque requête :

- la méthode HTTP ;
- le chemin ;
- l'origine, ou `none` si elle est absente ;
- le type de contenu, ou `none` s'il est absent.

### Contrôle CORS

La fonction de validation CORS produit le journal `[CORS BLOCKED]` lorsqu'elle refuse une origine. Seule l'origine refusée est affichée.

### Route `POST /api/cloudinary/delete`

La route produit les journaux suivants :

1. `[CLOUDINARY DELETE REQUEST]` dès son entrée, avec le corps reçu et un booléen indiquant la présence de `publicId` ;
2. `[CLOUDINARY DESTROY START]` juste avant l'appel à Cloudinary, avec uniquement la longueur du `publicId` ;
3. `[CLOUDINARY DESTROY RESULT]` après l'appel, avec le statut renvoyé par Cloudinary ;
4. `[CLOUDINARY DELETE ERROR]` en cas d'exception, avec uniquement le message et le nom de l'erreur.

Les journaux n'affichent ni secret API Cloudinary, ni clé API, ni jeton Firebase. Le journal de démarrage de la destruction n'affiche pas le `publicId` complet.

## Exemple des logs attendus

Pour une suppression autorisée depuis le frontend :

```text
[HTTP] {
  method: 'OPTIONS',
  path: '/api/cloudinary/delete',
  origin: 'https://frontend.example.com',
  contentType: 'none'
}
[HTTP] {
  method: 'POST',
  path: '/api/cloudinary/delete',
  origin: 'https://frontend.example.com',
  contentType: 'application/json'
}
[CLOUDINARY DELETE REQUEST] {
  bodyReceived: { publicId: 'dossier/image' },
  hasPublicId: true
}
[CLOUDINARY DESTROY START] { publicIdLength: 13 }
[CLOUDINARY DESTROY RESULT] { result: 'ok' }
```

Pour une origine refusée :

```text
[CORS BLOCKED] { origin: 'https://origine-non-autorisee.example.com' }
```

Pour une erreur pendant la suppression :

```text
[CLOUDINARY DELETE ERROR] {
  message: 'message renvoyé par la bibliothèque Cloudinary',
  name: 'Error'
}
```

## Procédure de test depuis le frontend

1. Déployer le backend sur Render avec `FRONTEND_URL` configuré sur l'URL exacte du frontend.
2. Ouvrir le frontend dans un navigateur, puis ouvrir ses outils de développement et l'onglet **Réseau**.
3. Depuis l'interface, cliquer sur l'action de suppression d'une image.
4. Dans l'onglet **Réseau**, vérifier la requête `OPTIONS` de pré-vérification, puis la requête `POST` vers `/api/cloudinary/delete`.
5. Dans les logs du service Render, rechercher successivement `[HTTP]`, `[CLOUDINARY DELETE REQUEST]`, `[CLOUDINARY DESTROY START]` et `[CLOUDINARY DESTROY RESULT]`.
6. Si la requête est bloquée avant la route, rechercher `[CORS BLOCKED]` et comparer l'origine affichée à la valeur de `FRONTEND_URL`.
7. Si l'appel Cloudinary échoue, rechercher `[CLOUDINARY DELETE ERROR]` et utiliser uniquement le nom et le message de l'erreur pour le diagnostic.
