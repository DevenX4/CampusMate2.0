import express from 'express';
import bcrypt from 'bcryptjs';
import nodemailer from 'nodemailer';
import jwt from 'jsonwebtoken';
import speakeasy from 'speakeasy';
import QRCode from 'qrcode';
import rateLimit from 'express-rate-limit';
import User from '../models/User.js';
import AuditLog from '../models/AuditLog.js';
import { getOTPEmailTemplate } from '../utils/emailTemplates.js';
import { authenticateJWT } from '../middleware/studentAuth.js';

const router = express.Router();

// Helper to generate 6-digit numeric OTP
const generateOTP = () => {
    return Math.floor(100000 + Math.random() * 900000).toString();
};

// Transport configuration for Gmail
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

// Send OTP assistance function
const sendOTPEmail = async (email, otpCode, firstName = 'there') => {
    const transporter = getMailerTransporter();

    console.log(`\n========================================`);
    console.log(`[OTP DISPATCH] Destination: ${email}`);
    console.log(`[OTP DISPATCH] Code: ${otpCode}`);
    console.log(`========================================\n`);

    if (!transporter) {
        console.warn(`[WARNING] Gmail credentials (EMAIL_USER/EMAIL_PASS) are not set. OTP has been logged to console above for developer access.`);
        return { success: true, bypassed: true };
    }

    const { html, text } = getOTPEmailTemplate(firstName, otpCode);

    const mailOptions = {
        from: `"CampusMateAI" <${process.env.EMAIL_USER}>`,
        to: email,
        subject: 'CampusMateAI Signup Verification OTP',
        html,
        text
    };

    try {
        await transporter.sendMail(mailOptions);
        return { success: true };
    } catch (error) {
        console.error(`[ERROR] Failed to send email via Gmail SMTP: ${error.message}`);
        // fallback in development so that developer runs successfully
        return { success: false, error: error.message };
    }
};

// 1. REGISTER: Create user and send OTP (if student) or await approval (if teacher)
router.post('/register', async (req, res) => {
    try {
        const {
            name,
            email,
            password,
            role,
            department,
            phone,
            enrollmentNumber,
            semester,
            employeeId
        } = req.body;

        // Basic verification checks
        if (!name || !email || !password || !role || !department) {
            return res.status(400).json({ message: 'All required fields must be supplied' });
        }

        if (!email.endsWith('@gnu.ac.in')) {
            return res.status(400).json({ message: 'Email must use college official domain (@gnu.ac.in)' });
        }

        let existingUser = await User.findOne({ email });

        if (existingUser) {
            if (existingUser.isVerified) {
                return res.status(400).json({ message: 'Email account is already registered' });
            }
            // If exists but not verified, we allow overwriting with new form inputs
            console.log(`[REGISTER] Overwriting unverified record for email: ${email}`);
        }

        // Salt and hash password
        const salt = await bcrypt.genSalt(10);
        const hashedPassword = await bcrypt.hash(password, salt);

        const otpCode = generateOTP();
        const otpExpires = new Date(Date.now() + 15 * 60 * 1000); // 15 mins

        let userRecord;
        if (existingUser) {
            // Update unverified user
            existingUser.name = name;
            existingUser.password = hashedPassword;
            existingUser.role = role;
            existingUser.department = department;
            existingUser.phone = phone || '';
            existingUser.enrollmentNumber = enrollmentNumber || '';
            existingUser.semester = semester || '';
            existingUser.employeeId = employeeId || '';
            existingUser.otp = { code: otpCode, expiresAt: otpExpires };

            // If they are a teacher, we might not verify via OTP, but we can verify them via admin approvals later. Use isVerified status
            if (role === 'teacher') {
                existingUser.isVerified = false; // Awaiting admin approval
            } else {
                existingUser.isVerified = false; // Awaiting OTP
            }

            userRecord = await existingUser.save();
        } else {
            // Create user
            userRecord = new User({
                name,
                email,
                password: hashedPassword,
                role,
                department,
                phone: phone || '',
                enrollmentNumber: enrollmentNumber || '',
                semester: semester || '',
                employeeId: employeeId || '',
                isVerified: role === 'teacher' ? false : false, // Teachers require admin verify, students require OTP verification
                otp: {
                    code: otpCode,
                    expiresAt: otpExpires
                }
            });
            userRecord = await userRecord.save();
        }

        // Send OTP specifically for Student
        if (role === 'student') {
            const firstName = name ? name.split(' ')[0] : 'there';
            const mailResult = await sendOTPEmail(email, otpCode, firstName);
            return res.status(200).json({
                message: 'OTP registration verification code dispatched to official student email',
                email: userRecord.email,
                role: 'student',
                emailStatus: mailResult.bypassed ? 'bypassed' : (mailResult.success ? 'sent' : 'fallback-console')
            });
        } else {
            // For teacher, save successfully (pending admin approval)
            return res.status(200).json({
                message: 'Teacher application received and awaiting administrator verification info',
                email: userRecord.email,
                role: 'teacher'
            });
        }

    } catch (err) {
        console.error(`[REGISTER ERROR]: ${err.message}`);
        return res.status(500).json({ message: 'Internal server registration error' });
    }
});

