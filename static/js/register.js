document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('form');
    
    form.addEventListener('submit', function(event) {
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        // Validación del nombre de usuario
        if (username.length < 5) {
            alert('El nombre de usuario debe tener al menos 5 caracteres.');
            event.preventDefault(); // Evita que el formulario se envíe
            return;
        }

        // Validación de la contraseña (mínimo 8 caracteres)
        if (password.length < 8) {
            alert('La contraseña debe tener al menos 8 caracteres.');
            event.preventDefault(); // Evita que el formulario se envíe
            return;
        }
    });
});
