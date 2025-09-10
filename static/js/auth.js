function comparePasswords() {
    const password = document.getElementById('password').value;
    const confirm = document.getElementById('confirm_password').value;
    const message = document.getElementById('password-message');
    if (confirm.length > 0 && password !== confirm) {
        message.textContent = "* Passwords do not match.";
    } else {
        message.textContent = "";
    }
}