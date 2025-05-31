document.addEventListener('DOMContentLoaded', function() {
    const eventLogBody = document.getElementById('eventLogBody');
    const refreshButton = document.getElementById('refreshButton');
    const welcomeMessageElement = document.getElementById('welcomeMessage');

    if (welcomeMessageElement && welcomeMessageElement.dataset.message) {
        // You can use this if you pass messages from Flask to the template
        // console.log("Message from server:", welcomeMessageElement.dataset.message);
    }

    async function fetchEvents() {
        if (!eventLogBody) return; // Guard if element not found
        eventLogBody.innerHTML = '<tr><td colspan="4">Loading events...</td></tr>'; // Wider colspan
        try {
            const response = await fetch('/api/events');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const events = await response.json();
            displayEvents(events);
        } catch (error) {
            console.error("Could not fetch events:", error);
            if (eventLogBody) eventLogBody.innerHTML = '<tr><td colspan="4">Error loading events. Please try again.</td></tr>';
        }
    }

    function displayEvents(events) {
        if (!eventLogBody) return;
        eventLogBody.innerHTML = ''; 

        if (!events || events.length === 0) {
            eventLogBody.innerHTML = '<tr><td colspan="4">No events found.</td></tr>';
            return;
        }

        events.forEach(event => {
            const row = eventLogBody.insertRow();
            row.insertCell().textContent = event.id || 'N/A';
            row.insertCell().textContent = event.timestamp ? new Date(event.timestamp).toLocaleString() : 'N/A';
            row.insertCell().textContent = event.tag_id || 'N/A';
            
            const cellVideo = row.insertCell();
            if (event.video_url) {
                const videoLink = document.createElement('a');
                videoLink.href = event.video_url;
                videoLink.textContent = "View Video";
                videoLink.target = "_blank";
                cellVideo.appendChild(videoLink);
            } else {
                cellVideo.textContent = "No video";
            }
        });
    }

    if (refreshButton) {
        refreshButton.addEventListener('click', fetchEvents);
    }

    // Fetch events on initial page load if the table body exists
    if (eventLogBody) {
        fetchEvents();
    }
});