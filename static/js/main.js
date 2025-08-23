/**
 * Real Estate CRM - Main JavaScript Functions
 */

// Global variables
let currentDate = new Date();

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

/**
 * Initialize the application
 */
function initializeApp() {
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize responsive sidebar
    initializeSidebar();
    
    // Initialize form validation
    initializeFormValidation();
    
    // Initialize data tables
    initializeDataTables();
    
    // Initialize auto-refresh
    initializeAutoRefresh();
    
    console.log('Real Estate CRM initialized successfully');
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize responsive sidebar
 */
function initializeSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    
    // Mobile sidebar toggle
    if (window.innerWidth <= 768) {
        const sidebarToggle = document.createElement('button');
        sidebarToggle.className = 'btn btn-primary d-lg-none position-fixed';
        sidebarToggle.style.cssText = 'top: 20px; left: 20px; z-index: 1001;';
        sidebarToggle.innerHTML = '<i class="fas fa-bars"></i>';
        
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('show');
        });
        
        document.body.appendChild(sidebarToggle);
        
        // Close sidebar when clicking outside
        document.addEventListener('click', function(e) {
            if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                sidebar.classList.remove('show');
            }
        });
    }
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768) {
            sidebar.classList.remove('show');
        }
    });
}

/**
 * Initialize form validation
 */
function initializeFormValidation() {
    // Custom validation for all forms
    const forms = document.querySelectorAll('form[data-validate="true"]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                showNotification('Please fill in all required fields', 'error');
            }
            form.classList.add('was-validated');
        });
    });
    
    // Phone number formatting
    const phoneInputs = document.querySelectorAll('input[type="tel"]');
    phoneInputs.forEach(input => {
        input.addEventListener('input', formatPhoneNumber);
    });
    
    // Currency formatting
    const currencyInputs = document.querySelectorAll('input[data-type="currency"]');
    currencyInputs.forEach(input => {
        input.addEventListener('input', formatCurrency);
    });
}

/**
 * Format phone number input
 */
function formatPhoneNumber(e) {
    let value = e.target.value.replace(/\D/g, '');
    if (value.length >= 6) {
        value = value.replace(/(\d{3})(\d{3})(\d{4})/, '($1) $2-$3');
    } else if (value.length >= 3) {
        value = value.replace(/(\d{3})(\d{0,3})/, '($1) $2');
    }
    e.target.value = value;
}

/**
 * Format currency input
 */
function formatCurrency(e) {
    let value = e.target.value.replace(/[^\d]/g, '');
    if (value) {
        value = parseInt(value).toLocaleString();
        e.target.value = value;
    }
}

/**
 * Initialize data tables with sorting and pagination
 */
function initializeDataTables() {
    const tables = document.querySelectorAll('table[data-sortable="true"]');
    
    tables.forEach(table => {
        addTableSorting(table);
    });
}

/**
 * Add sorting functionality to table
 */
function addTableSorting(table) {
    const headers = table.querySelectorAll('th[data-sortable="true"]');
    
    headers.forEach((header, index) => {
        header.style.cursor = 'pointer';
        header.innerHTML += ' <i class="fas fa-sort text-muted"></i>';
        
        header.addEventListener('click', function() {
            sortTable(table, index);
        });
    });
}

/**
 * Sort table by column
 */
function sortTable(table, columnIndex) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const header = table.querySelectorAll('th')[columnIndex];
    
    const isAscending = !header.classList.contains('sort-asc');
    
    // Remove all sort classes
    table.querySelectorAll('th').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
        const icon = th.querySelector('i');
        if (icon) {
            icon.className = 'fas fa-sort text-muted';
        }
    });
    
    // Add sort class to current header
    header.classList.add(isAscending ? 'sort-asc' : 'sort-desc');
    const icon = header.querySelector('i');
    if (icon) {
        icon.className = `fas fa-sort-${isAscending ? 'up' : 'down'} text-primary`;
    }
    
    // Sort rows
    rows.sort((a, b) => {
        const aText = a.cells[columnIndex].textContent.trim();
        const bText = b.cells[columnIndex].textContent.trim();
        
        // Try to parse as numbers
        const aNum = parseFloat(aText.replace(/[^\d.-]/g, ''));
        const bNum = parseFloat(bText.replace(/[^\d.-]/g, ''));
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return isAscending ? aNum - bNum : bNum - aNum;
        }
        
        // String comparison
        return isAscending 
            ? aText.localeCompare(bText) 
            : bText.localeCompare(aText);
    });
    
    // Reappend sorted rows
    rows.forEach(row => tbody.appendChild(row));
}

/**
 * Initialize auto-refresh for dashboard
 */
function initializeAutoRefresh() {
    if (window.location.pathname === '/') {
        // Refresh dashboard stats every 5 minutes
        setInterval(() => {
            refreshDashboardStats();
        }, 300000);
    }
}

/**
 * Refresh dashboard statistics
 */
