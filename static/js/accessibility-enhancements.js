/**
 * Accessibility and Responsive Design Enhancements
 * Real Estate CRM System
 */

class AccessibilityEnhancements {
    constructor() {
        this.init();
    }

    init() {
        this.setupSkipLinks();
        this.setupMobileNavigation();
        this.setupKeyboardNavigation();
        this.setupFocusManagement();
        this.setupResponsiveFeatures();
        this.setupScreenReaderEnhancements();
        console.log('Accessibility enhancements initialized');
    }

    /**
     * Setup skip to main content links
     */
    setupSkipLinks() {
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.className = 'skip-link';
        skipLink.textContent = 'Skip to main content';
        skipLink.addEventListener('click', (e) => {
            e.preventDefault();
            const mainContent = document.getElementById('main-content') ||
                document.querySelector('main') ||
                document.querySelector('.main-content');
            if (mainContent) {
                mainContent.focus();
                mainContent.scrollIntoView();
            }
        });

        document.body.insertBefore(skipLink, document.body.firstChild);

        // Ensure main content area is focusable
        const mainContent = document.getElementById('main-content') ||
            document.querySelector('main') ||
            document.querySelector('.main-content');
        if (mainContent && !mainContent.hasAttribute('tabindex')) {
            mainContent.setAttribute('tabindex', '-1');
        }
    }

