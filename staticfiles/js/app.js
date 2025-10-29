if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/js/service-worker.js')
    .then(reg => console.log("✅ Service Worker registrado correctamente", reg))
    .catch(err => console.log("❌ Error al registrar Service Worker", err));
}

let deferredPrompt;
window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredPrompt = event;

    console.log("ℹ️ Evento beforeinstallprompt detectado");

    // Detectar si el usuario está en un dispositivo móvil
    const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);

    if (isMobile) {
        const installButton = document.getElementById("installButton");
        if (installButton) {
            installButton.style.display = "block"; // Mostrar botón solo en móviles
            installButton.addEventListener("click", () => {
                deferredPrompt.prompt();
                deferredPrompt.userChoice.then((choice) => {
                    if (choice.outcome === "accepted") {
                        console.log("✅ App instalada correctamente");
                    } else {
                        console.log("❌ Instalación cancelada");
                    }
                    deferredPrompt = null;
                    installButton.style.display = "none";
                });
            });
        }
    }
});
