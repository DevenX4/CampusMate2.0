import mongoose from 'mongoose';
import { withMemoryFallback } from './memoryStore.js';

const InviteSchema = new mongoose.Schema({
    email: {
        type: String,
        required: true,
        unique: true,
        lowercase: true,
        trim: true
    },
    token: {
        type: String,
        required: true,
        unique: true
    },
    expiresAt: {
        type: Date,
        required: true
    },
    isUsed: {
        type: Boolean,
        default: false
    },
    createdBy: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        required: true
    },
    twoFactorSecret: {
        type: String,
        default: ''
    }
}, {
    timestamps: true
});

const MongooseInvite = mongoose.model('Invite', InviteSchema);
const Invite = withMemoryFallback(MongooseInvite, () => ({ isUsed: false, twoFactorSecret: '' }));
export default Invite;
