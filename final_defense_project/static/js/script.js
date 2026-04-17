// ==================== DOM ELEMENTS ====================
let currentUser = null;
const chatArea = document.getElementById('chatArea');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');

// ==================== ADD MESSAGE ====================
function addMessage(sender, text, link = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender === 'user' ? 'user-message' : 'bot-message'}`;
    
    const bubble = document.createElement('div');
    bubble.className = `bubble ${sender === 'user' ? 'user-bubble' : 'bot-bubble'}`;
    bubble.innerHTML = text.replace(/\n/g, '<br>');
    
    if (link) {
        const linkEl = document.createElement('a');
        linkEl.href = link;
        linkEl.target = '_blank';
        linkEl.style.display = 'inline-block';
        linkEl.style.marginTop = '8px';
        linkEl.style.color = '#667eea';
        linkEl.style.textDecoration = 'none';
        linkEl.innerHTML = '🔗 লিংক খুলুন';
        bubble.appendChild(document.createElement('br'));
        bubble.appendChild(linkEl);
    }
    
    const timeSpan = document.createElement('div');
    timeSpan.className = 'time';
    timeSpan.innerText = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    
    messageDiv.appendChild(bubble);
    messageDiv.appendChild(timeSpan);
    chatArea.appendChild(messageDiv);
    chatArea.scrollTop = chatArea.scrollHeight;
}

// ==================== SEND MESSAGE ====================
async function sendMessage() {
    const text = messageInput.value.trim();
    if (!text) return;
    
    addMessage('user', text);
    messageInput.value = '';
    
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot-message';
    typingDiv.id = 'typingIndicator';
    typingDiv.innerHTML = '<div class="bubble bot-bubble">🤔 ভাবছি...</div>';
    chatArea.appendChild(typingDiv);
    chatArea.scrollTop = chatArea.scrollHeight;
    
    try {
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: text })
        });
        const data = await response.json();
        
        document.getElementById('typingIndicator')?.remove();
        addMessage('bot', data.response, data.link);
    } catch (error) {
        document.getElementById('typingIndicator')?.remove();
        addMessage('bot', '❌ দুঃখিত, সার্ভার সমস্যা হচ্ছে। আবার চেষ্টা করুন।');
    }
}

// ==================== VOICE ANIMATION (Clean - No Icons, No Background) ====================
let recognition = null;
let isListening = false;
let submitTimer = null;
let finalText = '';
let animationInterval = null;

// Beautiful animation frames (only symbols)
const animationFrames = ['( •', '။၊', '||၊', '|။', '||||', '။‌‌‌', '၊|', '• )'];
let frameIndex = 0;
let animationMessageDiv = null;

function showVoiceAnimation() {
    // Remove existing animation if any
    if (animationMessageDiv) {
        animationMessageDiv.remove();
    }

    // Create new animation message
    animationMessageDiv = document.createElement('div');
    animationMessageDiv.className = 'message bot-message';
    animationMessageDiv.id = 'voiceAnimation';

    const bubble = document.createElement('div');
    bubble.className = 'bubble bot-bubble';
    bubble.style.textAlign = 'center';
    bubble.style.padding = '12px 20px';
    bubble.style.display = 'inline-block';
    bubble.style.width = 'auto';
    bubble.style.minWidth = '120px';
    bubble.id = 'animationBubble';

    // Only the animation text - no icons, no background color (inherits from bot-bubble)
    const animText = document.createElement('span');
    animText.id = 'animText';
    animText.style.fontSize = '18px';
    animText.style.fontFamily = 'monospace';
    animText.style.letterSpacing = '3px';
    animText.style.fontWeight = '500';
    animText.style.display = 'inline-block';
    animText.innerHTML = '( •';

    bubble.appendChild(animText);

    const timeSpan = document.createElement('div');
    timeSpan.className = 'time';
    timeSpan.innerText = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});

    animationMessageDiv.appendChild(bubble);
    animationMessageDiv.appendChild(timeSpan);
    chatArea.appendChild(animationMessageDiv);
    chatArea.scrollTop = chatArea.scrollHeight;

    // Add wave animation CSS
    const style = document.createElement('style');
    style.id = 'voiceAnimStyle';
    if (!document.getElementById('voiceAnimStyle')) {
        style.textContent = `
            @keyframes waveAnimation {
                0% { letter-spacing: 3px; opacity: 0.7; }
                50% { letter-spacing: 8px; opacity: 1; }
                100% { letter-spacing: 3px; opacity: 0.7; }
            }
            .wave-effect {
                animation: waveAnimation 0.6s ease-in-out;
            }
        `;
        document.head.appendChild(style);
    }

    // Start frame animation
    frameIndex = 0;
    if (animationInterval) clearInterval(animationInterval);

    animationInterval = setInterval(() => {
        const animTextEl = document.getElementById('animText');
        if (animTextEl) {
            frameIndex = (frameIndex + 1) % animationFrames.length;
            animTextEl.innerHTML = animationFrames[frameIndex];
            // Add wave effect
            animTextEl.classList.add('wave-effect');
            setTimeout(() => {
                if (animTextEl) animTextEl.classList.remove('wave-effect');
            }, 600);
        }
    }, 400);
}

function hideVoiceAnimation() {
    if (animationInterval) {
        clearInterval(animationInterval);
        animationInterval = null;
    }
    if (animationMessageDiv) {
        animationMessageDiv.remove();
        animationMessageDiv = null;
    }
}

// ==================== VOICE RECOGNITION ====================
if ('webkitSpeechRecognition' in window) {
    recognition = new webkitSpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'bn-IN';

    recognition.onstart = function() {
        isListening = true;
        finalText = '';
        const voiceBtn = document.getElementById('voiceBtn');
        voiceBtn.style.background = "#ef4444";
        voiceBtn.innerHTML = "🔴";
        voiceBtn.style.transform = "scale(1.05)";

        // Show clean animation
        showVoiceAnimation();
    };

    recognition.onend = function() {
        isListening = false;
        const voiceBtn = document.getElementById('voiceBtn');
        voiceBtn.style.background = "linear-gradient(135deg, #10b981, #059669)";
        voiceBtn.innerHTML = "🎤";
        voiceBtn.style.transform = "scale(1)";

        // Hide animation
        hideVoiceAnimation();

        if (finalText) {
            messageInput.value = finalText;
            addMessage('bot', `🎤 আপনি বলেছেন: "${finalText}"\n\n✅ 2 সেকেন্ড পর自动 পাঠানো হবে...`);

            if (submitTimer) clearTimeout(submitTimer);
            submitTimer = setTimeout(() => {
                if (messageInput.value.trim()) {
                    sendMessage();
                }
            }, 2000);
        } else {
            addMessage('bot', '❌ কোনো কথা শুনতে পাইনি। আবার চেষ্টা করুন။');
        }
    };

    recognition.onresult = function(event) {
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript;
            }
        }

        if (finalTranscript) {
            finalText = finalTranscript;
        }

        if (submitTimer) {
            clearTimeout(submitTimer);
            submitTimer = null;
        }
    };

    recognition.onerror = function(event) {
        console.error('Speech error:', event.error);
        const voiceBtn = document.getElementById('voiceBtn');
        voiceBtn.style.background = "linear-gradient(135deg, #10b981, #059669)";
        voiceBtn.innerHTML = "🎤";
        voiceBtn.style.transform = "scale(1)";
        isListening = false;

        hideVoiceAnimation();

        if (submitTimer) {
            clearTimeout(submitTimer);
            submitTimer = null;
        }

        if (event.error === 'not-allowed') {
            addMessage('bot', '❌ মাইক ব্যবহারের অনুমতি দিন। ব্রাউজারের সেটিংস থেকে মাইক অন করুন।');
        } else if (event.error === 'no-speech') {
            addMessage('bot', '❌ কোনো কথা শুনতে পাইনি। আবার চেষ্টা করুন।');
        }
    };
}

const voiceBtn = document.getElementById('voiceBtn');
if (voiceBtn && recognition) {
    voiceBtn.addEventListener('click', () => {
        if (isListening) {
            recognition.stop();
        } else {
            try {
                recognition.start();
            } catch(e) {
                console.log('Start error:', e);
                addMessage('bot', '❌ মাইক শুরু করতে ব্যর্থ। পৃষ্ঠা রিফ্রেশ করুন।');
            }
        }
    });
} else if (voiceBtn) {
    voiceBtn.disabled = true;
    voiceBtn.style.opacity = "0.5";
    voiceBtn.title = "ভয়েস ফিচার সাপোর্ট করে না। Chrome ব্যবহার করুন।";
}

messageInput.addEventListener('input', () => {
    if (submitTimer) {
        clearTimeout(submitTimer);
        submitTimer = null;
    }
});

sendBtn.addEventListener('click', () => {
    if (submitTimer) {
        clearTimeout(submitTimer);
        submitTimer = null;
    }
});

// ==================== EVENT LISTENERS ====================
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

document.querySelectorAll('.feature-card').forEach(card => {
    card.addEventListener('click', () => {
        const cmd = card.dataset.command;
        if (cmd === 'মনে রাখো') {
            messageInput.value = 'মনে রাখো ';
        } else if (cmd === 'মনে করে দাও') {
            messageInput.value = 'মনে করে দাও ';
        } else if (cmd === 'গুগল সার্চ করো') {
            messageInput.value = 'গুগল সার্চ করো ';
        } else if (cmd === 'ইউটিউব') {
            messageInput.value = 'ইউটিউব ';
        } else if (cmd === 'ফাইল বের করে দাও') {
            messageInput.value = 'ফাইল বের করে দাও ';
        } else if (cmd === 'অ্যালার্ম সেট করো সকাল ৮টা') {
            messageInput.value = 'অ্যালার্ম সেট করো ';
        } else if (cmd === 'মনে করে দাও সকালের medicine') {
            messageInput.value = 'মনে করে দাও সকালের medicine';
        } else {
            messageInput.value = cmd;
        }
        messageInput.focus();
    });
});

// ==================== MEDICINE REMINDER ====================
const medicineBtn = document.getElementById('medicineReminderBtn');
const medicineModal = document.getElementById('medicineModal');
const closeMedicineBtn = document.getElementById('closeMedicineBtn');
const saveMedicineBtn = document.getElementById('saveMedicineBtn');

if (medicineBtn) {
    medicineBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/api/get_medicines');
            const data = await response.json();
            if (data.success && data.medicines) {
                document.getElementById('morningMedicine').value = data.medicines.morning || '';
                document.getElementById('afternoonMedicine').value = data.medicines.afternoon || '';
                document.getElementById('nightMedicine').value = data.medicines.night || '';
            }
        } catch(e) {}
        medicineModal.style.display = 'flex';
    });
}

if (closeMedicineBtn) {
    closeMedicineBtn.addEventListener('click', () => {
        medicineModal.style.display = 'none';
    });
}

if (saveMedicineBtn) {
    saveMedicineBtn.addEventListener('click', async () => {
        const morning = document.getElementById('morningMedicine').value;
        const afternoon = document.getElementById('afternoonMedicine').value;
        const night = document.getElementById('nightMedicine').value;

        try {
            const response = await fetch('/api/save_medicines', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ morning, afternoon, night })
            });
            const data = await response.json();
            alert(data.message);
            medicineModal.style.display = 'none';
        } catch(e) {
            alert('Medicine সংরক্ষণ করতে ব্যর্থ!');
        }
    });
}

// ==================== AUTHENTICATION ====================
async function checkSession() {
    try {
        const response = await fetch('/api/check_session');
        const data = await response.json();
        if (data.logged_in) {
            currentUser = data.user;
            document.getElementById('loginBtn').style.display = 'none';
            document.getElementById('registerBtn').style.display = 'none';
            document.getElementById('logoutBtn').style.display = 'block';
            document.getElementById('userInfo').style.display = 'flex';
            document.getElementById('userName').innerText = currentUser.username;
        }
    } catch(e) {}
}

document.getElementById('loginBtn').onclick = () => {
    document.getElementById('loginModal').style.display = 'flex';
};

document.getElementById('registerBtn').onclick = () => {
    document.getElementById('registerModal').style.display = 'flex';
};

document.getElementById('closeLoginBtn').onclick = () => {
    document.getElementById('loginModal').style.display = 'none';
};

document.getElementById('closeRegisterBtn').onclick = () => {
    document.getElementById('registerModal').style.display = 'none';
};

document.getElementById('confirmLoginBtn').onclick = async () => {
    const username = document.getElementById('loginUser').value;
    const password = document.getElementById('loginPass').value;

    const response = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    const data = await response.json();
    alert(data.message);
    if (data.success) location.reload();
};

document.getElementById('confirmRegisterBtn').onclick = async () => {
    const username = document.getElementById('regUser').value;
    const password = document.getElementById('regPass').value;

    const response = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });
    const data = await response.json();
    alert(data.message);
    if (data.success) {
        document.getElementById('registerModal').style.display = 'none';
    }
};

document.getElementById('logoutBtn').onclick = async () => {
    await fetch('/api/logout', { method: 'POST' });
    location.reload();
};

window.onclick = (e) => {
    if (e.target === document.getElementById('loginModal')) {
        document.getElementById('loginModal').style.display = 'none';
    }
    if (e.target === document.getElementById('registerModal')) {
        document.getElementById('registerModal').style.display = 'none';
    }
    if (e.target === medicineModal) {
        medicineModal.style.display = 'none';
    }
};

async function checkMicrophone() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach(track => track.stop());
        console.log('Microphone permission granted');
    } catch (err) {
        console.log('Microphone permission denied:', err);
        addMessage('bot', '⚠️ মাইক ব্যবহারের অনুমতি দিন। ব্রাউজারের অ্যাড্রেস বারে 🔒 আইকনে ক্লিক করে মাইক অন করুন।');
    }
}

if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    checkMicrophone();
}

checkSession();