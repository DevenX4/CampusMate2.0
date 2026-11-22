/**
 * Generates OTP Verification Email templates (both HTML and Plain Text).
 *
 * @param {string} firstName - Target receiver's display or first name.
 * @param {string} otpCode - Six digit numeric secure code.
 * @param {number} [expiryMinutes=15] - Expire period in minutes.
 * @param {number} [currentYear] - Footer copyright year parameter.
 * @returns {{ html: string, text: string }}
 */
export const getOTPEmailTemplate = (firstName, otpCode, expiryMinutes = 15, currentYear = new Date().getFullYear()) => {
    // Extract individual digits for the box alignment
    const digits = otpCode.toString().split('');
    const otpDigits = digits.concat(['', '', '', '', '', '']).slice(0, 6); // safeguard exactly 6 digits

    const htmlContent = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CampusMateAI OTP Verification</title>
</head>
<body style="margin: 0; padding: 0; background-color: #F4F4F6; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, Helvetica, sans-serif; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #F4F4F6; padding: 40px 10px;">
        <tr>
            <td align="center">
                <!-- Main Container Card -->
                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 480px; background-color: #FFFFFF; border-collapse: separate; border: 1px solid #E5E7EB; border-top: 4px solid #6366F1; border-radius: 16px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); overflow: hidden;">
                    
                    <!-- Header Area -->
                    <tr>
                        <td align="center" style="padding: 32px 24px 20px 24px;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td align="center">
                                        <!-- Logo Symbol representation using table styled shapes -->
                                        <table role="presentation" border="0" cellpadding="0" cellspacing="0" style="display: inline-block; vertical-align: middle; margin-right: 8px;">
                                            <tr>
                                                <td style="background-color: #6366F1; width: 8px; height: 8px; border-radius: 2px;"></td>
                                                <td style="width: 3px;"></td>
                                                <td style="background-color: #4F46E5; width: 8px; height: 8px; border-radius: 2px;"></td>
                                            </tr>
                                            <tr><td style="height: 3px;"></td></tr>
                                            <tr>
                                                <td style="background-color: #4F46E5; width: 8px; height: 8px; border-radius: 2px;"></td>
                                                <td style="width: 3px;"></td>
                                                <td style="background-color: #6366F1; width: 8px; height: 8px; border-radius: 2px;"></td>
                                            </tr>
                                        </table>
                                        <span style="font-size: 24px; font-weight: 800; color: #1F2937; letter-spacing: -0.5px; vertical-align: middle;">CampusMate<span style="color: #6366F1;">AI</span></span>
                                    </td>
                                </tr>
                                <tr>
                                    <td align="center" style="padding-top: 6px;">
                                        <span style="font-size: 12px; color: #6B7280; letter-spacing: 0.5px;">Your Personalized Campus AI Companion</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Divider -->
                    <tr>
                        <td style="padding: 0 24px;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td style="border-top: 1px solid #F3F4F6;"></td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Body Content -->
                    <tr>
                        <td style="padding: 24px 32px 10px 32px; text-align: left;">
                            <p style="margin: 0 0 12px 0; font-size: 16px; font-weight: 600; color: #374151;">Hi ${firstName},</p>
                            <p style="margin: 0; font-size: 15px; line-height: 1.6; color: #4B5563;">Use the code below to verify your email and activate your CampusMateAI account.</p>
                        </td>
                    </tr>

                    <!-- OTP Boxes Section -->
                    <tr>
                        <td align="center" style="padding: 10px 24px 20px 24px;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="4" style="margin: 10px auto;">
                                <tr>
                                    <td align="center" valign="middle" style="width: 46px; height: 54px; background-color: #EEF0FF; border: 1px solid #C7CBFA; border-radius: 10px; font-size: 32px; font-weight: 800; color: #4F46E5; font-family: 'Courier New', Courier, monospace;">${otpDigits[0]}</td>
                                    <td align="center" valign="middle" style="width: 46px; height: 54px; background-color: #EEF0FF; border: 1px solid #C7CBFA; border-radius: 10px; font-size: 32px; font-weight: 800; color: #4F46E5; font-family: 'Courier New', Courier, monospace;">${otpDigits[1]}</td>
                                    <td align="center" valign="middle" style="width: 46px; height: 54px; background-color: #EEF0FF; border: 1px solid #C7CBFA; border-radius: 10px; font-size: 32px; font-weight: 800; color: #4F46E5; font-family: 'Courier New', Courier, monospace;">${otpDigits[2]}</td>
                                    <td align="center" valign="middle" style="width: 46px; height: 54px; background-color: #EEF0FF; border: 1px solid #C7CBFA; border-radius: 10px; font-size: 32px; font-weight: 800; color: #4F46E5; font-family: 'Courier New', Courier, monospace;">${otpDigits[3]}</td>
                                    <td align="center" valign="middle" style="width: 46px; height: 54px; background-color: #EEF0FF; border: 1px solid #C7CBFA; border-radius: 10px; font-size: 32px; font-weight: 800; color: #4F46E5; font-family: 'Courier New', Courier, monospace;">${otpDigits[4]}</td>
                                    <td align="center" valign="middle" style="width: 46px; height: 54px; background-color: #EEF0FF; border: 1px solid #C7CBFA; border-radius: 10px; font-size: 32px; font-weight: 800; color: #4F46E5; font-family: 'Courier New', Courier, monospace;">${otpDigits[5]}</td>
                                </tr>
                            </table>
                            <p style="margin: 8px 0 0 0; font-size: 13px; font-weight: 500; color: #9CA3AF;">This code expires in ${expiryMinutes} minutes</p>
                        </td>
                    </tr>

                    <!-- Security Alert Strip -->
                    <tr>
                        <td style="padding: 0 32px 16px 32px;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #FFF8E6; border: 1px solid #FFEBAA; border-radius: 8px;">
                                <tr>
                                    <td style="padding: 12px 14px; text-align: left; vertical-align: top; width: 20px;">
                                        <span style="font-size: 16px; line-height: 1;">🔒</span>
                                    </td>
                                    <td style="padding: 11px 14px 11px 0; text-align: left; font-size: 12px; line-height: 1.5; color: #8A6D00; font-weight: 500;">
                                        For your security, never share this code with anyone — including anyone claiming to be from CampusMateAI support.
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Secondary Ignorable Action -->
                    <tr>
                        <td align="center" style="padding: 0 24px 28px 24px;">
                            <span style="font-size: 12px; color: #9CA3AF;">Didn't request this? You can safely ignore this email.</span>
                        </td>
                    </tr>

                    <!-- Footer Divider -->
                    <tr>
                        <td style="padding: 0 24px;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td style="border-top: 1px solid #F3F4F6;"></td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Footer closing details -->
                    <tr>
                        <td style="padding: 24px 32px; background-color: #FAFAFA; text-align: left;">
                            <p style="margin: 0; font-size: 13px; color: #6B7280; line-height: 1.5;">
                                Best regards,<br>
                                <strong style="color: #4F46E5;">The CampusMateAI Team</strong>
                            </p>
                            <p style="margin: 16px 0 0 0; font-size: 11px; color: #9CA3AF; line-height: 1.4; border-top: 1px solid #EAEAEA; padding-top: 14px;">
                                &copy; ${currentYear} CampusMateAI. This is an automated email — please do not reply directly.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>`;

    const textContent = `
CampusMateAI - OTP Verification
Your Personalized Campus AI Companion
--------------------------------------------------

Hi ${firstName},

Use the code below to verify your email and activate your CampusMateAI account.

Verification Code: [ ${otpCode} ]

This code expires in ${expiryMinutes} minutes.

--------------------------------------------------
🔒 For your security, never share this code with anyone.
--------------------------------------------------
Didn't request this? You can safely ignore this email.

Best regards,
The CampusMateAI Team
© ${currentYear} CampusMateAI.
`;

    return {
        html: htmlContent,
        text: textContent
    };
};
