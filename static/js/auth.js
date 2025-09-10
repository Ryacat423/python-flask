function comparePasswords() {
    const password = document.getElementById('password').value;
    const confirm = document.getElementById('confirm_password').value;
    const message = document.getElementById('password-message');
    const submitBtn = document.getElementById('submitBtn');
    
    if (confirm.length > 0) {
        if (password !== confirm) {
            message.textContent = "* Passwords do not match.";
            message.className = "text-danger";
            submitBtn.disabled = true;
        } else {
            message.textContent = "✓ Passwords match.";
            message.className = "text-success";
            submitBtn.disabled = false;
        }
    } else {
        message.textContent = "";
        submitBtn.disabled = false;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('registerForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            const password = document.getElementById('password').value;
            const confirm = document.getElementById('confirm_password').value;
            
            if (password !== confirm) {
                e.preventDefault();
                errorAlert('Passwords do not match!', 'Validation Error');
                return false;
            }
        
            const submitBtn = document.getElementById('submitBtn');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status"></span> Registering...';
        });
    }
});

window.addEventListener('load', function() {
    const submitBtn = document.getElementById('submitBtn');
    if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Register';
    }
});