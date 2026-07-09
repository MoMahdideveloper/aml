/**
 * Recommendations Page JavaScript
 * Handles AI recommendations, customer selection, and property actions
 */

class RecommendationsManager {
    constructor() {
        this.init();
    }

    init() {
        console.log('Recommendations Manager initialized');
        this.bindEvents();
        this.setupAutoRefresh();
        this.checkInitialErrors();
    }

    checkInitialErrors() {
        // Log any backend-provided errors to the console for easier debugging
        const errorAlert = document.querySelector('.alert-danger, .alert-warning');
        if (errorAlert && errorAlert.textContent.includes('AI')) {
            console.error('[AI Service Error]:', errorAlert.textContent.trim());
        }
    }

    bindEvents() {
        // Bind global functions to class methods
        window.toggleAnalysis = this.toggleAnalysis.bind(this);
        window.refreshRecommendations = this.refreshRecommendations.bind(this);
        window.exportRecommendations = this.exportRecommendations.bind(this);
        window.createDeal = this.createDeal.bind(this);
        window.scheduleViewing = this.scheduleViewing.bind(this);
        window.shareProperty = this.shareProperty.bind(this);
        window.showRecommendationTips = this.showRecommendationTips.bind(this);
        window.exportReport = this.exportReport.bind(this);
    }

    toggleAnalysis(button) {
        const card = button.closest('.recommendation-card');
        const fullAnalysis = card.querySelector('.full-analysis');
        const isHidden = fullAnalysis.style.display === 'none';

        fullAnalysis.style.display = isHidden ? 'block' : 'none';
        button.innerHTML = isHidden ? '<small>Show less</small>' : '<small>Show more</small>';
    }

    refreshRecommendations() {
        const selectedCustomerId = this.getSelectedCustomerId();
        if (selectedCustomerId) {
            // Show loading state
            this.showLoadingState();
            window.location.href = `/recommendations/${selectedCustomerId}`;
        } else {
            this.showToast('Please select a customer first', 'warning');
        }
    }

    exportRecommendations() {
        const selectedCustomerId = this.getSelectedCustomerId();
        if (selectedCustomerId) {
            this.showExportOptions(selectedCustomerId);
        } else {
            this.showToast('Please select a customer first to export recommendations', 'warning');
        }
    }

