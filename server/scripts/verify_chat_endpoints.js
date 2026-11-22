import mongoose from 'mongoose';
import dotenv from 'dotenv';
import path from 'path';
import axios from 'axios';
import jwt from 'jsonwebtoken';

// Load environmental parameters
dotenv.config({ path: path.resolve(process.cwd(), 'server/.env') });

const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017/campusmate';
const JWT_SECRET = process.env.JWT_SECRET;

import User from '../models/User.js';

async function verifyChatAPI() {
    console.log('--- STARTING CHAT ROUTER VERIFICATION ---');
    try {
        await mongoose.connect(MONGODB_URI);
        console.log('[DB] Connected to MongoDB.');

        // Find or create test student
        let student = await User.findOne({ role: 'student' });
        if (!student) {
            console.log('Seeding mock student for test...');
            student = new User({
                name: 'Test Chat Student',
                email: 'chatstudent@gnu.ac.in',
                password: 'hashedpassworddontmatter',
                role: 'student',
                department: 'Computer Science',
                semester: '6',
                isVerified: true
            });
            await student.save();
        }

        console.log(`[USER] Testing with student email: ${student.email}`);

        // Sign JWT mimicking auth behavior
        const token = jwt.sign(
            { userId: student._id.toString(), id: student._id.toString(), email: student.email, role: student.role },
            JWT_SECRET,
            { expiresIn: '1h' }
        );

        const config = {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        };

        // Terminate checks on localhost:5000 endpoints
        // 1. Direct RAG
        console.log('\n[TEST 1] POSTing to /api/chat/direct ...');
        const directRes1 = await axios.post('http://localhost:5000/api/chat/direct', {
            message: 'Am I below the attendance limit?'
        }, config);
        console.log('Status:', directRes1.status);
        console.log('Data:', JSON.stringify(directRes1.data, null, 2));

        // 2. Direct ECE RAG
        console.log('\n[TEST 2] POSTing notice query to /api/chat/direct ...');
        const directRes2 = await axios.post('http://localhost:5000/api/chat/direct', {
            message: 'Show details from recent academic notices'
        }, config);
        console.log('Status:', directRes2.status);
        console.log('Data:', JSON.stringify(directRes2.data, null, 2));

        // 3. n8n workflow engine
        console.log('\n[TEST 3] POSTing to /api/chat/n8n ...');
        const n8nRes = await axios.post('http://localhost:5000/api/chat/n8n', {
            message: 'Explain Unit 3 routing tables'
        }, config);
        console.log('Status:', n8nRes.status);
        console.log('Data:', JSON.stringify(n8nRes.data, null, 2));

        console.log('\n--- VERIFICATION SUCCESSFULLY PASSED ---');

        // Delete temporary seed student if created specifically
        if (student.email === 'chatstudent@gnu.ac.in') {
            await User.deleteOne({ email: 'chatstudent@gnu.ac.in' });
            console.log('[CLEANUP] Deleted mock student.');
        }

    } catch (err) {
        console.error('\n✖ VERIFICATION FAILED:', err.message);
        if (err.response) {
            console.error('Response Error details:', err.response.data);
        }
    } finally {
        await mongoose.connection.close();
        console.log('[DB] Database connection closed.');
    }
}

verifyChatAPI();
