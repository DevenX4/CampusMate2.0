import mongoose from 'mongoose';
import bcrypt from 'bcryptjs';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';
import User from '../models/User.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load env parameters matching project root or server dir
dotenv.config({ path: path.join(__dirname, '../.env') });

const MONGO_URI = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/CampusMateAI_2';

const seedAdmin = async () => {
    console.log('--- CAMPUSMATEAI ADMIN BOOTSTRAP SEEDING ---');
    try {
        console.log(`Connecting to MongoDB at: ${MONGO_URI}`);
        await mongoose.connect(MONGO_URI);
        console.log('MongoDB connection initialized successfully.');

        // Parameters for default administrator
        const adminEmail = 'admin@gnu.ac.in';
        const adminPassword = 'DemoAdmin@2026';

        // Check if admin already exists
        const existingAdmin = await User.findOne({ role: 'admin' });
        if (existingAdmin) {
            console.log(`[BOOTSTRAP SUCCESS] An admin user already exists: ${existingAdmin.email}`);
            console.log('No action taken to preserve existing administrative credentials.');
            return;
        }

        // Salt and hash credentials
        const salt = await bcrypt.genSalt(10);
        const hashedPassword = await bcrypt.hash(adminPassword, salt);

        const newAdmin = new User({
            name: 'System Administrator',
            email: adminEmail,
            password: hashedPassword,
            role: 'admin',
            department: 'Administration',
            phone: '0000000000',
            isVerified: true,
            twoFactorEnabled: false, // Setup on first login
            twoFactorSecret: '',
            lastLogin: null
        });

        await newAdmin.save();
        console.log('\n======================================================');
        console.log('ADMINISTRATOR ACCOUNT CREATED SUCCESSFULLY!');
        console.log(`Email:    ${adminEmail}`);
        console.log(`Password: ${adminPassword}`);
        console.log('Please login to set up 2FA at the admin portal.');
        console.log('======================================================\n');

    } catch (error) {
        console.error(`[SEED ERROR] Failed to seed administrator: ${error.message}`);
    } finally {
        await mongoose.disconnect();
        console.log('MongoDB database disconnected.');
    }
};

seedAdmin();