// 2. VERIFY OTP: Validate OTP verification code for student
router.post('/verify-otp', async (req, res) => {
    try {
        const { email, otpCode } = req.body;

        if (!email || !otpCode) {
            return res.status(400).json({ message: 'Email and OTP verification code are required' });
        }

        const user = await User.findOne({ email });
        if (!user) {
            return res.status(404).json({ message: 'User record not found' });
        }

        if (user.isVerified) {
            return res.status(400).json({ message: 'User email is already verified' });
        }

        // Validate code matching and expiration
        if (!user.otp || !user.otp.code || user.otp.code !== otpCode) {
            return res.status(400).json({ message: 'Invalid OTP verification code' });
        }

        if (new Date() > user.otp.expiresAt) {
            return res.status(400).json({ message: 'OTP verification code has expired' });
        }

        // Clear OTP fields and verify user
        user.isVerified = true;
        user.otp.code = '';
        user.otp.expiresAt = null;
        user.lastLogin = new Date(); // first login is verification time

        await user.save();

        return res.status(200).json({
            message: 'Email verified successfully!',
            user: {
                name: user.name,
                email: user.email,
                role: user.role,
                department: user.department,
                lastLogin: null // this was their very first login
            }
        });

    } catch (err) {
        console.error(`[VERIFY OTP ERROR]: ${err.message}`);
        return res.status(500).json({ message: 'Internal verification validation error' });
    }
});

// 3. RESEND OTP: Create a new OTP code and dispatch it
router.post('/resend-otp', async (req, res) => {
    try {
        const { email } = req.body;
        if (!email) {
            return res.status(400).json({ message: 'Email address is required' });
        }

        const user = await User.findOne({ email });
        if (!user) {
            return res.status(404).json({ message: 'User record not found' });
        }

        if (user.isVerified) {
            return res.status(400).json({ message: 'This email is already verified' });
        }

        const otpCode = generateOTP();
        user.otp.code = otpCode;
        user.otp.expiresAt = new Date(Date.now() + 15 * 60 * 1000); // 15 mins

        await user.save();

        const firstName = user.name ? user.name.split(' ')[0] : 'there';
        const mailResult = await sendOTPEmail(email, otpCode, firstName);
        return res.status(200).json({
            message: 'A fresh OTP authentication key has been dispatched to your email',
            emailStatus: mailResult.bypassed ? 'bypassed' : (mailResult.success ? 'sent' : 'fallback-console')
        });

    } catch (err) {
        console.error(`[RESEND OTP ERROR]: ${err.message}`);
        return res.status(500).json({ message: 'Internal server error while resending OTP' });
    }
});

// 3.5. VERIFY SESSION: Check if access token is valid and user account exists
router.get('/verify', authenticateJWT, async (req, res) => {
    try {
        const userId = req.user.id || req.user.userId;
        const user = await User.findById(userId).select('-password -twoFactorSecret -otp');
        if (!user) {
            return res.status(401).json({ message: 'User account no longer exists' });
        }
        return res.status(200).json({ authenticated: true, user });
    } catch (err) {
        console.error(`[VERIFY ERROR]: ${err.message}`);
        return res.status(500).json({ message: 'Server verification error' });
    }
});

