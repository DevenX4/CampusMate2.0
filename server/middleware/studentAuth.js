import jwt from 'jsonwebtoken';

export const authenticateJWT = async (req, res, next) => {
    let token = '';

    // 1. Extract token from Authorization header or cookies
    if (req.headers.authorization && req.headers.authorization.startsWith('Bearer ')) {
        token = req.headers.authorization.split(' ')[1];
    } else if (req.cookies && req.cookies.accessToken) {
        token = req.cookies.accessToken;
    }

    if (token) {
        try {
            const decoded = jwt.verify(token, process.env.JWT_SECRET);
            req.user = decoded;
            // Ensure decoded has an id property mapped correctly to userId or _id
            if (!req.user.id && req.user.userId) {
                req.user.id = req.user.userId;
            }
            return next();
        } catch (err) {
            console.error(`[JWT AUTH EXCEPTION]: ${err.message}`);
            return res.status(401).json({ message: 'Session expired or invalid token. Access denied.' });
        }
    }

    return res.status(401).json({ message: 'Authentication required. Access denied.' });
};
