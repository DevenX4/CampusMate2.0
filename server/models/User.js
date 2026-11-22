import mongoose from 'mongoose';
import bcrypt from 'bcryptjs';
import { isMongoConnected } from '../config/db.js';
import { matchesQuery, memoryQuery } from './memoryStore.js';

const UserSchema = new mongoose.Schema({
    name: { type: String, required: true, trim: true },
    email: { type: String, required: true, unique: true, lowercase: true, trim: true },
    password: { type: String, required: true },
    role: { type: String, enum: ['student', 'teacher', 'admin'], required: true },
    department: { type: String, required: true },
    phone: { type: String, default: '' },
    enrollmentNumber: { type: String, trim: true, default: '' },
    semester: { type: String, default: '' },
    employeeId: { type: String, trim: true, default: '' },
    isVerified: { type: Boolean, default: false },
    otp: {
        code: { type: String, default: '' },
        expiresAt: { type: Date }
    },
    lastLogin: { type: Date, default: null },
    twoFactorSecret: { type: String, default: '' },
    twoFactorEnabled: { type: Boolean, default: false },
    failedLoginAttempts: { type: Number, default: 0 },
    lockedUntil: { type: Date, default: null },
    notificationPreferences: {
        lowAttendance: { email: { type: Boolean, default: true }, inApp: { type: Boolean, default: true } },
        newAssignment: { email: { type: Boolean, default: false }, inApp: { type: Boolean, default: true } },
        assignmentDue: { email: { type: Boolean, default: true }, inApp: { type: Boolean, default: true } },
        gradePublished: { email: { type: Boolean, default: false }, inApp: { type: Boolean, default: true } },
        newNotice: { email: { type: Boolean, default: false }, inApp: { type: Boolean, default: true } },
        eventReminder: { email: { type: Boolean, default: false }, inApp: { type: Boolean, default: true } }
    },
    notifications: [{
        text: { type: String, required: true },
        type: { type: String, default: 'info' },
        unread: { type: Boolean, default: true },
        timestamp: { type: Date, default: Date.now }
    }]
}, { timestamps: true });

const MongooseUser = mongoose.model('User', UserSchema);

// In-Memory Storage Fallback when MongoDB daemon is not running locally
const inMemoryUsers = new Map();

// Helper to wrap object as doc
function createInMemoryUserDoc(data) {
    const doc = {
        _id: data._id || `user_${Date.now()}_${Math.floor(Math.random() * 10000)}`,
        name: data.name || '',
        email: (data.email || '').toLowerCase(),
        password: data.password || '',
        role: data.role || 'student',
        department: data.department || 'IT',
        phone: data.phone || '',
        enrollmentNumber: data.enrollmentNumber || '',
        semester: data.semester || '',
        employeeId: data.employeeId || '',
        isVerified: data.isVerified !== undefined ? data.isVerified : false,
        otp: data.otp || { code: '', expiresAt: null },
        lastLogin: data.lastLogin || null,
        twoFactorSecret: data.twoFactorSecret || '',
        twoFactorEnabled: data.twoFactorEnabled || false,
        failedLoginAttempts: data.failedLoginAttempts || 0,
        lockedUntil: data.lockedUntil || null,
        createdAt: data.createdAt || new Date(),
        updatedAt: new Date(),

        async save() {
            this.updatedAt = new Date();
            inMemoryUsers.set(this.email.toLowerCase(), this);
            inMemoryUsers.set(this._id.toString(), this);
            return this;
        }
    };

    doc.saveSync = () => {
        inMemoryUsers.set(doc.email.toLowerCase(), doc);
        inMemoryUsers.set(doc._id.toString(), doc);
        return doc;
    };

    return doc;
}

// Seed default accounts in memory
const defaultAdmin = createInMemoryUserDoc({
    _id: '65f1a2b3c4d5e6f7a8b9c0d1',
    name: 'Admin User',
    email: 'admin@gnu.ac.in',
    password: bcrypt.hashSync('DemoAdmin@2026', 10),
    role: 'admin',
    department: 'Administration',
    isVerified: true
});
defaultAdmin.saveSync();

const defaultStudent = createInMemoryUserDoc({
    _id: '65f1a2b3c4d5e6f7a8b9c0d2',
    name: 'Student User',
    email: 'student@gnu.ac.in',
    password: bcrypt.hashSync('DemoStudent@2026', 10),
    role: 'student',
    department: 'Information Technology',
    enrollmentNumber: 'CM-2026-001',
    semester: '4',
    isVerified: true
});
defaultStudent.saveSync();

const defaultDemoUser = createInMemoryUserDoc({
    _id: '65f1a2b3c4d5e6f7a8b9c0d3',
    name: 'Demo Student',
    email: 'demo.student@gnu.ac.in',
    password: bcrypt.hashSync('DemoUser@2026', 10),
    role: 'student',
    department: 'Information Technology',
    enrollmentNumber: 'CM-2026-002',
    semester: '4',
    isVerified: true
});
defaultDemoUser.saveSync();

const makeQueryable = memoryQuery;

class UserProxy {
    constructor(data) {
        if (isMongoConnected) {
            return new MongooseUser(data);
        } else {
            return createInMemoryUserDoc(data);
        }
    }

    static findOne(query) {
        if (isMongoConnected) {
            return MongooseUser.findOne(query);
        }
        let found = null;
        if (query.email) {
            found = inMemoryUsers.get(query.email.toLowerCase()) || null;
        } else if (query._id) {
            found = inMemoryUsers.get(query._id.toString()) || null;
        } else {
            for (const user of inMemoryUsers.values()) {
                let match = true;
                for (const key in query) {
                    if (user[key] !== query[key]) {
                        match = false;
                        break;
                    }
                }
                if (match) {
                    found = user;
                    break;
                }
            }
        }
        return makeQueryable(found);
    }

    static findById(id) {
        if (isMongoConnected) {
            return MongooseUser.findById(id);
        }
        const found = inMemoryUsers.get(id ? id.toString() : '') || null;
        return makeQueryable(found);
    }

    static find(query = {}, projection) {
        if (isMongoConnected) {
            return MongooseUser.find(query, projection);
        }
        const list = Array.from(new Set(inMemoryUsers.values()));
        return makeQueryable(list.filter(u => matchesQuery(u, query))).select(projection);
    }

    static countDocuments(query = {}) {
        if (isMongoConnected) {
            return MongooseUser.countDocuments(query);
        }
        const list = Array.from(new Set(inMemoryUsers.values()));
        return makeQueryable(list.filter(u => matchesQuery(u, query)).length);
    }

    static findByIdAndUpdate(id, update, options = {}) {
        if (isMongoConnected) {
            return MongooseUser.findByIdAndUpdate(id, update, options);
        }
        const user = inMemoryUsers.get(id ? id.toString() : '');
        if (user) {
            Object.assign(user, update.$set || update);
            user.saveSync();
        }
        return makeQueryable(user);
    }

    static findByIdAndDelete(id) {
        if (isMongoConnected) {
            return MongooseUser.findByIdAndDelete(id);
        }
        const user = inMemoryUsers.get(id ? id.toString() : '');
        if (user) {
            inMemoryUsers.delete(user.email.toLowerCase());
            inMemoryUsers.delete(user._id.toString());
        }
        return makeQueryable(user);
    }

    static async create(data) {
        if (isMongoConnected) {
            return MongooseUser.create(data);
        }
        const doc = createInMemoryUserDoc(data);
        await doc.save();
        return doc;
    }
}

export default UserProxy;
