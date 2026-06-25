/**
 * Dual View Handler - Manages modal and new tab viewing preferences
 * Real Estate CRM System
 */

class DualViewHandler {
    constructor() {
        this.storageKey = 'crm_view_preferences';
        this.defaultPreference = 'modal';
        this.preferences = this.loadPreferences();
        this.popupBlockedNotified = false;
        
        this.init();
    }

    /**
     * Initialize the dual view handler
     */
    init() {
        this.bindEvents();
        this.updatePreferenceIndicators();
        console.log('DualViewHandler initialized');
    }

    /**
     * Bind event listeners for view option selectors
     */
    bindEvents() {
        // Delegate event handling for dynamically added selectors
        document.addEventListener('click', (e) => {
            const viewButton = e.target.closest('.view-option-modal, .view-option-tab');
            if (viewButton) {
                e.preventDefault();
                this.handleViewAction(viewButton);
            }
        });

        // Handle Ctrl+click for new tab override
        document.addEventListener('click', (e) => {
            if (e.ctrlKey || e.metaKey) {
                const viewButton = e.target.closest('.view-option-modal');
                if (viewButton) {
                    e.preventDefault();
                    this.handleViewAction(viewButton, 'tab');
                }
            }
        });

        // Handle keyboard navigation
        document.addEventListener('keydown', (e) => {
            const selector = e.target.closest('.view-options-selector');
            if (selector && (e.key === 'Enter' || e.key === ' ')) {
                const activeButton = selector.querySelector('.btn:focus');
                if (activeButton) {
                    e.preventDefault();
                    this.handleViewAction(activeButton);
                }
            }
        });
    }

    /**
     * Handle view action (modal or tab)
     * @param {HTMLElement} button - The clicked button
     * @param {string} forceMode - Force specific mode (optional)
     */
    async handleViewAction(button, forceMode = null) {
        const selector = button.closest('.view-options-selector');
        const entityType = selector.dataset.entityType;
        const entityId = selector.dataset.entityId;
        const viewMode = forceMode || button.dataset.viewMode || this.getUserPreference(entityType);

        // Update preference if user explicitly chose a mode
        if (!forceMode && button.dataset.viewMode) {
            this.setUserPreference(entityType, button.dataset.viewMode);
            this.updatePreferenceIndicators();
        }

        // Show loading state
        this.setButtonLoading(button, true);

        try {
            if (viewMode === 'tab') {
                await this.openInNewTab(entityType, entityId);
            } else {
                await this.openInModal(entityType, entityId);
            }
        } catch (error) {
            console.error('View action failed:', error);
            this.showError('Failed to open view. Please try again.');
        } finally {
            this.setButtonLoading(button, false);
        }
    }

    /**
     * Open entity in modal view
     * @param {string} entityType - Type of entity
     * @param {string} entityId - Entity ID
     */
    async openInModal(entityType, entityId) {
        const modalId = `${entityType}ViewModal`;
        const url = `/${entityType}/${entityId}`;
        const title = `${this.capitalizeFirst(entityType)} Details`;

        // Use existing CRUDUtils if available
        if (window.CRUDUtils && typeof window.CRUDUtils.loadModal === 'function') {
            await window.CRUDUtils.loadModal(url, modalId, title);
        } else {
            // Fallback to basic modal handling
            await this.loadModalFallback(url, modalId, title);
        }

        this.trackViewAction(entityType, entityId, 'modal');
    }

    /**
     * Open entity in new tab
     * @param {string} entityType - Type of entity
     * @param {string} entityId - Entity ID
     */
    async openInNewTab(entityType, entityId) {
        const url = this.generateDetailUrl(entityType, entityId);
        
        try {
            const newTab = window.open(url, '_blank', 'noopener,noreferrer');
            
            if (!newTab || newTab.closed || typeof newTab.closed === 'undefined') {
                this.handlePopupBlocked(url);
                return;
            }

            // Focus the new tab
            newTab.focus();
            this.trackViewAction(entityType, entityId, 'tab');
            
        } catch (error) {
            console.error('Failed to open new tab:', error);
            this.handlePopupBlocked(url);
        }
    }

