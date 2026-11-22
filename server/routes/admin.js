import express from 'express';
import crypto from 'crypto';
import { promises as fsp } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import speakeasy from 'speakeasy';
import QRCode from 'qrcode';
import bcrypt from 'bcryptjs';
import nodemailer from 'nodemailer';
import Invite from '../models/Invite.js';
import User from '../models/User.js';
import AuditLog from '../models/AuditLog.js';
import KnowledgeFile from '../models/KnowledgeFile.js';
// Subject and ElectiveGroup imports kept for potential future use
// import Subject from '../models/Subject.js';
// import ElectiveGroup from '../models/ElectiveGroup.js';
import { adminAuth } from '../middleware/adminAuth.js';

const router = express.Router();

// GET /api/admin/stats: Aggregate metrics for the admin dashboard
router.get('/stats', adminAuth, async (req, res) => {
    try {
        const oneWeekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
        const [
            totalUsers,
            verifiedUsers,
            pendingUsers,
            students,
            admins,
            newThisWeek,
            totalFiles,
            indexedFiles
        ] = await Promise.all([
            User.countDocuments(),
            User.countDocuments({ isVerified: true }),
            User.countDocuments({ isVerified: false }),
            User.countDocuments({ role: 'student' }),
            User.countDocuments({ role: 'admin' }),
            User.countDocuments({ createdAt: { $gte: oneWeekAgo } }),
            KnowledgeFile.countDocuments(),
            KnowledgeFile.countDocuments({ status: 'indexed' })
        ]);

        return res.status(200).json({
            totalUsers,
            verifiedUsers,
            pendingUsers,
            students,
            admins,
            newThisWeek,
            totalFiles,
            indexedFiles
        });
    } catch (error) {
        console.error(`[ADMIN STATS ERROR]: ${error.message}`);
        return res.status(500).json({ message: 'Error retrieving statistics' });
    }
});

// Helper to configure Nodemailer transporter
const getMailerTransporter = () => {
    const user = process.env.EMAIL_USER;
    const pass = process.env.EMAIL_PASS;

    if (!user || !pass) {
        return null;
    }

    return nodemailer.createTransport({
        service: 'gmail',
        auth: {
            user,
            pass
        }
    });
};

// Helper for invite HTML templates
const getInviteEmailTemplate = (inviteLink) => {
    return {
        html: `
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #1a1a1a; bg-color: #0d0d0d; color: #ffffff; background-color: #0b0f19;">
                <h2 style="color: #6366f1; border-bottom: 2px solid #6366f1; padding-bottom: 10px;">CampusMateAI Admin Invitation</h2>
                <p>Hello,</p>
                <p>You have been invited to join CampusMateAI as an **Administrator**. To set up your account, click the link below:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="${inviteLink}" style="background-color: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Set Up Admin Account</a>
                </div>
                <p>This invitation link is single-use and will expire in **48 hours**.</p>
                <p style="color: #9ca3af; font-size: 12px; margin-top: 30px;">If you did not request this invite, please ignore this email.</p>
            </div>
        `,
        text: `CampusMateAI Admin Invitation\n\nYou have been invited to join CampusMateAI as an Administrator. To set up your account, visit the link below:\n\n${inviteLink}\n\nThis invitation link is single-use and will expire in 48 hours.`
    };
};

// 1. GET /api/admin/logs: Fetch all audit logs (Protected)
router.get('/logs', adminAuth, async (req, res) => {
    try {
        const logs = await AuditLog.find()
            .sort({ timestamp: -1 })
            .limit(100);
        return res.status(200).json({ logs });
    } catch (error) {
        console.error(`[AUDIT LOG EXCEPTION]: ${error.message}`);
        return res.status(500).json({ message: 'Internal server error fetching logs' });
    }
});

// 1.5 GET /api/admin/verify: Verify session validation status (Protected)
router.get('/verify', adminAuth, async (req, res) => {
    return res.status(200).json({ authenticated: true, user: req.user });
});

