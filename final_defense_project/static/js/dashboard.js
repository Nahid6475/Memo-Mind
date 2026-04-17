// Dashboard JavaScript with Charts
let charts = {};

// Show notification
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = 'toast-notification';
    notification.style.background = type === 'success' ? '#10b981' : '#ef4444';
    notification.innerText = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Load dashboard data
async function loadDashboardData() {
    try {
        const response = await fetch('/api/dashboard_stats');
        const data = await response.json();
        
        if (data.error) {
            window.location.href = '/';
            return;
        }
        
        // Update stats cards
        document.getElementById('totalMemories').innerText = data.total_memories || 0;
        document.getElementById('totalConversations').innerText = data.total_conversations || 0;
        document.getElementById('currentStreak').innerText = data.current_streak || 0;
        
        // Calculate weekly average
        const weeklyTotal = Object.values(data.last_7_days || {}).reduce((a, b) => a + b, 0);
        const weeklyAvg = Math.round(weeklyTotal / 7) || 0;
        document.getElementById('weeklyAvg').innerText = weeklyAvg;
        
        // Create all charts
        createWeeklyChart(data.last_7_days || {});
        createIntentChart(data.intent_breakdown || {});
        createKeywordsChart(data.top_keywords || {});
        createHourlyChart(data.hourly_activity || Array(24).fill(0));
        createWeeklyPatternChart(data.weekly_activity || { days: ['সোম', 'মঙ্গল', 'বুধ', 'বৃহস্পতি', 'শুক্র', 'শনি', 'রবি'], counts: [0,0,0,0,0,0,0] });
        createTrendChart(data.memory_trend || {});
        createFileTypeChart(data.file_types || {});
        
        showNotification(`📊 Dashboard লোড হয়েছে! ${data.total_memories}টি মেমরি`, 'success');
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showNotification('ড্যাশবোর্ড লোড করতে ব্যর্থ!', 'error');
    }
}

// Chart 1: Last 7 Days Activity
function createWeeklyChart(data) {
    const ctx = document.getElementById('weeklyChart').getContext('2d');
    const days = Object.keys(data);
    const values = Object.values(data);
    
    if (charts.weekly) charts.weekly.destroy();
    
    charts.weekly = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: days.length ? days : ['সোম', 'মঙ্গল', 'বুধ', 'বৃহস্পতি', 'শুক্র', 'শনি', 'রবি'],
            datasets: [{
                label: 'মেমরি সংখ্যা',
                data: values.length ? values : [0, 0, 0, 0, 0, 0, 0],
                backgroundColor: 'rgba(102, 126, 234, 0.7)',
                borderColor: '#667eea',
                borderWidth: 1,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'top' },
                tooltip: { callbacks: { label: (ctx) => `${ctx.raw}টি মেমরি` } }
            }
        }
    });
}

