// dashboard.js - VS Code friendly version

// Update date and time
function updateDateTime() {
    const now = new Date();
    const options = { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    };
    const dateTimeElement = document.getElementById('currentDateTime');
    if (dateTimeElement) {
        dateTimeElement.textContent = now.toLocaleDateString('en-US', options);
    }
}

// Calculate session uptime
const sessionStart = new Date();
function updateUptime() {
    const now = new Date();
    const diff = Math.floor((now - sessionStart) / 1000);
    const hours = Math.floor(diff / 3600);
    const minutes = Math.floor((diff % 3600) / 60);
    const seconds = diff % 60;
    
    const uptimeElement = document.getElementById('uptime');
    if (uptimeElement) {
        uptimeElement.textContent = 
            `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    }
}

// Set member since date
function setMemberSince(dateString) {
    const memberSinceElement = document.getElementById('memberSince');
    if (!memberSinceElement) return;
    
    try {
        let date;
        if (dateString) {
            date = new Date(dateString);
            if (isNaN(date.getTime())) {
                throw new Error('Invalid date');
            }
        } else {
            date = new Date();
        }
        
        memberSinceElement.textContent = date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    } catch (e) {
        memberSinceElement.textContent = new Date().toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }
}

// Check AI status
async function checkAIStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        const statusElement = document.querySelector('.ai-status');
        if (!statusElement) return;
        
        const icon = statusElement.querySelector('i');
        const text = statusElement.querySelector('span');
        
        if (data.ai_loaded) {
            icon.style.color = 'var(--secondary)';
            icon.className = 'fas fa-circle';
            text.textContent = 'AI Status: Online';
        } else {
            icon.style.color = 'var(--warning)';
            icon.className = 'fas fa-circle';
            text.textContent = 'AI Status: Loading...';
        }
    } catch (error) {
        console.error('Error checking AI status:', error);
        const statusElement = document.querySelector('.ai-status');
        if (statusElement) {
            const icon = statusElement.querySelector('i');
            const text = statusElement.querySelector('span');
            icon.style.color = 'var(--danger)';
            icon.className = 'fas fa-circle';
            text.textContent = 'AI Status: Offline';
        }
    }
}

// Load recent activity
async function loadRecentActivity() {
    try {
        const response = await fetch('/api/conversation');
        const conversations = await response.json();
        
        const activityList = document.getElementById('recentActivity');
        if (!activityList) return;
        
        if (conversations && conversations.length > 0) {
            activityList.innerHTML = '';
            
            // Get last 5 conversations
            const recent = conversations.slice(-5).reverse();
            
            recent.forEach(conv => {
                const activityItem = document.createElement('div');
                activityItem.className = 'activity-item';
                
                const time = new Date(conv.timestamp);
                const timeString = time.toLocaleTimeString('en-US', {
                    hour: '2-digit',
                    minute: '2-digit'
                });
                
                activityItem.innerHTML = `
                    <div class="activity-icon">
                        <i class="fas fa-comment"></i>
                    </div>
                    <div class="activity-details">
                        <div class="activity-title">You: ${conv.user.substring(0, 50)}${conv.user.length > 50 ? '...' : ''}</div>
                        <div class="activity-time">${time.toLocaleDateString()} at ${timeString}</div>
                    </div>
                `;
                
                activityList.appendChild(activityItem);
            });
        }
    } catch (error) {
        console.error('Error loading activity:', error);
    }
}

// Toggle sidebar on mobile
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.toggle('active');
    }
}

// Check mobile view
function checkMobile() {
    const menuToggle = document.querySelector('.menu-toggle');
    const sidebar = document.getElementById('sidebar');
    
    if (!menuToggle || !sidebar) return;
    
    if (window.innerWidth <= 768) {
        menuToggle.style.display = 'flex';
    } else {
        menuToggle.style.display = 'none';
        sidebar.classList.remove('active');
    }
}

// Initialize everything
function initDashboard(memberSinceDate) {
    updateDateTime();
    updateUptime();
    checkAIStatus();
    loadRecentActivity();
    setMemberSince(memberSinceDate);
    
    // Update time every second
    setInterval(updateDateTime, 1000);
    setInterval(updateUptime, 1000);
    setInterval(checkAIStatus, 5000);
    setInterval(loadRecentActivity, 30000);
    
    // Check mobile on load and resize
    checkMobile();
    window.addEventListener('resize', checkMobile);
}

// Export for global use
window.initDashboard = initDashboard;
window.toggleSidebar = toggleSidebar;