    /**
     * Generate detail URL for entity
     * @param {string} entityType - Type of entity
     * @param {string} entityId - Entity ID
     * @returns {string} Detail URL
     */
    generateDetailUrl(entityType, entityId) {
        // Handle different entity types and their URL patterns
        const urlMap = {
            'property': `/properties/${entityId}`,
            'properties': `/properties/${entityId}`,
            'customer': `/customers/${entityId}`,
            'customers': `/customers/${entityId}`,
            'agent': `/agents/${entityId}`,
            'agents': `/agents/${entityId}`,
            'deal': `/deals/${entityId}`,
            'deals': `/deals/${entityId}`,
            'task': `/tasks/${entityId}`,
            'tasks': `/tasks/${entityId}`
        };

        return urlMap[entityType] || `/${entityType}/${entityId}`;
    }

    /**
     * Handle popup blocked scenario
     * @param {string} url - The URL that was blocked
     */
    handlePopupBlocked(url) {
        if (this.popupBlockedNotified) return;
        
        this.popupBlockedNotified = true;
        
        const message = 'Popup blocked by browser. Click here to open in current tab.';
        
        if (window.CRUDUtils && typeof window.CRUDUtils.showToast === 'function') {
            window.CRUDUtils.showToast(message, 'warning', {
                duration: 8000,
                onclick: () => {
                    window.location.href = url;
                }
            });
        } else {
            // Fallback notification
            if (confirm('Popup blocked. Open in current tab instead?')) {
                window.location.href = url;
            }
        }
        
        // Reset notification flag after delay
        setTimeout(() => {
            this.popupBlockedNotified = false;
        }, 10000);
    }

