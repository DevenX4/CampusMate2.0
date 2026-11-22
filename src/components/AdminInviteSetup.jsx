import { useEffect, useState } from 'react';
import { ArrowLeft, ShieldCheck } from 'lucide-react';
import AuthShell, { AuthAlert, AuthField, AuthHeading, AuthPasswordField, AuthSubmit } from './auth/AuthShell';
import CampyLoader from './auth/CampyLoader';
import { useCampyState } from './auth/useCampyState';

export default function AdminInviteSetup({ navigate, theme, toggleTheme }) {
    // Capture token from URL path
    const [token, setToken] = useState('');
    const [email, setEmail] = useState('');
    const [qrCode, setQrCode] = useState('');

    // Form inputs
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [otpCode, setOtpCode] = useState('');

    // UX states
    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(true); // default true for verification on mount
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [errorMessage, setErrorMessage] = useState('');
    const [setupSuccess, setSetupSuccess] = useState(false);

    useEffect(() => {
        // Simple extraction of token from path: /portal/invite/TOKEN
        const pathParts = window.location.pathname.split('/');
        const inviteToken = pathParts[pathParts.length - 1];
        setToken(inviteToken);

        if (!inviteToken) {
            setErrorMessage('Invalid invitation path URL format.');
            setIsLoading(false);
            return;
        }

        const verifyInviteLink = async () => {
            try {
                const res = await fetch(`/api/admin/invite/verify/${inviteToken}`, {
                    method: 'GET',
                    headers: { 'Content-Type': 'application/json' }
                });

                const data = await res.json();
                setIsLoading(false);

                if (res.ok) {
                    setEmail(data.email);
                    setQrCode(data.qrCode);
                } else {
                    setErrorMessage(data.message || 'Invitation link is invalid or has expired.');
                }
            } catch (err) {
                setIsLoading(false);
                setErrorMessage('Network connection failure validating invitation. Please retry.');
            }
        };

        verifyInviteLink();
    }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!password || !confirmPassword || !otpCode) return;

        if (password.length < 8) {
            setErrorMessage('Password must be at least 8 characters long.');
            return;
        }

        if (password !== confirmPassword) {
            setErrorMessage('Passwords do not match.');
            return;
        }

        setIsSubmitting(true);
        setErrorMessage('');

        try {
            const res = await fetch('/api/admin/invite/setup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    token,
                    password,
                    otpCode
                })
            });

            const data = await res.json();
            setIsSubmitting(false);

            if (res.ok) {
                setSetupSuccess(true);
            } else {
                setErrorMessage(data.message || 'Failed security setup.');
            }
        } catch (err) {
            setIsSubmitting(false);
            setErrorMessage('Network connection failure processing administrator setup. Please retry.');
        }
    };

    // Presentation only: Campy reacts to the form state above.
    const [focusField, setFocusField] = useState(null);
    const campy = useCampyState({
        loading: isSubmitting,
        success: setupSuccess,
        error: errorMessage,
        focus: focusField,
        secretFields: ['password', 'confirmPassword'],
        revealed: showPassword && (focusField === 'password' || Boolean(password)) && focusField !== 'confirmPassword',
        ready: Boolean(password && confirmPassword && otpCode.length === 6),
        gazeText: otpCode,
        lines: {
            idle: 'You have been invited. Let us secure your account.',
            watching: 'Six digits from your authenticator.',
            happy: setupSuccess ? 'You are all set.' : 'Looks good. Ready when you are.',
        },
    });

    if (isLoading) {
        return <CampyLoader label="Validating your invitation" />;
    }

    return (
        <AuthShell
            campy={campy}
            theme={theme}
            toggleTheme={toggleTheme}
            headline="Set up admin access."
            subline="Choose a password and link your authenticator to finish."
        >
            {setupSuccess ? (
                <>
                    <AuthHeading title="Setup Succeeded!">
                        Your administrator credentials and 2FA configuration are verified and saved.
                    </AuthHeading>
                    <button onClick={() => navigate('/portal/login')} className="auth-btn auth-btn-primary">
                        Log in to Admin Dashboard
                    </button>
                </>
            ) : (
                <>
                    <AuthHeading title="Configure Admin Setup">
                        {email ? <>Setting up access for <b className="font-medium text-text-primary">{email}</b></> : 'Admin invitation'}
                    </AuthHeading>

                    {errorMessage ? (
                        <AuthAlert tone="danger" icon={ShieldCheck}>{errorMessage}</AuthAlert>
                    ) : (
                        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
                            <AuthPasswordField
                                id="newPassword"
                                label="Admin Password"
                                required
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                onFocus={() => setFocusField('password')}
                                onBlur={() => setFocusField(null)}
                                revealed={showPassword}
                                onToggle={() => setShowPassword(!showPassword)}
                                placeholder="Min. 8 characters"
                            />

                            <AuthField
                                id="confirmPassword"
                                type="password"
                                label="Confirm Password"
                                required
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                onFocus={() => setFocusField('confirmPassword')}
                                onBlur={() => setFocusField(null)}
                                placeholder="Retype password"
                            />

                            {qrCode && (
                                <div className="auth-qr">
                                    <p className="m-0">2FA is required. Link this QR code containing your TOTP token:</p>
                                    <div className="auth-qr-img">
                                        <img src={qrCode} alt="TOTP Invitation QR Code" className="w-28 h-28" />
                                    </div>
                                </div>
                            )}

                            <AuthField id="otpSetupCode" label="Verify 2FA TOTP Code">
                                <input
                                    id="otpSetupCode"
                                    type="text"
                                    maxLength="6"
                                    required
                                    value={otpCode}
                                    onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                                    onFocus={() => setFocusField('otp')}
                                    onBlur={() => setFocusField(null)}
                                    placeholder="000000"
                                    className="auth-input auth-input-otp"
                                />
                            </AuthField>

                            <AuthSubmit loading={isSubmitting} disabled={!password || !confirmPassword || otpCode.length !== 6 || isSubmitting}>
                                Secure Administrator Account
                            </AuthSubmit>
                        </form>
                    )}
                </>
            )}

            <button type="button" className="auth-text-btn inline-flex items-center justify-center gap-1.5" onClick={() => navigate('/')}>
                <ArrowLeft size={14} /> Return to Campus Dashboard
            </button>
        </AuthShell>
    );
}
