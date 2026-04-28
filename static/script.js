// 1. Tab Switching Logic
function showTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    
    document.getElementById(tabId).classList.add('active');
    event.currentTarget.classList.add('active');
}

// 2. Sender Logic
async function handleUpload() {
    const fileInput = document.getElementById('videoInput');
    if (!fileInput.files[0]) return alert("Select a video first!");

    const msg = document.getElementById('senderMsg');
    const loader = document.getElementById('senderLoader');
    
    msg.innerText = "Encrypting & Segmenting...";
    loader.style.display = "block";

    const formData = new FormData();
    formData.append('video', fileInput.files[0]);

    try {
        const response = await fetch('/sender_upload', { method: 'POST', body: formData });
        const data = await response.json();
        msg.innerText = `✅ Streamed ${data.chunks} encrypted chunks to RAM buffer.`;
        
        // Auto-refresh the player after upload
        refreshPlayer();
    } catch (err) {
        msg.innerText = "❌ Upload failed.";
    } finally {
        loader.style.display = "none";
    }
}

// 3. Receiver Logic
function refreshPlayer() {
    const player = document.getElementById('mainPlayer');
    const stat = document.getElementById('receiveStat');
    
    player.load(); // Force the browser to fetch the updated /stream file
    stat.innerText = "Live Stream Updated!";
    setTimeout(() => stat.innerText = "Monitoring live buffer...", 3000);
}

// 4. AI Scanner Logic
async function scanLink() {
    const url = document.getElementById('susLink').value;
    if (!url) return;

    const res = await fetch('/scan_link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url })
    });
    const data = await res.json();

    const table = document.getElementById('pirateTable');
    const row = `<tr>
        <td>${data.found ? '🚩 PIRACY' : '✅ CLEAN'}</td>
        <td>${data.url}</td>
        <td>${data.ip || 'N/A'}</td>
    </tr>`;
    table.innerHTML = row + table.innerHTML;

    // Show Gemini AI Report
    if (data.ai_report) {
        document.getElementById('aiReportBox').style.display = "block";
        document.getElementById('aiText').innerText = data.ai_report;
    }
}

// Function to switch between tabs
function showTab(tabId) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    // Deactivate all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show current tab and activate button
    document.getElementById(tabId).classList.add('active');
    event.currentTarget.classList.add('active');
}

// Function to refresh the video player
function refreshPlayer() {
    const player = document.getElementById('mainPlayer');
    player.load(); // Reloads the /stream source
    document.getElementById('receiveStat').innerText = "Status: Feed Refreshed";
}
