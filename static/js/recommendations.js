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
            <div class="modal fade" id="exportOptionsModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header bg-primary text-white">
                            <h5 class="modal-title">
                                <i class="fas fa-download me-2"></i>
                                Export Recommendations
                            </h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p>Choose the format for your recommendations report:</p>
                            <div class="d-grid gap-2">
                                <button class="btn btn-outline-danger" onclick="window.recommendationsManager.exportReport(${customerId}, 'pdf')">
                                    <i class="fas fa-file-pdf me-2"></i>
                                    Export as PDF
                                </button>
                                <button class="btn btn-outline-success" onclick="window.recommendationsManager.exportReport(${customerId}, 'excel')">
                                    <i class="fas fa-file-excel me-2"></i>
                                    Export as Excel
                                </button>
                                <button class="btn btn-outline-info" onclick="window.recommendationsManager.exportReport(${customerId}, 'json')">
                                    <i class="fas fa-file-code me-2"></i>
                                    Export as JSON
                                </button>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal if present
        const existingModal = document.getElementById('exportOptionsModal');
        if (existingModal) {
            existingModal.remove();
        }

        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', exportModal);

        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('exportOptionsModal'));
        modal.show();

        // Clean up when modal is hidden
        document.getElementById('exportOptionsModal').addEventListener('hidden.bs.modal', function () {
            this.remove();
        });
    }

    exportReport(customerId, format) {
        // Close the export options modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('exportOptionsModal'));
        if (modal) {
            modal.hide();
        }

        // Show loading toast
        this.showToast(`Generating ${format.toUpperCase()} report...`, 'info');

        // Create download link
        const exportUrl = `/recommendations/export?customer_id=${customerId}&format=${format}`;

        // Trigger download
        window.location.href = exportUrl;
    }

    createDeal(propertyId, customerId) {
        document.getElementById('deal_property_id').value = propertyId;
        document.getElementById('deal_customer_id').value = customerId;

        const modal = new bootstrap.Modal(document.getElementById('createDealModal'));
        modal.show();
    }

    async scheduleViewing(propertyId) {
        try {
            // Show loading state
            this.showToast('Loading viewing schedule...', 'info');

            // Load viewing schedule modal content
            const response = await fetch(`/properties/${propertyId}/schedule-viewing?ajax=1`);

            if (!response.ok) {
                throw new Error('Failed to load viewing schedule');
            }

            const html = await response.text();

            // Remove existing modal if present
            const existingModal = document.getElementById('viewingScheduleModal');
            if (existingModal) {
                existingModal.remove();
            }

            // Add modal to page
            document.body.insertAdjacentHTML('beforeend', html);

            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('viewingScheduleModal'));
            modal.show();

            // Clean up when modal is hidden
            document.getElementById('viewingScheduleModal').addEventListener('hidden.bs.modal', function () {
                this.remove();
            });

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
        const modal = new bootstrap.Modal(document.getElementById('recommendationTipsModal'));
        modal.show();
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