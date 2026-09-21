# Audit — images OUT côté backend

## Résultat

| Point contrôlé | État | Constat |
| --- | --- | --- |
| Routes | Conforme | `POST /api/out/upload-image`, `DELETE /api/out/:outId/image` et `DELETE /api/out/:outId` sont implémentées. |
| Authentification | Conforme | Chaque route vérifie un jeton Firebase ID transmis en Bearer. |
| Autorisation ADMIN | Conforme | L'UID déclaré doit correspondre au jeton. L'utilisateur est relu avec Firebase Auth, doit être actif, et son rôle doit être `ADMIN` (custom claim ou `USERS/{uid}`). |
| Validation image | Conforme | Multer limite à un fichier et 5 Mio par défaut. MIME et signature binaire JPEG, PNG, WebP ou GIF sont contrôlés. |
| Cloudinary | Conforme | Configuration exclusivement serveur via les trois variables `CLOUDINARY_*`; upload par flux mémoire et suppression par `destroy()`. |
| Firebase | Conforme | Firebase Admin initialise Auth et Firestore via compte de service explicite ou Application Default Credentials. Les métadonnées sont stockées dans `OUT/{outId}`. |
| Ordre de suppression | Conforme | `destroy()` termine avant `update()` ou `delete()`. En cas d'échec, celui-ci est journalisé et le document OUT demeure, donc l'image n'est pas orpheline. |

## Sécurité et cohérence

- Les secrets ne sont jamais acceptés du client ni renvoyés par l'API.
- Un upload est refusé si l'OUT n'existe pas ou possède déjà une image.
- Si Firestore échoue après un upload Cloudinary, une suppression compensatoire est tentée et toute erreur de rollback est journalisée.
- La date de création provient de l'horloge serveur Firestore.
- Les routes sensibles ont une limitation de débit et les erreurs ne divulguent pas les détails des fournisseurs.

## Configuration requise

Définir Cloudinary, `FRONTEND_URL`, puis soit `FIREBASE_SERVICE_ACCOUNT`, soit les trois variables Firebase séparées. Sur une infrastructure Google dotée d'une identité appropriée, Application Default Credentials peut être utilisée. Le compte de service doit pouvoir lire Firebase Auth et lire/mettre à jour/supprimer la collection `OUT` (ainsi que lire `USERS` si le rôle n'est pas un custom claim).
