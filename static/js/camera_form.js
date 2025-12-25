// Add Camera Form - Auto-generate RTSP URL from separate fields
document.addEventListener('DOMContentLoaded', function () {
    const usernameInput = document.getElementById('camera-username');
    const passwordInput = document.getElementById('camera-password');
    const ipInput = document.getElementById('camera-ip');
    const portInput = document.getElementById('camera-port');
    const streamPathInput = document.getElementById('camera-stream-path');
    const generatedUrlDisplay = document.getElementById('generated-rtsp-url');

    function updateGeneratedURL() {
        const username = usernameInput?.value || 'username';
        const password = passwordInput?.value || 'password';
        const ip = ipInput?.value || '192.168.1.100';
        const port = portInput?.value || '554';
        const streamPath = streamPathInput?.value || '/stream';

        // Encode credentials
        const encodedUsername = encodeURIComponent(username);
        const encodedPassword = encodeURIComponent(password);

        // Build RTSP URL
        const auth = `${encodedUsername}:${encodedPassword}@`;
        const path = streamPath.startsWith('/') ? streamPath : '/' + streamPath;
        const url = `rtsp://${auth}${ip}:${port}${path}`;

        if (generatedUrlDisplay) {
            generatedUrlDisplay.textContent = url;
        }

        return url;
    }

    // Update URL whenever any field changes
    if (usernameInput) usernameInput.addEventListener('input', updateGeneratedURL);
    if (passwordInput) passwordInput.addEventListener('input', updateGeneratedURL);
    if (ipInput) ipInput.addEventListener('input', updateGeneratedURL);
    if (portInput) portInput.addEventListener('input', updateGeneratedURL);
    if (streamPathInput) streamPathInput.addEventListener('input', updateGeneratedURL);

    // Initial update
    updateGeneratedURL();

    // Override the addCamera function to use separate fields
    if (typeof window.app !== 'undefined') {
        const originalAddCamera = window.app.addCamera;
        window.app.addCamera = async function () {
            const name = document.getElementById('camera-name').value;
            const type = document.getElementById('camera-type').value;
            const username = usernameInput.value;
            const password = passwordInput.value;
            const ip = ipInput.value;
            const port = portInput.value || '554';
            const streamPath = streamPathInput.value || '/';

            const rtspUrl = updateGeneratedURL();

            const data = {
                name: name,
                type: type.toUpperCase(),
                username: username,
                password: password,
                ip_address: ip,
                port: parseInt(port),
                stream_path: streamPath,
                rtsp_url: rtspUrl
            };

            try {
                const response = await fetch('/api/cameras/add', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (result.success) {
                    alert('Camera added successfully!');
                    document.getElementById('add-camera-modal').style.display = 'none';
                    document.getElementById('add-camera-form').reset();
                    // Reload camera list
                    if (window.app && window.app.loadCameras) {
                        window.app.loadCameras();
                    }
                } else {
                    alert('Error adding camera: ' + (result.error || 'Unknown error'));
                }
            } catch (error) {
                alert('Error adding camera: ' + error.message);
            }
        };
    }
});
