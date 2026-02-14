// chat.js
let socket = null;
let isVoiceEnabled = false;
let isListening = false;
let currentRecognition = null;

// Initialize WebSocket connection
function initializeChat() {
    // Connect to WebSocket server
    socket = io();
    
    socket.on('connect', function() {
        console.log('Connected to server');
        updateStatus('online', 'Connected');
    });
    
    socket.on('disconnect', function() {
        console.log('Disconnected from server');
        updateStatus('offline', 'Disconnected');
    });
    
    socket.on('typing', function(data) {
        const typingIndicator = document.getElementById('typingIndicator');
        if (data.status) {
            typingIndicator.classList.add('visible');
        } else {
            typingIndicator.classList.remove('visible');
        }
    });
    
    socket.on('chat_response', function(data) {
        addMessage(data.assistant, false, data.mood, data.timestamp);
    });
    
    socket.on('action', function(data) {
        showActionNotification(data);
    });
    
    socket.on('error', function(data) {
        showError(data.message);
    });
    
    // Set up message input
    const messageInput = document.getElementById('messageInput');
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Load initial status
    checkSystemStatus();
}

// Update connection status
function updateStatus(status, text) {
    const indicator = document.getElementById('aiStatusIndicator');
    const textElement = document.getElementById('aiStatusText');
    
    indicator.className = `status-indicator ${status}`;
    textElement.textContent = text;
}

// Send message
async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Disable send button and clear input
    const sendBtn = document.getElementById('sendBtn');
    sendBtn.disabled = true;
    
    // Add user message to chat
    addMessage(message, true);
    input.value = '';
    autoResize(input);
    
    try {
        // Send via REST API
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: message })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            if (data.type === 'action') {
                showActionNotification(data);
                addMessage(data.response, false);
            } else {
                addMessage(data.response, false, data.mood, data.timestamp);
            }
        } else {
            showError(data.error || 'Unknown error');
        }
    } catch (error) {
        showError(`Connection error: ${error.message}`);
    } finally {
        sendBtn.disabled = false;
        input.focus();
    }
}

// Add message to chat UI
function addMessage(text, isUser = false, mood = null, timestamp = null) {
    const chatMessages = document.getElementById('chatMessages');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'bot'}`;
    
    const time = timestamp ? new Date(timestamp) : new Date();
    const timeString = time.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    
    messageDiv.innerHTML = `
        <div class="avatar">
            <i class="fas fa-${isUser ? 'user' : 'robot'}"></i>
        </div>
        <div class="message-content">
            <div class="message-text">${formatMessage(text)}</div>
            <div class="message-time">
                ${timeString}
                ${mood ? ` • Mood: ${mood}` : ''}
            </div>
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

// Format message with line breaks
function formatMessage(text) {
    return text.replace(/\n/g, '<br>');
}

// Scroll to bottom of chat
function scrollToBottom() {
    const chatMessages = document.getElementById('chatMessages');
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Clear chat
function clearChat() {
    if (confirm('Are you sure you want to clear all messages?')) {
        const chatMessages = document.getElementById('chatMessages');
        chatMessages.innerHTML = `
            <div class="message bot">
                <div class="avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">
                    <div class="message-text">
                        Chat cleared. How can I help you?
                    </div>
                    <div class="message-time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                </div>
            </div>
        `;
        
        // Also clear server-side conversation if needed
        fetch('/api/clear', { method: 'POST' });
    }
}

// Toggle voice
function toggleVoice() {
    isVoiceEnabled = !isVoiceEnabled;
    const voiceIcon = document.getElementById('voiceIcon');
    
    if (isVoiceEnabled) {
        voiceIcon.className = 'fas fa-volume-up';
        showNotification('Voice enabled');
    } else {
        voiceIcon.className = 'fas fa-volume-mute';
        showNotification('Voice disabled');
    }
}

// Voice input functions
function toggleVoiceInput() {
    const modal = document.getElementById('voiceModal');
    modal.classList.add('visible');
}

function closeVoiceModal() {
    const modal = document.getElementById('voiceModal');
    modal.classList.remove('visible');
    stopVoiceRecognition();
}

function startVoiceRecognition() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        showError('Speech recognition not supported in this browser');
        return;
    }
    
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    
    recognition.onstart = function() {
        isListening = true;
        document.getElementById('voiceStartBtn').classList.add('listening');
        document.getElementById('voiceStartBtn').innerHTML = '<i class="fas fa-stop"></i> Stop Listening';
        document.getElementById('voiceStatusText').textContent = 'Listening... Speak now!';
    };
    
    recognition.onresult = function(event) {
        let transcript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }
        document.getElementById('voiceTranscript').textContent = transcript;
    };
    
    recognition.onend = function() {
        isListening = false;
        document.getElementById('voiceStartBtn').classList.remove('listening');
        document.getElementById('voiceStartBtn').innerHTML = '<i class="fas fa-microphone"></i> Start Listening';
        document.getElementById('voiceStatusText').textContent = 'Click the microphone and start speaking...';
        
        const transcript = document.getElementById('voiceTranscript').textContent;
        if (transcript.trim()) {
            document.getElementById('messageInput').value = transcript;
            closeVoiceModal();
            sendMessage();
        }
    };
    
    recognition.onerror = function(event) {
        showError('Speech recognition error: ' + event.error);
    };
    
    currentRecognition = recognition;
    recognition.start();
}

function stopVoiceRecognition() {
    if (currentRecognition && isListening) {
        currentRecognition.stop();
    }
}

// System status check
async function checkSystemStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if (data.ai_initialized) {
            updateStatus('online', 'Ready');
        } else {
            updateStatus('offline', 'AI Initializing...');
        }
        
        // Update voice status
        const voiceIcon = document.getElementById('voiceIcon');
        if (data.voice_enabled) {
            isVoiceEnabled = true;
            voiceIcon.className = 'fas fa-volume-up';
        } else {
            voiceIcon.className = 'fas fa-volume-mute';
            voiceIcon.title = 'Voice not available';
        }
    } catch (error) {
        console.error('Error checking status:', error);
        updateStatus('offline', 'Cannot connect to server');
    }
}

// Show action notification
function showActionNotification(data) {
    let message = '';
    
    switch (data.action) {
        case 'youtube':
            message = 'Playing YouTube video...';
            break;
        case 'open_url':
            message = 'Opening browser...';
            break;
        case 'open_app':
            message = 'Opening application...';
            break;
        default:
            message = 'Action performed';
    }
    
    showNotification(message);
}

// Show notification
function showNotification(message) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #10b981, #059669);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

// Show error
function showError(message) {
    const notification = document.createElement('div');
    notification.className = 'error-notification';
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #ef4444, #dc2626);
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 5000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);