require('dotenv').config();

const express = require('express');
const cors = require('cors');
const rateLimit = require('express-rate-limit');
const multer = require('multer');
const { v2: cloudinary } = require('cloudinary');
const { cert, getApps, initializeApp } = require('firebase-admin/app');
const { getAuth } = require('firebase-admin/auth');
const { FieldValue, getFirestore } = require('firebase-admin/firestore');

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
  console.error(`Variables d'environnement manquantes : ${missingEnvironmentVariables.join(', ')}`);
  process.exit(1);
}

cloudinary.config({
  cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
  api_key: process.env.CLOUDINARY_API_KEY,
  api_secret: process.env.CLOUDINARY_API_SECRET,
  secure: true,
});

function firebaseCredential() {
  if (process.env.FIREBASE_SERVICE_ACCOUNT) {
    return cert(JSON.parse(process.env.FIREBASE_SERVICE_ACCOUNT));
  }

  if (process.env.FIREBASE_PROJECT_ID && process.env.FIREBASE_CLIENT_EMAIL && process.env.FIREBASE_PRIVATE_KEY) {
    return cert({
      projectId: process.env.FIREBASE_PROJECT_ID,
      clientEmail: process.env.FIREBASE_CLIENT_EMAIL,
      privateKey: process.env.FIREBASE_PRIVATE_KEY.replace(/\\n/g, '\n'),
    });
  }

  return undefined; // Application Default Credentials (Cloud Run, Google Cloud, etc.)
}

const firebaseApp = getApps()[0] || initializeApp(
  firebaseCredential() ? { credential: firebaseCredential() } : undefined,
);
const auth = getAuth(firebaseApp);
const db = getFirestore(firebaseApp);
const app = express();
const port = process.env.PORT || 3000;
const maxImageSize = Number(process.env.MAX_IMAGE_SIZE_BYTES) || 5 * 1024 * 1024;
const allowedOrigins = ['https://kanto0316.github.io', process.env.FRONTEND_URL]
  .filter(Boolean)
  .map((origin) => origin.replace(/\/$/, ''));

app.set('trust proxy', 1);
app.disable('x-powered-by');
app.use(cors({
  origin(origin, callback) {
    if (!origin || allowedOrigins.includes(origin.replace(/\/$/, ''))) return callback(null, true);
    return callback(new Error('Origine non autorisée par CORS'));
  },
  methods: ['GET', 'POST', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization'],
}));
app.use(express.json({ limit: '10kb' }));

const imageLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  limit: 30,
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  message: { success: false, message: 'Trop de requêtes, veuillez réessayer plus tard' },
});
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: maxImageSize, files: 1, fields: 2 },
});
const documentIdPattern = /^[^/]{1,1500}$/;

