/**
 * Real Estate CRM - Main JavaScript Functions
 */

(function() {
    var currentDate = new Date();

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

        // Initialize AI autofill (property extract forms)
        initializeAIAutofill();

        console.log('Real Estate CRM initialized successfully');
    }

/**
 * AI text autofill for property forms. Sends CSRF when ENABLE_CSRF=1.
 */
function initializeAIAutofill() {
    const btn = document.getElementById('ai_autofill_btn');
    if (!btn) return;

    btn.addEventListener('click', async () => {
        const blobEl = document.getElementById('ai_blob');
        const status = document.getElementById('ai_autofill_status');
        const text = blobEl ? blobEl.value.trim() : '';

        if (!text) {
            if (status) {
                status.textContent = 'Please paste some text.';
                status.className = 'text-warning small';
            }
            return;
        }

        if (status) {
            status.textContent = 'Asking AI...';
            status.className = 'text-info small';
        }
        btn.disabled = true;

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content ||
                document.querySelector('input[name="csrf_token"]')?.value ||
                '';
            const headers = {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            };
            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            // Prefer Track A extract endpoint; fall back to legacy path if present.
            let res = await fetch('/properties/extract-from-text', {
                method: 'POST',
                headers: headers,
                credentials: 'same-origin',
                body: JSON.stringify({ text: text })
            });
            if (res.status === 404) {
                res = await fetch('/api/ai/parse/property', {
                    method: 'POST',
                    headers: headers,
                    credentials: 'same-origin',
                    body: JSON.stringify({ text: text })
                });
            }

            const payload = await res.json().catch(() => ({}));
            if (!res.ok) throw new Error(payload.error || 'Request failed');

            const d = payload.data || payload || {};
            const fieldMap = {
                title: 'title',
                address: 'address',
                price: 'sale_price',
                property_type: 'property_type',
                bedrooms: 'bedrooms',
                bathrooms: 'bathrooms',
                square_feet: 'square_feet',
                description: 'description',
                year_built: 'year_built',
                parking_spaces: 'parking_spaces',
                floors: 'floors',
                units: 'units',
                property_condition: 'property_condition',
                neighborhood: 'neighborhood',
                property_category: 'category',
                listing_type: 'listing_type',
                rahn: 'rahn',
                ejare: 'ejare'
            };

            Object.entries(fieldMap).forEach(([dataKey, fieldName]) => {
                if (d[dataKey] === null || d[dataKey] === undefined || d[dataKey] === '') return;
                const element = document.getElementById(fieldName) ||
                    document.querySelector(`[name="${fieldName}"]`);
                if (!element) return;
                element.value = d[dataKey];
                if (element.tagName === 'SELECT' || element.type === 'radio') {
                    element.dispatchEvent(new Event('change'));
                }
            });

            if (status) {
                const confidence = Math.round((payload.confidence || 0) * 100);
                status.textContent = `Autofilled (${confidence}% confidence)`;
                status.className = 'text-success small';
            }
        } catch (e) {
            if (status) {
                status.textContent = 'AI autofill failed. Please try again.';
                status.className = 'text-danger small';
            }
            console.error('AI Autofill error:', e);
        } finally {
            btn.disabled = false;
        }
    });
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    if (typeof bootstrap === 'undefined') return;
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
    if (!sidebar) return;
    const mainContent = document.querySelector('.main-content');

    // Mobile sidebar toggle
    if (window.innerWidth <= 768) {
        const sidebarToggle = document.createElement('button');
        sidebarToggle.className = 'btn btn-primary d-lg-none position-fixed';
        sidebarToggle.style.cssText = 'top:20px; left:20px; z-index:1001;';
        sidebarToggle.innerHTML = '<i class="fas fa-bars"></i>';

        sidebarToggle.addEventListener('click', function() {
            if (sidebar) sidebar.classList.toggle('show');
        });

        document.body.appendChild(sidebarToggle);

        // Close sidebar when clicking outside
        document.addEventListener('click', function(e) {
            if (sidebar && !sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                sidebar.classList.remove('show');
            }
        });
    }

    // Handle window resize
    window.addEventListener('resize', function() {
        if (sidebar && window.innerWidth > 768) {
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

    // Initialize Iranian property pricing system
    initializePropertyPricing();
}

/**
 * Format phone number input
 */
function formatPhoneNumber(e) {
    let value = e.target.value.replace(/\D/g, '');
    if (value.length >= 6) {
        value = value.replace(/(\d{3})(\d{3})(\d{4})/, '($1) $2-$3');
    } else if (value.length >= 3) {
        value = value.replace(/(\d{3})(\d{0,3})/, '$1 $2');
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
 * Initialize Iranian Property Pricing System
 */
function initializePropertyPricing() {
    const listingTypeRadios = document.querySelectorAll('input[name="listing_type"]');
    const salePricing = document.getElementById('sale-pricing');
    const rentalPricing = document.getElementById('rental-pricing');
    const squareFootInput = document.getElementById('square_feet');

    // Price input fields
    const salePriceInput = document.getElementById('sale_price');
    const rahnInput = document.getElementById('rahn');
    const ejareInput = document.getElementById('ejare');
    const salePricePerMeterInput = document.getElementById('sale_price_per_meter');
    const rahnPerMeterInput = document.getElementById('rahn_per_meter');
    const ejarePerMeterInput = document.getElementById('ejare_per_meter');

    if (!listingTypeRadios.length) return; // Only run on pages with property forms

    // Toggle pricing sections based on listing type
    function togglePricingSections() {
        const selectedType = document.querySelector('input[name="listing_type"]:checked').value;

        if (selectedType === 'sale') {
            salePricing.style.display = 'block';
            rentalPricing.style.display = 'none';

            // Make sale price required
            if (salePriceInput) salePriceInput.required = true;
            if (rahnInput) rahnInput.required = false;
            if (ejareInput) ejareInput.required = false;
        } else {
            salePricing.style.display = 'none';
            rentalPricing.style.display = 'block';

            // Make rental fields required
            if (salePriceInput) salePriceInput.required = false;
            if (rahnInput) rahnInput.required = true;
            if (ejareInput) ejareInput.required = true;
        }

        // Recalculate per-meter prices
        calculatePerMeterPrices();
    }

    // Calculate per-meter prices in real-time
    function calculatePerMeterPrices() {
        const squareMeters = parseFloat(squareFootInput?.value) || 0;

        if (squareMeters <= 0) {
            // Clear per-meter fields if no valid area
            if (salePricePerMeterInput) salePricePerMeterInput.value = '';
            if (rahnPerMeterInput) rahnPerMeterInput.value = '';
            if (ejarePerMeterInput) ejarePerMeterInput.value = '';
            return;
        }

        // Calculate sale price per meter
        if (salePriceInput && salePricePerMeterInput) {
            const salePrice = parseFloat(salePriceInput.value) || 0;
            if (salePrice > 0) {
                const pricePerMeter = (salePrice / squareMeters).toFixed(0);
                salePricePerMeterInput.value = `$${parseInt(pricePerMeter).toLocaleString()}/m²`;
            } else {
                salePricePerMeterInput.value = '';
            }
        }

        // Calculate rahn per meter
        if (rahnInput && rahnPerMeterInput) {
            const rahn = parseFloat(rahnInput.value) || 0;
            if (rahn > 0) {
                const rahnPerMeter = (rahn / squareMeters).toFixed(0);
                rahnPerMeterInput.value = `${parseInt(rahnPerMeter).toLocaleString()} تومان/متر`;
            } else {
                rahnPerMeterInput.value = '';
            }
        }

        // Calculate ejare per meter
        if (ejareInput && ejarePerMeterInput) {
            const ejare = parseFloat(ejareInput.value) || 0;
            if (ejare > 0) {
                const ejarePerMeter = (ejare / squareMeters).toFixed(0);
                ejarePerMeterInput.value = `${parseInt(ejarePerMeter).toLocaleString()} تومان/متر`;
            } else {
                ejarePerMeterInput.value = '';
            }
        }
    }

    // Add event listeners for listing type change
    listingTypeRadios.forEach(radio => {
        radio.addEventListener('change', togglePricingSections);
    });

    // Add event listeners for real-time calculation
    if (salePriceInput) {
        salePriceInput.addEventListener('input', calculatePerMeterPrices);
    }
    if (rahnInput) {
        rahnInput.addEventListener('input', calculatePerMeterPrices);
    }
    if (ejareInput) {
        ejareInput.addEventListener('input', calculatePerMeterPrices);
    }
    if (squareFootInput) {
        squareFootInput.addEventListener('input', calculatePerMeterPrices);
    }

    // Initialize on page load
    togglePricingSections();
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

    input.addEventListener('input', (e) => {
        searchFunction(e.target.value);
    });
}

/**
 * Export data to CSV
 */
function exportToCSV(data, filename) {
    const csv = convertToCSV(data);
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);

    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();

    URL.revokeObjectURL(url);
}

/**
 * Convert array of objects to CSV string
 */
function convertToCSV(data) {
    if (!data || data.length === 0) return '';

    const headers = Object.keys(data[0]);
    const csvContent = [
        headers.join(','),
        ...data.map(row => {
            return headers.map(header => {
                const value = row[header] || '';
                return `"${String(value).replace(/"/g, '""')}"`;
            }).join(',');
        })
    ].join('\n');

    return csvContent;
}

/**
 * Expose utilities globally
 */
window.CRM = {
    showNotification,
    confirmAction,
    formatAsCurrency,
    formatDate,
    datesBetween,
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
});