function refreshDashboardStats() {
    // This would typically make an AJAX call to refresh stats
    // For now, just show a subtle indication that data is fresh
    const statsCards = document.querySelectorAll('.card .h5');
    statsCards.forEach(card => {
        card.style.animation = 'pulse 1s ease-in-out';
        setTimeout(() => {
            card.style.animation = '';
        }, 1000);
    });
}

/**
 * Show notification to user
 */
function showNotification(message, type = 'info', duration = 5000) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    const icon = type === 'success' ? 'check-circle' : 
                 type === 'error' ? 'exclamation-triangle' : 
                 type === 'warning' ? 'exclamation-triangle' : 'info-circle';
    
    notification.innerHTML = `
        <i class="fas fa-${icon} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-dismiss after duration
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
}

/**
 * Confirm action with user
 */
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

/**
 * Format number as currency
 */
function formatAsCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

/**
 * Format date as readable string
 */
function formatDate(date, options = {}) {
    const defaultOptions = {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    };
    
    return new Date(date).toLocaleDateString('en-US', {...defaultOptions, ...options});
}

/**
 * Calculate days between two dates
 */
function daysBetween(date1, date2) {
    const oneDay = 24 * 60 * 60 * 1000;
    return Math.round((date2 - date1) / oneDay);
}

/**
 * Debounce function for search inputs
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Search and filter functionality
 */
function initializeSearch(inputSelector, itemsSelector, searchFields) {
    const searchInput = document.querySelector(inputSelector);
    if (!searchInput) return;
    
    const searchFunction = debounce((query) => {
        const items = document.querySelectorAll(itemsSelector);
        const lowerQuery = query.toLowerCase();
        
        items.forEach(item => {
            let match = false;
            searchFields.forEach(field => {
                const element = item.querySelector(field);
                if (element && element.textContent.toLowerCase().includes(lowerQuery)) {
                    match = true;
                }
            });
            
            item.style.display = match ? '' : 'none';
        });
    }, 300);
    
    searchInput.addEventListener('input', (e) => {
        searchFunction(e.target.value);
    });
}

/**
 * Export data to CSV
 */
function exportToCSV(data, filename) {
    const csv = convertToCSV(data);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    
    window.URL.revokeObjectURL(url);
}

/**
 * Convert array of objects to CSV string
 */
function convertToCSV(data) {
    if (!data || data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const csvContent = [
        headers.join(','),
        ...data.map(row => 
            headers.map(header => {
                const value = row[header] || '';
                return `"${String(value).replace(/"/g, '""')}"`;
            }).join(',')
        )
    ].join('\n');
    
    return csvContent;
}

/**
 * Local storage utilities
 */
const Storage = {
    set: function(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
        } catch (e) {
            console.warn('Failed to save to localStorage:', e);
        }
    },
    
    get: function(key, defaultValue = null) {
        try {
            const item = localStorage.getItem(key);
            return item ? JSON.parse(item) : defaultValue;
        } catch (e) {
            console.warn('Failed to read from localStorage:', e);
            return defaultValue;
        }
    },
    
    remove: function(key) {
        try {
            localStorage.removeItem(key);
        } catch (e) {
            console.warn('Failed to remove from localStorage:', e);
        }
    }
};

/**
 * API utility functions
 */
const API = {
    /**
     * Make HTTP request
     */
    request: async function(url, options = {}) {
        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    ...options.headers
                },
                ...options
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            return await response.text();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    },
    
    get: function(url, options = {}) {
        return this.request(url, { ...options, method: 'GET' });
    },
    
    post: function(url, data, options = {}) {
        return this.request(url, {
            ...options,
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    
    put: function(url, data, options = {}) {
        return this.request(url, {
            ...options,
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    
    delete: function(url, options = {}) {
        return this.request(url, { ...options, method: 'DELETE' });
    }
};

/**
 * Animation utilities
 */
const Animate = {
    fadeIn: function(element, duration = 300) {
        element.style.opacity = '0';
        element.style.display = 'block';
        
        const start = performance.now();
        const animate = (timestamp) => {
            const progress = Math.min((timestamp - start) / duration, 1);
            element.style.opacity = progress;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    },
    
    slideUp: function(element, duration = 300) {
        const height = element.offsetHeight;
        element.style.height = height + 'px';
        element.style.overflow = 'hidden';
        
        const start = performance.now();
        const animate = (timestamp) => {
            const progress = Math.min((timestamp - start) / duration, 1);
            element.style.height = (height * (1 - progress)) + 'px';
            
            if (progress >= 1) {
                element.style.display = 'none';
                element.style.height = '';
                element.style.overflow = '';
            } else {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    }
};

// Expose utilities globally
window.CRM = {
    showNotification,
    confirmAction,
    formatAsCurrency,
    formatDate,
    daysBetween,
    debounce,
    initializeSearch,
    exportToCSV,
    Storage,
    API,
    Animate
};

// Error handling
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    showNotification('An error occurred. Please refresh the page if problems persist.', 'error');
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    showNotification('A network error occurred. Please check your connection.', 'error');
});

console.log('Real Estate CRM JavaScript loaded successfully');
