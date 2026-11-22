import { useState } from 'react';
import { Zap } from 'lucide-react';
import AuthShell, { AuthAlert, AuthField, AuthHeading, AuthPasswordField, AuthSubmit } from './auth/AuthShell';
import { useCampyState } from './auth/useCampyState';

/**
 * Technical Security & Architecture Comments:
 * 1. Admin Provisioning: Admin accounts are provisioned clean out-of-band (via seeds/direct admin invite tokens)
 *    and cannot register through the public registration route.
 * 2. Backend Validation: Server must re-validate institution domains, session roles, and security bounds.
 * 3. Hashing: Password must be hashed via bcrypt on server side; never log or exchange passwords in APIs.
 * 4. Token handling: Use short-lived JWT access tokens in memory and httpOnly-cookie refresh tokens for sessions.
 * 5. Rate limiting: Rate limit endpoint (e.g. 5 attempts per 15 minutes per IP address) to avoid brute-forcing.
 */

export default function Login({ navigate, onLoginSuccess, theme, toggleTheme }) {
    // Form inputs state
    const [formData, setFormData] = useState({
        email: '',
        password: ''
    });

    // Touch/Validation status tracker
    const [touched, setTouched] = useState({
        email: false,
        password: false
    });

    const [errors, setErrors] = useState({
        email: '',
        password: ''
    });

    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [authMessage, setAuthMessage] = useState(null); // { type: 'pending' | 'error', text: string }

    // Handlers
    const handleBlur = (field) => {
        setTouched(prev => ({ ...prev, [field]: true }));
        validateField(field, formData[field]);
    };

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
        if (touched[name]) {
            validateField(name, value);
        }
    };

    const validateField = (name, value) => {
        let errorMsg = '';
        if (name === 'email') {
            if (!value) {
                errorMsg = 'Email is required';
            } else if (!/\S+@\S+\.\S+/.test(value)) {
                errorMsg = 'Please enter a valid email address';
            } else if (!value.endsWith('@gnu.ac.in')) {
                errorMsg = 'Please use your official college email address (@gnu.ac.in)';
            }
        } else if (name === 'password') {
            if (!value) {
                errorMsg = 'Password is required';
            } else if (value.length < 8) {
                errorMsg = 'Password must be at least 8 characters';
            }
        }

        setErrors(prev => ({ ...prev, [name]: errorMsg }));
        return errorMsg;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        // Touch all fields and validate
        const emailErr = validateField('email', formData.email);
        const passErr = validateField('password', formData.password);
        setTouched({ email: true, password: true });

        if (emailErr || passErr) return;

        setIsLoading(true);
        setAuthMessage(null);

        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: formData.email,
                    password: formData.password
                })
            });
            const data = await res.json();
            setIsLoading(false);

            if (res.ok) {
                // Store user details in local storage
                localStorage.setItem('currentUser', JSON.stringify({
                    name: data.user.name,
                    email: data.user.email,
                    role: data.user.role,
                    department: data.user.department,
                    semester: data.user.semester,
                    lastLogin: data.user.lastLogin, // prior login time
                    token: data.token
                }));

                // Sync React-level auth state, then navigate
                if (onLoginSuccess) onLoginSuccess();
                navigate(`/dashboard/${data.user.role}`);
            } else {
                if (res.status === 403) {
                    setAuthMessage({
                        type: 'pending',
                        text: data.message
                    });
                } else {
                    setAuthMessage({
                        type: 'error',
                        text: data.message || 'Login credentials invalid'
                    });
                }
            }
        } catch (err) {
            setIsLoading(false);

            // Fail-safe offline/local authentication fallback for student & admin demo profiles
            if (formData.email === 'demo.student@gnu.ac.in' || formData.email === 'student@gnu.ac.in') {
                const isDemoUser = formData.email.includes('demo.student');
                const fallbackUser = {
                    name: isDemoUser ? 'Demo Student' : 'Student User',
                    email: formData.email,
                    role: 'student',
                    department: 'Information Technology',
                    semester: '4',
                    lastLogin: new Date().toISOString(),
                    token: 'demo-student-token-2026'
                };
                localStorage.setItem('currentUser', JSON.stringify(fallbackUser));
                if (onLoginSuccess) onLoginSuccess();
                navigate('/dashboard/student');
                return;
            } else if (formData.email === 'admin@gnu.ac.in') {
                const fallbackAdmin = {
                    name: 'Admin User',
                    email: 'admin@gnu.ac.in',
                    role: 'admin',
                    department: 'Administration',
                    lastLogin: new Date().toISOString(),
                    token: 'demo-admin-token-2026'
                };
                localStorage.setItem('currentUser', JSON.stringify(fallbackAdmin));
                if (onLoginSuccess) onLoginSuccess();
                navigate('/dashboard/admin');
                return;
            }

            setAuthMessage({
                type: 'error',
                text: 'Cannot complete server authentication request. Please ensure the backend server is running.'
            });
        }
    };

    const isFormValid = formData.email && formData.password && !errors.email && !errors.password;

    // Presentation only: Campy reacts to the form state above.
    const [focusField, setFocusField] = useState(null);
    const fieldError = (touched.email && errors.email) || (touched.password && errors.password) || '';
    const campy = useCampyState({
        loading: isLoading,
        error: authMessage?.text || fieldError,
        focus: focusField,
        secretFields: ['password'],
        revealed: showPassword && (focusField === 'password' || Boolean(formData.password)),
        ready: Boolean(isFormValid),
        gazeText: formData.email,
        lines: {
            idle: 'Hi, I am Campy. Log in and I will take it from here.',
            watching: 'Use your @gnu.ac.in email.',
            confused: authMessage?.type === 'pending' ? 'Your account is waiting for approval.' : 'That did not work. See the message on the form.',
        },
    });

    return (
        <AuthShell
            campy={campy}
            theme={theme}
            toggleTheme={toggleTheme}
            headline="Welcome back."
            subline="Log in to pick up right where you left off with your campus assistant."
        >
            <AuthHeading title="Log in to your account">
                Enter credentials or select a quick demo login below.
            </AuthHeading>

            {authMessage && authMessage.type === 'pending' && (
                <AuthAlert tone="warning" title="Teacher Verification Status:">{authMessage.text}</AuthAlert>
            )}

            {authMessage && authMessage.type === 'error' && (
                <AuthAlert tone="danger" title="Login Error:">{authMessage.text}</AuthAlert>
            )}

            <div className="auth-panel">
                <p className="auth-panel-title"><Zap size={13} className="text-accent" /> Quick demo logins</p>
                <div className="auth-chip-row">
                    <button
                        type="button"
                        onClick={() => {
                            setFormData({ email: 'demo.student@gnu.ac.in', password: 'DemoUser@2026' });
                            setErrors({ email: '', password: '' });
                            setTouched({ email: true, password: true });
                        }}
                        className="auth-chip"
                    >
                        Student (Deven)
                    </button>
                    <button
                        type="button"
                        onClick={() => {
                            setFormData({ email: 'student@gnu.ac.in', password: 'DemoStudent@2026' });
                            setErrors({ email: '', password: '' });
                            setTouched({ email: true, password: true });
                        }}
                        className="auth-chip"
                    >
                        Student (Demo)
                    </button>
                    <button
                        type="button"
                        onClick={() => {
                            setFormData({ email: 'admin@gnu.ac.in', password: 'DemoAdmin@2026' });
                            setErrors({ email: '', password: '' });
                            setTouched({ email: true, password: true });
                        }}
                        className="auth-chip"
                    >
                        Admin (Demo)
                    </button>
                </div>
            </div>

            <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
                <AuthField
                    id="email"
                    name="email"
                    type="email"
                    label="Institution Email"
                    required
                    value={formData.email}
                    onChange={handleChange}
                    onFocus={() => setFocusField('email')}
                    onBlur={() => { handleBlur('email'); setFocusField(null); }}
                    error={touched.email ? errors.email : ''}
                    placeholder="name@gnu.ac.in"
                />

                <AuthPasswordField
                    id="password"
                    name="password"
                    label="Password"
                    required
                    value={formData.password}
                    onChange={handleChange}
                    onFocus={() => setFocusField('password')}
                    onBlur={() => { handleBlur('password'); setFocusField(null); }}
                    error={touched.password ? errors.password : ''}
                    revealed={showPassword}
                    onToggle={() => setShowPassword(!showPassword)}
                    placeholder="••••••••"
                    aside={(
                        <button type="button" onClick={() => navigate('#forgot-password')} className="auth-text-btn">
                            Forgot password?
                        </button>
                    )}
                />

                <AuthSubmit loading={isLoading} disabled={!isFormValid || isLoading}>Log in</AuthSubmit>
            </form>

            <div className="auth-divider">or</div>

            <p className="m-0 text-center text-sm text-text-secondary">
                Don't have an account?{' '}
                <button onClick={() => navigate('/register')} className="auth-text-btn" data-strong="true">
                    Register
                </button>
            </p>
        </AuthShell>
    );
}
