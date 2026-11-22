import express from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import KnowledgeFile from '../models/KnowledgeFile.js';
import { adminAuth } from '../middleware/adminAuth.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const router = express.Router();

// ── Upload storage configuration ─────────────────────────────────────────────
const UPLOAD_DIR = path.join(__dirname, '../uploads/knowledge');

// Ensure upload directory exists
if (!fs.existsSync(UPLOAD_DIR)) {
    fs.mkdirSync(UPLOAD_DIR, { recursive: true });
}

const storage = multer.diskStorage({
    destination: (req, file, cb) => cb(null, UPLOAD_DIR),
    filename: (req, file, cb) => {
        const timestamp = Date.now();
        const safe = file.originalname.replace(/[^a-zA-Z0-9._-]/g, '_');
        cb(null, `${timestamp}_${safe}`);
    }
});

const ALLOWED_MIME_TYPES = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'text/markdown',
    'text/csv',
    'application/json',
    'image/jpeg',
    'image/png',
    'image/webp',
];

const upload = multer({
    storage,
    limits: { fileSize: 20 * 1024 * 1024 }, // 20 MB
    fileFilter: (req, file, cb) => {
        if (ALLOWED_MIME_TYPES.includes(file.mimetype)) {
            cb(null, true);
        } else {
            cb(new Error(`Unsupported file type: ${file.mimetype}. Allowed: PDF, DOCX, TXT, MD, CSV, JSON, JPEG, PNG, WEBP`));
        }
    }
});

// ── POST /api/admin/knowledge/upload ─────────────────────────────────────────
// Upload a file into the AI knowledge workflow pipeline
router.post('/upload', adminAuth, (req, res) => {
    upload.single('file')(req, res, async (err) => {
        if (err) {
            return res.status(400).json({ message: err.message });
        }

        if (!req.file) {
            return res.status(400).json({ message: 'No file attached. Please select a file to upload.' });
        }

        try {
            const record = await KnowledgeFile.create({
                originalName:    req.file.originalname,
                storedName:      req.file.filename,
                filePath:        req.file.path,
                mimeType:        req.file.mimetype,
                size:            req.file.size,
                status:          'pending',   // AI pipeline will update this to 'indexed'
                uploadedBy:      req.user?.userId || null,
                uploadedByEmail: req.user?.email || '',
                description:     req.body.description || '',
            });

            // Trigger AI ingestion pipeline — fire and forget
            const aiUrl = process.env.AI_WORKFLOW_URL || 'http://127.0.0.1:8010';
            fetch(`${aiUrl}/api/v1/chat/ingest`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_path:     req.file.path,
                    original_name: req.file.originalname,
                    source_type:   'official',
                }),
            }).catch(err => console.error('[INGEST WEBHOOK ERROR]:', err.message));

            return res.status(201).json({
                message: 'File uploaded successfully. Queued for AI knowledge indexing.',
                file: {
                    id:           record._id,
                    originalName: record.originalName,
                    size:         record.size,
                    mimeType:     record.mimeType,
                    status:       record.status,
                    uploadedAt:   record.uploadedAt,
                }
            });
        } catch (dbErr) {
            console.error(`[KNOWLEDGE UPLOAD DB ERROR]: ${dbErr.message}`);
            return res.status(500).json({ message: 'File saved but failed to register in database.' });
        }
    });
});

// ── GET /api/admin/knowledge/files ───────────────────────────────────────────
// List all uploaded knowledge files
router.get('/files', adminAuth, async (req, res) => {
    try {
        const files = await KnowledgeFile.find()
            .sort({ uploadedAt: -1 })
            .limit(200);
        return res.status(200).json({ files });
    } catch (error) {
        console.error(`[KNOWLEDGE FILES ERROR]: ${error.message}`);
        return res.status(500).json({ message: 'Internal server error fetching knowledge files.' });
    }
});

// ── DELETE /api/admin/knowledge/:id ──────────────────────────────────────────
// Delete a knowledge file record and its stored file
router.delete('/:id', adminAuth, async (req, res) => {
    try {
        const record = await KnowledgeFile.findById(req.params.id);
        if (!record) return res.status(404).json({ message: 'File record not found.' });

        // Delete physical file if it exists
        if (fs.existsSync(record.filePath)) {
            fs.unlinkSync(record.filePath);
        }

        await KnowledgeFile.findByIdAndDelete(req.params.id);

        return res.status(200).json({ message: `File "${record.originalName}" removed from knowledge base.` });
    } catch (error) {
        console.error(`[KNOWLEDGE DELETE ERROR]: ${error.message}`);
        return res.status(500).json({ message: 'Internal server error deleting knowledge file.' });
    }
});

// ── PATCH /api/admin/knowledge/:id/status ────────────────────────────────────
// (Called by AI pipeline to update indexing status)
router.patch('/:id/status', adminAuth, async (req, res) => {
    try {
        const { status } = req.body;
        const allowed = ['pending', 'processing', 'indexed', 'error'];
        if (!allowed.includes(status)) {
            return res.status(400).json({ message: `Invalid status. Use: ${allowed.join(', ')}` });
        }
        const record = await KnowledgeFile.findByIdAndUpdate(
            req.params.id,
            { status },
            { new: true }
        );
        if (!record) return res.status(404).json({ message: 'File not found.' });
        return res.status(200).json({ message: 'Status updated.', file: record });
    } catch (error) {
        return res.status(500).json({ message: 'Internal server error updating status.' });
    }
});

export default router;