// Chart 2: Intent Distribution (Pie Chart)
function createIntentChart(data) {
    const ctx = document.getElementById('intentChart').getContext('2d');
    const labels = Object.keys(data);
    const values = Object.values(data);
    const colors = ['#667eea', '#764ba2', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6', '#06b6d4'];
    
    if (charts.intent) charts.intent.destroy();
    
    if (labels.length === 0) {
        charts.intent = new Chart(ctx, {
            type: 'pie',
            data: { labels: ['কোনো ডাটা নেই'], datasets: [{ data: [1], backgroundColor: ['#e2e8f0'] }] },
            options: { responsive: true }
        });
        return;
    }
    
    charts.intent = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'right' },
                tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${ctx.raw} বার` } }
            }
        }
    });
}

// Chart 3: Top Keywords (Bar Chart)
function createKeywordsChart(data) {
    const ctx = document.getElementById('keywordsChart').getContext('2d');
    const keywords = Object.keys(data).slice(0, 8);
    const counts = Object.values(data).slice(0, 8);
    
    if (charts.keywords) charts.keywords.destroy();
    
    if (keywords.length === 0) {
        charts.keywords = new Chart(ctx, {
            type: 'bar',
            data: { labels: ['কোনো কীওয়ার্ড নেই'], datasets: [{ data: [0], backgroundColor: '#e2e8f0' }] },
            options: { responsive: true }
        });
        return;
    }
    
    charts.keywords = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: keywords,
            datasets: [{
                label: 'ব্যবহারের সংখ্যা',
                data: counts,
                backgroundColor: 'rgba(245, 158, 11, 0.7)',
                borderColor: '#f59e0b',
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { position: 'top' }
            }
        }
    });
}

// Chart 4: Hourly Activity (Line Chart)
function createHourlyChart(data) {
    const ctx = document.getElementById('hourlyChart').getContext('2d');
    const hours = Array.from({length: 24}, (_, i) => `${i}:00`);
    
    if (charts.hourly) charts.hourly.destroy();
    
    charts.hourly = new Chart(ctx, {
        type: 'line',
        data: {
            labels: hours,
            datasets: [{
                label: 'কথোপকথন সংখ্যা',
                data: data,
                borderColor: '#8b5cf6',
                backgroundColor: 'rgba(139, 92, 246, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 3,
                pointBackgroundColor: '#8b5cf6'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                tooltip: { callbacks: { label: (ctx) => `${ctx.raw}টি মেসেজ` } }
            },
            scales: {
                x: { title: { display: true, text: 'ঘন্টা' } },
                y: { title: { display: true, text: 'কার্যকলাপ' }, beginAtZero: true }
            }
        }
    });
}

// Chart 5: Weekly Pattern
function createWeeklyPatternChart(data) {
    const ctx = document.getElementById('weeklyPatternChart').getContext('2d');
    
    if (charts.weeklyPattern) charts.weeklyPattern.destroy();
    
    charts.weeklyPattern = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.days,
            datasets: [{
                label: 'কার্যকলাপ',
                data: data.counts,
                backgroundColor: 'rgba(16, 185, 129, 0.7)',
                borderColor: '#10b981',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                tooltip: { callbacks: { label: (ctx) => `${ctx.raw}টি কার্যকলাপ` } }
            }
        }
    });
}

// Chart 6: Memory Growth Trend
function createTrendChart(data) {
    const ctx = document.getElementById('trendChart').getContext('2d');
    const dates = Object.keys(data);
    const counts = Object.values(data);
    
    if (charts.trend) charts.trend.destroy();
    
    if (dates.length === 0) {
        charts.trend = new Chart(ctx, {
            type: 'line',
            data: { labels: ['কোনো ডাটা নেই'], datasets: [{ data: [0], borderColor: '#e2e8f0' }] },
            options: { responsive: true }
        });
        return;
    }
    
    charts.trend = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: 'মেমরি তৈরি',
                data: counts,
                borderColor: '#ef4444',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 4,
                pointBackgroundColor: '#ef4444'
            }]
        },
        options: {
            responsive: true,
            plugins: {
                tooltip: { callbacks: { label: (ctx) => `${ctx.raw}টি মেমরি` } }
            },
            scales: {
                x: { title: { display: true, text: 'তারিখ' } },
                y: { title: { display: true, text: 'মেমরি সংখ্যা' }, beginAtZero: true }
            }
        }
    });
}

// Chart 7: File Type Distribution
function createFileTypeChart(data) {
    const ctx = document.getElementById('fileTypeChart').getContext('2d');
    const types = Object.keys(data);
    const counts = Object.values(data);
    const colors = ['#06b6d4', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#ef4444'];
    
    if (charts.fileType) charts.fileType.destroy();
    
    if (types.length === 0) {
        charts.fileType = new Chart(ctx, {
            type: 'doughnut',
            data: { labels: ['কোনো ফাইল সার্চ করা হয়নি'], datasets: [{ data: [1], backgroundColor: ['#e2e8f0'] }] },
            options: { responsive: true }
        });
        return;
    }
    
    charts.fileType = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: types,
            datasets: [{
                data: counts,
                backgroundColor: colors.slice(0, types.length),
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'right' },
                tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${ctx.raw} বার` } }
            }
        }
    });
}

// Dark Mode Toggle
function initDarkMode() {
    const toggle = document.getElementById('themeToggle');
    if (!toggle) return;
    
    // Check saved preference
    if (localStorage.getItem('darkMode') === 'true') {
        document.body.classList.add('dark-mode');
        toggle.innerHTML = '☀️';
    }
    
    toggle.onclick = () => {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        toggle.innerHTML = isDark ? '☀️' : '🌙';
        localStorage.setItem('darkMode', isDark);
        showNotification(isDark ? 'ডার্ক মোড চালু' : 'লাইট মোড চালু');
    };
}

// Real-time notifications
function setupRealTimeNotifications() {
    let lastMemoryCount = parseInt(document.getElementById('totalMemories').innerText);
    
    setInterval(async () => {
        try {
            const response = await fetch('/api/dashboard_stats');
            const data = await response.json();
            const newCount = data.total_memories;
            
            if (newCount > lastMemoryCount) {
                showNotification(`📝 নতুন মেমরি সংরক্ষণ করা হয়েছে! (${newCount - lastMemoryCount}টি নতুন)`);
                lastMemoryCount = newCount;
                document.getElementById('totalMemories').innerText = newCount;
            }
        } catch(e) {}
    }, 30000);
}

// Logout function
document.getElementById('logoutBtn')?.addEventListener('click', async () => {
    await fetch('/api/logout', { method: 'POST' });
    window.location.href = '/';
});

// Get username
async function getUserName() {
    try {
        const response = await fetch('/api/check_session');
        const data = await response.json();
        if (data.logged_in) {
            document.getElementById('userName').innerText = data.user.username;
        } else {
            window.location.href = '/';
        }
    } catch(e) {
        window.location.href = '/';
    }
}

// Initialize dashboard
getUserName();
loadDashboardData();
initDarkMode();
setupRealTimeNotifications();