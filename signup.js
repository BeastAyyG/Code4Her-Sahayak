/* ===== SIGNUP PAGE SCRIPTS ===== */

document.addEventListener('DOMContentLoaded', () => {

    const form = document.getElementById('signupForm');
    const passwordInput = document.getElementById('password');
    const toggleBtn = document.getElementById('togglePassword');
    const strengthContainer = document.getElementById('passwordStrength');
    const strengthText = document.getElementById('strengthText');
    const strengthBars = document.querySelectorAll('.strength-bar');
    const submitBtn = document.getElementById('submitBtn');

    // ===== TOGGLE PASSWORD VISIBILITY =====
    toggleBtn.addEventListener('click', () => {
        const isPassword = passwordInput.type === 'password';
        passwordInput.type = isPassword ? 'text' : 'password';
        toggleBtn.textContent = isPassword ? '🙈' : '👁️';
    });

    // ===== PASSWORD STRENGTH METER =====
    passwordInput.addEventListener('input', () => {
        const val = passwordInput.value;

        if (val.length === 0) {
            strengthContainer.classList.remove('visible');
            return;
        }

        strengthContainer.classList.add('visible');

        let score = 0;
        if (val.length >= 8) score++;
        if (/[A-Z]/.test(val)) score++;
        if (/[0-9]/.test(val)) score++;
        if (/[^A-Za-z0-9]/.test(val)) score++;

        // Reset bars
        strengthBars.forEach(bar => {
            bar.className = 'strength-bar';
        });

        let level = '';
        let colorClass = '';

        if (score <= 1) {
            level = 'Weak';
            colorClass = 'weak';
        } else if (score <= 2) {
            level = 'Fair';
            colorClass = 'medium';
        } else if (score <= 3) {
            level = 'Good';
            colorClass = 'strong';
        } else {
            level = 'Strong';
            colorClass = 'strong';
        }

        for (let i = 0; i < score; i++) {
            strengthBars[i].classList.add(colorClass);
        }

        strengthText.textContent = level;
        strengthText.className = 'strength-text ' + colorClass;
    });


    // ===== INPUT ANIMATION ON FOCUS =====
    document.querySelectorAll('.form-group input').forEach(input => {
        input.addEventListener('focus', () => {
            input.closest('.form-group').style.transform = 'translateY(-1px)';
        });
        input.addEventListener('blur', () => {
            input.closest('.form-group').style.transform = '';
        });
    });


    // ===== FORM VALIDATION & SUBMISSION =====
    form.addEventListener('submit', (e) => {
        e.preventDefault();

        // Clear previous errors
        document.querySelectorAll('.form-group.error').forEach(g => g.classList.remove('error'));
        document.querySelectorAll('.error-message').forEach(m => m.remove());

        let hasError = false;

        // Validate first name
        const firstName = document.getElementById('firstName');
        if (!firstName.value.trim()) {
            showError(firstName, 'First name is required');
            hasError = true;
        }

        // Validate email
        const email = document.getElementById('email');
        if (!email.value.match(/^[^\s@]+@[^\s@]+\.[^\s@]+$/)) {
            showError(email, 'Please enter a valid email');
            hasError = true;
        }

        // Validate phone
        const phone = document.getElementById('phone');
        if (!phone.value.replace(/\s/g, '').match(/^\d{10}$/)) {
            showError(phone, 'Enter a valid 10-digit number');
            hasError = true;
        }

        // Validate password
        if (passwordInput.value.length < 8) {
            showError(passwordInput, 'Password must be at least 8 characters');
            hasError = true;
        }

        // Validate emergency contact
        const emergency = document.getElementById('emergencyContact');
        if (!emergency.value.replace(/\s/g, '').match(/^\d{10}$/)) {
            showError(emergency, 'Enter a valid 10-digit number');
            hasError = true;
        }

        // Validate terms
        const terms = document.getElementById('terms');
        if (!terms.checked) {
            const check = terms.closest('.form-check');
            check.style.animation = 'shake 0.4s ease-out';
            setTimeout(() => check.style.animation = '', 400);
            hasError = true;
        }

        if (hasError) return;

        // Simulate submission
        submitBtn.classList.add('loading');

        setTimeout(() => {
            showSuccess();
        }, 1800);
    });


    function showError(input, message) {
        const group = input.closest('.form-group');
        group.classList.add('error');

        const errorEl = document.createElement('span');
        errorEl.className = 'error-message';
        errorEl.textContent = '⚠ ' + message;
        group.appendChild(errorEl);
    }


    function showSuccess() {
        const wrapper = document.querySelector('.signup-form-wrapper');
        wrapper.innerHTML = `
      <div class="signup-success">
        <div class="success-icon">🛡️</div>
        <h2>Welcome to Sahayak!</h2>
        <p>
          Your safety shield is activated. We've sent a verification email 
          to confirm your account. Your emergency contact has been notified too.
        </p>
        <a href="index.html" class="btn btn-primary">
          <span>🏠</span> Go to Home
        </a>
      </div>
    `;
    }


    // ===== GOOGLE SIGN-IN (Google Identity Services) =====
    // -------------------------------------------------------
    // To make this work with YOUR Google account:
    // 1. Go to https://console.cloud.google.com/apis/credentials
    // 2. Create an OAuth 2.0 Client ID (Web application type)
    // 3. Add your domain to Authorized JavaScript origins
    //    (for local dev: http://localhost:8080)
    // 4. Replace the client_id below with your own
    // -------------------------------------------------------
    const GOOGLE_CLIENT_ID = 'YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com';

    function initGoogleSignIn() {
        if (typeof google === 'undefined' || !google.accounts) {
            // GIS script hasn't loaded yet, retry
            setTimeout(initGoogleSignIn, 500);
            return;
        }

        google.accounts.id.initialize({
            client_id: GOOGLE_CLIENT_ID,
            callback: handleGoogleCredential,
            auto_select: false,
        });
    }

    function handleGoogleCredential(response) {
        // Decode the JWT credential to get user info
        const payload = parseJwt(response.credential);

        if (payload) {
            showGoogleSuccess(payload);
        }
    }

    function parseJwt(token) {
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            return JSON.parse(decodeURIComponent(
                atob(base64).split('').map(c =>
                    '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
                ).join('')
            ));
        } catch (e) {
            return null;
        }
    }

    function showGoogleSuccess(user) {
        const wrapper = document.querySelector('.signup-form-wrapper');
        const avatarHtml = user.picture
            ? `<img src="${user.picture}" alt="${user.name}" style="width:72px;height:72px;border-radius:50%;border:3px solid rgba(168,85,247,0.4);margin:0 auto 16px;">`
            : `<div class="success-icon">🛡️</div>`;

        wrapper.innerHTML = `
      <div class="signup-success">
        ${avatarHtml}
        <h2>Welcome, ${user.given_name || user.name}!</h2>
        <p>
          Signed in with <strong>${user.email}</strong>.<br>
          Your safety shield is now activated. 💜
        </p>
        <a href="index.html" class="btn btn-primary">
          <span>🛡️</span> Go to Dashboard
        </a>
      </div>
    `;
    }

    // Google button click handler
    const googleBtn = document.getElementById('googleBtn');
    if (googleBtn) {
        googleBtn.addEventListener('click', () => {
            googleBtn.style.transform = 'scale(0.98)';
            setTimeout(() => { googleBtn.style.transform = ''; }, 200);

            if (typeof google !== 'undefined' && google.accounts) {
                // Use GIS prompt for real Google login
                google.accounts.id.prompt((notification) => {
                    if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
                        // If popup blocked or no client ID, show a demo simulation
                        showGoogleDemo();
                    }
                });
            } else {
                // GIS not loaded — show demo simulation
                showGoogleDemo();
            }
        });
    }

    // Demo simulation when Google API isn't configured
    function showGoogleDemo() {
        googleBtn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z" fill="#4285F4"/>
              <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill="#34A853"/>
              <path d="M3.964 10.706A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.706V4.962H.957A8.997 8.997 0 0 0 0 9c0 1.452.348 2.827.957 4.038l3.007-2.332Z" fill="#FBBC05"/>
              <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.962L3.964 7.294C4.672 5.166 6.656 3.58 9 3.58Z" fill="#EA4335"/>
            </svg>
            Connecting...
        `;

        setTimeout(() => {
            showGoogleSuccess({
                name: 'Priya',
                given_name: 'Priya',
                email: 'priya@gmail.com',
                picture: null,
            });
        }, 1500);
    }

    // Initialize Google Sign-In
    initGoogleSignIn();

});

// Shake animation for terms checkbox
const style = document.createElement('style');
style.textContent = `
  @keyframes shake {
    0%, 100% { transform: translateX(0); }
    20% { transform: translateX(-6px); }
    40% { transform: translateX(6px); }
    60% { transform: translateX(-4px); }
    80% { transform: translateX(4px); }
  }
`;
document.head.appendChild(style);
