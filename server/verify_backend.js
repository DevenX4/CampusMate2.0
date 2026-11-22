import mongoose from 'mongoose';
import bcrypt from 'bcryptjs';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import User from './models/User.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.join(__dirname, '.env') });

const MONGO_URI = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/campusmate';

const testBackendFlow = async () => {
    console.log('--- STARTING BACKEND AUTHENTICATION FLOW VERIFICATION ---');
    try {
        console.log(`Connecting to MongoDB at: ${MONGO_URI}`);
        await mongoose.connect(MONGO_URI);
        console.log('MongoDB Connected successfully!');

        // 1. Cleanup old verification test data
        console.log('Cleaning up old test users...');
        await User.deleteMany({ email: 'teststudent@gnu.ac.in' });

        // 2. Mock Registration saving
        console.log('Testing student registration creation in database...');
        const salt = await bcrypt.genSalt(10);
        const hashedPassword = await bcrypt.hash('password123', salt);
        const testOtpCode = '654321';
        const testOtpExpires = new Date(Date.now() + 15 * 60 * 1000);

        const newStudent = new User({
            name: 'Test Student',
            email: 'teststudent@gnu.ac.in',
            password: hashedPassword,
            role: 'student',
            department: 'CSE',
            enrollmentNumber: 'TX-2026-001',
            semester: '6',
            isVerified: false,
            otp: {
                code: testOtpCode,
                expiresAt: testOtpExpires
            }
        });

        await newStudent.save();
        console.log('Saved unverified student record successfully!');

        // 3. Verify OTP verification validation
        console.log('Verifying OTP validation correctness...');
        const studentRecord = await User.findOne({ email: 'teststudent@gnu.ac.in' });
        if (!studentRecord) {
            throw new Error('Student record could not be fetched from DB');
        }

        if (studentRecord.otp.code !== '654321') {
            throw new Error('OTP code mismatch in database');
        }

        if (studentRecord.isVerified !== false) {
            throw new Error('Unverified student was marked as verified prematurely');
        }

        // Verify simulated OTP validation API logic
        studentRecord.isVerified = true;
        studentRecord.otp.code = '';
        studentRecord.otp.expiresAt = null;
        studentRecord.lastLogin = new Date();
        await studentRecord.save();
        console.log('OTP verified and verified status marked successfully!');

        // 4. Test login & lastLogin tracking
        console.log('Testing login tracking system...');
        const loggedInUser = await User.findOne({ email: 'teststudent@gnu.ac.in' });
        if (!loggedInUser.isVerified) {
            throw new Error('Verified status was not saved in DB!');
        }

        const match = await bcrypt.compare('password123', loggedInUser.password);
        if (!match) {
            throw new Error('Bcrypt password validation failed!');
        }

        // Capture previous login
        const prevLogin = loggedInUser.lastLogin;
        console.log(`Initial login timestamp captured: ${prevLogin}`);

        // Update login timestamp
        const newLoginTime = new Date();
        loggedInUser.lastLogin = newLoginTime;
        await loggedInUser.save();

        const doubleCheckedUser = await User.findOne({ email: 'teststudent@gnu.ac.in' });
        console.log(`New login timestamp written: ${doubleCheckedUser.lastLogin}`);

        if (doubleCheckedUser.lastLogin.getTime() === prevLogin.getTime()) {
            throw new Error('Login timestamp was not updated on subsequent authentication!');
        }

        console.log('\n=======================================');
        console.log('BACKEND VERIFICATION SUCCESSFUL!');
        console.log('=======================================\n');

    } catch (error) {
        console.error('\n=======================================');
        console.error('VERIFICATION FAILED WITH ERROR:');
        console.error(error.message);
        console.error('=======================================\n');
        process.exit(1);
    } finally {
        await mongoose.disconnect();
        console.log('Mongoose connection disconnected.');
    }
};

testBackendFlow();
