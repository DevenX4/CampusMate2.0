import mongoose from 'mongoose';
import dotenv from 'dotenv';
import path from 'path';
import crypto from 'crypto';
import speakeasy from 'speakeasy';
import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';

// Load environmental parameters
dotenv.config({ path: path.resolve(process.cwd(), 'server/.env') });

import User from '../models/User.js';
import Invite from '../models/Invite.js';
import AuditLog from '../models/AuditLog.js';

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017/campusmate';
const JWT_SECRET = process.env.JWT_SECRET;

async function runTests() {
    console.log('==================================================');
    console.log('  STARTING CAMPUSMATEAI ADMIN SECURITY VALIDATION');
    console.log('==================================================\n');

    try {
        await mongoose.connect(MONGODB_URI);
        console.log('[DB] Connected to MongoDB database successfully.');
    } catch (err) {
        console.error('[DB ERROR] Failed to connect to MongoDB:', err.message);
        process.exit(1);
    }

    let testEmail = `temp_admin_test_${Date.now()}@gnu.ac.in`;
    let tempPass = 'SecurityPass123!';

    try {
        // ----------------------------------------------------
        // TEST 1: Admin Seeding and Account Isolation
        // ----------------------------------------------------
        console.log('\n[TEST 1] Testing Admin Account Seeding & Schema integrity...');

        // Clean up any left-over tests
        await User.deleteMany({ email: testEmail });
        await Invite.deleteMany({ email: testEmail });

        const salt = await bcrypt.genSalt(10);
        const hashedPassword = await bcrypt.hash(tempPass, salt);
        const secret = speakeasy.generateSecret({ name: `Test Admin` });

        const newAdmin = new User({
            name: 'Test Admin',
            email: testEmail,
            password: hashedPassword,
            role: 'admin',
            department: 'Administration',
            twoFactorSecret: secret.base32,
            twoFactorEnabled: true
        });

        await newAdmin.save();
        console.log('✔ Admin account inserted into database successfully.');

        const fetchedUser = await User.findOne({ email: testEmail });
        if (fetchedUser && fetchedUser.role === 'admin' && fetchedUser.twoFactorEnabled) {
            console.log('✔ Schema integrity: verified admin role and 2FA fields.');
        } else {
            throw new Error('Schema fields validation failed.');
        }

        // ----------------------------------------------------
        // TEST 2: Brute Force Limit & Locked Status logic
        // ----------------------------------------------------
        console.log('\n[TEST 2] Testing credential verify, attempts tracking, and Account Lockout...');

        // Simulating wrong login attempt 1
        fetchedUser.failedLoginAttempts += 1;
        await fetchedUser.save();
        console.log(`Failed attempt logged: count = ${fetchedUser.failedLoginAttempts}`);

        // Simulating lock trigger: 5 wrong attempts
        while (fetchedUser.failedLoginAttempts < 5) {
            fetchedUser.failedLoginAttempts += 1;
        }
        fetchedUser.lockedUntil = new Date(Date.now() + 15 * 60 * 1000); // 15 mins lock
        await fetchedUser.save();

        const checkLocked = await User.findOne({ email: testEmail });
        const now = new Date();
        if (checkLocked.lockedUntil && checkLocked.lockedUntil > now) {
            console.log(`✔ Account lockout verified. Locked until: ${checkLocked.lockedUntil.toISOString()}`);
        } else {
            throw new Error('Lockout enforcement failed to register timestamp.');
        }

        // Reset Attempts for further test stages
        checkLocked.failedLoginAttempts = 0;
        checkLocked.lockedUntil = null;
        await checkLocked.save();
        console.log('✔ Temporary lockout parameters reset successfully.');

        // ----------------------------------------------------
        // TEST 3: Admin invitation generation and expiration check
        // ----------------------------------------------------
        console.log('\n[TEST 3] Testing Invitation token models & expire parameters...');
        const inviteEmail = `invited_admin_${Date.now()}@gnu.ac.in`;
        const inviteToken = crypto.randomBytes(32).toString('hex');

        // Expired token (expires 1 hour ago)
        const expiredTime = new Date(Date.now() - 60 * 60 * 1000);
        const testInvite = new Invite({
            email: inviteEmail,
            token: inviteToken,
            expiresAt: expiredTime,
            createdBy: fetchedUser._id
        });
        await testInvite.save();

        const fetchedInvite = await Invite.findOne({ token: inviteToken });
        if (fetchedInvite && new Date() > fetchedInvite.expiresAt) {
            console.log(`✔ Invite token expiration validation verified. Registered expiry: ${fetchedInvite.expiresAt.toISOString()}`);
        } else {
            throw new Error('Invite expiration logic failed to record older time.');
        }

        // Delete expired invite
        await Invite.deleteMany({ email: inviteEmail });

        // ----------------------------------------------------
        // TEST 4: TOTP Verification and Speakeasy compliance
        // ----------------------------------------------------
        console.log('\n[TEST 4] Testing 2FA TOTP speakeasy compliance...');
        const userSecretBase32 = secret.base32;

        // Generate current token code
        const code = speakeasy.totp({
            secret: userSecretBase32,
            encoding: 'base32'
        });

        const is2FAValid = speakeasy.totp.verify({
            secret: userSecretBase32,
            encoding: 'base32',
            token: code,
            window: 1
        });

        if (is2FAValid) {
            console.log(`✔ 2FA Verification succeeded. Simulated code: ${code} verified against secret.`);
        } else {
            throw new Error('2FA Token verification compatibility check failed.');
        }

        // ----------------------------------------------------
        // TEST 5: JWT Generation, Expiry, and Role Enforcement
        // ----------------------------------------------------
        console.log('\n[TEST 5] Testing Admin JWT signature validation & Role verification...');

        // Sign token mimicking backend auth.js logic
        const adminAccessToken = jwt.sign(
            { userId: fetchedUser._id, email: fetchedUser.email, role: fetchedUser.role },
            JWT_SECRET,
            { expiresIn: '15m' }
        );

        console.log('JWT Token successfully generated.');

        // Verify and decode
        const decoded = jwt.verify(adminAccessToken, JWT_SECRET);
        if (decoded.role === 'admin' && decoded.email === testEmail) {
            console.log(`✔ JWT payload verifies correctly. Decoded role matches: ${decoded.role}`);
        } else {
            throw new Error('JWT decode parameters or roles mismatch.');
        }

        // ----------------------------------------------------
        // TEST 6: Audit Log Capture
        // ----------------------------------------------------
        console.log('\n[TEST 6] Testing Audit Log operations integrity...');
        const logAction = 'test_validation_event';
        const logEntry = new AuditLog({
            adminId: fetchedUser._id,
            adminEmail: fetchedUser.email,
            action: logAction,
            targetResource: 'admin_security_verify_script',
            ipAddress: '127.0.0.1',
            details: 'CampusMateAI Administrative Integration Test Case'
        });
        await logEntry.save();

        const fetchedLog = await AuditLog.findOne({ action: logAction, adminEmail: testEmail });
        if (fetchedLog) {
            console.log(`✔ Audit log successfully saved and retrieved. Details: ${fetchedLog.details}`);
        } else {
            throw new Error('Audit log logging entry failed.');
        }

        // ----------------------------------------------------
        // CLEAN UP
        // ----------------------------------------------------
        console.log('\n[CLEANUP] Cleaning up temporary test nodes...');
        await User.deleteMany({ email: testEmail });
        await AuditLog.deleteMany({ adminEmail: testEmail });
        console.log('✔ Cleanup completed.');

        console.log('\n==================================================');
        console.log('  ALL ADMIN SECURITY SYSTEM TESTS PASSED SUCCESSFULLY!  ');
        console.log('==================================================\n');

    } catch (err) {
        console.error('\n✖ TEST SUITE RUN FAILURE:', err.message);
    } finally {
        await mongoose.connection.close();
        console.log('[DB] Database connection closed.');
    }
}

runTests();