    /**
     * Load modal fallback when CRUDUtils is not available
     * @param {string} url - Content URL
     * @param {string} modalId - Modal ID
     * @param {string} title - Modal title
     */
    async loadModalFallback(url, modalId, title) {
        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Accept': 'text/html',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const html = await response.text();
            
            // Create or update modal
            let modal = document.getElementById(modalId);
            if (!modal) {
                modal = this.createModal(modalId, title);
            }

            const modalBody = modal.querySelector('.modal-body');
            if (modalBody) {
                modalBody.innerHTML = html;
            }

            // Show modal
            const modalInstance = new bootstrap.Modal(modal);
            modalInstance.show();

        } catch (error) {
            console.error('Modal fallback failed:', error);
            throw error;
        }
    }

    /**
     * Create a basic modal element
     * @param {string} modalId - Modal ID
     * @param {string} title - Modal title
     * @returns {HTMLElement} Modal element
     */
    createModal(modalId, title) {
        const modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="text-center p-4">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);
        return document.getElementById(modalId);
    }

    /**
     * Set button loading state
     * @param {HTMLElement} button - Button element
     * @param {boolean} loading - Loading state
     */
    setButtonLoading(button, loading) {
        if (loading) {
            button.disabled = true;
            const icon = button.querySelector('i');
            if (icon) {
                icon.className = 'fas fa-spinner fa-spin';
            }
        } else {
            button.disabled = false;
            const icon = button.querySelector('i');
            if (icon) {
                // Restore original icon based on button type
                if (button.classList.contains('view-option-modal')) {
                    icon.className = 'fas fa-eye';
                } else {
                    icon.className = 'fas fa-external-link-alt';
                }
            }
        }
    }

    /**
     * Get user preference for entity type
     * @param {string} entityType - Entity type
     * @returns {string} Preference (modal|tab)
     */
    getUserPreference(entityType) {
        return this.preferences[entityType] || this.preferences.global || this.defaultPreference;
    }

    /**
     * Set user preference for entity type
     * @param {string} entityType - Entity type
     * @param {string} preference - Preference (modal|tab)
     */
    setUserPreference(entityType, preference) {
        this.preferences[entityType] = preference;
        this.savePreferences();
    }

    /**
     * Load preferences from localStorage
     * @returns {Object} Preferences object
     */
    loadPreferences() {
        try {
            const stored = localStorage.getItem(this.storageKey);
            if (stored) {
                const parsed = JSON.parse(stored);
                return {
                    global: this.defaultPreference,
                    ...parsed,
                    lastUpdated: new Date().toISOString()
                };
            }
        } catch (error) {
            console.warn('Failed to load view preferences:', error);
        }

        return {
            global: this.defaultPreference,
            lastUpdated: new Date().toISOString()
        };
    }

    /**
     * Save preferences to localStorage
     */
    savePreferences() {
        try {
            this.preferences.lastUpdated = new Date().toISOString();
            localStorage.setItem(this.storageKey, JSON.stringify(this.preferences));
        } catch (error) {
            console.warn('Failed to save view preferences:', error);
            // Try sessionStorage as fallback
            try {
                sessionStorage.setItem(this.storageKey, JSON.stringify(this.preferences));
            } catch (sessionError) {
                console.warn('Failed to save to sessionStorage:', sessionError);
            }
        }
    }

    /**
     * Update preference indicators in UI
     */
    updatePreferenceIndicators() {
        document.querySelectorAll('.view-options-selector').forEach(selector => {
            const entityType = selector.dataset.entityType;
            const preference = this.getUserPreference(entityType);
            const indicator = selector.querySelector('.preference-indicator');
            const buttons = selector.querySelectorAll('.btn');

            // Update button states
            buttons.forEach(btn => {
                btn.classList.remove('preferred');
                if (btn.dataset.viewMode === preference) {
                    btn.classList.add('preferred');
                }
            });

            // Update indicator
            if (indicator && this.preferences[entityType]) {
                indicator.classList.remove('d-none');
                const text = indicator.querySelector('.preference-text');
                if (text) {
                    text.textContent = preference === 'modal' ? 'Quick View Default' : 'Full View Default';
                }
            } else if (indicator) {
                indicator.classList.add('d-none');
            }
        });
    }

    /**
     * Track view action for analytics
     * @param {string} entityType - Entity type
     * @param {string} entityId - Entity ID
     * @param {string} viewMode - View mode used
     */
    trackViewAction(entityType, entityId, viewMode) {
        // Basic tracking - can be extended with analytics service
        console.log(`View action: ${entityType}/${entityId} in ${viewMode} mode`);
        
        // Could integrate with analytics service here
        if (window.gtag) {
            window.gtag('event', 'view_entity', {
                entity_type: entityType,
                entity_id: entityId,
                view_mode: viewMode
            });
        }
    }

    /**
     * Show error message
     * @param {string} message - Error message
     */
    showError(message) {
        if (window.CRUDUtils && typeof window.CRUDUtils.showToast === 'function') {
            window.CRUDUtils.showToast(message, 'error');
        } else if (window.CRM && typeof window.CRM.showNotification === 'function') {
            window.CRM.showNotification(message, 'error');
        } else {
            alert(message);
        }
    }

    /**
     * Capitalize first letter of string
     * @param {string} str - String to capitalize
     * @returns {string} Capitalized string
     */
    capitalizeFirst(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }

    /**
     * Reset all preferences
     */
    resetPreferences() {
        this.preferences = {
            global: this.defaultPreference,
            lastUpdated: new Date().toISOString()
        };
        this.savePreferences();
        this.updatePreferenceIndicators();
    }

    /**
     * Get preference statistics
     * @returns {Object} Preference statistics
     */
    getPreferenceStats() {
        const stats = {
            total: 0,
            modal: 0,
            tab: 0,
            entities: {}
        };

        Object.keys(this.preferences).forEach(key => {
            if (key !== 'global' && key !== 'lastUpdated') {
                stats.total++;
                stats.entities[key] = this.preferences[key];
                if (this.preferences[key] === 'modal') {
                    stats.modal++;
                } else {
                    stats.tab++;
                }
            }
        });

        return stats;
    }
}

// Initialize dual view handler when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.DualViewHandler = new DualViewHandler();
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DualViewHandler;
}