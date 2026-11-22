import { useState } from 'react';
import { ArrowLeft, Loader2, Lock, ShieldCheck } from 'lucide-react';
import AuthShell, { AuthAlert, AuthField, AuthHeading, AuthPasswordField, AuthSubmit } from './auth/AuthShell';
import { useCampyState } from './auth/useCampyState';

export default function AdminLogin({ navigate, onLoginSuccess, theme, toggleTheme }) {
    // Form stages: 1 = Email + Password, 2 = 2FA TOTP Code
    const [step, setStep] = useState(1);

    // Auth variables
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [otpCode, setOtpCode] = useState('');
    const [tempToken, setTempToken] = useState('');
    const [qrCode, setQrCode] = useState('');
    const [isSetup2FA, setIsSetup2FA] = useState(false);

    // UX state variables
    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState('');
    const [showLockoutMessage, setShowLockoutMessage] = useState(false);

    const handleGoogleLogin = async () => {
        setIsLoading(true);
        setErrorMessage('');
        try {
            const adminEmail = email || 'admin@gnu.ac.in';
            const res = await fetch('/api/auth/google', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email: adminEmail,
                    name: 'System Administrator',
                    role: 'admin'
                })
            });
            const data = await res.json();
            setIsLoading(false);

            if (res.ok) {
                localStorage.setItem('currentUser', JSON.stringify({
                    name: data.user.name,
                    email: data.user.email,
                    role: data.user.role,
                    department: data.user.department,
                    lastLogin: data.user.lastLogin,
                    currentLogin: data.user.currentLogin,
                    token: data.accessToken || data.token
                }));

                if (onLoginSuccess) onLoginSuccess();
                navigate('/dashboard/admin');
            } else {
                setErrorMessage(data.message || 'Google Auth failed');
            }
        } catch (err) {
            setIsLoading(false);
            setErrorMessage('Network connection failure during Google Auth.');
        }
    };

    const handleStep1Submit = async (e) => {
        e.preventDefault();
        if (!email || !password) return;

        setIsLoading(true);
        setErrorMessage('');
        setShowLockoutMessage(false);

        try {
            const res = await fetch('/api/auth/admin/login-step1', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            const data = await res.json();
            setIsLoading(false);

            if (res.ok) {
                if (data.requiresSetup) {
                    setIsSetup2FA(true);
                    setQrCode(data.qrCode);
                    setTempToken(data.tempToken);
                    setStep(2);
                } else if (data.requires2FA) {
                    setIsSetup2FA(false);
                    setTempToken(data.tempToken);
                    setStep(2);
                }
            } else {
                if (res.status === 423) {
                    setErrorMessage('Too many failed attempts. Try again in 15 minutes or contact another admin.');
                    setShowLockoutMessage(true);
                } else {
                    setErrorMessage('Invalid credentials. (Default Admin: admin@gnu.ac.in / DemoAdmin@2026)');
                }
            }
        } catch (err) {
            setIsLoading(false);
            setErrorMessage('Network connection failure. Please try again.');
        }
    };

    const handleStep2Submit = async (e) => {
        e.preventDefault();
        if (otpCode.length !== 6) return;

        setIsLoading(true);
        setErrorMessage('');

        try {
            const res = await fetch('/api/auth/admin/login-step2', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tempToken, code: otpCode })
            });

            const data = await res.json();
            setIsLoading(false);

            if (res.ok) {
                localStorage.setItem('currentUser', JSON.stringify({
                    name: data.user.name,
                    email: data.user.email,
                    role: data.user.role,
                    department: data.user.department,
                    lastLogin: data.user.lastLogin,
                    currentLogin: data.user.currentLogin,
                    token: data.accessToken || data.token
                }));

                if (onLoginSuccess) onLoginSuccess();
                navigate('/dashboard/admin');
            } else {
                if (res.status === 423) {
                    setErrorMessage('Too many failed attempts. Try again in 15 minutes or contact another admin.');
                    setShowLockoutMessage(true);
                    setStep(1);
                    setOtpCode('');
                } else {
                    setErrorMessage('Invalid 2FA code. Retry or use Google Admin SSO.');
                    setStep(1);
                    setOtpCode('');
                }
            }
        } catch (err) {
            setIsLoading(false);
            setErrorMessage('Network connection failure. Please try again.');
        }
    };

    // Presentation only: Campy reacts to the form state above.
    const [focusField, setFocusField] = useState(null);
    const campy = useCampyState({
        loading: isLoading,
        error: errorMessage,
        focus: focusField,
        secretFields: ['password'],
        revealed: step === 1 && showPassword && (focusField === 'password' || Boolean(password)),
        ready: step === 1 ? Boolean(email && password) : otpCode.length === 6,
        gazeText: focusField === 'otp' ? otpCode : email,
        lines: {
            idle: step === 1 ? 'Admin area. Sign in to continue.' : 'One more step. Enter your 2FA code.',
            watching: focusField === 'otp' ? 'Six digits from your authenticator.' : 'Reading along.',
        },
    });

    return (
        <AuthShell
            campy={campy}
            theme={theme}
            toggleTheme={toggleTheme}
            headline="CampusMate admin."
            subline="Manage users, knowledge files and everything the assistant knows."
        >
            <AuthHeading title="Admin Access Portal">
                {step === 1 ? 'Sign in with your administrator account.' : 'Confirm your identity to continue.'}
            </AuthHeading>

            {errorMessage && (
                <AuthAlert tone="danger" icon={showLockoutMessage ? Lock : ShieldCheck}>{errorMessage}</AuthAlert>
            )}

            {step === 1 ? (
                <>
                    <form onSubmit={handleStep1Submit} className="flex flex-col gap-4" noValidate>
                        <AuthField
                            id="adminEmail"
                            type="email"
                            label="Administrator Email"
                            required
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            onFocus={() => setFocusField('email')}
                            onBlur={() => setFocusField(null)}
                            placeholder="admin@gnu.ac.in"
                        />

                        <AuthPasswordField
                            id="adminPassword"
                            label="Password"
                            required
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            onFocus={() => setFocusField('password')}
                            onBlur={() => setFocusField(null)}
                            revealed={showPassword}
                            onToggle={() => setShowPassword(!showPassword)}
                            placeholder="••••••••"
                        />

                        <AuthSubmit loading={isLoading} disabled={!email || !password || isLoading}>Verify Account</AuthSubmit>

                        <div className="auth-divider">or admin SSO</div>

                        <button
                            type="button"
                            onClick={handleGoogleLogin}
                            disabled={isLoading}
                            className="auth-btn auth-btn-secondary"
                        >
                            {isLoading ? (
                                <Loader2 size={18} className="auth-spin" aria-label="Working" />
                            ) : (
                                <>
                                    <svg viewBox="0 0 24 24" className="w-4 h-4" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                                        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                                        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                                        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                                        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                                    </svg>
                                    <span>Continue with Google (Admin)</span>
                                </>
                            )}
                        </button>
                    </form>

                    <div className="auth-panel">
                        <p className="auth-panel-title">Default Admin Credentials</p>
                        <p className="m-0 text-xs leading-relaxed text-text-secondary">
                            Email: <span className="auth-mono">admin@gnu.ac.in</span><br />
                            Password: <span className="auth-mono">DemoAdmin@2026</span><br />
                            2FA is required on first login. Scan the QR in Google Authenticator or Authy.
                        </p>
                    </div>
                </>
            ) : (
                <form onSubmit={handleStep2Submit} className="flex flex-col gap-4">
                    {isSetup2FA && qrCode && (
                        <div className="auth-qr">
                            <p className="m-0">TOTP 2FA required. Scan this QR code in your Authenticator app (for example Google Authenticator or Authy):</p>
                            <div className="auth-qr-img">
                                <img src={qrCode} alt="TOTP Setting QR Code" className="w-36 h-36" />
                            </div>
                            <span className="text-xs text-text-muted">This QR link is mandatory for initial setup</span>
                        </div>
                    )}

                    <AuthField id="otpCode" label={isSetup2FA ? 'Confirm 6-Digit 2FA Code' : 'Enter 6-Digit 2FA Code'}>
                        <input
                            id="otpCode"
                            type="text"
                            maxLength="6"
                            required
                            value={otpCode}
                            onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                            onFocus={() => setFocusField('otp')}
                            onBlur={() => setFocusField(null)}
                            placeholder="000 000"
                            className="auth-input auth-input-otp"
                        />
                    </AuthField>

                    <div className="grid grid-cols-[1fr_2fr] gap-3">
                        <button
                            type="button"
                            onClick={() => {
                                setStep(1);
                                setOtpCode('');
                                setErrorMessage('');
                            }}
                            className="auth-btn auth-btn-secondary"
                        >
                            Back
                        </button>
                        <AuthSubmit loading={isLoading} disabled={otpCode.length !== 6 || isLoading}>Confirm Access</AuthSubmit>
                    </div>
                </form>
            )}

            <button type="button" className="auth-text-btn inline-flex items-center justify-center gap-1.5" onClick={() => navigate('/')}>
                <ArrowLeft size={14} /> Return to Campus Dashboard
            </button>
        </AuthShell>
    );
}
