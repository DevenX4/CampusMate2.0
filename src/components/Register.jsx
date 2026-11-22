import { useState, useEffect } from 'react';
import { ShieldCheck, Mail } from 'lucide-react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import AuthShell, { AuthAlert, AuthField, AuthHeading, AuthPasswordField, AuthSelect, AuthSubmit } from './auth/AuthShell';
import { useCampyState } from './auth/useCampyState';

/**
 * Modern technical comments for Register implementation:
 * 1. Role validation: Admin accounts are rejected from this register flow (out-of-band only).
 * 2. Password safety: Minimum length and strength bar. Client-side checks only serve as user feedback;
 *    passwords must be salted and hashed with bcrypt on the server before database inserts.
 * 3. Token-based security: Sessions established post-register and post-login require cookie-based token validation.
 * 4. Verification state: Non-verified student records are locked in active session checks until OTP matches.
 */

export default function Register({ navigate, theme, toggleTheme }) {
    // Selected role: 'student' | 'teacher'
    const [role, setRole] = useState('student');

    // Registration UI screens: 'form' | 'verify_student' | 'verify_teacher'
    const [screen, setScreen] = useState('form');

    // Main Forms State
    const [formData, setFormData] = useState({
        name: '',
        email: '',
        password: '',
        confirmPassword: '',
        enrollmentNumber: '',
        employeeId: '',
        department: '',
        semester: '',
        phone: '',
        agreeToTerms: false
    });

    // Touch status tracker for validation timing
    const [touched, setTouched] = useState({});

    // Dynamic error store
    const [errors, setErrors] = useState({});

    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);

    // OTP verification code screen states for Student
    const [otpCode, setOtpCode] = useState('');
    const [resendTimer, setResendTimer] = useState(30);
    const [isResendDisabled, setIsResendDisabled] = useState(true);

    // Timer countdown loop
    useEffect(() => {
        let interval;
        if (screen === 'verify_student' && resendTimer > 0) {
            interval = setInterval(() => {
                setResendTimer((prev) => prev - 1);
            }, 1000);
        } else if (resendTimer === 0) {
            setIsResendDisabled(false);
        }
        return () => clearInterval(interval);
    }, [screen, resendTimer]);

    const [submitError, setSubmitError] = useState(null);

    const handleResendOtp = async () => {
        setIsResendDisabled(true);
        setResendTimer(30);
        setSubmitError(null);
        try {
            const res = await fetch('/api/auth/resend-otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: formData.email })
            });
            const data = await res.json();
            if (!res.ok) {
                setSubmitError(data.message || 'Failed to resend OTP');
            }
        } catch (err) {
            setSubmitError('Network error while resending OTP');
        }
    };

    const handleOtpChange = (e) => {
        setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6));
    };

    const handleOtpSubmit = async (e) => {
        e.preventDefault();
        if (otpCode.length === 6) {
            setIsLoading(true);
            setSubmitError(null);
            try {
                const res = await fetch('/api/auth/verify-otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email: formData.email, otpCode })
                });
                const data = await res.json();
                setIsLoading(false);
                if (res.ok) {
                    // Store student user session info locally
                    localStorage.setItem('currentUser', JSON.stringify({
                        name: data.user.name,
                        email: data.user.email,
                        role: data.user.role,
                        department: data.user.department,
                        semester: data.user.semester,
                        lastLogin: data.user.lastLogin // first login is verification time, will be null/undefined
                    }));
                    navigate('/dashboard/student');
                } else {
                    setSubmitError(data.message || 'OTP verification failed');
                }
            } catch (err) {
                setIsLoading(false);
                setSubmitError('Network failure during verification');
            }
        }
    };

    // Client side validation
    const validateField = (name, value) => {
        let err = '';
        if (name === 'name' && !value) {
            err = 'Full name is required';
        } else if (name === 'email') {
            if (!value) {
                err = 'Email is required';
            } else if (!/\S+@\S+\.\S+/.test(value)) {
                err = 'Invalid email structure';
            } else if (!value.endsWith('@gnu.ac.in')) {
                err = 'Email must use college domain (@gnu.ac.in)';
            }
        } else if (name === 'password') {
            if (!value) {
                err = 'Password is required';
            } else if (value.length < 8) {
                err = 'Password must meet length requirement (8+ characters)';
            }
        } else if (name === 'confirmPassword') {
            if (!value) {
                err = 'Please confirm your password';
            } else if (value !== formData.password) {
                err = 'Passwords do not match';
            }
        } else if (name === 'enrollmentNumber' && role === 'student' && !value) {
            err = 'Enrollment / Roll number is required';
        } else if (name === 'employeeId' && role === 'teacher' && !value) {
            err = 'Employee ID is required';
        } else if (name === 'department' && !value) {
            err = 'Please select a department';
        } else if (name === 'semester' && role === 'student' && !value) {
            err = 'Please select your semester/year';
        }

        setErrors(prev => ({ ...prev, [name]: err }));
        return err;
    };

    const handleBlur = (field) => {
        setTouched(prev => ({ ...prev, [field]: true }));
        validateField(field, formData[field]);
    };

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        const targetVal = type === 'checkbox' ? checked : value;
        setFormData(prev => {
            const next = { ...prev, [name]: targetVal };
            // Auto re-validate confirmation code as password changes
            if (name === 'password' && touched.confirmPassword) {
                setTimeout(() => validateField('confirmPassword', next.confirmPassword), 0);
            }
            return next;
        });

        if (touched[name] || name === 'agreeToTerms') {
            validateField(name, targetVal);
        }
    };

    // Password strength check helper
    const getPasswordStrength = (pass) => {
        if (!pass) return { score: 0, text: 'Blank', color: 'bg-border-default' };
        if (pass.length < 8) return { score: 1, text: 'Too short', color: 'bg-status-danger' };

        let criteria = 0;
        if (/[A-Z]/.test(pass)) criteria++;
        if (/[0-9]/.test(pass)) criteria++;
        if (/[^A-Za-z0-9]/.test(pass)) criteria++;

        if (criteria === 0) return { score: 1, text: 'Weak', color: 'bg-status-danger' };
        if (criteria === 1) return { score: 2, text: 'Medium', color: 'bg-status-warning' };
        return { score: 3, text: 'Strong', color: 'bg-status-success' };
    };

    const passStrength = getPasswordStrength(formData.password);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitError(null);

        // Validate all required fields
        const localErrors = {};
        const fieldsToCheck = [
            'name', 'email', 'password', 'confirmPassword', 'department',
            role === 'student' ? 'enrollmentNumber' : 'employeeId',
            role === 'student' && 'semester'
        ].filter(Boolean);

        let hasError = false;
        fieldsToCheck.forEach(f => {
            const err = validateField(f, formData[f]);
            if (err) hasError = true;
        });

        setTouched(fieldsToCheck.reduce((acc, f) => ({ ...acc, [f]: true }), {}));

        if (hasError || !formData.agreeToTerms) return;

        setIsLoading(true);
        try {
            const res = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: formData.name,
                    email: formData.email,
                    password: formData.password,
                    role,
                    department: formData.department,
                    phone: formData.phone,
                    enrollmentNumber: role === 'student' ? formData.enrollmentNumber : undefined,
                    semester: role === 'student' ? formData.semester : undefined,
                    employeeId: role === 'teacher' ? formData.employeeId : undefined
                })
            });
            const data = await res.json();
            setIsLoading(false);
            if (res.ok) {
                if (role === 'student') {
                    setScreen('verify_student');
                } else {
                    setScreen('verify_teacher');
                }
            } else {
                setSubmitError(data.message || 'Registration failed');
            }
        } catch (err) {
            setIsLoading(false);
            setSubmitError('Failed to connect to authentication server');
        }
    };

    // Check required completeness to unlock styling
    const isFormValid =
        formData.name &&
        formData.email &&
        formData.password &&
        formData.confirmPassword &&
        formData.department &&
        formData.agreeToTerms &&
        (role === 'student' ? formData.enrollmentNumber && formData.semester : formData.employeeId) &&
        Object.values(errors).every(err => !err);

    // List of departments used on Campus
    const departments = [
        { value: 'CSE', label: 'Computer Science & Engineering' },
        { value: 'IT', label: 'Information Technology' },
        { value: 'AI', label: 'Artificial Intelligence & ML' },
        { value: 'ECE', label: 'Electronics & Communication' },
        { value: 'EE', label: 'Electrical Engineering' }
    ];

    // Presentation only: Campy reacts to the form state above.
    const reduceMotion = useReducedMotion();
    const [focusField, setFocusField] = useState(null);
    const firstFieldError = Object.keys(errors).find((key) => touched[key] && errors[key]);
    const passwordFocused = focusField === 'password' || focusField === 'confirmPassword';
    const campy = useCampyState({
        loading: isLoading,
        success: screen === 'verify_teacher',
        error: submitError || (firstFieldError ? errors[firstFieldError] : ''),
        focus: focusField,
        secretFields: ['password', 'confirmPassword'],
        revealed: (focusField === 'password' && showPassword) || (focusField === 'confirmPassword' && showConfirmPassword)
            || (!passwordFocused && ((showPassword && Boolean(formData.password)) || (showConfirmPassword && Boolean(formData.confirmPassword)))),
        ready: Boolean(isFormValid),
        gazeText: focusField && !passwordFocused && typeof formData[focusField] === 'string' ? formData[focusField] : otpCode,
        lines: {
            idle: screen === 'verify_student' ? 'Your code is on its way.' : 'Hi, I am Campy. Let us set up your account.',
            watching: focusField === 'email' ? 'Use your @gnu.ac.in email.' : 'Reading along.',
            happy: screen === 'verify_teacher' ? 'Application received.' : 'Looks good. Ready when you are.',
        },
    });

    const fieldFocus = (name) => ({
        onFocus: () => setFocusField(name),
        onBlur: () => { handleBlur(name); setFocusField(null); },
    });
    const fieldError = (name) => (touched[name] ? errors[name] : '');
    const screenMotion = reduceMotion
        ? { initial: false, animate: { opacity: 1 }, exit: { opacity: 1 }, transition: { duration: 0 } }
        : { initial: { opacity: 0, y: 12 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -8 }, transition: { duration: 0.2 } };
    const roleFieldMotion = reduceMotion
        ? { initial: false, animate: { opacity: 1 }, exit: { opacity: 1 }, transition: { duration: 0 } }
        : { initial: { opacity: 0, y: 6 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0 }, transition: { duration: 0.14 } };

    return (
        <AuthShell
            campy={campy}
            theme={theme}
            toggleTheme={toggleTheme}
            wide
            headline="Join your campus AI assistant."
            subline="Create an account to get answers about courses, schedules and campus services."
        >
            <AnimatePresence mode="wait">
                {screen === 'form' && (
                    <motion.div key="form-view" {...screenMotion} className="flex flex-col gap-5">
                        <AuthHeading title="Create your account">
                            Join CampusMate with your institution details.
                        </AuthHeading>

                        <div className="auth-switch" role="group" aria-label="Account type">
                            <motion.span
                                className="auth-switch-thumb"
                                initial={false}
                                animate={{ x: role === 'student' ? 0 : 104 }}
                                transition={reduceMotion ? { duration: 0 } : { type: 'spring', stiffness: 380, damping: 30 }}
                            />
                            <button type="button" aria-pressed={role === 'student'} onClick={() => setRole('student')}>Student</button>
                            <button type="button" aria-pressed={role === 'teacher'} onClick={() => setRole('teacher')}>Teacher</button>
                        </div>

                        {submitError && <AuthAlert tone="danger" title="Error:">{submitError}</AuthAlert>}

                        <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
                            <AuthField
                                id="name" name="name" type="text" label="Full Name" required
                                value={formData.name} onChange={handleChange} {...fieldFocus('name')}
                                error={fieldError('name')} placeholder="Your full name"
                            />

                            <AuthField
                                id="email" name="email" type="email" label="Institution Email" required
                                value={formData.email} onChange={handleChange} {...fieldFocus('email')}
                                error={fieldError('email')} placeholder="name@gnu.ac.in"
                                hint="Use your official college email address"
                            />

                            <div className="auth-grid-2">
                                <div className="flex flex-col gap-2">
                                    <AuthPasswordField
                                        id="password" name="password" label="Password" required
                                        value={formData.password} onChange={handleChange} {...fieldFocus('password')}
                                        error={fieldError('password')} revealed={showPassword}
                                        onToggle={() => setShowPassword(!showPassword)} placeholder="••••••••"
                                    />
                                    {formData.password && (
                                        <div className="auth-strength">
                                            <div className="auth-strength-row">
                                                <span>Strength</span>
                                                <b>{passStrength.text}</b>
                                            </div>
                                            <div className="auth-strength-bar" aria-hidden="true">
                                                {[1, 2, 3].map((step) => (
                                                    <i key={step} className={step <= passStrength.score ? passStrength.color : ''} />
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <AuthPasswordField
                                    id="confirmPassword" name="confirmPassword" label="Confirm Password" required
                                    value={formData.confirmPassword} onChange={handleChange} {...fieldFocus('confirmPassword')}
                                    error={fieldError('confirmPassword')} revealed={showConfirmPassword}
                                    onToggle={() => setShowConfirmPassword(!showConfirmPassword)} placeholder="••••••••"
                                />
                            </div>

                            <div className="border-t border-border-default pt-4">
                                <AnimatePresence mode="wait" initial={false}>
                                    {role === 'student' ? (
                                        <motion.div key="student-fields" {...roleFieldMotion} className="flex flex-col gap-4">
                                            <div className="auth-grid-2">
                                                <AuthField
                                                    id="enrollmentNumber" name="enrollmentNumber" type="text" label="Enrollment / Roll Number" required
                                                    value={formData.enrollmentNumber} onChange={handleChange} {...fieldFocus('enrollmentNumber')}
                                                    error={fieldError('enrollmentNumber')} placeholder="e.g. CM-2026-902"
                                                />
                                                <AuthSelect
                                                    id="department" name="department" label="Department" required
                                                    value={formData.department} onChange={handleChange} {...fieldFocus('department')}
                                                    error={fieldError('department')}
                                                >
                                                    <option value="">Select Dept</option>
                                                    {departments.map(d => (
                                                        <option key={d.value} value={d.value}>{d.label}</option>
                                                    ))}
                                                </AuthSelect>
                                            </div>

                                            <div className="auth-grid-2">
                                                <AuthSelect
                                                    id="semester" name="semester" label="Semester / Year" required
                                                    value={formData.semester} onChange={handleChange} {...fieldFocus('semester')}
                                                    error={fieldError('semester')}
                                                >
                                                    <option value="">Select Item</option>
                                                    <option value="1">1st Sem (Year 1)</option>
                                                    <option value="2">2nd Sem (Year 1)</option>
                                                    <option value="3">3rd Sem (Year 2)</option>
                                                    <option value="4">4th Sem (Year 2)</option>
                                                    <option value="5">5th Sem (Year 3)</option>
                                                    <option value="6">6th Sem (Year 3)</option>
                                                    <option value="7">7th Sem (Year 4)</option>
                                                    <option value="8">8th Sem (Year 4)</option>
                                                </AuthSelect>
                                                <AuthField
                                                    id="phone" name="phone" type="tel" label="Phone Number" labelNote="(Optional)"
                                                    value={formData.phone} onChange={handleChange}
                                                    onFocus={() => setFocusField('phone')} onBlur={() => setFocusField(null)}
                                                    placeholder="+91 99999 99999"
                                                />
                                            </div>
                                        </motion.div>
                                    ) : (
                                        <motion.div key="teacher-fields" {...roleFieldMotion} className="flex flex-col gap-4">
                                            <div className="auth-grid-2">
                                                <AuthField
                                                    id="employeeId" name="employeeId" type="text" label="Employee ID" required
                                                    value={formData.employeeId} onChange={handleChange} {...fieldFocus('employeeId')}
                                                    error={fieldError('employeeId')} placeholder="e.g. CM-TEACH-902"
                                                />
                                                <AuthSelect
                                                    id="department-teacher" name="department" label="Department" required
                                                    value={formData.department} onChange={handleChange} {...fieldFocus('department')}
                                                    error={fieldError('department')}
                                                >
                                                    <option value="">Select Dept</option>
                                                    {departments.map(d => (
                                                        <option key={d.value} value={d.value}>{d.label}</option>
                                                    ))}
                                                </AuthSelect>
                                            </div>
                                            <AuthField
                                                id="phone-teacher" name="phone" type="tel" label="Phone Number" labelNote="(Optional)"
                                                value={formData.phone} onChange={handleChange}
                                                onFocus={() => setFocusField('phone')} onBlur={() => setFocusField(null)}
                                                placeholder="+91 99999 99999"
                                            />
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>

                            <div className="auth-check">
                                <input
                                    id="agreeToTerms" name="agreeToTerms" type="checkbox" required
                                    checked={formData.agreeToTerms} onChange={handleChange}
                                />
                                <label htmlFor="agreeToTerms">
                                    I agree to the <button type="button" className="auth-text-btn" data-strong="true">Terms of Service</button> and <button type="button" className="auth-text-btn" data-strong="true">Privacy Policy</button>
                                </label>
                            </div>

                            <AuthSubmit loading={isLoading} disabled={!isFormValid || isLoading}>
                                {role === 'student' ? 'Create student account' : 'Create teacher account'}
                            </AuthSubmit>
                        </form>

                        <div className="auth-divider">or</div>

                        <p className="m-0 text-center text-sm text-text-secondary">
                            Already have an account?{' '}
                            <button onClick={() => navigate('/login')} className="auth-text-btn" data-strong="true">Log in</button>
                        </p>
                    </motion.div>
                )}

                {screen === 'verify_student' && (
                    <motion.div key="verify-student" {...screenMotion} className="flex flex-col gap-5">
                        <span className="grid h-11 w-11 place-items-center rounded-lg border border-accent/25 bg-accent-muted text-accent"><Mail size={20} /></span>
                        <AuthHeading title="Verify your email">
                            A verification code has been sent to <b className="font-medium text-text-primary">{formData.email}</b>. Enter the 6-digit code below.
                        </AuthHeading>

                        {submitError && <AuthAlert tone="danger" title="Error:">{submitError}</AuthAlert>}

                        <form onSubmit={handleOtpSubmit} className="flex flex-col gap-4">
                            <AuthField id="registerOtp" label="Verification code">
                                <input
                                    id="registerOtp"
                                    type="text"
                                    pattern="\d*"
                                    required
                                    value={otpCode}
                                    onChange={handleOtpChange}
                                    onFocus={() => setFocusField('otp')}
                                    onBlur={() => setFocusField(null)}
                                    className="auth-input auth-input-otp"
                                    placeholder="000000"
                                />
                            </AuthField>
                            <AuthSubmit loading={isLoading} disabled={otpCode.length !== 6 || isLoading}>Verify & Sign in</AuthSubmit>
                        </form>

                        <div className="flex flex-col items-center gap-3 border-t border-border-default pt-4">
                            <div className="flex items-center gap-2">
                                <button
                                    type="button"
                                    disabled={isResendDisabled}
                                    onClick={handleResendOtp}
                                    className="auth-text-btn"
                                    data-strong="true"
                                >
                                    Resend email
                                </button>
                                {isResendDisabled && <span className="text-xs text-text-muted">(in {resendTimer}s)</span>}
                            </div>
                            <button type="button" onClick={() => setScreen('form')} className="auth-text-btn">Back to registration</button>
                        </div>
                    </motion.div>
                )}

                {screen === 'verify_teacher' && (
                    <motion.div key="verify-teacher" {...screenMotion} className="flex flex-col gap-5">
                        <span className="grid h-11 w-11 place-items-center rounded-lg border border-status-warning/30 bg-status-warning/10 text-status-warning"><ShieldCheck size={20} /></span>
                        <AuthHeading title="Registration received">
                            Your teacher application is pending administrator review. No OTP is required for teacher accounts.
                        </AuthHeading>
                        <AuthAlert tone="warning">
                            You'll receive an email notification at <strong className="inline">{formData.email}</strong> once an admin verifies your employee record.
                        </AuthAlert>
                        <button type="button" onClick={() => navigate('/login')} className="auth-btn auth-btn-secondary">Return to login</button>
                    </motion.div>
                )}
            </AnimatePresence>
        </AuthShell>
    );
}
