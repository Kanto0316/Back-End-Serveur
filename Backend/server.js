require('dotenv').config();

const express = require('express');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const { v2: cloudinary } = require('cloudinary');

const requiredEnvironmentVariables = [
  'CLOUDINARY_CLOUD_NAME',
  'CLOUDINARY_API_KEY',
  'CLOUDINARY_API_SECRET',
  'FRONTEND_URL',
];

const missingEnvironmentVariables = requiredEnvironmentVariables.filter(
  (variableName) => !process.env[variableName]?.trim(),
);

if (missingEnvironmentVariables.length > 0) {
  console.error(
    `Variables d'environnement manquantes : ${missingEnvironmentVariables.join(', ')}`,
  );
  process.exit(1);
}

cloudinary.config({
  cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
  api_key: process.env.CLOUDINARY_API_KEY,
  api_secret: process.env.CLOUDINARY_API_SECRET,
  secure: true,
});

const app = express();
const port = process.env.PORT || 3000;
const frontendUrl = process.env.FRONTEND_URL.replace(/\/$/, '');

app.set('trust proxy', 1);
app.disable('x-powered-by');

app.use(
  cors({
    origin(origin, callback) {
      // Les requêtes sans en-tête Origin (Render, curl, monitoring) ne sont pas
      // concernées par CORS. Les navigateurs sont limités au frontend déclaré.
      if (!origin || origin.replace(/\/$/, '') === frontendUrl) {
        return callback(null, true);
      }

      return callback(new Error('Origine non autorisée par CORS'));
    },
    methods: ['GET', 'POST'],
    allowedHeaders: ['Content-Type'],
  }),
);

app.use(express.json({ limit: '10kb' }));

const deleteImageLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  limit: 30,
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  message: {
    success: false,
    message: 'Trop de requêtes, veuillez réessayer plus tard',
  },
});

const publicIdPattern = /^[a-zA-Z0-9][a-zA-Z0-9_\-/]{0,254}$/;

app.get('/', (_request, response) => {
  response.json({ status: 'API Suivi Matériel active' });
});

app.post('/api/cloudinary/delete', deleteImageLimiter, async (request, response) => {
  const { publicId } = request.body ?? {};

  if (typeof publicId !== 'string' || !publicIdPattern.test(publicId)) {
    return response.status(400).json({
      success: false,
      message: 'publicId invalide ou manquant',
    });
  }

  try {
    const result = await cloudinary.uploader.destroy(publicId);

    if (!['ok', 'not found'].includes(result.result)) {
      throw new Error(`Réponse Cloudinary inattendue : ${result.result}`);
    }

    return response.json({
      success: true,
      message: 'Image supprimée de Cloudinary',
    });
  } catch (error) {
    console.error('Échec de la suppression Cloudinary :', error.message);

    return response.status(502).json({
      success: false,
      message: 'Erreur suppression image',
    });
  }
});

app.use((error, _request, response, _next) => {
  if (error instanceof SyntaxError && error.status === 400 && 'body' in error) {
    return response.status(400).json({
      success: false,
      message: 'Corps JSON invalide',
    });
  }

  if (error.message === 'Origine non autorisée par CORS') {
    return response.status(403).json({
      success: false,
      message: 'Origine non autorisée',
    });
  }

  console.error('Erreur serveur :', error.message);
  return response.status(500).json({
    success: false,
    message: 'Erreur interne du serveur',
  });
});

app.listen(port, () => {
  console.log(`API Suivi Matériel démarrée sur le port ${port}`);
});