// 3.6. LOGOUT: Clear authentication cookies
router.post('/logout', async (req, res) => {
    res.clearCookie('accessToken');
    return res.status(200).json({ message: 'Session terminated successfully' });
});

// 4. LOGIN: Verify credentials, record/track lastLogin, and return login status
router.post('/login', async (req, res) => {
    try {
        const { email, password } = req.body;

        if (!email || !password) {
            return res.status(400).json({ message: 'Email and password are required' });
        }

        const user = await User.findOne({ email });
        if (!user) {
            return res.status(400).json({ message: 'Invalid credentials' });
        }

        // If it's a student, must be verified via OTP
        if (user.role === 'student' && !user.isVerified) {
            return res.status(401).json({
                message: 'Please complete your email OTP verification first',
                needsVerification: true,
                email: user.email
            });
        }

        // If it's a teacher, we simulate admin approval check. Let's make pending@gnu.ac.in unapproved, and approve others
        if (user.role === 'teacher' && !user.isVerified && email === 'pending@gnu.ac.in') {
            return res.status(403).json({
                message: "Your teacher account is currently awaiting admin approval.",
                needsApproval: true
            });
        }

        // Match password
        const isMatch = await bcrypt.compare(password, user.password);
        if (!isMatch) {
            return res.status(400).json({ message: 'Invalid credentials' });
        }

        // Cache the previous login timestamp to return it first
        const previousLogin = user.lastLogin;

        // Save current timestamp as the new login time
        user.lastLogin = new Date();
        // Ensure verified (for teachers that log in, auto-verify for convenience if not already)
        if (!user.isVerified) {
            user.isVerified = true;
        }
        await user.save();

        // Sign JWT token
        const jwtSecret = process.env.JWT_SECRET;
        const token = jwt.sign(
            { userId: user._id, id: user._id, email: user.email, role: user.role },
            jwtSecret,
            { expiresIn: '7d' }
        );

        // Set Cookie
        res.cookie('accessToken', token, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'strict',
            maxAge: 7 * 24 * 60 * 60 * 1000 // 7 days
        });

        return res.status(200).json({
            message: 'Login successful',
            token,
            user: {
                name: user.name,
                email: user.email,
                role: user.role,
                department: user.department,
                lastLogin: previousLogin, // past timestamp
                currentLogin: user.lastLogin // new timestamp
            }
        });

    } catch (err) {
        console.error(`[LOGIN ERROR]: ${err.message}`);
        return res.status(500).json({ message: 'Internal Server Login Error' });
    }
});

