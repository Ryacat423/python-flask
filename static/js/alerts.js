function successAlert() {
    Swal.fire({
        title: 'Registration Sent',
        text: 'Please wait for a confirmation email',
        icon: 'success',
        confirmButtonText: 'OK'
    });
}

function errorAlert(message, title = "Error!") {
    Swal.fire({
        title: title,
        text: message,
        icon: 'error',
        confirmButtonText: 'OK'
    });
}

function warningAlert(message, title = "Warning!") {
    Swal.fire({
        title: title,
        text: message,
        icon: 'warning',
        confirmButtonText: 'OK'
    });
}

function infoAlert(message, title = "Info") {
    Swal.fire({
        title: title,
        text: message,
        icon: 'info',
        confirmButtonText: 'OK'
    });
}
