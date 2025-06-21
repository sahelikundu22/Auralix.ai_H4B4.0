let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let statusDisplay = document.getElementById("status");
let summarySection = document.getElementById("summarySection");
let summaryEdit = document.getElementById("summaryEdit");
let postToSlackBtn = document.getElementById("postToSlack");
let toast = document.getElementById("toast");
let serverStatus = document.getElementById("serverStatus");

const recordBtn = document.getElementById("recordBtn");
const meetingTitleInput = document.getElementById("meetingTitle");
const slackEnabledCheckbox = document.getElementById("slackEnabled");
const uploadFile = document.getElementById("uploadFile");
const notionEnabledCheckbox = document.getElementById("notionEnabled");

// Backend buttons
const checkCommitsBtn = document.getElementById("checkCommits");
const sendStandupBtn = document.getElementById("sendStandup");
const initDbBtn = document.getElementById("initDb");

// Flask backend URL - change this to your deployed backend URL
const FLASK_BACKEND_URL = "http://localhost:5000";

// Check server status on load
checkServerStatus();

// Check server status every 30 seconds
setInterval(checkServerStatus, 30000);

async function checkServerStatus() {
    try {
        const response = await fetch(`${FLASK_BACKEND_URL}/health`);
        if (response.ok) {
            serverStatus.textContent = "🟢 Backend server connected";
            serverStatus.className = "server-status connected";
        } else {
            throw new Error("Server not responding");
        }
    } catch (error) {
        serverStatus.textContent = "🔴 Backend server disconnected";
        serverStatus.className = "server-status disconnected";
    }
}

// --- UI State ---
function showStatus(msg, type = "") {
    statusDisplay.textContent = msg;
    statusDisplay.className = "status" + (type ? ` ${type}` : "");
}

function showToast(msg, type = "") {
    toast.textContent = msg;
    toast.className = `toast show${type ? ' ' + type : ''}`;
    setTimeout(() => { toast.className = "toast"; }, 3000);
}

function showSummarySection(summary) {
    summarySection.classList.add("show");
    summaryEdit.value = summary;
}

function hideSummarySection() {
    summarySection.classList.remove("show");
    summaryEdit.value = "";
}

function setRecordingUI(isRec) {
    isRecording = isRec;
    if (isRec) {
        recordBtn.classList.add("recording");
        recordBtn.querySelector(".label").textContent = "Stop Recording";
        showStatus("Recording…");
    } else {
        recordBtn.classList.remove("recording");
        recordBtn.querySelector(".label").textContent = "Start Recording";
        showStatus("");
    }
}

// --- Flask Backend Communication ---
async function callFlaskEndpoint(endpoint, action) {
    try {
        showStatus(`${action}...`);
        const response = await fetch(`${FLASK_BACKEND_URL}${endpoint}`);
        const data = await response.json();
        
        if (response.ok) {
            showStatus(`${action} completed!`, "success");
            showToast(`${action} successful!`, "success");
            return data;
        } else {
            throw new Error(data.message || 'Request failed');
        }
    } catch (error) {
        console.error(`Error ${action.toLowerCase()}:`, error);
        showStatus(`Error: ${error.message}`, "error");
        showToast(`Failed to ${action.toLowerCase()}`, "error");
        return null;
    }
}

// --- Backend Feature Buttons ---
if (checkCommitsBtn) {
    checkCommitsBtn.addEventListener("click", async () => {
        await callFlaskEndpoint("/check-commits", "Checking GitHub commits");
    });
}

if (sendStandupBtn) {
    sendStandupBtn.addEventListener("click", async () => {
        await callFlaskEndpoint("/send-standup", "Sending standup");
    });
}

if (initDbBtn) {
    initDbBtn.addEventListener("click", async () => {
        await callFlaskEndpoint("/init-db", "Initializing database");
    });
}

// --- Recording ---
recordBtn.addEventListener("click", async () => {
    if (!isRecording) {
        await startRecording();
    } else {
        stopRecording();
    }
});

async function startRecording() {
    try {
        // Request microphone access
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // Set up MediaRecorder
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        
        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
            uploadAudio(audioBlob);
            stream.getTracks().forEach(track => track.stop());
        };
        
        mediaRecorder.start();
        setRecordingUI(true);
        hideSummarySection();
    } catch (error) {
        showStatus("Microphone access denied.", "error");
        showToast("Please allow microphone access.", "error");
    }
}

function stopRecording() {
    if (mediaRecorder) {
        mediaRecorder.stop();
        setRecordingUI(false);
        showStatus("Processing audio…");
    }
}

// --- Upload ---
uploadFile.addEventListener("change", event => {
    const file = event.target.files[0];
    if (file) {
        uploadAudio(file);
    }
});

// --- Audio Upload & Backend ---
function uploadAudio(audioBlob) {
    hideSummarySection();
    showStatus("Processing audio…");
    
    const formData = new FormData();
    formData.append("file", audioBlob, "meeting_audio.wav");
    formData.append("meetingTitle", meetingTitleInput.value || "Untitled Meeting");
    formData.append("slackEnabled", slackEnabledCheckbox.checked);
    formData.append("notionEnabled", notionEnabledCheckbox.checked);
    
    fetch(`${FLASK_BACKEND_URL}/transcribe`, {
        method: "POST",
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        if (data.summary && data.summary.formatted_text && !data.summary.formatted_text.startsWith("Error")) {
            showSummarySection(data.summary.formatted_text);
            showStatus("Summary ready. Edit and post to Slack!", "success");
            showToast("Summary generated!", "success");
        } else {
            showStatus("Could not generate summary.", "error");
            showToast("Could not generate summary.", "error");
        }
    })
    .catch(error => {
        showStatus("Error processing audio.", "error");
        showToast("Error processing audio.", "error");
    });
}

// --- Post to Slack ---
postToSlackBtn.addEventListener("click", () => {
    const summary = summaryEdit.value;
    if (!summary.trim()) {
        showToast("Summary is empty!", "error");
        return;
    }
    showToast("Posted to Slack!", "success");
    showStatus("Posted to Slack!", "success");
});

// --- Keyboard navigation ---
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        hideSummarySection();
    }
});

// --- Initial UI State ---
hideSummarySection();
setRecordingUI(false);
showStatus("Ready to record"); 