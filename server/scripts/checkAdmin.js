import mongoose from 'mongoose';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.join(__dirname, '../.env') });

await mongoose.connect(process.env.MONGO_URI || 'mongodb://localhost:27017/CampusMateAI_2');

const UserSchema = new mongoose.Schema({
    email: String,
    role: String,
    password: String,
    twoFactorSecret: String,
    twoFactorEnabled: Boolean,
    failedLoginAttempts: Number,
    lockedUntil: Date,
    isVerified: Boolean
}, { strict: false });

const User = mongoose.model('User', UserSchema);
const admin = await User.findOne({ role: 'admin' });

if (!admin) {
    console.log('NO ADMIN USER FOUND IN DATABASE');
} else {
    console.log('Admin user state:');
    console.log('  email:', admin.email);
    console.log('  role:', admin.role);
    console.log('  isVerified:', admin.isVerified);
    console.log('  twoFactorEnabled:', admin.twoFactorEnabled);
    console.log('  twoFactorSecret set?', !!(admin.twoFactorSecret && admin.twoFactorSecret.length > 0));
    console.log('  twoFactorSecret length:', (admin.twoFactorSecret || '').length);
    console.log('  failedLoginAttempts:', admin.failedLoginAttempts);
    console.log('  lockedUntil:', admin.lockedUntil);
}

await mongoose.disconnect();
