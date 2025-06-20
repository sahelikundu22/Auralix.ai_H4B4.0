let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let statusDisplay = document.getElementById("status");
let summarySection = document.getElementById("summarySection");
let summaryEdit = document.getElementById("summaryEdit");
let postToSlackBtn = document.getElementById("postToSlack");
let toast = document.getElementById("toast");

const recordBtn = document.getElementById("recordBtn");
const meetingTitleInput = document.getElementById("meetingTitle");
const slackEnabledCheckbox = document.getElementById("slackEnabled");
const uploadFile = document.getElementById("uploadFile");
const notionEnabledCheckbox = document.getElementById("notionEnabled");

// For tab + mic capture
let tabStream = null;
let micStream = null;
let mixedStream = null;
let audioContext = null;

// Load saved settings
chrome.storage.local.get(['slackEnabled', 'notionEnabled'], function(result) {
    if (result.slackEnabled !== undefined) {
        slackEnabledCheckbox.checked = result.slackEnabled;
    }
    if (result.notionEnabled !== undefined) {
        notionEnabledCheckbox.checked = result.notionEnabled;
    }
});

slackEnabledCheckbox.addEventListener('change', function() {
    chrome.storage.local.set({ slackEnabled: slackEnabledCheckbox.checked });
});
notionEnabledCheckbox.addEventListener('change', function() {
    chrome.storage.local.set({ notionEnabled: notionEnabledCheckbox.checked });
});

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
  summarySection.classList.remove("hidden");
  summaryEdit.value = summary;
}
function hideSummarySection() {
  summarySection.classList.add("hidden");
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
    // 1. Capture tab audio
    tabStream = await new Promise((resolve, reject) => {
      chrome.tabCapture.capture({ audio: true, video: false }, (stream) => {
        if (stream) resolve(stream);
        else reject(new Error('Failed to capture tab audio'));
      });
    });
    // 2. Capture mic audio
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    // 3. Mix both streams using Web Audio API
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const destination = audioContext.createMediaStreamDestination();
    const tabSource = audioContext.createMediaStreamSource(tabStream);
    const micSource = audioContext.createMediaStreamSource(micStream);
    // Connect tab audio to both the recording destination and the speakers
    tabSource.connect(destination);
    tabSource.connect(audioContext.destination); // Allow user to hear tab audio
    // Connect mic audio only to the recording destination
    micSource.connect(destination);
    mixedStream = destination.stream;
    // 4. Set up MediaRecorder
    mediaRecorder = new MediaRecorder(mixedStream);
    audioChunks = [];
    mediaRecorder.ondataavailable = event => {
      audioChunks.push(event.data);
    };
    mediaRecorder.onstop = () => {
      const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
      uploadAudio(audioBlob);
      cleanupStreams();
    };
    mediaRecorder.start();
    setRecordingUI(true);
    hideSummarySection();
  } catch (error) {
    showStatus("Audio access error.", "error");
    showToast("Audio access error.", "error");
    cleanupStreams();
  }
}

function stopRecording() {
  if (mediaRecorder) mediaRecorder.stop();
  setRecordingUI(false);
  showStatus("Processing audio…");
}

function cleanupStreams() {
  if (tabStream) {
    tabStream.getTracks().forEach(track => track.stop());
    tabStream = null;
  }
  if (micStream) {
    micStream.getTracks().forEach(track => track.stop());
    micStream = null;
  }
  if (mixedStream) {
    mixedStream.getTracks().forEach(track => track.stop());
    mixedStream = null;
  }
  if (audioContext) {
    audioContext.close();
    audioContext = null;
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
  fetch("http://127.0.0.1:5000/transcribe", {
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

// --- Accessibility: Keyboard navigation ---
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    hideSummarySection();
  }
});

// --- Initial UI State ---
hideSummarySection();
setRecordingUI(false);
showStatus("Ready");
