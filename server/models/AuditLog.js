import mongoose from 'mongoose';
import { isMongoConnected } from '../config/db.js';
import { memoryQuery } from './memoryStore.js';

const AuditLogSchema = new mongoose.Schema({
    adminId: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        default: null
    },
    adminEmail: {
        type: String,
        default: ''
    },
    action: {
        type: String,
        required: true
    },
    targetResource: {
        type: String,
        default: ''
    },
    ipAddress: {
        type: String,
        default: ''
    },
    details: {
        type: String,
        default: ''
    },
    timestamp: {
        type: Date,
        default: Date.now
    }
});

const MongooseAuditLog = mongoose.model('AuditLog', AuditLogSchema);
const inMemoryAuditLogs = [];

class AuditLogProxy {
    static async create(data) {
        if (isMongoConnected) {
            return MongooseAuditLog.create(data);
        }
        const log = {
            _id: `log_${Date.now()}_${Math.random()}`,
            ...data,
            timestamp: new Date()
        };
        inMemoryAuditLogs.push(log);
        return log;
    }

    static find(query = {}) {
        if (isMongoConnected) {
            return MongooseAuditLog.find(query);
        }
        return memoryQuery([...inMemoryAuditLogs]);
    }
}

export default AuditLogProxy;