// 2. POST /api/admin/invite: Generate admin invite link and email it (Protected)
router.post('/invite', adminAuth, async (req, res) => {
    try {
        const { email } = req.body;
        if (!email) {
            return res.status(400).json({ message: 'Email address is required' });
        }

        // Validate domain format matching admin expectations
        if (!email.endsWith('@gnu.ac.in')) {
            return res.status(400).json({ message: 'Invited admin must use official domain (@gnu.ac.in)' });
        }

        // Check if user already exists
        const userExists = await User.findOne({ email });
        if (userExists) {
            return res.status(400).json({ message: 'Account with this email already exists' });
        }

        // Clear existing invites for this email to avoid duplicates
        await Invite.deleteMany({ email });

        const token = crypto.randomBytes(32).toString('hex');
        const expiresAt = new Date(Date.now() + 48 * 60 * 60 * 1000); // 48 hours

        const invite = new Invite({
            email,
            token,
            expiresAt,
            createdBy: req.user.userId
        });

        await invite.save();

        const origin = req.headers.origin || 'http://localhost:5173';
        const inviteLink = `${origin}/portal/invite/${token}`;

        const transporter = getMailerTransporter();
        console.log(`\n========================================`);
        console.log(`[ADMIN INVITE CODE]: ${email}`);
        console.log(`[ADMIN LINK]: ${inviteLink}`);
        console.log(`========================================\n`);

        let emailStatus = 'sent';
        if (!transporter) {
            console.warn(`[WARNING] SMTP credentials not set. Invitation link printed in server console instead.`);
            emailStatus = 'fallback-console';
        } else {
            const { html, text } = getInviteEmailTemplate(inviteLink);
            try {
                await transporter.sendMail({
                    from: `"CampusMateAI Admin" <${process.env.EMAIL_USER}>`,
                    to: email,
                    subject: 'CampusMateAI Admin Access Invitation',
                    html,
                    text
                });
            } catch (mailError) {
                console.error(`[SMTP ERROR]: Failed to send admin invite mail: ${mailError.message}`);
                emailStatus = 'fallback-console';
            }
        }

        // Log invite generation
        await AuditLog.create({
            adminId: req.user.userId,
            adminEmail: req.user.email,
            action: 'generate_admin_invite',
            targetResource: email,
            ipAddress: req.ip || req.headers['x-forwarded-for'] || req.socket.remoteAddress || '',
            details: `Successfully generated invite link for: ${email}. Email state: ${emailStatus}`
        });

        return res.status(200).json({
            message: 'Administrative invitation generated and sent successfully.',
            email,
            emailStatus,
            inviteLink,
            token
        });

    } catch (error) {
        console.error(`[INVITE EVENT EXCEPTION]: ${error.message}`);
        return res.status(500).json({ message: 'Internal server error generating invite link' });
    }
});

// 3. GET /api/admin/invite/verify/:token: Public endpoint to verify invite token validity
router.get('/invite/verify/:token', async (req, res) => {
    try {
        const { token } = req.params;
        const invite = await Invite.findOne({ token });

        if (!invite) {
            return res.status(404).json({ message: 'Invitation link is invalid or has expired.' });
        }

        if (invite.isUsed) {
            return res.status(400).json({ message: 'Invitation link has already been used.' });
        }

        if (new Date() > invite.expiresAt) {
            return res.status(400).json({ message: 'Invitation link has expired.' });
        }

        // Generate 2FA secret on this verification step if not already present
        if (!invite.twoFactorSecret) {
            const secret = speakeasy.generateSecret({ name: `CampusMateAI Admin (${invite.email})` });
            invite.twoFactorSecret = secret.base32;
            await invite.save();
        }

        const otpSecret = invite.twoFactorSecret;
        // Generate QR code data URL
        const otpauthUrl = `otpauth://totp/CampusMateAI%20Admin:${invite.email}?secret=${otpSecret}&issuer=CampusMateAI`;
        const qrCodeDataUrl = await QRCode.toDataURL(otpauthUrl);

        return res.status(200).json({
            email: invite.email,
            qrCode: qrCodeDataUrl
        });

    } catch (error) {
        console.error(`[VERIFY INVITE EXCEPTION]: ${error.message}`);
        return res.status(500).json({ message: 'Internal server error verifying invite link' });
    }
});

