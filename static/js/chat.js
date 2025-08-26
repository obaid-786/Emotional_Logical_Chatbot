// Chat functionality
async function sendMessage() {
    const userInput = document.getElementById('user-input');
    const message = userInput.value.trim();

    if (message) {
        // Add user message to chat
        addMessageToChat(message, 'user');
        userInput.value = '';

        try {
            const typingIndicator = addTypingIndicator();

            // Send message to backend - ADD PROPER HEADERS
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ message: message })
            });

            // Remove typing indicator
            if (typingIndicator) {
                typingIndicator.remove();
            }

            // Check if response is OK first
            if (!response.ok) {
                // Try to get error message from response
                const errorText = await response.text();
                throw new Error(`Server error: ${response.status} - ${errorText}`);
            }

            // Now parse as JSON
            const data = await response.json();

            if (data.error) {
                addMessageToChat(data.error, 'bot');
            } else {
                addMessageToChat(data.response, 'bot');
            }
        } catch (error) {
            console.error('Error:', error);
            addMessageToChat('Sorry, I encountered an error. Please try again.', 'bot');
        }
    }
}

function addMessageToChat(message, sender) {
    const chatMessages = document.getElementById('chat-messages');
    const messageElement = document.createElement('div');
    messageElement.classList.add('message');
    messageElement.classList.add(sender === 'user' ? 'user-message' : 'bot-message');
    messageElement.textContent = message;
    chatMessages.appendChild(messageElement);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return messageElement;
}

function addTypingIndicator() {
    const chatMessages = document.getElementById('chat-messages');
    const typingElement = document.createElement('div');
    typingElement.classList.add('message', 'bot-message');
    typingElement.id = 'typing-indicator';
    typingElement.innerHTML = '<i class="fas fa-circle"></i><i class="fas fa-circle"></i><i class="fas fa-circle"></i>';
    chatMessages.appendChild(typingElement);

    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;

    return typingElement;
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

// Add a health check function
async function checkAPIHealth() {
    try {
        const response = await fetch('/api/health');
        const data = await response.json();

        if (!data.api_accessible) {
            addMessageToChat('Warning: Unable to connect to the AI service. Please check your internet connection.', 'bot');
        }
    } catch (error) {
        console.error('Health check failed:', error);
    }
}

// Call health check when page loads
window.addEventListener('load', checkAPIHealth);

// Modal functionality
function openLoginModal() {
    document.getElementById('login-modal').style.display = 'flex';
}

function closeLoginModal() {
    document.getElementById('login-modal').style.display = 'none';
}

// Google login simulation
function loginWithGoogle() {
    alert('In a real implementation, this would redirect to Google OAuth login.');
    closeLoginModal();
}

// Smooth scrolling
function scrollToChat() {
    document.querySelector('.chat-container').scrollIntoView({
        behavior: 'smooth'
    });
}

// Close modal if clicked outside
window.onclick = function(event) {
    const modal = document.getElementById('login-modal');
    if (event.target === modal) {
        closeLoginModal();
    }
}