    /**
     * Setup mobile navigation with accessibility
     */
    setupMobileNavigation() {
        const sidebar = document.querySelector('.sidebar');
        const mainContent = document.querySelector('.main-content');

        if (!sidebar || !mainContent) return;

        // Create mobile menu toggle button
        const toggleButton = document.createElement('button');
        toggleButton.className = 'btn btn-primary d-lg-none mobile-nav-toggle';
        toggleButton.innerHTML = `
            <i class="fas fa-bars" aria-hidden="true"></i>
            <span class="visually-hidden">Toggle navigation menu</span>
        `;
        toggleButton.setAttribute('aria-expanded', 'false');
        toggleButton.setAttribute('aria-controls', 'sidebar-nav');
        toggleButton.setAttribute('aria-label', 'Toggle navigation menu');

        // Add toggle button to top of main content
        const topNavbar = document.querySelector('.top-navbar');
        if (topNavbar) {
            const container = topNavbar.querySelector('.container-fluid') || topNavbar;
            container.insertBefore(toggleButton, container.firstChild);
        } else {
            mainContent.insertBefore(toggleButton, mainContent.firstChild);
        }

        // Add ID to sidebar for ARIA reference
        sidebar.id = sidebar.id || 'sidebar-nav';
        sidebar.setAttribute('aria-label', 'Main navigation');

        // Toggle functionality
        let isOpen = false;
        toggleButton.addEventListener('click', () => {
            isOpen = !isOpen;
            sidebar.classList.toggle('show', isOpen);
            toggleButton.setAttribute('aria-expanded', isOpen.toString());

            // Update icon
            const icon = toggleButton.querySelector('i');
            icon.className = isOpen ? 'fas fa-times' : 'fas fa-bars';

            // Manage focus
            if (isOpen) {
                // Focus first navigation link
                const firstNavLink = sidebar.querySelector('.nav-link');
                if (firstNavLink) {
                    firstNavLink.focus();
                }

                // Add overlay for mobile
                this.addMobileOverlay();
            } else {
                this.removeMobileOverlay();
                toggleButton.focus();
            }
        });

        // Close on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && isOpen) {
                isOpen = false;
                sidebar.classList.remove('show');
                toggleButton.setAttribute('aria-expanded', 'false');
                const icon = toggleButton.querySelector('i');
                icon.className = 'fas fa-bars';
                this.removeMobileOverlay();
                toggleButton.focus();
            }
        });

        // Close on outside click (mobile)
        document.addEventListener('click', (e) => {
            if (isOpen && !sidebar.contains(e.target) && !toggleButton.contains(e.target)) {
                isOpen = false;
                sidebar.classList.remove('show');
                toggleButton.setAttribute('aria-expanded', 'false');
                const icon = toggleButton.querySelector('i');
                icon.className = 'fas fa-bars';
                this.removeMobileOverlay();
            }
        });

        // Handle window resize
        window.addEventListener('resize', () => {
            if (window.innerWidth >= 992 && isOpen) {
                isOpen = false;
                sidebar.classList.remove('show');
                toggleButton.setAttribute('aria-expanded', 'false');
                const icon = toggleButton.querySelector('i');
                icon.className = 'fas fa-bars';
                this.removeMobileOverlay();
            }
        });
    }

    /**
     * Add mobile overlay
     */
    addMobileOverlay() {
        if (window.innerWidth < 992) {
            const overlay = document.createElement('div');
            overlay.className = 'mobile-nav-overlay';
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                z-index: 999;
                display: block;
            `;
            document.body.appendChild(overlay);

            overlay.addEventListener('click', () => {
                const sidebar = document.querySelector('.sidebar');
                const toggleButton = document.querySelector('.mobile-nav-toggle');
                if (sidebar && toggleButton) {
                    sidebar.classList.remove('show');
                    toggleButton.setAttribute('aria-expanded', 'false');
                    const icon = toggleButton.querySelector('i');
                    icon.className = 'fas fa-bars';
                    this.removeMobileOverlay();
                }
            });
        }
    }

    /**
     * Remove mobile overlay
     */
    removeMobileOverlay() {
        const overlay = document.querySelector('.mobile-nav-overlay');
        if (overlay) {
            overlay.remove();
        }
    }

    /**
     * Setup enhanced keyboard navigation
     */
    setupKeyboardNavigation() {
        // Enhanced table navigation
        const tables = document.querySelectorAll('.table');
        tables.forEach(table => {
            this.setupTableKeyboardNavigation(table);
        });

        // Enhanced card navigation
        const cards = document.querySelectorAll('.card');
        cards.forEach(card => {
            this.setupCardKeyboardNavigation(card);
        });

        // Enhanced button group navigation
        const buttonGroups = document.querySelectorAll('.btn-group');
        buttonGroups.forEach(group => {
            this.setupButtonGroupNavigation(group);
        });
    }

    /**
     * Setup table keyboard navigation
     * @param {HTMLElement} table - Table element
     */
    setupTableKeyboardNavigation(table) {
        const rows = table.querySelectorAll('tbody tr');

        rows.forEach((row, index) => {
            row.setAttribute('tabindex', '0');
            row.setAttribute('role', 'button');
            row.setAttribute('aria-label', `Table row ${index + 1}`);

            row.addEventListener('keydown', (e) => {
                switch (e.key) {
                    case 'ArrowDown':
                        e.preventDefault();
                        const nextRow = rows[index + 1];
                        if (nextRow) nextRow.focus();
                        break;
                    case 'ArrowUp':
                        e.preventDefault();
                        const prevRow = rows[index - 1];
                        if (prevRow) prevRow.focus();
                        break;
                    case 'Enter':
                    case ' ':
                        // Don't trigger if user is typing in an input inside the row
                        if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) {
                            return;
                        }
                        e.preventDefault();
                        const firstButton = row.querySelector('button, a');
                        if (firstButton) firstButton.click();
                        break;
                }
            });
        });
    }

    /**
     * Setup card keyboard navigation
     * @param {HTMLElement} card - Card element
     */
    setupCardKeyboardNavigation(card) {
        if (!card.hasAttribute('tabindex')) {
            card.setAttribute('tabindex', '0');
        }

        card.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                // Don't trigger if user is typing in an input inside the card
                if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) {
                    return;
                }
                const firstButton = card.querySelector('button, a');
                if (firstButton) {
                    e.preventDefault();
                    firstButton.click();
                }
            }
        });
    }

    /**
     * Setup button group navigation
     * @param {HTMLElement} group - Button group element
     */
    setupButtonGroupNavigation(group) {
        const buttons = group.querySelectorAll('button, a');

        buttons.forEach((button, index) => {
            button.addEventListener('keydown', (e) => {
                switch (e.key) {
                    case 'ArrowRight':
                        e.preventDefault();
                        const nextButton = buttons[index + 1] || buttons[0];
                        nextButton.focus();
                        break;
                    case 'ArrowLeft':
                        e.preventDefault();
                        const prevButton = buttons[index - 1] || buttons[buttons.length - 1];
                        prevButton.focus();
                        break;
                }
            });
        });
    }

    /**
     * Setup focus management
     */
    setupFocusManagement() {
        // Manage focus for dynamic content
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            this.enhanceNewContent(node);
                        }
                    });
                }
            });
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // Focus management for page navigation
        this.setupPageFocusManagement();
    }

    /**
     * Enhance newly added content
     * @param {HTMLElement} element - New element
     */
    enhanceNewContent(element) {
        // Add focus management to new buttons
        const buttons = element.querySelectorAll ? element.querySelectorAll('button, a') : [];
        buttons.forEach(button => {
            if (!button.hasAttribute('aria-label') && !button.textContent.trim()) {
                const icon = button.querySelector('i');
                if (icon) {
                    const iconClass = icon.className;
                    let label = 'Button';

                    if (iconClass.includes('edit')) label = 'Edit';
                    else if (iconClass.includes('delete') || iconClass.includes('trash')) label = 'Delete';
                    else if (iconClass.includes('view') || iconClass.includes('eye')) label = 'View';
                    else if (iconClass.includes('save')) label = 'Save';
                    else if (iconClass.includes('cancel') || iconClass.includes('times')) label = 'Cancel';

                    button.setAttribute('aria-label', label);
                }
            }
        });

        // Add keyboard navigation to new tables
        const tables = element.querySelectorAll ? element.querySelectorAll('.table') : [];
        tables.forEach(table => {
            this.setupTableKeyboardNavigation(table);
        });
    }

    /**
     * Setup page focus management
     */
    setupPageFocusManagement() {
        // Focus management for AJAX page updates
        window.addEventListener('popstate', () => {
            const mainContent = document.querySelector('main, .main-content');
            if (mainContent) {
                mainContent.focus();
            }
        });
    }

    /**
     * Setup responsive features
     */
    setupResponsiveFeatures() {
        // Responsive table handling
        this.setupResponsiveTables();

        // Responsive modal handling
        this.setupResponsiveModals();

        // Responsive form handling
        this.setupResponsiveForms();
    }

    /**
     * Setup responsive tables
     */
    setupResponsiveTables() {
        const tables = document.querySelectorAll('.table');

        tables.forEach(table => {
            // Add responsive wrapper if not present
            if (!table.closest('.table-responsive')) {
                const wrapper = document.createElement('div');
                wrapper.className = 'table-responsive';
                table.parentNode.insertBefore(wrapper, table);
                wrapper.appendChild(table);
            }

            // Add mobile-friendly attributes
            const headers = table.querySelectorAll('th');
            const rows = table.querySelectorAll('tbody tr');

            headers.forEach((header, index) => {
                const headerText = header.textContent.trim();
                rows.forEach(row => {
                    const cell = row.cells[index];
                    if (cell) {
                        cell.setAttribute('data-label', headerText);
                    }
                });
            });
        });
    }

    /**
     * Setup responsive modals
     */
    setupResponsiveModals() {
        const modals = document.querySelectorAll('.modal');

        modals.forEach(modal => {
            const dialog = modal.querySelector('.modal-dialog');
            if (!dialog) return;

            // Add responsive classes
            if (!dialog.classList.contains('modal-dialog-scrollable')) {
                dialog.classList.add('modal-dialog-scrollable');
            }

            // Handle orientation changes
            window.addEventListener('orientationchange', () => {
                setTimeout(() => {
                    if (modal.classList.contains('show')) {
                        const modalBody = modal.querySelector('.modal-body');
                        if (modalBody) {
                            modalBody.style.maxHeight = `${window.innerHeight - 200}px`;
                        }
                    }
                }, 100);
            });
        });
    }

    /**
     * Setup responsive forms
     */
    setupResponsiveForms() {
        const forms = document.querySelectorAll('form');

        forms.forEach(form => {
            // Prevent zoom on iOS for input fields
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                if (input.type !== 'hidden' && !input.style.fontSize) {
                    input.style.fontSize = '16px';
                }
            });
        });
    }

    /**
     * Setup screen reader enhancements
     */
    setupScreenReaderEnhancements() {
        // Add landmarks
        this.addLandmarks();

        // Enhance headings
        this.enhanceHeadings();

        // Add live regions
        this.addLiveRegions();
    }

    /**
     * Add ARIA landmarks
     */
    addLandmarks() {
        // Main navigation
        const sidebar = document.querySelector('.sidebar');
        if (sidebar && !sidebar.hasAttribute('role')) {
            sidebar.setAttribute('role', 'navigation');
            sidebar.setAttribute('aria-label', 'Main navigation');
        }

        // Main content
        const mainContent = document.querySelector('.main-content, main');
        if (mainContent && !mainContent.hasAttribute('role')) {
            mainContent.setAttribute('role', 'main');
        }

        // Search forms
        const searchForms = document.querySelectorAll('form[role="search"], .search-form');
        searchForms.forEach(form => {
            if (!form.hasAttribute('role')) {
                form.setAttribute('role', 'search');
            }
        });
    }

    /**
     * Enhance headings structure
     */
    enhanceHeadings() {
        const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');

        headings.forEach(heading => {
            // Add IDs for anchor links if not present
            if (!heading.id && heading.textContent.trim()) {
                const id = heading.textContent.trim()
                    .toLowerCase()
                    .replace(/[^a-z0-9]+/g, '-')
                    .replace(/^-+|-+$/g, '');
                if (id) {
                    heading.id = id;
                }
            }
        });
    }

    /**
     * Add live regions for dynamic content
     */
    addLiveRegions() {
        // Add status region if not present
        if (!document.getElementById('status-region')) {
            const statusRegion = document.createElement('div');
            statusRegion.id = 'status-region';
            statusRegion.setAttribute('aria-live', 'polite');
            statusRegion.setAttribute('aria-atomic', 'true');
            statusRegion.className = 'visually-hidden';
            document.body.appendChild(statusRegion);
        }

        // Add alert region if not present
        if (!document.getElementById('alert-region')) {
            const alertRegion = document.createElement('div');
            alertRegion.id = 'alert-region';
            alertRegion.setAttribute('aria-live', 'assertive');
            alertRegion.setAttribute('aria-atomic', 'true');
            alertRegion.className = 'visually-hidden';
            document.body.appendChild(alertRegion);
        }
    }

    /**
     * Announce message to status region
     * @param {string} message - Message to announce
     */
    announceStatus(message) {
        const statusRegion = document.getElementById('status-region');
        if (statusRegion) {
            statusRegion.textContent = message;
            setTimeout(() => {
                statusRegion.textContent = '';
            }, 1000);
        }
    }

    /**
     * Announce alert to alert region
     * @param {string} message - Alert message to announce
     */
    announceAlert(message) {
        const alertRegion = document.getElementById('alert-region');
        if (alertRegion) {
            alertRegion.textContent = message;
            setTimeout(() => {
                alertRegion.textContent = '';
            }, 1000);
        }
    }
}

// Initialize accessibility enhancements when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.accessibilityEnhancements = new AccessibilityEnhancements();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AccessibilityEnhancements;
}