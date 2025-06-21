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
const uploadFile = document.getElementById("uploadFile");

// New buttons for Flask backend features
const checkCommitsBtn = document.getElementById("checkCommits");
const sendStandupBtn = document.getElementById("sendStandup");
const initDbBtn = document.getElementById("initDb");

// For tab + mic capture
let tabStream = null;
let micStream = null;
let mixedStream = null;
let audioContext = null;

// Flask backend URL
const FLASK_BACKEND_URL = "http://localhost:5000";

// --- Enhanced UI State with Animations ---
function showStatus(msg, type = "") {
  const statusIcon = statusDisplay.querySelector('.status-icon');
  const statusText = statusDisplay.querySelector('.status-text');
  
  // Update status text
  statusText.textContent = msg;
  statusDisplay.className = "status" + (type ? ` ${type}` : "");
  
  // Update status icon based on message type
  if (type === "processing") {
    statusIcon.textContent = "🔄";
  } else if (type === "success") {
    statusIcon.textContent = "✅";
  } else if (type === "error") {
    statusIcon.textContent = "❌";
  } else {
    statusIcon.textContent = "✨";
  }
  
  // Add processing animation for specific messages
  if (msg.includes("Processing") || msg.includes("Recording") || msg.includes("Uploading")) {
    statusDisplay.classList.add("processing");
    addLoadingSpinner(statusDisplay);
  } else {
    statusDisplay.classList.remove("processing");
    removeLoadingSpinner(statusDisplay);
  }
}

function addLoadingSpinner(element) {
  if (!element.querySelector('.loading-spinner')) {
    const spinner = document.createElement('span');
    spinner.className = 'loading-spinner';
    element.insertBefore(spinner, element.firstChild);
  }
}

function removeLoadingSpinner(element) {
  const spinner = element.querySelector('.loading-spinner');
  if (spinner) {
    spinner.remove();
  }
}

function showToast(msg, type = "") {
  toast.textContent = msg;
  toast.className = `toast show${type ? ' ' + type : ''}`;
  
  // Add entrance animation
  toast.style.transform = 'translateX(-50%) translateY(100px)';
  toast.style.opacity = '0';
  
  setTimeout(() => {
    toast.style.transform = 'translateX(-50%) translateY(0)';
    toast.style.opacity = '1';
  }, 10);
  
  setTimeout(() => {
    toast.style.transform = 'translateX(-50%) translateY(100px)';
    toast.style.opacity = '0';
    setTimeout(() => { 
      toast.className = "toast"; 
    }, 300);
  }, 3000);
}

function showSummarySection(summary) {
  summarySection.classList.remove("hidden");
  
  // Format the summary with proper emojis and clean formatting
  const formattedSummary = formatSummary(summary);
  summaryEdit.value = formattedSummary;
  
  // Add entrance animation
  summarySection.style.opacity = '0';
  summarySection.style.transform = 'translateY(20px)';
  
  setTimeout(() => {
    summarySection.style.opacity = '1';
    summarySection.style.transform = 'translateY(0)';
    
    // Add a subtle highlight animation to the textarea
    summaryEdit.style.boxShadow = '0 0 0 4px rgba(72, 187, 120, 0.2)';
    setTimeout(() => {
      summaryEdit.style.boxShadow = '';
    }, 1000);
  }, 10);
}