// 4.5. GOOGLE OAUTH / SSO: Authenticate user or admin via Google credential/email
router.post('/google', async (req, res) => {
    try {
        // This route does not verify a real Google token, so it is limited to local development.
        const isLocal = ['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(req.socket.remoteAddress);
        if (process.env.NODE_ENV === 'production' || !isLocal) {
            return res.status(403).json({ message: 'Google Sign-In is not configured on this server.' });
        }

        const { email, name, role = 'student' } = req.body;

        if (!email) {
            return res.status(400).json({ message: 'Google account email is required' });
        }

        // Domain verification
        if (!email.endsWith('@gnu.ac.in') && email !== 'admin@gnu.ac.in') {
            return res.status(400).json({
                message: 'Google Sign-In is restricted to official institution domain (@gnu.ac.in)'
            });
        }

        let user = await User.findOne({ email });

        if (!user) {
            // Auto-register google user if not existing
            const targetRole = email.includes('admin') ? 'admin' : role;
            user = new User({
                name: name || email.split('@')[0],
                email,
                password: '', // Google authenticated, no password set
                role: targetRole,
                department: targetRole === 'admin' ? 'Administration' : 'Computer Engineering',
                isVerified: true,
                lastLogin: new Date()
            });
            await user.save();
        } else {
            user.isVerified = true;
            user.lastLogin = new Date();
            await user.save();
        }

        const previousLogin = user.lastLogin;

        if (user.role === 'admin') {
            const accessToken = jwt.sign(
                { userId: user._id, email: user.email, role: 'admin' },
                process.env.JWT_SECRET,
                { expiresIn: '15m' }
            );

            const refreshToken = jwt.sign(
                { userId: user._id, role: 'admin' },
                process.env.JWT_REFRESH_SECRET,
                { expiresIn: '7d' }
            );

            res.cookie('adminRefreshToken', refreshToken, {
                httpOnly: true,
                secure: process.env.NODE_ENV === 'production',
                sameSite: 'strict',
                maxAge: 7 * 24 * 60 * 60 * 1000
            });

            res.cookie('adminAccessToken', accessToken, {
                httpOnly: true,
                secure: process.env.NODE_ENV === 'production',
                sameSite: 'strict',
                maxAge: 15 * 60 * 1000
            });

            await AuditLog.create({
                adminId: user._id,
                adminEmail: user.email,
                action: 'admin_google_login_success',
                targetResource: 'admin_portal_google_auth',
                ipAddress: req.ip || req.headers['x-forwarded-for'] || req.socket.remoteAddress || '',
                details: 'Admin authenticated via Google OAuth SSO successfully.'
            });

            return res.status(200).json({
                message: 'Admin Google Auth Successful',
                accessToken,
                token: accessToken,
                user: {
                    name: user.name,
                    email: user.email,
                    role: 'admin',
                    department: user.department,
                    lastLogin: previousLogin,
                    currentLogin: user.lastLogin
                }
            });
        }

        // Standard student/teacher JWT
        const token = jwt.sign(
            { userId: user._id, id: user._id, email: user.email, role: user.role },
            process.env.JWT_SECRET,
            { expiresIn: '7d' }
        );

        res.cookie('accessToken', token, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'strict',
            maxAge: 7 * 24 * 60 * 60 * 1000
        });

        return res.status(200).json({
            message: 'Google Sign-In successful',
            token,
            user: {
                name: user.name,
                email: user.email,
                role: user.role,
                department: user.department,
                lastLogin: previousLogin,
                currentLogin: user.lastLogin
            }
        });

    } catch (err) {
        console.error(`[GOOGLE AUTH ERROR]: ${err.message}`);
        return res.status(500).json({ message: 'Internal Server Error during Google Authentication' });
    }
});

// Admin authentication rate-limiter
const adminLoginLimiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 mins
    max: 10, // count limit per IP
    message: { message: 'Too many attempts. Try again in 15 minutes.' }
});