function isSupportedImage(file) {
  if (!file || !['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes(file.mimetype)) return false;
  const signatures = {
    'image/jpeg': [0xff, 0xd8, 0xff],
    'image/png': [0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a],
    'image/gif': [0x47, 0x49, 0x46, 0x38],
    'image/webp': [0x52, 0x49, 0x46, 0x46],
  };
  const signature = signatures[file.mimetype];
  if (!signature.every((byte, index) => file.buffer[index] === byte)) return false;
  return file.mimetype !== 'image/webp' || file.buffer.subarray(8, 12).toString() === 'WEBP';
}

async function authenticate(request, response, next) {
  const match = request.get('authorization')?.match(/^Bearer (.+)$/);
  if (!match) return response.status(401).json({ success: false, message: 'Authentification requise' });
  try {
    request.user = await auth.verifyIdToken(match[1]);
    return next();
  } catch (_error) {
    return response.status(401).json({ success: false, message: 'Jeton invalide ou expiré' });
  }
}

async function requireAdmin(request, response, next) {
  const suppliedUserId = request.body?.userId || request.get('x-user-id');
  if (!suppliedUserId || suppliedUserId !== request.user.uid) {
    return response.status(403).json({ success: false, message: 'Identité utilisateur invalide' });
  }
  try {
    const userRecord = await auth.getUser(suppliedUserId);
    if (userRecord.disabled) return response.status(403).json({ success: false, message: 'Utilisateur désactivé' });
    const userDocument = await db.collection('USERS').doc(suppliedUserId).get();
    const role = userRecord.customClaims?.role || userDocument.data()?.role;
    if (role !== 'ADMIN') return response.status(403).json({ success: false, message: 'Rôle ADMIN obligatoire' });
    return next();
  } catch (error) {
    if (error.code === 'auth/user-not-found') {
      return response.status(404).json({ success: false, message: 'Utilisateur introuvable' });
    }
    return next(error);
  }
}

function uploadToCloudinary(file, outId) {
  return new Promise((resolve, reject) => {
    const stream = cloudinary.uploader.upload_stream(
      { folder: 'out', public_id: `${outId}-${Date.now()}`, resource_type: 'image' },
      (error, result) => (error ? reject(error) : resolve(result)),
    );
    stream.end(file.buffer);
  });
}

async function destroyImage(publicId) {
  const result = await cloudinary.uploader.destroy(publicId, { resource_type: 'image' });
  if (!['ok', 'not found'].includes(result.result)) throw new Error(`Réponse Cloudinary inattendue : ${result.result}`);
}

app.get('/', (_request, response) => response.json({ status: 'API Suivi Matériel active' }));

app.post('/api/out/upload-image', imageLimiter, authenticate, upload.single('image'), requireAdmin, async (request, response, next) => {
  const { outId, userId } = request.body;
  if (!documentIdPattern.test(outId || '')) return response.status(400).json({ success: false, message: 'outId invalide ou manquant' });
  if (!isSupportedImage(request.file)) return response.status(400).json({ success: false, message: 'Image JPEG, PNG, WebP ou GIF valide requise' });

  const outReference = db.collection('OUT').doc(outId);
  let uploadedImage;
  try {
    const outDocument = await outReference.get();
    if (!outDocument.exists) return response.status(404).json({ success: false, message: 'OUT introuvable' });
    if (outDocument.data().imagePublicId) return response.status(409).json({ success: false, message: "L’OUT possède déjà une image" });

    uploadedImage = await uploadToCloudinary(request.file, outId);
    await outReference.update({
      imageUrl: uploadedImage.secure_url,
      imagePublicId: uploadedImage.public_id,
      imageCreatedBy: userId,
      imageCreatedAt: FieldValue.serverTimestamp(),
    });
    return response.json({ success: true, imageUrl: uploadedImage.secure_url, imagePublicId: uploadedImage.public_id });
  } catch (error) {
    if (uploadedImage?.public_id) {
      try { await destroyImage(uploadedImage.public_id); } catch (rollbackError) {
        console.error('[OUT IMAGE ROLLBACK ERROR]', { outId, publicId: uploadedImage.public_id, message: rollbackError.message });
      }
    }
    return next(error);
  }
});

app.delete('/api/out/:outId/image', imageLimiter, authenticate, requireAdmin, async (request, response, next) => {
  const { outId } = request.params;
  if (!documentIdPattern.test(outId)) return response.status(400).json({ success: false, message: 'outId invalide' });
  try {
    const reference = db.collection('OUT').doc(outId);
    const document = await reference.get();
    if (!document.exists) return response.status(404).json({ success: false, message: 'OUT introuvable' });
    const { imagePublicId } = document.data();
    if (imagePublicId) await destroyImage(imagePublicId);
    await reference.update({
      imageUrl: FieldValue.delete(), imagePublicId: FieldValue.delete(),
      imageCreatedBy: FieldValue.delete(), imageCreatedAt: FieldValue.delete(),
    });
    return response.json({ success: true });
  } catch (error) {
    console.error('[OUT IMAGE DELETE ERROR]', { outId, message: error.message });
    return next(error);
  }
});

app.delete('/api/out/:outId', imageLimiter, authenticate, requireAdmin, async (request, response, next) => {
  const { outId } = request.params;
  if (!documentIdPattern.test(outId)) return response.status(400).json({ success: false, message: 'outId invalide' });
  try {
    const reference = db.collection('OUT').doc(outId);
    const document = await reference.get();
    if (!document.exists) return response.status(404).json({ success: false, message: 'OUT introuvable' });
    const { imagePublicId } = document.data();
    if (imagePublicId) await destroyImage(imagePublicId); // Toujours avant la suppression Firestore.
    await reference.delete();
    return response.json({ success: true });
  } catch (error) {
    console.error('[OUT DELETE ABORTED]', { outId, message: error.message });
    return next(error); // Le document reste présent si Cloudinary échoue.
  }
});

app.use((error, _request, response, _next) => {
  if (error instanceof multer.MulterError && error.code === 'LIMIT_FILE_SIZE') {
    return response.status(413).json({ success: false, message: `Image trop volumineuse (maximum ${maxImageSize} octets)` });
  }
  if (error instanceof multer.MulterError) return response.status(400).json({ success: false, message: 'Formulaire image invalide' });
  if (error instanceof SyntaxError && error.status === 400 && 'body' in error) return response.status(400).json({ success: false, message: 'Corps JSON invalide' });
  if (error.message === 'Origine non autorisée par CORS') return response.status(403).json({ success: false, message: 'Origine non autorisée' });
  console.error('[SERVER ERROR]', { message: error.message, name: error.name });
  return response.status(502).json({ success: false, message: 'Opération externe impossible' });
});

if (require.main === module) app.listen(port, () => console.log(`API Suivi Matériel démarrée sur le port ${port}`));
module.exports = { app, destroyImage, isSupportedImage };