// 4. POST /api/admin/invite/setup: Consumes token, registers admin password, activates 2FA
router.post('/invite/setup', async (req, res) => {
    try {
        const { token, password, otpCode } = req.body;
        if (!token || !password || !otpCode) {
            return res.status(400).json({ message: 'Token, password, and 2FA code are required.' });
        }

        const invite = await Invite.findOne({ token });
        if (!invite || invite.isUsed || new Date() > invite.expiresAt) {
            return res.status(400).json({ message: 'Invitation link is invalid, consumed, or expired.' });
        }

        // Check if an account already exists (safety double check)
        const existingUser = await User.findOne({ email: invite.email });
        if (existingUser) {
            return res.status(400).json({ message: 'An account with this email is already registered.' });
        }

        // Verify the 2FA code matches
        const is2FAValid = speakeasy.totp.verify({
            secret: invite.twoFactorSecret,
            encoding: 'base32',
            token: otpCode,
            window: 2 // allow 1 step time clock mismatch buffer
        });

        if (!is2FAValid) {
            return res.status(400).json({ message: 'Invalid 2FA code. Please verify your authenticator app.' });
        }

        // Hash administration password
        const salt = await bcrypt.genSalt(10);
        const hashedPassword = await bcrypt.hash(password, salt);

        // Account is fully created in MongoDB
        const newAdmin = new User({
            name: invite.email.split('@')[0],
            email: invite.email,
            password: hashedPassword,
            role: 'admin',
            department: 'Administration',
            isVerified: true,
            twoFactorSecret: invite.twoFactorSecret,
            twoFactorEnabled: true
        });

        await newAdmin.save();

        // Invalidate token
        invite.isUsed = true;
        await invite.save();

        // Log admin setup
        await AuditLog.create({
            adminId: newAdmin._id,
            adminEmail: newAdmin.email,
            action: 'setup_admin_account',
            targetResource: newAdmin.email,
            ipAddress: req.ip || req.headers['x-forwarded-for'] || req.socket.remoteAddress || '',
            details: 'Setup administrator account via invitation token'
        });

        return res.status(200).json({
            message: 'Administrator account configured and secured with 2FA successfully!'
        });

    } catch (error) {
        console.error(`[SETUP EXCEPTION]: ${error.message}`);
        return res.status(500).json({ message: 'Internal server error processing administrator setup' });
    }
});

// ── Users CRUD ────────────────────────────────────────────────────────────────

// GET /api/admin/users: List all users (Protected)
router.get('/users', adminAuth, async (req, res) => {
    try {
        const users = await User.find({}, '-password -twoFactorSecret -otp').sort({ createdAt: -1 });
        return res.status(200).json({ users });
    } catch (error) {
        console.error(`[ADMIN USERS ERROR]: ${error.message}`);
        return res.status(500).json({ message: 'Internal server error fetching users' });
    }
});

// PATCH /api/admin/users/:id/password: Reset a user's password (Protected)
router.patch('/users/:id/password', adminAuth, async (req, res) => {
    try {
        const { newPassword } = req.body;
        if (!newPassword || newPassword.length < 8) {
            return res.status(400).json({ message: 'New password must be at least 8 characters.' });
        }

        const user = await User.findById(req.params.id);
        if (!user) return res.status(404).json({ message: 'User not found.' });

        // Prevent admin resetting another admin's password
        if (user.role === 'admin' && user._id.toString() !== req.user.userId) {
            return res.status(403).json({ message: 'Cannot reset another admin\'s password.' });
        }

        const salt = await bcrypt.genSalt(10);
        user.password = await bcrypt.hash(newPassword, salt);
        // Reset any lockout
        user.failedLoginAttempts = 0;
        user.lockedUntil = null;
        await user.save();

        await AuditLog.create({
            adminId: req.user.userId, adminEmail: req.user.email,
            action: 'reset_user_password', targetResource: user.email,
            ipAddress: req.ip || '',
            details: `Admin reset password for ${user.email} (role: ${user.role})`
        });

        return res.status(200).json({ message: `Password reset successfully for ${user.email}.` });
    } catch (error) {
        console.error(`[ADMIN RESET PASSWORD ERROR]: ${error.message}`);
        return res.status(500).json({ message: 'Internal server error resetting password' });
    }
});

// PATCH /api/admin/users/:id/verify: Toggle isVerified for a user (Protected)
router.patch('/users/:id/verify', adminAuth, async (req, res) => {
    try {
        const user = await User.findById(req.params.id);
        if (!user) return res.status(404).json({ message: 'User not found.' });

        user.isVerified = !user.isVerified;
        await user.save();

        await AuditLog.create({
            adminId: req.user.userId, adminEmail: req.user.email,
            action: user.isVerified ? 'verify_user' : 'unverify_user',
            targetResource: user.email, ipAddress: req.ip || '',
            details: `Admin set isVerified=${user.isVerified} for ${user.email}`
        });

        return res.status(200).json({ message: `User ${user.isVerified ? 'verified' : 'unverified'} successfully.`, isVerified: user.isVerified });
    } catch (error) {
        console.error(`[ADMIN VERIFY USER ERROR]: ${error.message}`);
        return res.status(500).json({ message: 'Internal server error toggling verification' });
    }
});

