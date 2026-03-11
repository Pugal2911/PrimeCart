// DOM Elements
const loginForm = document.getElementById('loginForm');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');
const passwordToggle = document.getElementById('passwordToggle');
const loginBtn = document.getElementById('loginBtn');
const successAlert = document.getElementById('successAlert');
const errorAlert = document.getElementById('errorAlert');
const errorMessage = document.getElementById('errorMessage');

// Password visibility toggle
passwordToggle.addEventListener('click', () => {
    const type = passwordInput.type === 'password' ? 'text' : 'password';
    passwordInput.type = type;

    const icon = passwordToggle.querySelector('i');
    icon.classList.toggle('fa-eye');
    icon.classList.toggle('fa-eye-slash');
});

// Validation helpers
function validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function validatePassword(password) {
    return password.length >= 8;
}

function showError(input, message) {
    input.classList.add('error');
    const errorDiv = input.closest('.form-group').querySelector('.error-message');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

function clearError(input) {
    input.classList.remove('error');
    const errorDiv = input.closest('.form-group').querySelector('.error-message');
    errorDiv.style.display = 'none';
}

// Real-time validation
emailInput.addEventListener('input', () => {
    validateEmail(emailInput.value)
        ? clearError(emailInput)
        : showError(emailInput, 'Please enter a valid email address');
});

passwordInput.addEventListener('input', () => {
    validatePassword(passwordInput.value)
        ? clearError(passwordInput)
        : showError(passwordInput, 'Password must be at least 8 characters');
});

// Login submit
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    // Validate email and password
    if (!validateEmail(email)) {
        showError(emailInput, 'Please enter a valid email address');
        return;
    }

    if (!validatePassword(password)) {
        showError(passwordInput, 'Password must be at least 8 characters');
        return;
    }

    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const result = await response.json();

        if (result.status === 'success') {
            successAlert.style.display = 'flex';
            errorAlert.style.display = 'none';

            // Redirect based on role
            setTimeout(() => {
                switch (result.role) {
                    case 'admin':
                        window.location.href = '/admin/dashboard';
                        break;
                    case 'seller':
                        window.location.href = '/seller/dashboard';
                        break;
                    case 'delivery_agent':
                        window.location.href = '/delivery/dashboard';
                        break;
                    case 'customer':
                        window.location.href = '/';
                        break;
                    default:
                        window.location.href = '/';
                }
            }, 1000);

        } else {
            // Show error message
            successAlert.style.display = 'none';
            errorAlert.style.display = 'flex';
            errorMessage.textContent = result.message || 'Login failed';
        }

    } catch (err) {
        console.error('Login error:', err);
        successAlert.style.display = 'none';
        errorAlert.style.display = 'flex';
        errorMessage.textContent = 'An error occurred. Please try again.';
    }
});
