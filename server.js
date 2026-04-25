const express = require('express');
const cors = require('cors');
const multer = require('multer');
const path = require('path');
const fs = require('fs/promises');
const xlsx = require('xlsx');

const app = express();
const PORT = process.env.PORT || 10000;
const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB
const UPLOAD_DIR = path.join(__dirname, 'uploads');

// CORS compatible GitHub Pages (et override possible via FRONTEND_ORIGIN)
app.use(
  cors({
    origin(origin, callback) {
      if (!origin) return callback(null, true);

      const allowedOrigin = process.env.FRONTEND_ORIGIN;
      if (allowedOrigin && origin === allowedOrigin) {
        return callback(null, true);
      }

      if (origin.endsWith('.github.io') || origin.startsWith('http://localhost')) {
        return callback(null, true);
      }

      return callback(new Error('Origine non autorisée par CORS.'));
    }
  })
);

app.use(express.json());

const storage = multer.diskStorage({
  destination: async (_req, _file, cb) => {
    try {
      await fs.mkdir(UPLOAD_DIR, { recursive: true });
      cb(null, UPLOAD_DIR);
    } catch (error) {
      cb(error);
    }
  },
  filename: (_req, file, cb) => {
    const safeName = `${Date.now()}-${file.originalname.replace(/\s+/g, '_')}`;
    cb(null, safeName);
  }
});

const upload = multer({
  storage,
  limits: { fileSize: MAX_FILE_SIZE },
  fileFilter: (_req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    if (ext !== '.xlsx' && ext !== '.xls') {
      return cb(new Error('Type de fichier invalide. Utilisez .xlsx ou .xls')); 
    }
    cb(null, true);
  }
});

const normalizeHeader = (value) =>
  String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase();

const cleanValue = (value) => String(value ?? '').trim();

app.get('/health', (_req, res) => {
  res.json({ status: 'ok' });
});

app.post('/api/excel-to-json', upload.single('file'), async (req, res) => {
  const uploadedFilePath = req.file?.path;

  try {
    if (!req.file) {
      return res.status(400).json({ error: 'Aucun fichier fourni (champ attendu: file).' });
    }

    const workbook = xlsx.readFile(uploadedFilePath);
    const firstSheetName = workbook.SheetNames[0];

    if (!firstSheetName) {
      return res.status(400).json({ error: 'Le fichier Excel est vide.' });
    }

    const firstSheet = workbook.Sheets[firstSheetName];
    const rows = xlsx.utils.sheet_to_json(firstSheet, { defval: '' });

    if (!rows.length) {
      return res.status(400).json({ error: 'Aucune donnée exploitable trouvée dans la première feuille.' });
    }

    const headers = Object.keys(rows[0]);
    const codeKey = headers.find((h) => normalizeHeader(h) === 'code');
    const designationKey = headers.find((h) => normalizeHeader(h) === 'designation');

    if (!codeKey || !designationKey) {
      return res.status(400).json({
        error:
          'Colonnes manquantes. Les colonnes acceptées sont: code/Code/CODE et Désignation/Designation/designation.'
      });
    }

    const transformed = rows
      .map((row) => ({
        code: cleanValue(row[codeKey]),
        designation: cleanValue(row[designationKey])
      }))
      .filter((item) => item.code || item.designation);

    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.setHeader('Content-Disposition', 'attachment; filename="suggestions.json"');
    return res.status(200).send(JSON.stringify(transformed, null, 2));
  } catch (error) {
    return res.status(500).json({ error: error.message || 'Erreur interne lors du traitement du fichier.' });
  } finally {
    // Nettoyage systématique du fichier temporaire uploadé.
    if (uploadedFilePath) {
      await fs.unlink(uploadedFilePath).catch(() => {});
    }
  }
});

app.use((error, _req, res, _next) => {
  if (error instanceof multer.MulterError) {
    if (error.code === 'LIMIT_FILE_SIZE') {
      return res.status(400).json({ error: 'Fichier trop volumineux (max: 5MB).' });
    }
  }

  if (error.message?.includes('Type de fichier invalide')) {
    return res.status(400).json({ error: error.message });
  }

  if (error.message?.includes('CORS')) {
    return res.status(400).json({ error: error.message });
  }

  return res.status(500).json({ error: 'Erreur serveur inattendue.' });
});

app.listen(PORT, () => {
  // Render injecte la variable PORT automatiquement.
  console.log(`Serveur démarré sur le port ${PORT}`);
});