// DELETE /api/admin/users/:id: Delete a user account (Protected)
router.delete('/users/:id', adminAuth, async (req, res) => {
    try {
        const user = await User.findById(req.params.id);
        if (!user) return res.status(404).json({ message: 'User not found.' });

        // Prevent admin deleting their own account or another admin
        if (user.role === 'admin') {
            return res.status(403).json({ message: 'Admin accounts cannot be deleted from the dashboard.' });
        }

        await User.findByIdAndDelete(req.params.id);

        await AuditLog.create({
            adminId: req.user.userId, adminEmail: req.user.email,
            action: 'delete_user', targetResource: user.email,
            ipAddress: req.ip || '',
            details: `Admin deleted account: ${user.email} (role: ${user.role})`
        });

        return res.status(200).json({ message: `Account ${user.email} deleted successfully.` });
    } catch (error) {
        console.error(`[ADMIN DELETE USER ERROR]: ${error.message}`);
        return res.status(500).json({ message: 'Internal server error deleting user' });
    }
});

// ── Campus data catalog (read only) ───────────────────────────────────────────

const ROUTE_DIR = path.dirname(fileURLToPath(import.meta.url));
const STRUCTURED_DATA_DIR = path.resolve(ROUTE_DIR, '..', '..', 'AI_workflow', 'data', 'structured');
const KNOWLEDGE_INDEX_FILE = path.resolve(ROUTE_DIR, '..', '..', 'AI_workflow', 'storage', 'knowledge_base.json');

// Strict allowlist. A Map keeps names like __proto__ from resolving to anything.
const CATALOG_TABLES = new Map([
    ['university', { label: 'University', group: 'Organisation' }],
    ['org_units', { label: 'Organisation Units', group: 'Organisation' }],
    ['departments', { label: 'Department Profiles', group: 'Organisation' }],
    ['department_directory', { label: 'Department Directory', group: 'Organisation' }],
    ['programs', { label: 'Programmes', group: 'Academics' }],
    ['semesters', { label: 'Semesters', group: 'Academics' }],
    ['courses', { label: 'Courses', group: 'Academics' }],
    ['course_offerings', { label: 'Course Offerings', group: 'Academics' }],
    ['course_prerequisites', { label: 'Course Prerequisites', group: 'Academics' }],
    ['elective_groups', { label: 'Elective Groups', group: 'Academics' }],
    ['grading_scheme', { label: 'Grading Scheme', group: 'Academics' }],
    ['faculty', { label: 'Faculty', group: 'People' }],
    ['teaching_assignments', { label: 'Teaching Assignments', group: 'People' }],
    ['research_areas', { label: 'Research Areas', group: 'People' }],
    ['buildings', { label: 'Buildings', group: 'Campus' }],
    ['rooms', { label: 'Rooms', group: 'Campus' }],
    ['laboratories', { label: 'Laboratories', group: 'Campus' }],
    ['facilities', { label: 'Facilities', group: 'Campus' }],
    ['academic_calendar', { label: 'Academic Calendar', group: 'Schedule' }],
    ['notices', { label: 'Notices', group: 'Schedule' }],
    ['policies', { label: 'Policies', group: 'Guidance' }],
    ['faq', { label: 'FAQ', group: 'Guidance' }],
    ['data_quality_conflicts', { label: 'Data Quality Conflicts', group: 'Guidance' }],
]);

// Only counts are cached, keyed on file mtime and size, so parsed records never stay in memory.
const catalogSummaryCache = new Map();

const countByField = (records, field) => {
    const counts = {};
    for (const record of records) {
        const raw = record && typeof record === 'object' ? record[field] : null;
        const key = typeof raw === 'string' && raw.trim() ? raw.trim() : 'unknown';
        counts[key] = (counts[key] || 0) + 1;
    }
    return counts;
};

const readCatalogTable = async (name) => {
    const raw = await fsp.readFile(path.join(STRUCTURED_DATA_DIR, `${name}.json`), 'utf8');
    const parsed = JSON.parse(raw);
    if (!parsed || !Array.isArray(parsed.records)) {
        throw new Error(`Table "${name}" has no records array`);
    }
    return parsed;
};

