import mongoose from 'mongoose';
import { withMemoryFallback } from './memoryStore.js';

const knowledgeFileSchema = new mongoose.Schema({
    originalName: { type: String, required: true },
    storedName:   { type: String, required: true },
    filePath:     { type: String, required: true },
    mimeType:     { type: String, default: '' },
    size:         { type: Number, default: 0 }, // bytes
    status: {
        type: String,
        enum: ['pending', 'processing', 'indexed', 'error'],
        default: 'pending'
    },
    uploadedBy:   { type: mongoose.Schema.Types.ObjectId, ref: 'User', default: null },
    uploadedByEmail: { type: String, default: '' },
    description:  { type: String, default: '' },
    uploadedAt:   { type: Date, default: Date.now },
});

const MongooseKnowledgeFile = mongoose.model('KnowledgeFile', knowledgeFileSchema);
const KnowledgeFile = withMemoryFallback(MongooseKnowledgeFile, () => ({ status: 'pending', uploadedAt: new Date() }));
export default KnowledgeFile;