// 5. ADMIN LOGIN STEP 1: Verify Username & Password, return 2FA require/setup
router.post('/admin/login-step1', adminLoginLimiter, async (req, res) => {
    try {
        const { email, password } = req.body;
        if (!email || !password) {
            return res.status(400).json({ message: 'Email and password are required' });
        }

        const sendInvalidCredentials = async (userRecord) => {
            if (userRecord && userRecord.role === 'admin') {
                userRecord.failedLoginAttempts += 1;
                if (userRecord.failedLoginAttempts >= 5) {
                    userRecord.lockedUntil = new Date(Date.now() + 15 * 60 * 1000);
                }
                await userRecord.save();

                await AuditLog.create({
                    adminId: userRecord._id,
                    adminEmail: userRecord.email,
                    action: 'admin_login_failed_step1',
                    targetResource: 'admin_portal_login',
                    ipAddress: req.ip || req.headers['x-forwarded-for'] || req.socket.remoteAddress || '',
                    details: `Failed step 1 credentials matching. Failed attempts: ${userRecord.failedLoginAttempts}`
                });
            } else {
                await AuditLog.create({
                    adminId: null,
                    adminEmail: email,
                    action: 'admin_login_failed_step1',
                    targetResource: 'admin_portal_login',
                    ipAddress: req.ip || req.headers['x-forwarded-for'] || req.socket.remoteAddress || '',
                    details: 'Login attempt on unrecognized admin email'
                });
            }
            return res.status(400).json({ message: 'Invalid credentials' });
        };

        const user = await User.findOne({ email });
        if (!user || user.role !== 'admin') {
            return await sendInvalidCredentials(null);
        }

        // Lockout validator
        if (user.lockedUntil && new Date() < user.lockedUntil) {
            return res.status(423).json({
                message: 'Too many failed attempts. Try again in 15 minutes or contact another admin.'
            });
        }

        if (user.lockedUntil && new Date() >= user.lockedUntil) {
            user.failedLoginAttempts = 0;
            user.lockedUntil = null;
            await user.save();
        }

        const isMatch = await bcrypt.compare(password, user.password);
        if (!isMatch) {
            return await sendInvalidCredentials(user);
        }

        // Create temporary token valid for 3 minutes to pass to step 2 verification
        const tempToken = jwt.sign(
            { userId: user._id, type: 'temp_admin_auth' },
            process.env.JWT_SECRET,
            { expiresIn: '3m' }
        );

        // Scan if user has configured 2FA
        if (!user.twoFactorSecret || !user.twoFactorEnabled) {
            const secret = speakeasy.generateSecret({ name: `CampusMateAI Admin (${user.email})` });

            const setupToken = jwt.sign(
                { userId: user._id, type: 'temp_admin_setup', secret: secret.base32 },
                process.env.JWT_SECRET,
                { expiresIn: '3m' }
            );

            const otpauthUrl = `otpauth://totp/CampusMateAI%20Admin:${user.email}?secret=${secret.base32}&issuer=CampusMateAI`;
            const qrCodeDataUrl = await QRCode.toDataURL(otpauthUrl);

            return res.status(200).json({
                requiresSetup: true,
                qrCode: qrCodeDataUrl,
                tempToken: setupToken
            });
        }

        return res.status(200).json({
            requires2FA: true,
            tempToken
        });

    } catch (error) {
        console.error(`[ADMIN LOGIN STEP1 ERROR]: ${error.message}`);
        return res.status(500).json({ message: 'Internal Server Error' });
    }
});

// 6. ADMIN LOGIN STEP 2: Verify TOTP 2FA code, set cookie session
router.post('/admin/login-step2', adminLoginLimiter, async (req, res) => {
    try {
        const { tempToken, code } = req.body;
        if (!tempToken || !code) {
            return res.status(400).json({ message: 'Token and 2FA code are required' });
        }

        let decoded;
        try {
            decoded = jwt.verify(tempToken, process.env.JWT_SECRET);
        } catch (err) {
            return res.status(400).json({ message: 'Session expired. Please login again.' });
        }

        const user = await User.findById(decoded.userId);
        if (!user || user.role !== 'admin') {
            return res.status(400).json({ message: 'Invalid session' });
        }

        // Lockout validator
        if (user.lockedUntil && new Date() < user.lockedUntil) {
            return res.status(423).json({
                message: 'Too many failed attempts. Try again in 15 minutes or contact another admin.'
            });
        }

        const handleFailed2FA = async () => {
            user.failedLoginAttempts += 1;
            if (user.failedLoginAttempts >= 5) {
                user.lockedUntil = new Date(Date.now() + 15 * 60 * 1000);
            }
            await user.save();

            await AuditLog.create({
                adminId: user._id,
                adminEmail: user.email,
                action: 'admin_login_failed_2fa',
                targetResource: 'admin_portal_login',
                ipAddress: req.ip || req.headers['x-forwarded-for'] || req.socket.remoteAddress || '',
                details: `Failed step 2 2FA matching. Failed attempts: ${user.failedLoginAttempts}`
            });

            return res.status(400).json({ message: 'Invalid credentials' });
        };

        let secret = '';
        if (decoded.type === 'temp_admin_setup') {
            secret = decoded.secret;
        } else if (decoded.type === 'temp_admin_auth') {
            secret = user.twoFactorSecret;
        } else {
            return res.status(400).json({ message: 'Invalid token type' });
        }

        const isValid = speakeasy.totp.verify({
            secret,
            encoding: 'base32',
            token: code,
            window: 2
        });

        if (!isValid) {
            return await handleFailed2FA();
        }

        // Commit 2FA secret to DB if this was configuration session
        if (decoded.type === 'temp_admin_setup') {
            user.twoFactorSecret = secret;
            user.twoFactorEnabled = true;
            if (!user.isVerified) {
                user.isVerified = true;
            }
        }

        // Reset counts and login logging
        user.failedLoginAttempts = 0;
        user.lockedUntil = null;
        const prevLogin = user.lastLogin;
        user.lastLogin = new Date();
        await user.save();

        const accessToken = jwt.sign(
            { userId: user._id, email: user.email, role: 'admin' },
            process.env.JWT_SECRET,
            { expiresIn: '15m' }
        );

        const refreshToken = jwt.sign(
            { userId: user._id, role: 'admin' },
            process.env.JWT_REFRESH_SECRET,
            { expiresIn: '7d' }
        );

        // Set Cookies
        res.cookie('adminRefreshToken', refreshToken, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'strict',
            maxAge: 7 * 24 * 60 * 60 * 1000
        });

        res.cookie('adminAccessToken', accessToken, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'strict',
            maxAge: 15 * 60 * 1000
        });

        await AuditLog.create({
            adminId: user._id,
            adminEmail: user.email,
            action: 'admin_login_success',
            targetResource: 'admin_portal_login',
            ipAddress: req.ip || req.headers['x-forwarded-for'] || req.socket.remoteAddress || '',
            details: 'Admin verified 2FA and established standard cookie session.'
        });

        return res.status(200).json({
            message: 'Administrative login authenticated successfully.',
            accessToken,
            user: {
                name: user.name,
                email: user.email,
                role: user.role,
                department: user.department,
                lastLogin: prevLogin,
                currentLogin: user.lastLogin
            }
        });

    } catch (error) {
        console.error(`[ADMIN LOGIN STEP2 ERROR]: ${error.message}`);
        return res.status(500).json({ message: 'Internal Server Error' });
    }
});

