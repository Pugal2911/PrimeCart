document.addEventListener('DOMContentLoaded', () => {
const firstNameInput = document.getElementById('firstName');
const lastNameInput = document.getElementById('lastName');
const emailInput = document.getElementById('email');
const phone = document.getElementById('phone');
const countryCode = document.getElementById('countryCode');
const newsletter = document.getElementById('newsletter');
const smsAlerts = document.getElementById('smsAlerts');

const signupForm = document.getElementById('signupForm');
const stepCircles = document.querySelectorAll('.step-circle');
const stepLabels = document.querySelectorAll('.step-label');

// Buttons
const nextStep1Btn = document.getElementById('nextStep1');
const nextStep2Btn = document.getElementById('nextStep2');
const prevStep1Btn = document.getElementById('prevStep1');
const prevStep2Btn = document.getElementById('prevStep2');
const cancelBtn = document.getElementById('cancelBtn');
const createAccountBtn = document.getElementById('createAccountBtn');

// Alerts
const successAlert = document.getElementById('successAlert');
const errorAlert = document.getElementById('errorAlert');
const errorMessage = document.getElementById('errorMessage');

// Password
const passwordInput = document.getElementById('password');
const confirmPasswordInput = document.getElementById('confirmPassword');
const passwordToggle1 = document.getElementById('passwordToggle1');
const passwordToggle2 = document.getElementById('passwordToggle2');
const strengthText = document.getElementById('strengthText');
const strengthFill = document.querySelector('.strength-fill');

let currentStep = 1;

/* -------------------- Helpers -------------------- */
function hideAlerts() {
    successAlert.style.display = 'none';
    errorAlert.style.display = 'none';
}

function goToStep(step) {
    document.getElementById(`step${currentStep}Form`).classList.remove('active');
    stepCircles[currentStep - 1].classList.remove('active');
    stepLabels[currentStep - 1].classList.remove('active');

    document.getElementById(`step${step}Form`).classList.add('active');
    stepCircles[step - 1].classList.add('active');
    stepLabels[step - 1].classList.add('active');

    currentStep = step;
}

function togglePassword(input, btn) {
    const type = input.type === 'password' ? 'text' : 'password';
    input.type = type;
    btn.querySelector('i').classList.toggle('fa-eye');
    btn.querySelector('i').classList.toggle('fa-eye-slash');
}

function showError(msg) {
    errorMessage.textContent = msg;
    errorAlert.style.display = 'flex';
}

/* -------------------- Validation -------------------- */
function validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function validateStep1() {
    const firstName = firstNameInput.value.trim();
    const lastName = lastNameInput.value.trim();
    const email = emailInput.value.trim();

    if (!firstName || !lastName || !email) {
        showError('All required fields must be filled');
        return false;
    }
    if (!validateEmail(email)) {
        showError('Invalid email address');
        return false;
    }
    return true;
}

function validateStep2() {
    const password = passwordInput.value;
    const confirmPassword = confirmPasswordInput.value;

    if (password.length < 8) {
        showError('Password must be at least 8 characters');
        return false;
    }
    if (password !== confirmPassword) {
        showError('Passwords do not match');
        return false;
    }
    return true;
}

function validateStep3() {
    if (!document.getElementById('terms').checked) {
        showError('You must accept Terms & Privacy Policy');
        return false;
    }
    return true;
}

/* -------------------- Password Strength -------------------- */
passwordInput.addEventListener('input', () => {
    const val = passwordInput.value;
    let strength = 0;

    if (val.length >= 8) strength++;
    if (/[A-Z]/.test(val)) strength++;
    if (/[0-9]/.test(val)) strength++;
    if (/[^A-Za-z0-9]/.test(val)) strength++;

    const percent = strength * 25;
    strengthFill.style.width = percent + '%';

    strengthText.textContent =
        percent <= 25 ? 'Weak' :
        percent <= 50 ? 'Fair' :
        percent <= 75 ? 'Good' : 'Strong';
});

/* -------------------- Events -------------------- */
passwordToggle1.onclick = () => togglePassword(passwordInput, passwordToggle1);
passwordToggle2.onclick = () => togglePassword(confirmPasswordInput, passwordToggle2);

nextStep1Btn.onclick = () => validateStep1() && goToStep(2);
nextStep2Btn.onclick = () => validateStep2() && goToStep(3);

prevStep1Btn.onclick = () => goToStep(1);
prevStep2Btn.onclick = () => goToStep(2);

cancelBtn.onclick = () => {
    if (confirm('Cancel signup?')) window.location.href = '/';
};

/* -------------------- Submit -------------------- */
signupForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideAlerts();

    if (!validateStep3()) return;

    const payload = {
        first_name: firstNameInput.value.trim(),
        last_name: lastNameInput.value.trim(),
        email: emailInput.value.trim(),
        phone: countryCode.value + phone.value,
        password: passwordInput.value,
        newsletter: newsletter.checked,
        sms_alerts: smsAlerts.checked
    };

    const res = await fetch('/signup', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    });

    const result = await res.json();

    if (result.status === 'success') {
        successAlert.style.display = 'flex';
        setTimeout(() => window.location.href = '/login', 1500);
    } else {
        showError(result.message);
    }
});

/* -------------------- Init -------------------- */
hideAlerts();
});