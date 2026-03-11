document.addEventListener('DOMContentLoaded', function() {
    // Configuration
    const statusOrder = ['Processing', 'Shipped', 'Delivered']; 
    const POLL_INTERVAL = 5000; // Check DB every 5 seconds
    
    const progressTracker = document.getElementById('progressTracker');
    // Get Order ID from the HTML attribute we set in the template
    const orderId = progressTracker.dataset.orderId;

    if (!orderId) return;

    // Initial fetch
    fetchFromDatabase();

    // Start Polling: This is what makes it "Automatic" from the DB
    setInterval(fetchFromDatabase, POLL_INTERVAL);

    async function fetchFromDatabase() {
        try {
            const response = await fetch(`/api/get-order-status/${orderId}`);
            const data = await response.json();
            console.log(data)
            if (data.success) {
                updateUI(data.status, data.placed_date);
            }
        } catch (error) {
            console.error("Database connection failed:", error);
        }
    }

function updateUI(currentStatus) {
    currentStatus = currentStatus.trim();

    const steps = document.querySelectorAll('.tracker-step');

    steps.forEach(step => {
        const stepName = step.dataset.step;

        if (stepName === currentStatus) {
            step.classList.add('active');
            step.classList.remove('completed');
        } else if (
            statusOrder.indexOf(stepName) <
            statusOrder.indexOf(currentStatus)
        ) {
            step.classList.add('completed');
            step.classList.remove('active');
        } else {
            step.classList.remove('active', 'completed');
        }
    });
}



    function updateTimeline(status, stepIndex) {
        const timeline = document.getElementById('statusTimeline');
        timeline.innerHTML = ''; // Clear and rebuild based on DB status

        for (let i = 0; i <= stepIndex; i++) {
            const div = document.createElement('div');
            div.className = 'timeline-item';
            div.innerHTML = `
                <div class="timeline-icon"><i class="fas fa-check"></i></div>
                <div class="timeline-content">
                    <div class="timeline-title">${statusOrder[i]}</div>
                    <div class="timeline-note">Status updated in our records.</div>
                </div>
            `;
            timeline.appendChild(div);
        }
    }

    function createLine() {
        const line = document.createElement('div');
        line.className = 'progress-line';
        progressTracker.appendChild(line);
        return line;
    }
});