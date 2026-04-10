# Back-End-Serveur

Backend Flask pour transfert de fichiers.

## Endpoints

- `POST /upload` : reçoit un fichier (`request.files['file']`), le stocke dans `uploads/`, puis retourne une URL unique de téléchargement.
- `GET /download/<id>` : télécharge le fichier associé à l'ID.
- `GET /health` : endpoint de vérification simple.

## Sécurité et robustesse

- Taille maximale de fichier : **20 MB**.
- Nettoyage du nom de fichier avec `secure_filename`.
- Gestion des erreurs (fichier absent, nom invalide, ID invalide, fichier expiré/introuvable).
- CORS activé via `flask-cors`.

## Bonus implémenté

- Les fichiers expirent automatiquement après **24h** (suppression au prochain accès upload/download).

## Lancer en local

```bash
pip install -r requirements.txt
python app.py
```
