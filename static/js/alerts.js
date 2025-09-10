function successAlert(message = 'Please wait for a confirmation email', title = 'Registration Successful!') {
    Swal.fire({
        title: title,
        text: message,
        icon: 'success',
        confirmButtonText: 'OK',
        confirmButtonColor: '#28a745',
        allowOutsideClick: false,
        timer: 3000,
        timerProgressBar: true
    });
}

function errorAlert(message, title = "Registration Failed") {
    Swal.fire({
        title: title,
        text: message,
        icon: 'error',
        confirmButtonText: 'Try Again',
        confirmButtonColor: '#dc3545',
        allowOutsideClick: false
    });
}

function warningAlert(message, title = "Warning!") {
    Swal.fire({
        title: title,
        text: message,
        icon: 'warning',
        confirmButtonText: 'OK',
        confirmButtonColor: '#ffc107'
    });
}

function infoAlert(message, title = "Info") {
    Swal.fire({
        title: title,
        text: message,
        icon: 'info',
        confirmButtonText: 'OK',
        confirmButtonColor: '#17a2b8'
    });
}

// Function to show loading alert
function loadingAlert(title = 'Processing...', text = 'Please wait while we process your request.') {
    Swal.fire({
        title: title,
        text: text,
        allowOutsideClick: false,
        allowEscapeKey: false,
        showConfirmButton: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
}

function logoutSuccessAlert(userName = 'User') {
    Swal.fire({
        title: 'Goodbye!',
        text: `See you later, ${userName}! You have been logged out successfully.`,
        icon: 'success',
        confirmButtonText: 'OK',
        confirmButtonColor: '#28a745',
        timer: 3000,
        timerProgressBar: true,
        allowOutsideClick: false
    }).then((result) => {
        window.location.href = '/';
    });
}

function confirmLogout() {
    Swal.fire({
        title: 'Are you sure?',
        text: 'Do you want to log out of your account?',
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#dc3545',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Yes, log out',
        cancelButtonText: 'Cancel',
        reverseButtons: true
    }).then((result) => {
        if (result.isConfirmed) {
            Swal.fire({
                title: 'Logging out...',
                allowOutsideClick: false,
                allowEscapeKey: false,
                showConfirmButton: false,
                didOpen: () => {
                    Swal.showLoading();
                }
            });

            window.location.href = '/logout';
        }
    });
}

function closeAlert() {
    Swal.close();
}