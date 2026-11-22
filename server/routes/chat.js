import express from 'express';
import axios from 'axios';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { authenticateJWT } from '../middleware/studentAuth.js';

const router = express.Router();
const NOTICES_PATH = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../AI_workflow/data/structured/notices.json');

// Active campus notices for the student notification bell, newest first.
router.get('/notices', authenticateJWT, (req, res) => {
    try {
        const { records = [] } = JSON.parse(fs.readFileSync(NOTICES_PATH, 'utf8'));
        const today = new Date().toISOString().slice(0, 10);
        const notices = records
            .filter((notice) => notice.status === 'active' && (!notice.expiry_date || notice.expiry_date >= today))
            .sort((a, b) => String(b.date).localeCompare(String(a.date)))
            .slice(0, 8)
            .map((notice) => ({ id: notice.notice_id, title: notice.title, date: notice.date, category: notice.category }));
        return res.json({ notices });
    } catch (error) {
        console.error(`[CHAT NOTICES ERROR]: ${error.message}`);
        return res.status(500).json({ message: 'Could not load notices.' });
    }
});

// AI Workflow FastAPI base URL (default port 8010 to prevent port conflict with port 8000)
const AI_WORKFLOW_URL = process.env.AI_WORKFLOW_URL || 'http://127.0.0.1:8010';
const AI_TIMEOUT_MS = 30000;

// An outage must never read like "the campus records have no answer".
const SERVICE_UNAVAILABLE = {
    text: 'The CampusMate answer engine is temporarily unavailable, so this question was not checked against campus records. Please try again in a moment.',
    sources: [],
    engineUsed: 'hybrid_rag',
    provider: 'CampusMate Service Monitor',
    route: 'service_unavailable',
    timings_ms: null
};

// ── Helper: map FastAPI ChatResponse → standard rich response shape ────────────
function mapAIResponse(data) {
    const sources = (data.sources || [])
        .filter(s => s.cited === undefined || s.cited === true)
        .map(s => ({
            ref: s.ref ?? null,
            title: s.title || s.label || s.citation?.document_id || 'Campus Knowledge Base',
            content: s.content || s.text || '',
            score: s.score !== undefined ? s.score : null,
            source_type: s.source_type || ''
        }));

    return {
        text: data.answer || data.text || 'No answer returned from AI workflow.',
        sources,
        engineUsed: 'hybrid_rag',
        provider: data.provider || 'CampusMate Hybrid Engine',
        query_id: data.query_id,
        conversation_id: data.conversation_id,
        clarification_required: Boolean(data.clarification_required),
        options: data.options || [],
        links: data.links || [],
        route: data.route || 'hybrid_rag',
        answer_type: data.answer_type,
        grounding: data.grounding || null,
        timings_ms: data.timings_ms || null
    };
}

// 1. POST /api/chat/direct — proxies to AI Workflow Hybrid RAG
router.post('/direct', async (req, res) => {
    try {
        const message = req.body.question || req.body.message;
        const conversation_id = req.body.conversation_id;
        const model = req.body.model;
        const history = req.body.history || [];

        if (!message) {
            return res.status(400).json({ message: 'Message is required' });
        }

        const hybridRes = await axios.post(
            `${AI_WORKFLOW_URL}/api/v1/chat/hybrid`,
            { question: message, conversation_id, model, history },
            { timeout: AI_TIMEOUT_MS, headers: { 'Content-Type': 'application/json' } }
        );
        return res.json(mapAIResponse(hybridRes.data));
    } catch (error) {
        console.error(`[CHAT DIRECT ERROR]: ${error.message}`);
        return res.status(503).json(SERVICE_UNAVAILABLE);
    }
});

// 1b. POST /api/chat/stream — Server-Sent Events (SSE) streaming proxy
router.post('/stream', async (req, res) => {
    const message = req.body.question || req.body.message;
    const conversation_id = req.body.conversation_id;
    const model = req.body.model;
    const history = req.body.history || [];

    if (!message) {
        return res.status(400).json({ message: 'Message is required' });
    }

    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders?.();

    try {
        const streamRes = await axios.post(
            `${AI_WORKFLOW_URL}/api/v1/chat/stream`,
            { question: message, conversation_id, model, history },
            { responseType: 'stream', timeout: AI_TIMEOUT_MS }
        );

        streamRes.data.pipe(res);

        streamRes.data.on('error', (err) => {
            console.error('[CHAT STREAM PROXY PIPE ERROR]:', err.message);
            res.end();
        });
    } catch (err) {
        console.error(`[CHAT STREAM ERROR]: ${err.message}`);
        res.write(`event: done\ndata: ${JSON.stringify(SERVICE_UNAVAILABLE)}\n\n`);
        res.end();
    }
});

// 2. POST /api/chat/n8n — proxies to an n8n webhook or returns simulated RAG
router.post('/n8n', authenticateJWT, async (req, res) => {
    try {
        const { message } = req.body;
        const studentId = req.user?.id || 'guest';

        if (!message) {
            return res.status(400).json({ message: 'Message is required' });
        }

        if (!process.env.N8N_WEBHOOK_URL) {
            const hybridRes = await axios.post(
                `${AI_WORKFLOW_URL}/api/v1/chat/hybrid`,
                { question: message },
                { timeout: AI_TIMEOUT_MS, headers: { 'Content-Type': 'application/json' } }
            );
            return res.json({
                ...mapAIResponse(hybridRes.data),
                engineUsed: 'n8n_hybrid'
            });
        }

        const n8nResponse = await axios.post(process.env.N8N_WEBHOOK_URL, {
            message,
            studentId,
        });

        return res.json({
            text: n8nResponse.data.text || 'No response from n8n.',
            sources: n8nResponse.data.sources || [],
            engineUsed: 'n8n'
        });

    } catch (error) {
        console.error(`[CHAT N8N PROXY ERROR]: ${error.message}`);
        return res.status(500).json({ message: 'Failed to communicate with n8n workflow engine.' });
    }
});

export default router;
