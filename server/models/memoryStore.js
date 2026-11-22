// In-memory stand-ins used while MongoDB is not running, so the admin screens keep working.
// Records stored here are lost when the server restarts.
import { randomUUID } from 'crypto';
import { isMongoConnected } from '../config/db.js';

export function matchesQuery(doc, query = {}) {
    return Object.entries(query).every(([key, condition]) => {
        const isOperator = condition && typeof condition === 'object' && !(condition instanceof Date);
        if (isOperator && '$gte' in condition) return doc[key] >= condition.$gte;
        return doc[key] === condition;
    });
}

function project(value, projection) {
    if (!projection) return value;
    if (Array.isArray(value)) return value.map((doc) => project(doc, projection));
    if (!value) return value;
    const fields = projection.split(/\s+/).filter(Boolean);
    const copy = { ...value };
    if (fields.every((field) => field.startsWith('-'))) {
        fields.forEach((field) => delete copy[field.slice(1)]);
        return copy;
    }
    return Object.fromEntries(Object.entries(copy).filter(([key]) => key === '_id' || fields.includes(key)));
}

// Supports the query chain the routes use: .select().sort().limit() and await.
export function memoryQuery(value) {
    let current = value;
    const query = {
        select(projection) { current = project(current, projection); return query; },
        sort(spec = {}) {
            if (Array.isArray(current)) {
                const keys = Object.entries(spec);
                current = [...current].sort((a, b) => {
                    for (const [key, direction] of keys) {
                        if (a[key] < b[key]) return -direction;
                        if (a[key] > b[key]) return direction;
                    }
                    return 0;
                });
            }
            return query;
        },
        limit(count) { if (Array.isArray(current)) current = current.slice(0, count); return query; },
        lean() { return query; },
        exec() { return Promise.resolve(current); },
        then(resolve, reject) { return Promise.resolve(current).then(resolve, reject); },
        catch(onRejected) { return Promise.resolve(current).catch(onRejected); },
    };
    return query;
}

export function withMemoryFallback(MongooseModel, defaults = () => ({})) {
    const docs = [];

    const toDoc = (data) => {
        const now = new Date();
        const doc = { _id: `mem_${randomUUID()}`, createdAt: now, updatedAt: now, ...defaults(), ...data };
        Object.defineProperty(doc, 'save', {
            enumerable: false,
            value: async function save() {
                this.updatedAt = new Date();
                if (!docs.includes(this)) docs.push(this);
                return this;
            },
        });
        return doc;
    };
    const byId = (id) => docs.find((doc) => String(doc._id) === String(id)) || null;

    return class MemoryBackedModel {
        constructor(data) {
            return isMongoConnected ? new MongooseModel(data) : toDoc(data);
        }

        static async create(data) {
            if (isMongoConnected) return MongooseModel.create(data);
            return toDoc(data).save();
        }

        static find(query = {}, projection) {
            if (isMongoConnected) return MongooseModel.find(query, projection);
            return memoryQuery(docs.filter((doc) => matchesQuery(doc, query))).select(projection);
        }

        static findOne(query = {}) {
            if (isMongoConnected) return MongooseModel.findOne(query);
            return memoryQuery(docs.find((doc) => matchesQuery(doc, query)) || null);
        }

        static findById(id) {
            if (isMongoConnected) return MongooseModel.findById(id);
            return memoryQuery(byId(id));
        }

        static findByIdAndUpdate(id, update, options = {}) {
            if (isMongoConnected) return MongooseModel.findByIdAndUpdate(id, update, options);
            const doc = byId(id);
            if (doc) Object.assign(doc, update.$set || update, { updatedAt: new Date() });
            return memoryQuery(doc);
        }

        static findByIdAndDelete(id) {
            if (isMongoConnected) return MongooseModel.findByIdAndDelete(id);
            const doc = byId(id);
            if (doc) docs.splice(docs.indexOf(doc), 1);
            return memoryQuery(doc);
        }

        static countDocuments(query = {}) {
            if (isMongoConnected) return MongooseModel.countDocuments(query);
            return memoryQuery(docs.filter((doc) => matchesQuery(doc, query)).length);
        }

        static async deleteMany(query = {}) {
            if (isMongoConnected) return MongooseModel.deleteMany(query);
            const remove = docs.filter((doc) => matchesQuery(doc, query));
            remove.forEach((doc) => docs.splice(docs.indexOf(doc), 1));
            return { deletedCount: remove.length };
        }
    };
}
