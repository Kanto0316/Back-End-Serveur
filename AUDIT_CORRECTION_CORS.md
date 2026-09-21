# Audit de correction CORS

## Cause trouvée

La configuration CORS n'autorisait que l'origine définie par la variable
d'environnement `FRONTEND_URL`. L'origine du frontend déployé sur GitHub Pages,
`https://kanto0316.github.io`, pouvait donc être refusée lorsque cette variable
contenait une autre URL.

## Fichier modifié

- `Backend/server.js`

## Correction appliquée

Une liste d'origines autorisées contient désormais explicitement
`https://kanto0316.github.io` ainsi que la valeur de `FRONTEND_URL` lorsqu'elle
est définie. Les origines acceptées sont journalisées avec `[CORS OK]`, tandis
que toutes les autres origines restent bloquées.

## Test attendu

Depuis l'origine `https://kanto0316.github.io` :

- la prérequête `OPTIONS /api/cloudinary/delete` doit recevoir une réponse CORS
  valide ;
- la requête `POST /api/cloudinary/delete` doit atteindre la route et recevoir
  les en-têtes CORS attendus.

Une requête envoyée avec toute autre origine non configurée doit continuer à
recevoir une réponse HTTP `403` indiquant que l'origine n'est pas autorisée.