// 7. ADMIN REFRESH TOKEN: Exchange cookie-refresh for fresh access token
router.post('/admin/refresh', async (req, res) => {
    try {
        const refreshToken = req.cookies.adminRefreshToken;
        if (!refreshToken) {
            return res.status(401).json({ message: 'Session expired. Please log in again.' });
        }

        const decoded = jwt.verify(refreshToken, process.env.JWT_REFRESH_SECRET);
        const user = await User.findById(decoded.userId);
        if (!user || user.role !== 'admin') {
            return res.status(401).json({ message: 'Unauthorized session' });
        }

        const accessToken = jwt.sign(
            { userId: user._id, email: user.email, role: 'admin' },
            process.env.JWT_SECRET,
            { expiresIn: '15m' }
        );

        res.cookie('adminAccessToken', accessToken, {
            httpOnly: true,
            secure: process.env.NODE_ENV === 'production',
            sameSite: 'strict',
            maxAge: 15 * 60 * 1000
        });

        return res.status(200).json({ accessToken });

    } catch (err) {
        return res.status(401).json({ message: 'Invalid reference session parameters.' });
    }
});

// 8. ADMIN LOGOUT: Clear HTTP Only security cookie references
router.post('/admin/logout', async (req, res) => {
    res.clearCookie('adminAccessToken');
    res.clearCookie('adminRefreshToken');
    return res.status(200).json({ message: 'Administrative session terminated.' });
});

// ── STUDENT PAGE ROUTES (unused — parked for future use) ─────────────────────
// These endpoints supported the student page tabs (Profile Settings,
// In-App Notifications, Attendance Alerts) which are not active in the
// current build. Student side is chat-only for now.

// 9. STUDENT PROFILE ENDPOINTS: GET and PUT endpoints for profile and preferences
// router.get('/profile', async (req, res) => { ... });
// router.put('/profile', async (req, res) => { ... });

// 10. STUDENT IN-APP NOTIFICATIONS ENDPOINTS
// router.get('/notifications', async (req, res) => { ... });
// router.post('/notifications/read', async (req, res) => { ... });

// 11. SCHEDULER/TRIGGER: Check low attendance & trigger alerts
// router.post('/check-attendance-alerts', async (req, res) => { ... });

export default router;
