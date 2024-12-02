document.addEventListener("DOMContentLoaded", function () {
    const registrationForm = document.querySelector("#registrationForm");
    const loginForm = document.querySelector("#loginForm");

    if (registrationForm) {
        registrationForm.addEventListener("submit", function (event) {
            event.preventDefault();
            store();
        });
    }

    if (loginForm) {
        loginForm.addEventListener("submit", function (event) {
            event.preventDefault();
            check();
        });
    }

    function store() {
        const errorMessage = document.querySelector(".error-message");
        const errorText = document.querySelector(".error-text");
        const fullname = document.querySelector("#userFullName").value;
        const email = document.querySelector(".email-address").value;
        const password = document.querySelector(".user-password").value;

        clearErrors();

        let isValid = true;

        if (fullname === '' || email === '' || password === '') {
            errorText.textContent = "Please fill in all fields.";
            errorMessage.style.display = 'flex';
            if (fullname === '') markFieldAsInvalid('#userFullName', '.fullNameLabel');
            if (email === '') markFieldAsInvalid('.email-address', '.emailLabel');
            if (password === '') markFieldAsInvalid('.user-password', '.passwordLabel');
            isValid = false;
        }

        if (isValid) {
            if (!validateFullName(fullname)) {
                errorText.textContent = "Full name can only contain letters and spaces.";
                errorMessage.style.display = 'flex';
                markFieldAsInvalid('#userFullName', '.fullNameLabel');
                isValid = false;
            }

            if (!validateEmail(email)) {
                errorText.textContent = "Please enter a valid email address.";
                errorMessage.style.display = 'flex';
                markFieldAsInvalid('.email-address', '.emailLabel');
                isValid = false;
            }

            if (!validatePassword(password)) {
                errorText.textContent = "Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one digit, and one special character.";
                errorMessage.style.display = 'flex';
                markFieldAsInvalid('.user-password', '.passwordLabel');
                isValid = false;
            }
        }

        if (isValid) {
            errorMessage.style.display = 'none';
            //alert("Registration successful! Your account has been created.");
            localStorage.setItem('fullname', fullname);
            localStorage.setItem('email', email);
            localStorage.setItem('password', password);
            window.location.href = "login.html";  
        }
    }
    
    document.addEventListener("DOMContentLoaded", function () {
        const loginForm = document.querySelector("#loginForm");
    
        if (loginForm) {
            loginForm.addEventListener("submit", function (event) {
                event.preventDefault();
                check();
            });
        }
    
        function check() {
            const errorMessage = document.querySelector(".error-message");
            const errorText = document.querySelector(".error-text");
    
            const userEmail = document.getElementById('userEmail').value;
            const userPassword = document.getElementById('userPassword').value;
    
            if (userEmail === '' || userPassword === '') {
                errorText.textContent = "Please fill in all fields.";
                errorMessage.style.display = 'flex';
                markFieldAsInvalid('#userEmail', '.emailLabel');
                markFieldAsInvalid('#userPassword', '.passwordLabel');
                return;
            }
    
            // Send the data to Flask's login route using fetch
            fetch('/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: new URLSearchParams({
                    email: userEmail,
                    password: userPassword
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Redirect to the books page upon successful login
                    window.location.href = "/books";
                } else {
                    errorText.textContent = data.message;
                    errorMessage.style.display = 'flex';
                    markFieldAsInvalid('#userEmail', '.emailLabel');
                    markFieldAsInvalid('#userPassword', '.passwordLabel');
                }
            })
            .catch(error => {
                console.error("Error:", error);
                errorText.textContent = "An error occurred. Please try again.";
                errorMessage.style.display = 'flex';
            });
        }
    
        function markFieldAsInvalid(inputClass, labelClass) {
            document.querySelector(inputClass)?.classList.add('input-error');
            document.querySelector(labelClass)?.classList.add('label-error');
        }
    });
    

    function clearErrors() {
        document.querySelector('#userFullName')?.classList.remove('input-error');
        document.querySelector('.fullNameLabel')?.classList.remove('label-error');
        document.querySelector('.email-address')?.classList.remove('input-error');
        document.querySelector('.emailLabel')?.classList.remove('label-error');
        document.querySelector('.user-password')?.classList.remove('input-error');
        document.querySelector('.passwordLabel')?.classList.remove('label-error');
    }

    function markFieldAsInvalid(inputClass, labelClass) {
        document.querySelector(inputClass)?.classList.add('input-error');
        document.querySelector(labelClass)?.classList.add('label-error');
    }

    function validateFullName(fullname) {
        const textFullName = /^[a-zA-Z ]+$/;
        return textFullName.test(fullname);
    }

    function validateEmail(email) {
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailPattern.test(email);
    }

    function validatePassword(password) {
        const pattern = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$/;
        return pattern.test(password);
    }
});

function toSendCodePage() {
    window.location.href = "send_code.html";
}

function toResetPassPage() {
    window.location.href = "reset_pass.html";
}

function backToLoginPage() {
    window.location.href = "login.html";  
}

function backToRecoveryPage() {
    window.location.href = "account_recov.html";
}

