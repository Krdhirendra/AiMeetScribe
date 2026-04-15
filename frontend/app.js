const BACKEND_URL = "http://localhost:8000";

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(btn => {
        if (!btn.classList.contains('action')) {
            btn.classList.remove('active');
        }
    });
    event.target.classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}Tab`).classList.add('active');
}

async function deployBot() {
    const urlInput = document.getElementById('meetUrl').value.trim();
    const statusMsg = document.getElementById('statusMessage');

    if (!urlInput || !urlInput.includes('meet.google.com')) {
        statusMsg.textContent = "Please enter a valid Google Meet URL.";
        statusMsg.className = "status-msg error";
        return;
    }

    try {
        statusMsg.textContent = "Deploying bot to meeting...";
        statusMsg.className = "status-msg";

        const response = await fetch(`${BACKEND_URL}/api/bot/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url: urlInput })
        });

        const data = await response.json();
        
        if (response.ok) {
            statusMsg.textContent = "Bot successfully deployed! It will join shortly.";
            statusMsg.className = "status-msg success";
        } else {
            statusMsg.textContent = `Error: ${data.detail}`;
            statusMsg.className = "status-msg error";
        }
    } catch (err) {
        statusMsg.textContent = "Failed to connect to backend. Is it running?";
        statusMsg.className = "status-msg error";
    }
}

async function fetchData() {
    const summaryBox = document.getElementById('summaryBox');
    const transcriptBox = document.getElementById('transcriptBox');

    summaryBox.innerHTML = '<div class="placeholder">Loading AI summary...</div>';
    transcriptBox.innerHTML = '<div class="placeholder">Loading transcript...</div>';

    try {
        const [sumRes, transRes] = await Promise.all([
            fetch(`${BACKEND_URL}/api/summaries`),
            fetch(`${BACKEND_URL}/api/transcripts`)
        ]);

        const summaryData = await sumRes.json();
        const transcriptData = await transRes.json();

        if (summaryData.status === 'success' && summaryData.content) {
            summaryBox.textContent = summaryData.content;
        } else {
            summaryBox.innerHTML = '<div class="placeholder">No summary found yet. Deploy the bot to generate one!</div>';
        }

        if (transcriptData.status === 'success' && transcriptData.content) {
            transcriptBox.textContent = transcriptData.content;
        } else {
            transcriptBox.innerHTML = '<div class="placeholder">No transcript found yet.</div>';
        }

    } catch (err) {
        const errorHtml = '<div class="placeholder" style="color: #f87171">Failed to fetch data from backend.</div>';
        summaryBox.innerHTML = errorHtml;
        transcriptBox.innerHTML = errorHtml;
    }
}

// Fetch data on load
window.addEventListener('DOMContentLoaded', fetchData);
