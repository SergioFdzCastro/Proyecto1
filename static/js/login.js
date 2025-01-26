// script.js

document.addEventListener("DOMContentLoaded", function() {
    // Seleccionamos todos los formularios
    const forms = document.querySelectorAll("form");

    forms.forEach(form => {
        form.addEventListener("submit", function(event) {
            // Obtenemos los valores de los campos de entrada
            const username = form.querySelector("#username");
            const password = form.querySelector("#password");

            // Validamos que los campos no estén vacíos
            if (!username.value.trim()) {
                alert("El nombre de usuario es obligatorio.");
                event.preventDefault();  // Detiene el envío del formulario
                username.focus();        // Enfoca el campo de nombre de usuario
                return;
            }

            if (!password.value.trim()) {
                alert("La contraseña es obligatoria.");
                event.preventDefault();  // Detiene el envío del formulario
                password.focus();        // Enfoca el campo de contraseña
                return;
            }

          
        });
    });
});