const summariseCatalogTable = async (name, meta) => {
    const base = { name, label: meta.label, group: meta.group };
    try {
        const stat = await fsp.stat(path.join(STRUCTURED_DATA_DIR, `${name}.json`));
        const cached = catalogSummaryCache.get(name);
        if (cached && cached.mtimeMs === stat.mtimeMs && cached.size === stat.size) {
            return cached.summary;
        }
        const parsed = await readCatalogTable(name);
        const summary = {
            ...base,
            count: parsed.records.length,
            sourceTypes: countByField(parsed.records, 'source_type'),
            generatedAt: typeof parsed.generated_at === 'string' ? parsed.generated_at : null,
            note: typeof parsed.note === 'string' ? parsed.note : null,
            error: null,
        };
        catalogSummaryCache.set(name, { mtimeMs: stat.mtimeMs, size: stat.size, summary });
        return summary;
    } catch (error) {
        catalogSummaryCache.delete(name);
        console.error(`[ADMIN CATALOG ERROR] ${name}: ${error.message}`);
        return { ...base, count: 0, sourceTypes: {}, generatedAt: null, note: null, error: 'This dataset could not be read.' };
    }
};

const summariseKnowledgeIndex = async () => {
    try {
        const parsed = JSON.parse(await fsp.readFile(KNOWLEDGE_INDEX_FILE, 'utf8'));
        const records = Array.isArray(parsed) ? parsed : parsed?.records;
        if (!Array.isArray(records)) throw new Error('Knowledge index has no records array');
        return {
            total: records.length,
            byCategory: countByField(records, 'category'),
            bySourceType: countByField(records, 'source_type'),
            error: null,
        };
    } catch (error) {
        console.error(`[ADMIN CATALOG ERROR] knowledge index: ${error.message}`);
        return { total: 0, byCategory: {}, bySourceType: {}, error: 'The knowledge index could not be read.' };
    }
};

// GET /api/admin/catalog: Every dataset with record and source-type counts (Protected)
router.get('/catalog', adminAuth, async (req, res) => {
    try {
        const [tables, knowledgeIndex] = await Promise.all([
            Promise.all([...CATALOG_TABLES].map(([name, meta]) => summariseCatalogTable(name, meta))),
            summariseKnowledgeIndex(),
        ]);

        const sourceTypes = {};
        for (const table of tables) {
            for (const [type, count] of Object.entries(table.sourceTypes)) {
                sourceTypes[type] = (sourceTypes[type] || 0) + count;
            }
        }

        res.set('Cache-Control', 'no-store');
        return res.status(200).json({
            totals: {
                tables: tables.length,
                unavailableTables: tables.filter((table) => table.error).length,
                records: tables.reduce((sum, table) => sum + table.count, 0),
                sourceTypes,
            },
            tables,
            knowledgeIndex,
        });
    } catch (error) {
        console.error(`[ADMIN CATALOG ERROR]: ${error.message}`);
        return res.status(500).json({ message: 'Error reading the campus data catalog' });
    }
});

// GET /api/admin/catalog/:table: All records of one allowlisted dataset (Protected)
router.get('/catalog/:table', adminAuth, async (req, res) => {
    const { table } = req.params;
    const meta = CATALOG_TABLES.get(table);
    if (!meta) {
        return res.status(404).json({ message: 'Unknown dataset.' });
    }

    try {
        const parsed = await readCatalogTable(table);
        res.set('Cache-Control', 'no-store');
        return res.status(200).json({
            name: table,
            label: meta.label,
            group: meta.group,
            count: parsed.records.length,
            sourceTypes: countByField(parsed.records, 'source_type'),
            generatedAt: typeof parsed.generated_at === 'string' ? parsed.generated_at : null,
            note: typeof parsed.note === 'string' ? parsed.note : null,
            records: parsed.records,
        });
    } catch (error) {
        console.error(`[ADMIN CATALOG ERROR] ${table}: ${error.message}`);
        return res.status(500).json({ message: 'This dataset could not be read.' });
    }
});

// ── Subjects CRUD (unused — frontend tabs removed) ────────────────────────────

// GET /api/admin/subjects
// router.get('/subjects', adminAuth, async (req, res) => { ... });

// POST /api/admin/subjects
// router.post('/subjects', adminAuth, async (req, res) => { ... });

// DELETE /api/admin/subjects/:code
// router.delete('/subjects/:code', adminAuth, async (req, res) => { ... });

// ── Elective Groups CRUD (unused — frontend tabs removed) ─────────────────────

// GET /api/admin/elective-groups
// router.get('/elective-groups', adminAuth, async (req, res) => { ... });

// POST /api/admin/elective-groups
// router.post('/elective-groups', adminAuth, async (req, res) => { ... });

// DELETE /api/admin/elective-groups/:code
// router.delete('/elective-groups/:code', adminAuth, async (req, res) => { ... });

export default router;