    showExportOptions(customerId) {
        const exportModal = `
            <div id="exportOptionsModal" class="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-on-surface/40 backdrop-blur-[2px]" data-modal role="dialog" aria-modal="true">
                <div class="bg-surface-container-lowest rounded-lg border border-outline-variant shadow-ph w-full max-w-md" onclick="event.stopPropagation()">
                    <div class="flex items-center justify-between gap-3 px-5 py-4 border-b border-outline-variant">
                        <h2 class="text-lg font-semibold text-primary flex items-center gap-2">
                            <span class="material-symbols-outlined text-[20px]">download</span>
                            Export recommendations
                        </h2>
                        <button type="button" class="p-2 rounded-lg text-on-surface-variant hover:bg-surface-container" data-export-close aria-label="Close">
                            <span class="material-symbols-outlined text-[20px]">close</span>
                        </button>
                    </div>
                    <div class="px-5 py-4 space-y-2">
                        <p class="text-sm text-on-surface-variant mb-3">Choose a report format:</p>
                        <button type="button" class="w-full px-4 py-2.5 rounded-lg border border-outline-variant text-sm font-medium text-primary hover:bg-surface-container text-left"
                                onclick="window.recommendationsManager.exportReport(${customerId}, 'pdf')">PDF report</button>
                        <button type="button" class="w-full px-4 py-2.5 rounded-lg border border-outline-variant text-sm font-medium text-primary hover:bg-surface-container text-left"
                                onclick="window.recommendationsManager.exportReport(${customerId}, 'excel')">Excel spreadsheet</button>
                        <button type="button" class="w-full px-4 py-2.5 rounded-lg border border-outline-variant text-sm font-medium text-primary hover:bg-surface-container text-left"
                                onclick="window.recommendationsManager.exportReport(${customerId}, 'json')">JSON data</button>
                    </div>
                    <div class="px-5 py-4 border-t border-outline-variant flex justify-end">
                        <button type="button" class="px-4 py-2 rounded-lg border border-outline-variant text-sm font-medium text-primary hover:bg-surface-container" data-export-close>Cancel</button>
                    </div>
                </div>
            </div>
        `;

        const existingModal = document.getElementById('exportOptionsModal');
        if (existingModal) existingModal.remove();

        document.body.insertAdjacentHTML('beforeend', exportModal);
        const modal = document.getElementById('exportOptionsModal');
        if (window.PHModal) window.PHModal.show(modal);
        else {
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
        }

        modal.querySelectorAll('[data-export-close]').forEach(btn => {
            btn.addEventListener('click', () => {
                if (window.PHModal) window.PHModal.hide(modal);
                else modal.remove();
                modal.remove();
            });
        });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
                document.body.style.overflow = '';
            }
        });
    }

    exportReport(customerId, format) {
        const modal = document.getElementById('exportOptionsModal');
        if (modal) {
            if (window.PHModal) window.PHModal.hide(modal);
            modal.remove();
        }

        this.showToast(`Generating ${format.toUpperCase()} report...`, 'info');
        const exportUrl = `/recommendations/export?customer_id=${customerId}&format=${format}`;
        window.location.href = exportUrl;
    }

    createDeal(propertyId, customerId) {
        const propEl = document.getElementById('deal_property_id');
        const custEl = document.getElementById('deal_customer_id');
        if (propEl) propEl.value = propertyId;
        if (custEl) custEl.value = customerId;
        const modal = document.getElementById('createDealModal');
        if (!modal) return;
        if (window.PHModal) window.PHModal.show(modal);
        else {
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
        }
    }

    async scheduleViewing(propertyId) {
        try {
            this.showToast('Loading viewing schedule...', 'info');
            const modal = document.getElementById('viewingScheduleModal');
            if (modal) {
                if (window.PHModal) window.PHModal.show(modal);
                else {
                    modal.classList.remove('hidden');
                    document.body.style.overflow = 'hidden';
                }
                return;
            }
            // Fallback: navigate to property detail
            window.location.href = `/properties/${propertyId}/detail`;
        } catch (error) {
            console.error('Error loading viewing schedule:', error);
            this.showToast('Error loading viewing schedule. Please try again.', 'error');
        }
    }

    shareProperty(propertyId) {
        const currentUrl = window.location.href;

        if (navigator.share) {
            navigator.share({
                title: 'Property Recommendation',
                text: 'Check out this property recommendation',
                url: currentUrl
            }).catch(err => {
                console.log('Error sharing:', err);
                this.copyToClipboard(currentUrl);
            });
        } else {
            this.copyToClipboard(currentUrl);
        }
    }

    copyToClipboard(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                this.showToast('Link copied to clipboard!', 'success');
            }).catch(() => {
                this.fallbackCopyToClipboard(text);
            });
        } else {
            this.fallbackCopyToClipboard(text);
        }
    }

    fallbackCopyToClipboard(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();

        try {
            document.execCommand('copy');
            this.showToast('Link copied to clipboard!', 'success');
        } catch (err) {
            console.error('Fallback copy failed:', err);
            this.showToast('Unable to copy link', 'error');
        }

        document.body.removeChild(textArea);
    }

    showRecommendationTips() {
        const modal = document.getElementById('recommendationTipsModal');
        if (!modal) return;
        if (window.PHModal) window.PHModal.show(modal);
        else {
            modal.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
        }
    }

    getSelectedCustomerId() {
        // Try to get from URL path
        const pathMatch = window.location.pathname.match(/\/recommendations\/(\d+)/);
        if (pathMatch) {
            return parseInt(pathMatch[1]);
        }

        // Try to get from selected customer card
        const selectedCard = document.querySelector('.customer-selection-card.border-primary');
        if (selectedCard) {
            const link = selectedCard.querySelector('a[href*="/recommendations/"]');
            if (link) {
                const match = link.href.match(/\/recommendations\/(\d+)/);
                return match ? parseInt(match[1]) : null;
            }
        }

        return null;
    }

    showLoadingState() {
        const recommendationsSection = document.querySelector('.card:last-of-type .card-body');
        if (recommendationsSection) {
            recommendationsSection.innerHTML = `
                <div class="loading-spinner">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
                <div class="text-center mt-3">
                    <h5 class="text-muted">Refreshing Recommendations...</h5>
                    <p class="text-muted">Please wait while we update your recommendations.</p>
                </div>
            `;
        }
    }

    setupAutoRefresh() {
        // Auto-refresh recommendations if taking too long
        const isLoadingRecommendations = document.querySelector('.spinner-border') &&
            Array.from(document.querySelectorAll('h5')).some(el => el.textContent.includes("Generating AI Recommendations"));

        if (isLoadingRecommendations) {
            console.log('AI Recommendation generation detected, starting timeout monitor...');
            setTimeout(() => {
                if (document.querySelector('.spinner-border')) {
                    console.error('[AI Service Timeout]: Gemini response did not arrive within 10 seconds.');
                    const alertDiv = document.querySelector('.alert-warning');
                    if (alertDiv) {
                        alertDiv.innerHTML = `
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            <strong>Timeout:</strong> AI recommendations are taking longer than expected. 
                            <a href="javascript:window.recommendationsManager.refreshRecommendations()" class="alert-link">Click here to try again</a> 
                            or check your Gemini API configuration.
                        `;
                    }
                }
            }, 10000); // 10 seconds timeout
        }
    }

    showToast(message, type = 'info') {
        if (window.CRUDUtils && typeof window.CRUDUtils.showToast === 'function') {
            window.CRUDUtils.showToast(message, type);
        } else if (window.CRM && typeof window.CRM.showNotification === 'function') {
            window.CRM.showNotification(message, type);
        } else {
            // Fallback to console
            console.log(`${type.toUpperCase()}: ${message}`);

            // Try to show browser notification
            if (type === 'error') {
                alert(message);
            }
        }
    }

    // Utility method to handle responsive design
    handleResponsiveDesign() {
        const handleResize = () => {
            const isMobile = window.innerWidth <= 768;
            const cards = document.querySelectorAll('.recommendation-card');

            cards.forEach(card => {
                const footer = card.querySelector('.card-footer .d-flex');
                if (footer) {
                    if (isMobile) {
                        footer.classList.add('flex-column');
                        footer.classList.remove('flex-row');
                    } else {
                        footer.classList.remove('flex-column');
                        footer.classList.add('flex-row');
                    }
                }
            });
        };

        // Initial check
        handleResize();

        // Listen for resize events
        window.addEventListener('resize', handleResize);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    window.recommendationsManager = new RecommendationsManager();
    window.recommendationsManager.handleResponsiveDesign();
});

// Expose for backward compatibility
window.toggleAnalysis = function (button) {
    if (window.recommendationsManager) {
        window.recommendationsManager.toggleAnalysis(button);
    }
};

window.refreshRecommendations = function () {
    if (window.recommendationsManager) {
        window.recommendationsManager.refreshRecommendations();
    }
};

window.exportRecommendations = function () {
    if (window.recommendationsManager) {
        window.recommendationsManager.exportRecommendations();
    }
};

window.createDeal = function (propertyId, customerId) {
    if (window.recommendationsManager) {
        window.recommendationsManager.createDeal(propertyId, customerId);
    }
};

window.scheduleViewing = function (propertyId) {
    if (window.recommendationsManager) {
        window.recommendationsManager.scheduleViewing(propertyId);
    }
};

window.shareProperty = function (propertyId) {
    if (window.recommendationsManager) {
        window.recommendationsManager.shareProperty(propertyId);
    }
};

window.showRecommendationTips = function () {
    if (window.recommendationsManager) {
        window.recommendationsManager.showRecommendationTips();
    }
};

window.exportReport = function (customerId, format) {
    if (window.recommendationsManager) {
        window.recommendationsManager.exportReport(customerId, format);
    }
};