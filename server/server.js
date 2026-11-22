import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import cookieParser from 'cookie-parser';
import { connectDB } from './config/db.js';
import authRoutes from './routes/auth.js';
import adminRoutes from './routes/admin.js';
// import electiveRoutes from './routes/electives.js'; (Moved to server/_unused)
import chatRoutes from './routes/chat.js';
import knowledgeRoutes from './routes/knowledge.js';

// Setup __dirname equivalent in ESM
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environmental parameters
dotenv.config({ path: path.join(__dirname, '.env') });

const app = express();

// Middlewares
const ALLOWED_ORIGINS = new Set(['http://localhost:5173', 'http://127.0.0.1:5173']);
app.use(cors({
    origin: (origin, callback) => callback(null, !origin || ALLOWED_ORIGINS.has(origin)),
    credentials: true
}));
app.use(express.json());
app.use(cookieParser());

// Main DB connect
connectDB();

// API endpoint mapping
app.use('/api/auth', authRoutes);
app.use('/api/admin', adminRoutes);
// app.use('/api/electives', electiveRoutes); (Moved to server/_unused)
app.use('/api/chat', chatRoutes);
app.use('/api/admin/knowledge', knowledgeRoutes);

// Root verification & information routes
app.get('/api/health', (req, res) => {
    res.status(200).json({ status: 'healthy', timestamp: new Date() });
});

app.get('/', (req, res) => {
    res.send(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>CampusMate 2.0 API Server</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0c1222; color: #f8fafc; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; }
                .card { background: #1e293b; border: 1px solid #334155; border-radius: 16px; padding: 36px; max-width: 480px; width: 90%; text-align: center; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5); }
                h1 { font-size: 22px; color: #38bdf8; margin: 0 0 12px 0; }
                p { font-size: 14px; color: #94a3b8; line-height: 1.6; margin: 0 0 24px 0; }
                .btn { display: inline-block; background: #2563eb; color: #ffffff; padding: 12px 24px; border-radius: 10px; font-weight: 600; text-decoration: none; font-size: 14px; transition: background 0.2s; }
                .btn:hover { background: #1d4ed8; }
                .ports { display: flex; justify-content: space-around; margin-top: 24px; padding-top: 20px; border-top: 1px solid #334155; font-size: 12px; color: #64748b; }
                .badge { color: #10b981; font-weight: 600; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>CampusMate 2.0 API Gateway</h1>
                <p>Express backend active on <strong>port 5000</strong>. To access the interactive web interface, click below:</p>
                <a href="http://localhost:5173" class="btn">Open Web App (Port 5173) &rarr;</a>
                <div class="ports">
                    <span>Node: <span class="badge">5000</span></span>
                    <span>FastAPI: <span class="badge">8010</span></span>
                    <span>Vite UI: <span class="badge">5173</span></span>
                </div>
            </div>
        </body>
        </html>
    `);
});

const PORT = process.env.PORT || 5000;
const server = app.listen(PORT, '127.0.0.1', () => {
    console.log(`CampusMateAI Server boot active on port: ${PORT}`);
});

server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
        console.error(`[ERROR] Port ${PORT} is already in use by another program!`);
        console.error(`Run 'stop.bat' or kill existing processes on port ${PORT}.`);
        process.exit(1);
    }
});
