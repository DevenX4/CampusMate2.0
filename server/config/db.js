import mongoose from 'mongoose';

export let isMongoConnected = false;

export const connectDB = async () => {
    try {
        const uri = process.env.MONGO_URI || 'mongodb://127.0.0.1:27017/campusmate';
        const conn = await mongoose.connect(uri, {
            serverSelectionTimeoutMS: 2000
        });
        isMongoConnected = true;
        console.log(`[DB] MongoDB Connected: ${conn.connection.host}`);
    } catch (error) {
        isMongoConnected = false;
        console.warn(`[DB] Local MongoDB daemon not detected (${error.message}). Activating seamless in-memory user & auth store.`);
    }
};
