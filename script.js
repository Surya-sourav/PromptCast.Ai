document.getElementById('search-button').addEventListener('click', function() {
    const topic = document.getElementById('search-input').value.trim();
    if (topic) {
        // Disable the button to prevent multiple clicks
        document.getElementById('search-button').disabled = true;
        document.getElementById('search-button').innerText = 'Generating...';

        // Send the topic to the backend
        fetch('/generate_podcast', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ topic: topic })
        })
        .then(response => response.json())
        .then(data => {
            if (data.script) {
                // Display the generated script
                displayScript(data.script);
            } else if (data.error) {
                alert('Error: ' + data.error);
            }
            // Re-enable the button
            document.getElementById('search-button').disabled = false;
            document.getElementById('search-button').innerText = 'Generate Podcast';
        })
        .catch(error => {
            console.error('Error:', error);
            alert('An error occurred while generating the podcast.');
            document.getElementById('search-button').disabled = false;
            document.getElementById('search-button').innerText = 'Generate Podcast';
        });
    } else {
        alert('Please enter a topic.');
    }
});

function displayScript(script) {
    // Create a modal or a new section to display the script
    const scriptContainer = document.createElement('div');
    scriptContainer.classList.add('script-container');
    scriptContainer.innerHTML = `
        <h2>Your Podcast Script</h2>
        <p>${script.replace(/\n/g, '<br>')}</p>
        <button id="close-script">Close</button>
    `;
    document.body.appendChild(scriptContainer);

    document.getElementById('close-script').addEventListener('click', function() {
        document.body.removeChild(scriptContainer);
    });
}