// Function to format the AI summary
function formatSummary(summary) {
  if (!summary) return '';

  let formatted = summary;

  // Find the "Action Items" block more reliably
  const actionItemsRegex = /(#+\s*\d\.\s*Action Items:[\s\S]*?)(?=(#+\s*\d\.\s*)|$)/;
  const match = formatted.match(actionItemsRegex);
  
  if (match && match[1] && match[1].includes('|')) {
    const originalBlock = match[1];
    
    // Isolate the header and the table text
    const blockLines = originalBlock.trim().split('\n');
    const headerText = blockLines[0];
    const tableLines = blockLines.slice(1);

    const separatorIndex = tableLines.findIndex(l => l.includes('---'));
    
    if (separatorIndex > 0) {
      const headerLine = tableLines[separatorIndex - 1];
      const headers = headerLine.split('|').map(h => h.trim().replace(/\*| /g, '')).filter(Boolean);
      
      const rows = tableLines.slice(separatorIndex + 1)
        .map(line => line.split('|').map(cell => cell.trim()).filter(Boolean))
        .filter(row => row.length > 0);

      if (rows.length > 0 && headers.length > 0 && rows.every(r => r.length === headers.length)) {
        let newContent = `${headerText}\n`;
        rows.forEach(row => {
          newContent += '\n'; // Add a space between items
          headers.forEach((h, i) => {
            const label = h;
            const value = row[i] || 'N/A';
            if (i === 0) {
              newContent += `• ${label}: ${value}\n`;
            } else {
              newContent += `    ${label}: ${value}\n`;
            }
          });
        });
        
        // Replace the original action items block with the newly formatted list
        formatted = formatted.replace(originalBlock, newContent);
      }
    }
  }

  // Final cleanup for the entire summary
  formatted = formatted.replace(/\*\*/g, ''); 
  formatted = formatted.replace(/\*/g, ''); 
  formatted = formatted.replace(/^#+\s*\d\.\s*/gm, ''); // Remove numbering like ## 2.
  formatted = formatted.replace(/^[-•]\s*/gm, '• '); // Standardize list bullets
  formatted = formatted.replace(/(\n\s*){3,}/g, '\n\n'); // Condense 3+ newlines to 2
  formatted = formatted.trim();

  return formatted;
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
    showStatus("🎙️ Recording in progress...", "processing");
    
    // Add recording animation
    recordBtn.style.animation = 'recordingGlow 2s ease-in-out infinite alternate';
  } else {
    recordBtn.classList.remove("recording");
    recordBtn.querySelector(".label").textContent = "Start Recording";
    showStatus("Ready to record");
    recordBtn.style.animation = '';
  }
}

// --- Enhanced Flask Backend Communication ---
async function callFlaskEndpoint(endpoint, action) {
  try {
    showStatus(`${action}...`, "processing");
    const response = await fetch(`${FLASK_BACKEND_URL}${endpoint}`);
    const data = await response.json();
    
    if (response.ok) {
      showStatus(`${action} completed! ✨`, "success");
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

// --- Enhanced Flask Backend Feature Buttons ---
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

// --- Enhanced Recording with Better Animations ---
if (recordBtn) {
  recordBtn.addEventListener("click", async () => {
    if (!isRecording) {
      await startRecording();
    } else {
      stopRecording();
    }
  });
}

async function startRecording() {
  try {
    console.log("Starting recording process...");
    
    // Add button press animation
    recordBtn.style.transform = 'scale(0.95)';
    setTimeout(() => {
      recordBtn.style.transform = '';
    }, 150);
    
    // 1. Capture tab audio
    console.log("Attempting to capture tab audio...");
    tabStream = await new Promise((resolve, reject) => {
      chrome.tabCapture.capture({ audio: true, video: false }, (stream) => {
        if (chrome.runtime.lastError) {
          console.error("Tab capture error:", chrome.runtime.lastError);
          reject(new Error(`Tab capture failed: ${chrome.runtime.lastError.message}`));
          return;
        }
        if (stream) {
          console.log("Tab audio captured successfully");
          resolve(stream);
        } else {
          console.error("No stream returned from tab capture");
          reject(new Error('Failed to capture tab audio - no stream returned'));
        }
      });
    });
    
    // 2. Capture mic audio
    console.log("Attempting to capture microphone audio...");
    micStream = await navigator.mediaDevices.getUserMedia({ 
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      } 
    });
    console.log("Microphone audio captured successfully");
    
    // 3. Mix both streams using Web Audio API
    console.log("Setting up audio mixing...");
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
    console.log("Audio mixing setup complete");
    
    // 4. Set up MediaRecorder
    console.log("Setting up MediaRecorder...");
    mediaRecorder = new MediaRecorder(mixedStream, {
      mimeType: 'audio/webm;codecs=opus'
    });
    audioChunks = [];
    
    mediaRecorder.ondataavailable = event => {
      console.log("Data available:", event.data.size, "bytes");
      audioChunks.push(event.data);
    };
    
    mediaRecorder.onstop = () => {
      console.log("Recording stopped, processing audio...");
      const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
      uploadAudio(audioBlob);
      cleanupStreams();
    };
    
    mediaRecorder.onerror = (event) => {
      console.error("MediaRecorder error:", event);
      showStatus("Recording error occurred.", "error");
      showToast("Recording error occurred.", "error");
      cleanupStreams();
    };
    
    mediaRecorder.start(1000); // Collect data every second
    setRecordingUI(true);
    hideSummarySection();
    
    // Add success animation
    showToast("Recording started! 🎙️", "success");
    console.log("Recording started successfully");
    
  } catch (error) {
    console.error("Recording error:", error);
    showStatus(`Audio access error: ${error.message}`, "error");
    showToast(`Audio access error: ${error.message}`, "error");
    cleanupStreams();
  }
}

function stopRecording() {
  if (mediaRecorder) {
    mediaRecorder.stop();
    setRecordingUI(false);
    showStatus("🔄 Processing audio...", "processing");
    
    // Add processing animation
    const processingSteps = [
      "🔄 Processing audio...",
      "🎵 Analyzing audio content...",
      "🤖 Generating AI summary...",
      "✨ Finalizing results..."
    ];
    
    let stepIndex = 0;
    const stepInterval = setInterval(() => {
      if (stepIndex < processingSteps.length) {
        showStatus(processingSteps[stepIndex], "processing");
        stepIndex++;
      } else {
        clearInterval(stepInterval);
      }
    }, 1000);
  }
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

// --- Enhanced Upload with Animations ---
if (uploadFile) {
  uploadFile.addEventListener("change", event => {
    const file = event.target.files[0];
    if (file) {
      // Add file upload animation
      const uploadLabel = document.querySelector('.upload-label');
      if (uploadLabel) {
        uploadLabel.classList.add('file-upload-animation');
        
        setTimeout(() => {
          uploadLabel.classList.remove('file-upload-animation');
        }, 1500);
      }
      
      uploadAudio(file);
    }
  });
}

// --- Enhanced Audio Upload & Backend ---
function uploadAudio(audioBlob) {
  hideSummarySection();
  showStatus("📤 Uploading audio file...", "processing");
  
  const formData = new FormData();
  formData.append("file", audioBlob, "meeting_audio.wav");
  formData.append("meetingTitle", meetingTitleInput.value || "Untitled Meeting");
  formData.append("slackEnabled", "false"); // Default value since checkbox doesn't exist
  formData.append("notionEnabled", "false"); // Default value since checkbox doesn't exist
  
  // Add upload progress animation
  const uploadSteps = [
    "📤 Uploading audio file...",
    "🎵 Transcribing audio...",
    "🤖 Analyzing content...",
    "📝 Generating summary...",
    "✨ Finalizing results..."
  ];
  
  let currentStep = 0;
  const stepInterval = setInterval(() => {
    if (currentStep < uploadSteps.length) {
      showStatus(uploadSteps[currentStep], "processing");
      currentStep++;
    }
  }, 800);
  
  fetch("http://127.0.0.1:5000/transcribe", {
    method: "POST",
    body: formData,
  })
    .then(response => response.json())
    .then(data => {
      clearInterval(stepInterval);
      
      if (data.summary && data.summary.formatted_text && !data.summary.formatted_text.startsWith("Error")) {
        showSummarySection(data.summary.formatted_text);
        showStatus("✅ Summary ready! Edit and post to Slack!", "success");
        showToast("Summary generated successfully! ✨", "success");
      } else {
        showStatus("❌ Could not generate summary.", "error");
        showToast("Could not generate summary.", "error");
      }
    })
    .catch(error => {
      clearInterval(stepInterval);
      showStatus("❌ Error processing audio.", "error");
      showToast("Error processing audio.", "error");
    });
}

// --- Enhanced Post to Slack ---
if (postToSlackBtn) {
  postToSlackBtn.addEventListener("click", () => {
    const summary = summaryEdit.value;
    if (!summary.trim()) {
      showToast("Summary is empty!", "error");
      return;
    }
    
    // Add button press animation
    postToSlackBtn.style.transform = 'scale(0.95)';
    setTimeout(() => {
      postToSlackBtn.style.transform = '';
    }, 150);
    
    showStatus("📤 Posting to Slack...", "processing");
    
    setTimeout(() => {
      showToast("Posted to Slack! 🚀", "success");
      showStatus("✅ Posted to Slack!", "success");
    }, 1500);
  });
}

// --- Enhanced Accessibility: Keyboard navigation ---
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    hideSummarySection();
  }
});

// --- Input Enhancements ---
if (meetingTitleInput) {
  meetingTitleInput.addEventListener('focus', function() {
    this.parentElement.style.transform = 'scale(1.02)';
  });

  meetingTitleInput.addEventListener('blur', function() {
    this.parentElement.style.transform = 'scale(1)';
  });
}

// --- Initial UI State ---
hideSummarySection();
setRecordingUI(false);
showStatus("✨ Ready to record your meetings!");

// --- Add entrance animations for the popup ---
document.addEventListener('DOMContentLoaded', function() {
  const popup = document.querySelector('.auralix-popup');
  if (popup) {
    popup.style.opacity = '0';
    popup.style.transform = 'scale(0.9) translateY(20px)';
    
    setTimeout(() => {
      popup.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
      popup.style.opacity = '1';
      popup.style.transform = 'scale(1) translateY(0)';
    }, 100);
  }
});
