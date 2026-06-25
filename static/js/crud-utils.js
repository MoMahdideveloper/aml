/**
 * CRUD Utilities - Modal management, toast notifications, and AJAX operations
 * Real Estate CRM System
 */

if (!window.__crudUtilsBootstrapped) {
window.__crudUtilsBootstrapped = true;

class CRUDUtils {
    constructor() {
        this.activeModals = new Map();
        this.toastContainer = null;
        this.defaultOptions = {
            timeout: 5000,
            showProgress: true,
            confirmDelete: true,
            autoHideToasts: true
        };
        
        this.init();
    }

    /**
     * Initialize CRUD utilities
     */
    init() {
        this.createToastContainer();
        this.bindGlobalEvents();
        console.log('CRUDUtils initialized');
    }

    /**
     * Create toast container if it doesn't exist
     */
    createToastContainer() {
        if (!this.toastContainer) {
            this.toastContainer = document.createElement('div');
            this.toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            this.toastContainer.style.zIndex = '2000';
            document.body.appendChild(this.toastContainer);
        }
    }

    /**
     * Escape untrusted text before interpolating into dynamic HTML templates.
     * @param {*} value
     */
    escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    /**
     * Normalize numeric strings for <input type="number"> fields.
     * @param {*} value
     */
    normalizeNumberInput(value) {
        if (value === null || value === undefined || value === '') {
            return '';
        }
        const normalized = String(value)
            .replace(/[,_\s]/g, '')
            .replace(/[٬،]/g, '');
        const numeric = Number.parseFloat(normalized);
        if (!Number.isFinite(numeric)) {
            return '';
        }
        return Number.isInteger(numeric) ? String(numeric) : String(numeric);
    }

    /**
     * Show modal with enhanced accessibility and responsive features
     * @param {string} modalId - Modal element ID
     * @param {Object} options - Modal options
     */
    showModal(modalId, options = {}) {
        const modal = document.getElementById(modalId);
        if (!modal) {
            console.error(`Modal with ID '${modalId}' not found`);
            return null;
        }

        // Store the currently focused element to return focus later
        const previouslyFocusedElement = document.activeElement;
        modal.setAttribute('data-previous-focus', previouslyFocusedElement?.id || '');

        const modalInstance = new bootstrap.Modal(modal, {
            backdrop: options.backdrop !== false ? 'static' : false,
            keyboard: options.keyboard !== false
        });

        // Store modal instance for later reference
        this.activeModals.set(modalId, modalInstance);

        // Enhanced accessibility setup
        this.setupModalAccessibility(modal, modalId);

        // Load content if URL provided
        if (options.contentUrl) {
            this.loadModalContent(modalId, options.contentUrl, options.loadOptions);
        }

        // Show modal
        modalInstance.show();

        // Bind form submission if form exists
        const form = modal.querySelector('form');
        if (form && !form.hasAttribute('data-crud-bound')) {
            this.bindFormSubmission(form, options.onSubmit);
            form.setAttribute('data-crud-bound', 'true');
        }

        // Announce modal opening to screen readers
        this.announceToScreenReader(`${modal.querySelector('.modal-title')?.textContent || 'Dialog'} opened`);

        return modalInstance;
    }

    /**
     * Setup enhanced accessibility features for modal
     * @param {HTMLElement} modal - Modal element
     * @param {string} modalId - Modal ID
     */
    setupModalAccessibility(modal, modalId) {
        // Ensure proper ARIA attributes
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');
        
        // Setup focus trap
        this.setupFocusTrap(modal);
        
        // Setup keyboard navigation
        this.setupModalKeyboardNavigation(modal);
        
        // Setup responsive adjustments
        this.setupResponsiveModal(modal);
    }

    /**
     * Setup focus trap for modal
     * @param {HTMLElement} modal - Modal element
     */
    setupFocusTrap(modal) {
        const focusableElements = modal.querySelectorAll(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        
        const firstFocusableElement = focusableElements[0];
        const lastFocusableElement = focusableElements[focusableElements.length - 1];

        modal.addEventListener('keydown', function(e) {
            if (e.key === 'Tab') {
                if (e.shiftKey) {
                    // Shift + Tab
                    if (document.activeElement === firstFocusableElement) {
                        e.preventDefault();
                        lastFocusableElement?.focus();
                    }
                } else {
                    // Tab
                    if (document.activeElement === lastFocusableElement) {
                        e.preventDefault();
                        firstFocusableElement?.focus();
                    }
                }
            }
        });
    }

    /**
     * Setup keyboard navigation for modal
     * @param {HTMLElement} modal - Modal element
     */
    setupModalKeyboardNavigation(modal) {
        modal.addEventListener('keydown', function(e) {
            // Escape key
            if (e.key === 'Escape') {
                const closeBtn = modal.querySelector('[data-bs-dismiss="modal"]');
                if (closeBtn) {
                    closeBtn.click();
                }
                return;
            }
            
            // Enter key on buttons
            if (e.key === 'Enter' && e.target.tagName === 'BUTTON' && e.target.type !== 'submit') {
                e.target.click();
            }
        });
    }

    /**
     * Setup responsive modal adjustments
     * @param {HTMLElement} modal - Modal element
     */
    setupResponsiveModal(modal) {
        const dialog = modal.querySelector('.modal-dialog');
        if (!dialog) return;

        // Add responsive classes based on screen size
        const updateModalSize = () => {
            const screenWidth = window.innerWidth;
            
            if (screenWidth < 576) {
                // Extra small screens - full screen modal
                dialog.classList.add('modal-fullscreen');
                dialog.classList.remove('modal-dialog-centered');
            } else if (screenWidth < 768) {
                // Small screens - full width but not full screen
                dialog.classList.remove('modal-fullscreen');
                dialog.classList.add('modal-dialog-centered');
                dialog.style.margin = '0.5rem';
                dialog.style.maxWidth = 'calc(100% - 1rem)';
            } else {
                // Larger screens - normal modal
                dialog.classList.remove('modal-fullscreen');
                dialog.classList.add('modal-dialog-centered');
                dialog.style.margin = '';
                dialog.style.maxWidth = '';
            }
        };

        // Initial setup
        updateModalSize();

        // Update on resize
        window.addEventListener('resize', updateModalSize);
        
        // Cleanup on modal hide
        modal.addEventListener('hidden.bs.modal', () => {
            window.removeEventListener('resize', updateModalSize);
        });
    }

    /**
     * Hide modal with enhanced accessibility
     * @param {string} modalId - Modal element ID
     */
    hideModal(modalId) {
        const modalInstance = this.activeModals.get(modalId);
        const modal = document.getElementById(modalId);
        
        if (modalInstance) {
            modalInstance.hide();
            this.activeModals.delete(modalId);
            
            // Return focus to previously focused element
            if (modal) {
                const previousFocusId = modal.getAttribute('data-previous-focus');
                const previousElement = previousFocusId ? document.getElementById(previousFocusId) : null;
                
                if (previousElement && previousElement.focus) {
                    setTimeout(() => {
                        previousElement.focus();
                    }, 150);
                }
                
                // Announce modal closing to screen readers
                this.announceToScreenReader(`${modal.querySelector('.modal-title')?.textContent || 'Dialog'} closed`);
            }
        }
    }

    /**
     * Announce message to screen readers
     * @param {string} message - Message to announce
     * @param {string} priority - Announcement priority (polite|assertive)
     */
    announceToScreenReader(message, priority = 'polite') {
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', priority);
        announcement.setAttribute('aria-atomic', 'true');
        announcement.className = 'visually-hidden';
        announcement.textContent = message;
        
        document.body.appendChild(announcement);
        
        setTimeout(() => {
            if (document.body.contains(announcement)) {
                document.body.removeChild(announcement);
            }
        }, 1000);
    }

    /**
     * Load modal with content from URL
     * @param {string} url - Content URL
     * @param {string} modalId - Modal element ID
     * @param {string} title - Modal title
     * @param {Object} options - Load options
     */
    async loadModal(url, modalId, title, options = {}) {
        try {
            // Create modal if it doesn't exist
            let modal = document.getElementById(modalId);
            if (!modal) {
                modal = this.createDynamicModal(modalId, title);
            }

            // Load content
            const response = await this.makeRequest(url, {
                method: 'GET',
                headers: {
                    'Accept': 'text/html',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            // Update modal content
            const modalBody = modal.querySelector('.modal-body');
            if (modalBody) {
                modalBody.innerHTML = response;
            }

            // Update modal title
            const modalTitle = modal.querySelector('.modal-title');
            if (modalTitle) {
                modalTitle.textContent = title;
            }

            // Show modal
            this.showModal(modalId, options);

        } catch (error) {
            console.error('Failed to load modal:', error);
            this.showToast(error.message || 'Failed to load content', 'error');
        }
    }

    /**
     * Load edit modal with form content
     * @param {string} url - Content URL
     * @param {string} modalId - Modal element ID
     * @param {string} title - Modal title
     * @param {Function} onSuccess - Success callback
     * @param {Object} options - Load options
     */
    async loadEditModal(url, modalId, title, onSuccess, options = {}) {
        try {
            // Create modal if it doesn't exist
            let modal = document.getElementById(modalId);
            if (!modal) {
                modal = this.createDynamicModal(modalId, title);
            }

            // Load content
            const response = await this.makeRequest(url, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            // Handle JSON response with property data
            if (response.data && response.data.property) {
                this.populateEditForm(modal, response.data.property);
            } else {
                // Handle HTML response
                const modalBody = modal.querySelector('.modal-body');
                if (modalBody) {
                    modalBody.innerHTML = typeof response === 'string' ? response : JSON.stringify(response);
                }
            }

            // Update modal title
            const modalTitle = modal.querySelector('.modal-title');
            if (modalTitle) {
                modalTitle.textContent = title;
            }

            // Bind form submission
            const form = modal.querySelector('form');
            if (form) {
                this.bindFormSubmission(form, onSuccess);
            }

            // Show modal
            this.showModal(modalId, options);

        } catch (error) {
            console.error('Failed to load edit modal:', error);
            this.showToast(error.message || 'Failed to load edit form', 'error');
        }
    }

    /**
     * Create a dynamic modal element
     * @param {string} modalId - Modal ID
     * @param {string} title - Modal title
     */
    createDynamicModal(modalId, title) {
        const modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="text-center p-4">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <div class="mt-2">Loading...</div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = document.getElementById(modalId);

        // Clean up modal when hidden
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });

        return modal;
    }

    /**
     * Populate edit form with property data
     * @param {HTMLElement} modal - Modal element
     * @param {Object} property - Property data
     */
    populateEditForm(modal, property) {
        const propertyId = Number.parseInt(property?.id, 10);
        if (!Number.isInteger(propertyId) || propertyId <= 0) {
            this.showToast('Invalid property data received', 'error');
            return;
        }

        const propertyType = String(property.property_type || '').trim().toLowerCase();
        const safeTitle = this.escapeHtml(property.title);
        const safeAddress = this.escapeHtml(property.address);
        const safeNeighborhood = this.escapeHtml(property.neighborhood);
        const safeDescription = this.escapeHtml(property.description);
        const safeSquareFeet = this.normalizeNumberInput(property.square_feet);
        const safeBedrooms = this.normalizeNumberInput(property.bedrooms);
        const safeBathrooms = this.normalizeNumberInput(property.bathrooms);
        const safeParking = this.normalizeNumberInput(property.parking_spaces);
        const safePrice = this.normalizeNumberInput(property.price);

        // Create edit form HTML
        const formHtml = `
            <form id="propertyEditForm" method="POST" action="/properties/${propertyId}">
                <input type="hidden" name="csrf_token" value="">
                <input type="hidden" name="_method" value="PUT">
                <input type="hidden" name="property_id" value="${propertyId}">
                
                <div class="row">
                    <div class="col-md-8 mb-3">
                        <label for="edit_title" class="form-label">Property Title *</label>
                        <input type="text" class="form-control" id="edit_title" name="title" value="${safeTitle}" required>
                    </div>
                    <div class="col-md-4 mb-3">
                        <label for="edit_property_type" class="form-label">Type *</label>
                        <select class="form-select" id="edit_property_type" name="property_type" required>
                            <option value="house" ${propertyType === 'house' ? 'selected' : ''}>House</option>
                            <option value="condo" ${propertyType === 'condo' ? 'selected' : ''}>Condo</option>
                            <option value="loft" ${propertyType === 'loft' ? 'selected' : ''}>Loft</option>
                            <option value="townhouse" ${propertyType === 'townhouse' ? 'selected' : ''}>Townhouse</option>
                            <option value="commercial" ${propertyType === 'commercial' ? 'selected' : ''}>Commercial</option>
                        </select>
                    </div>
                </div>
                
                <div class="mb-3">
                    <label for="edit_address" class="form-label">Address *</label>
                    <textarea class="form-control" id="edit_address" name="address" rows="2" required>${safeAddress}</textarea>
                </div>
                
                <div class="row">
                    <div class="col-md-3 mb-3">
                        <label for="edit_square_feet" class="form-label">Square Meters *</label>
                        <input type="number" class="form-control" id="edit_square_feet" name="square_feet" min="0" value="${safeSquareFeet}" required>
                    </div>
                    <div class="col-md-3 mb-3">
                        <label for="edit_bedrooms" class="form-label">Bedrooms</label>
                        <input type="number" class="form-control" id="edit_bedrooms" name="bedrooms" min="0" max="20" value="${safeBedrooms}">
                    </div>
                    <div class="col-md-3 mb-3">
                        <label for="edit_bathrooms" class="form-label">Bathrooms</label>
                        <input type="number" class="form-control" id="edit_bathrooms" name="bathrooms" min="0" max="20" step="0.5" value="${safeBathrooms}">
                    </div>
                    <div class="col-md-3 mb-3">
                        <label for="edit_parking_spaces" class="form-label">Parking</label>
                        <input type="number" class="form-control" id="edit_parking_spaces" name="parking_spaces" min="0" max="10" value="${safeParking}">
                    </div>
                </div>
                
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <label for="edit_price" class="form-label">Price *</label>
                        <input type="number" class="form-control" id="edit_price" name="sale_price" step="1000" value="${safePrice}" required>
                    </div>
                    <div class="col-md-6 mb-3">
                        <label for="edit_neighborhood" class="form-label">Neighborhood</label>
                        <input type="text" class="form-control" id="edit_neighborhood" name="neighborhood" value="${safeNeighborhood}">
                    </div>
                </div>
                
                <div class="mb-3">
                    <label for="edit_description" class="form-label">Description</label>
                    <textarea class="form-control" id="edit_description" name="description" rows="3">${safeDescription}</textarea>
                </div>
            </form>
        `;

        const modalBody = modal.querySelector('.modal-body');
        if (modalBody) {
            modalBody.innerHTML = formHtml;
        }

        // Update modal footer with save button
        const modalFooter = modal.querySelector('.modal-footer');
        if (modalFooter) {
            modalFooter.innerHTML = `
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                <button type="submit" form="propertyEditForm" class="btn btn-primary">
                    <i class="fas fa-save me-1"></i>
                    Save Changes
                </button>
            `;
        }
    }

    /**
     * Load content into modal
     * @param {string} modalId - Modal element ID
     * @param {string} url - Content URL
     * @param {Object} options - Load options
     */
    async loadModalContent(modalId, url, options = {}) {
        const modal = document.getElementById(modalId);
        const loadingEl = modal.querySelector(`#${modalId}_loading`);
        const contentEl = modal.querySelector(`#${modalId}_content`);
        const errorEl = modal.querySelector(`#${modalId}_error`);

        try {
            // Show loading state
            if (loadingEl) loadingEl.style.display = 'block';
            if (contentEl) contentEl.style.display = 'none';
            if (errorEl) errorEl.classList.add('d-none');

            const response = await this.makeRequest(url, {
                method: 'GET',
                ...options
            });

            // Hide loading and show content
            if (loadingEl) loadingEl.style.display = 'none';
            if (contentEl) {
                contentEl.innerHTML = response;
                contentEl.style.display = 'block';
            }

            // Re-bind form if new content has forms
            const form = modal.querySelector('form');
            if (form && !form.hasAttribute('data-crud-bound')) {
                this.bindFormSubmission(form, options.onSubmit);
                form.setAttribute('data-crud-bound', 'true');
            }

        } catch (error) {
            // Show error state
            if (loadingEl) loadingEl.style.display = 'none';
            if (errorEl) {
                const errorMsg = errorEl.querySelector(`#${modalId}_error_message`);
                if (errorMsg) errorMsg.textContent = error.message;
                errorEl.classList.remove('d-none');
            }
            console.error('Failed to load modal content:', error);
        }
    }

    /**
     * Show accessible toast notification with responsive design
     * @param {string} message - Toast message
     * @param {string} type - Toast type (success, error, warning, info)
     * @param {Object} options - Toast options
     */
    showToast(message, type = 'info', options = {}) {
        const toastId = `toast_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const duration = options.duration || this.defaultOptions.timeout;
        
        const iconMap = {
            success: 'fas fa-check-circle text-success',
            error: 'fas fa-exclamation-triangle text-danger',
            warning: 'fas fa-exclamation-triangle text-warning',
            info: 'fas fa-info-circle text-info'
        };

        const titleMap = {
            success: 'Success',
            error: 'Error',
            warning: 'Warning',
            info: 'Information'
        };

        // Determine appropriate aria-live value based on type
        const ariaLive = type === 'error' ? 'assertive' : 'polite';
        
        // Add responsive classes
        const responsiveClasses = window.innerWidth < 768 ? 'toast-mobile' : '';

        const toastHtml = `
            <div id="${toastId}" class="toast ${responsiveClasses} toast-${type}" 
                 role="alert" aria-live="${ariaLive}" aria-atomic="true"
                 aria-describedby="${toastId}_message">
                <div class="toast-header">
                    <i class="${iconMap[type] || iconMap.info} me-2" aria-hidden="true"></i>
                    <strong class="me-auto">${options.title || titleMap[type] || titleMap.info}</strong>
                    <small class="text-muted" aria-hidden="true">${options.timestamp !== false ? 'now' : ''}</small>
                    <button type="button" class="btn-close" data-bs-dismiss="toast" 
                            aria-label="Close ${titleMap[type] || titleMap.info} notification"
                            title="Close notification"></button>
                </div>
                <div class="toast-body" id="${toastId}_message">
                    ${message}
                </div>
            </div>
        `;

        this.toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const toastElement = document.getElementById(toastId);
        
        // Enhanced toast configuration
        const toast = new bootstrap.Toast(toastElement, {
            autohide: this.defaultOptions.autoHideToasts && type !== 'error', // Keep error toasts visible longer
            delay: type === 'error' ? duration * 2 : duration
        });

        // Add keyboard navigation
        toastElement.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                toast.hide();
            }
        });

        // Make toast focusable for keyboard users
        toastElement.setAttribute('tabindex', '0');
        
        // Focus toast for screen readers if it's an error
        if (type === 'error') {
            setTimeout(() => {
                toastElement.focus();
            }, 100);
        }

        toast.show();

        // Announce to screen readers
        this.announceToScreenReader(
            `${titleMap[type] || titleMap.info}: ${message}`,
            type === 'error' ? 'assertive' : 'polite'
        );

        // Remove toast element after it's hidden
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });

        // Auto-adjust position on mobile
        if (window.innerWidth < 768) {
            this.adjustToastPositionMobile();
        }

        return toast;
    }

    /**
     * Adjust toast position for mobile devices
     */
    adjustToastPositionMobile() {
        if (window.innerWidth < 768) {
            this.toastContainer.className = 'toast-container position-fixed top-0 start-0 end-0 p-2';
            this.toastContainer.style.zIndex = '2000';
        } else {
            this.toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            this.toastContainer.style.zIndex = '2000';
        }
    }

    /**
     * Show confirmation dialog for delete operations
     * @param {string} message - Confirmation message
     * @param {Function} onConfirm - Callback for confirmation
     * @param {Object} options - Dialog options
     */
    confirmDelete(message, onConfirm, options = {}) {
        const title = options.title || 'Confirm Delete';
        const confirmText = options.confirmText || 'Delete';
        const cancelText = options.cancelText || 'Cancel';
        
        // Create confirmation modal
        const modalId = `confirmModal_${Date.now()}`;
        const modalHtml = `
            <div class="modal fade" id="${modalId}" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-exclamation-triangle text-warning me-2"></i>
                                ${title}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p>${message}</p>
                            ${options.warning ? `<div class="alert alert-warning"><i class="fas fa-exclamation-triangle me-2"></i>${options.warning}</div>` : ''}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">${cancelText}</button>
                            <button type="button" class="btn btn-danger" id="${modalId}_confirm">
                                <i class="fas fa-trash me-1"></i>
                                ${confirmText}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modalElement = document.getElementById(modalId);
        const modal = new bootstrap.Modal(modalElement);
        
        // Bind confirm button
        const confirmBtn = document.getElementById(`${modalId}_confirm`);
        confirmBtn.addEventListener('click', () => {
            modal.hide();
            if (typeof onConfirm === 'function') {
                onConfirm();
            }
        });

        // Clean up modal after hiding
        modalElement.addEventListener('hidden.bs.modal', () => {
            modalElement.remove();
        });

        modal.show();
        return modal;
    }

    /**
     * Bind form submission with AJAX
     * @param {HTMLFormElement} form - Form element
     * @param {Function} onSuccess - Success callback
     */
    bindFormSubmission(form, onSuccess) {
        if (!form || form.hasAttribute('data-crud-bound')) {
            return;
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            try {
                const result = await this.submitForm(form, {
                    onSuccess: (response) => {
                        if (typeof onSuccess === 'function') {
                            onSuccess(response);
                        } else {
                            // Default success behavior
                            this.showToast('Changes saved successfully!', 'success');
                            
                            // Close modal
                            const modal = form.closest('.modal');
                            if (modal) {
                                this.hideModal(modal.id);
                            }
                            
                            // Reload page after short delay
                            setTimeout(() => {
                                window.location.reload();
                            }, 1000);
                        }
                    },
                    reload: false // Don't auto-reload, let callback handle it
                });
            } catch (error) {
                console.error('Form submission failed:', error);
            }
        });

        form.setAttribute('data-crud-bound', 'true');
    }

    /**
     * Submit form via AJAX with enhanced loading indicators
     * @param {HTMLFormElement|string} form - Form element or selector
     * @param {Object} options - Submission options
     */
    async submitForm(form, options = {}) {
        const formElement = typeof form === 'string' ? document.querySelector(form) : form;
        if (!formElement) {
            throw new Error('Form not found');
        }

        const formData = new FormData(formElement);
        const submitBtn = formElement.querySelector('[type="submit"], .btn-primary');
        const loadingOverlay = this.createLoadingOverlay(formElement);

        try {
            // Clear previous errors
            this.clearFormErrors(formElement);
            
            // Show loading state
            this.showLoadingState(formElement, submitBtn, loadingOverlay);

            // Prepare request options
            const requestOptions = {
                method: formElement.method || 'POST',
                body: formData,
                ...options.requestOptions
            };

            // Make request
            const response = await this.makeRequest(
                formElement.action || window.location.href,
                requestOptions
            );

            // Handle success
            if (options.onSuccess) {
                options.onSuccess(response, formElement);
            } else {
                const message = response.message || 'Operation completed successfully';
                this.showToast(message, 'success');
                
                // Close modal if form is in a modal
                const modal = formElement.closest('.modal');
                if (modal) {
                    this.hideModal(modal.id);
                }
                
                // Optionally reload page or update UI
                if (options.reload !== false) {
                    setTimeout(() => window.location.reload(), 1000);
                }
            }

            return response;

        } catch (error) {
            // Handle error
            if (options.onError) {
                options.onError(error, formElement);
            } else {
                this.showToast(error.message || 'An error occurred', 'error');
                this.showFormErrors(formElement, error.errors);
            }
            throw error;

        } finally {
            // Reset loading state
            this.hideLoadingState(formElement, submitBtn, loadingOverlay);
        }
    }

    /**
     * Create loading overlay for form
     * @param {HTMLFormElement} form - Form element
     */
    createLoadingOverlay(form) {
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay position-absolute top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center';
        overlay.style.cssText = 'background: rgba(255,255,255,0.8); z-index: 1000; display: none;';
        overlay.innerHTML = `
            <div class="text-center">
                <div class="spinner-border text-primary mb-2" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div class="small text-muted">Processing...</div>
            </div>
        `;
        
        // Make form container relative if not already
        const container = form.closest('.modal-body') || form.parentNode;
        if (getComputedStyle(container).position === 'static') {
            container.style.position = 'relative';
        }
        
        container.appendChild(overlay);
        return overlay;
    }

    /**
     * Show loading state for form submission
     * @param {HTMLFormElement} form - Form element
     * @param {HTMLButtonElement} submitBtn - Submit button
     * @param {HTMLElement} overlay - Loading overlay
     */
    showLoadingState(form, submitBtn, overlay) {
        // Disable form inputs
        const inputs = form.querySelectorAll('input, select, textarea, button');
        inputs.forEach(input => {
            input.disabled = true;
            input.setAttribute('data-was-disabled', input.disabled);
        });

        // Update submit button
        if (submitBtn) {
            const originalText = submitBtn.innerHTML;
            submitBtn.setAttribute('data-original-text', originalText);
            submitBtn.innerHTML = `
                <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                Processing...
            `;
        }

        // Show overlay
        if (overlay) {
            overlay.style.display = 'flex';
        }
    }

    /**
     * Hide loading state after form submission
     * @param {HTMLFormElement} form - Form element
     * @param {HTMLButtonElement} submitBtn - Submit button
     * @param {HTMLElement} overlay - Loading overlay
     */
    hideLoadingState(form, submitBtn, overlay) {
        // Re-enable form inputs
        const inputs = form.querySelectorAll('input, select, textarea, button');
        inputs.forEach(input => {
            const wasDisabled = input.getAttribute('data-was-disabled') === 'true';
            input.disabled = wasDisabled;
            input.removeAttribute('data-was-disabled');
        });

        // Restore submit button
        if (submitBtn) {
            const originalText = submitBtn.getAttribute('data-original-text');
            if (originalText) {
                submitBtn.innerHTML = originalText;
                submitBtn.removeAttribute('data-original-text');
            }
        }

        // Hide overlay
        if (overlay) {
            overlay.style.display = 'none';
            setTimeout(() => overlay.remove(), 100);
        }
    }

    /**
     * Show loading indicator for AJAX operations
     * @param {string} message - Loading message
     * @param {HTMLElement} container - Container element
     */
    showLoadingIndicator(message = 'Loading...', container = document.body) {
        const loadingId = `loading_${Date.now()}`;
        const loadingHtml = `
            <div id="${loadingId}" class="loading-indicator position-fixed top-50 start-50 translate-middle" style="z-index: 2000;">
                <div class="card shadow">
                    <div class="card-body text-center p-4">
                        <div class="spinner-border text-primary mb-3" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <div class="fw-medium">${message}</div>
                    </div>
                </div>
            </div>
        `;
        
        container.insertAdjacentHTML('beforeend', loadingHtml);
        return document.getElementById(loadingId);
    }

    /**
     * Hide loading indicator
     * @param {HTMLElement} indicator - Loading indicator element
     */
    hideLoadingIndicator(indicator) {
        if (indicator) {
            indicator.remove();
        }
    }

    /**
     * Make HTTP request with error handling
     * @param {string} url - Request URL
     * @param {Object} options - Request options
     */
    async makeRequest(url, options = {}) {
        const defaultHeaders = {
            'X-Requested-With': 'XMLHttpRequest'
        };
        const method = (options.method || 'GET').toUpperCase();

        // Add CSRF token if available
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content ||
                         document.querySelector('input[name="csrf_token"]')?.value;
        if (csrfToken && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
            defaultHeaders['X-CSRFToken'] = csrfToken;
        }

        const requestOptions = {
            credentials: 'same-origin',
            headers: {
                ...defaultHeaders,
                ...options.headers
            },
            ...options
        };

        // Don't set Content-Type for FormData
        if (!(requestOptions.body instanceof FormData) && requestOptions.body && typeof requestOptions.body === 'object') {
            requestOptions.headers['Content-Type'] = 'application/json';
            requestOptions.body = JSON.stringify(requestOptions.body);
        }

        try {
            const response = await fetch(url, requestOptions);
            
            if (!response.ok) {
                const errorData = await this.parseErrorResponse(response);
                const error = new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
                error.status = response.status;
                error.errors = errorData.errors;
                throw error;
            }

            return await this.parseResponse(response);

        } catch (error) {
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                throw new Error('Network error. Please check your connection.');
            }
            throw error;
        }
    }

    /**
     * Parse response based on content type
     * @param {Response} response - Fetch response
     */
    async parseResponse(response) {
        const contentType = response.headers.get('content-type');

        // Read body as text once and parse as needed to avoid JSON parser hard failures.
        const rawBody = await response.text();
        if (contentType?.includes('application/json')) {
            if (!rawBody) {
                return {};
            }
            try {
                return JSON.parse(rawBody);
            } catch (error) {
                return { message: rawBody };
            }
        } else if (contentType?.includes('text/html')) {
            return rawBody;
        } else {
            return rawBody;
        }
    }

    /**
     * Parse error payload into a safe object shape for callers.
     * @param {Response} response - Fetch response
     */
    async parseErrorResponse(response) {
        const parsed = await this.parseResponse(response);
        if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
            const fallbackMessage = `HTTP ${response.status}: ${response.statusText}`;
            let message = parsed.message || parsed.error || fallbackMessage;
            if (response.status === 400 && /csrf/i.test(String(message))) {
                message = 'Session expired. Please refresh the page and try again.';
            }
            return { ...parsed, message };
        }

        const text = String(parsed || '').trim();
        const looksLikeHtml = text.startsWith('<!DOCTYPE') || text.startsWith('<html');
        let message = looksLikeHtml ? `HTTP ${response.status}: ${response.statusText}` : text;
        if (!message) {
            message = `HTTP ${response.status}: ${response.statusText}`;
        }
        if (response.status === 400 && /csrf/i.test(message)) {
            message = 'Session expired. Please refresh the page and try again.';
        }
        return { message };
    }

    /**
     * Show form validation errors with enhanced accessibility
     * @param {HTMLFormElement} form - Form element
     * @param {Object} errors - Validation errors
     */
    showFormErrors(form, errors) {
        if (!errors || typeof errors !== 'object') return;

        // Clear previous errors
        this.clearFormErrors(form);

        let firstInvalidField = null;
        const errorMessages = [];

        // Show new errors
        Object.entries(errors).forEach(([field, messages]) => {
            const input = form.querySelector(`[name="${field}"]`);
            if (input) {
                input.classList.add('is-invalid');
                input.classList.remove('is-valid');
                
                // Get field label for better error messages
                const label = input.labels?.[0]?.textContent || 
                             form.querySelector(`label[for="${input.id}"]`)?.textContent ||
                             field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                
                const errorMessage = Array.isArray(messages) ? messages[0] : messages;
                errorMessages.push(`${label}: ${errorMessage}`);
                
                // Find or create error container
                const errorId = input.getAttribute('aria-describedby')?.split(' ').find(id => id.includes('error')) ||
                               `${input.id || field}_error`;
                let errorDiv = document.getElementById(errorId);
                
                if (!errorDiv) {
                    errorDiv = document.createElement('div');
                    errorDiv.id = errorId;
                    errorDiv.className = 'invalid-feedback';
                    
                    // Insert after the input or its parent container
                    const container = input.closest('.form-group') || input.closest('.mb-3') || input.parentNode;
                    container.appendChild(errorDiv);
                    
                    // Update aria-describedby
                    const currentDescribedBy = input.getAttribute('aria-describedby') || '';
                    input.setAttribute('aria-describedby', `${currentDescribedBy} ${errorId}`.trim());
                }
                
                errorDiv.className = 'invalid-feedback d-block';
                errorDiv.setAttribute('role', 'alert');
                errorDiv.setAttribute('aria-live', 'assertive');
                errorDiv.innerHTML = `<i class="fas fa-exclamation-triangle me-1" aria-hidden="true"></i>${errorMessage}`;
                
                // Add error styling to form group
                const container = input.closest('.form-group') || input.closest('.mb-3') || input.parentNode;
                container.classList.add('has-error');
                
                // Mark input as invalid for screen readers
                input.setAttribute('aria-invalid', 'true');
                
                // Track first invalid field
                if (!firstInvalidField) {
                    firstInvalidField = input;
                }
            }
        });
        
        // Focus first invalid field and announce errors
        if (firstInvalidField) {
            firstInvalidField.focus();
            
            // Announce validation errors to screen readers
            const errorSummary = errorMessages.length > 1 
                ? `Form has ${errorMessages.length} errors: ${errorMessages.join(', ')}`
                : `Form error: ${errorMessages[0]}`;
                
            this.announceToScreenReader(errorSummary, 'assertive');
            
            // Show error toast with summary
            this.showToast(
                errorMessages.length > 1 
                    ? `Please correct ${errorMessages.length} form errors`
                    : errorMessages[0],
                'error'
            );
        } else if (Object.keys(errors).length === 0) {
            this.showToast('Please correct the form errors and try again.', 'error');
        }
    }

    /**
     * Clear form validation errors with accessibility cleanup
     * @param {HTMLFormElement} form - Form element
     */
    clearFormErrors(form) {
        // Remove validation classes and ARIA attributes
        form.querySelectorAll('.is-invalid, .is-valid').forEach(el => {
            el.classList.remove('is-invalid', 'is-valid');
            el.removeAttribute('aria-invalid');
            
            // Clean up aria-describedby
            const describedBy = el.getAttribute('aria-describedby');
            if (describedBy) {
                const cleanedDescribedBy = describedBy
                    .split(' ')
                    .filter(id => !id.includes('error'))
                    .join(' ')
                    .trim();
                
                if (cleanedDescribedBy) {
                    el.setAttribute('aria-describedby', cleanedDescribedBy);
                } else {
                    el.removeAttribute('aria-describedby');
                }
            }
        });
        
        // Remove error feedback elements
        form.querySelectorAll('.invalid-feedback, .valid-feedback').forEach(el => {
            el.remove();
        });
        
        // Remove error styling from form groups
        form.querySelectorAll('.has-error').forEach(el => {
            el.classList.remove('has-error');
        });
    }

    /**
     * Add real-time validation to form fields
     * @param {HTMLFormElement} form - Form element
     */
    addRealTimeValidation(form) {
        const inputs = form.querySelectorAll('input, select, textarea');
        
        inputs.forEach(input => {
            // Skip hidden inputs
            if (input.type === 'hidden') return;
            
            input.addEventListener('blur', () => {
                this.validateField(input);
            });
            
            input.addEventListener('input', () => {
                // Clear error state on input
                if (input.classList.contains('is-invalid')) {
                    input.classList.remove('is-invalid');
                    const feedback = input.parentNode.querySelector('.invalid-feedback');
                    if (feedback) feedback.remove();
                }
            });
        });
    }

    /**
     * Validate individual form field
     * @param {HTMLInputElement} input - Input element
     */
    validateField(input) {
        const value = input.value.trim();
        const isRequired = input.hasAttribute('required');
        const type = input.type;
        
        // Clear previous validation
        input.classList.remove('is-invalid', 'is-valid');
        const existingFeedback = input.parentNode.querySelector('.invalid-feedback');
        if (existingFeedback) existingFeedback.remove();
        
        let isValid = true;
        let errorMessage = '';
        
        // Required field validation
        if (isRequired && !value) {
            isValid = false;
            errorMessage = 'This field is required.';
        }
        // Email validation
        else if (type === 'email' && value && !this.isValidEmail(value)) {
            isValid = false;
            errorMessage = 'Please enter a valid email address.';
        }
        // Phone validation
        else if (input.name === 'phone' && value && !this.isValidPhone(value)) {
            isValid = false;
            errorMessage = 'Please enter a valid phone number.';
        }
        // Number validation
        else if (type === 'number' && value && isNaN(value)) {
            isValid = false;
            errorMessage = 'Please enter a valid number.';
        }
        // URL validation
        else if (type === 'url' && value && !this.isValidUrl(value)) {
            isValid = false;
            errorMessage = 'Please enter a valid URL.';
        }
        
        // Apply validation styling
        if (isValid && value) {
            input.classList.add('is-valid');
        } else if (!isValid) {
            input.classList.add('is-invalid');
            
            const errorDiv = document.createElement('div');
            errorDiv.className = 'invalid-feedback d-block';
            errorDiv.innerHTML = `<i class="fas fa-exclamation-triangle me-1"></i>${errorMessage}`;
            input.parentNode.appendChild(errorDiv);
        }
        
        return isValid;
    }

    /**
     * Validate email format
     * @param {string} email - Email to validate
     */
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    /**
     * Validate phone format
     * @param {string} phone - Phone to validate
     */
    isValidPhone(phone) {
        const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
        return phoneRegex.test(phone.replace(/[\s\-\(\)]/g, ''));
    }

    /**
     * Validate URL format
     * @param {string} url - URL to validate
     */
    isValidUrl(url) {
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    }

    /**
     * Bind form submission events with enhanced validation
     * @param {HTMLFormElement} form - Form element
     * @param {Function} onSubmit - Submit callback
     */
    bindFormSubmission(form, onSubmit) {
        // Add real-time validation
        this.addRealTimeValidation(form);
        
        // Bind submit event
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Validate form before submission
            if (!this.validateForm(form)) {
                this.showToast('Please correct the form errors before submitting.', 'error');
                return;
            }
            
            try {
                if (onSubmit) {
                    await onSubmit(form, this);
                } else {
                    await this.submitForm(form);
                }
            } catch (error) {
                console.error('Form submission error:', error);
            }
        });
        
        // Prevent double submission
        form.addEventListener('submit', (e) => {
            const submitBtn = form.querySelector('[type="submit"], .btn-primary');
            if (submitBtn && submitBtn.disabled) {
                e.preventDefault();
                return false;
            }
        });
    }

    /**
     * Validate entire form
     * @param {HTMLFormElement} form - Form element
     */
    validateForm(form) {
        const inputs = form.querySelectorAll('input:not([type="hidden"]), select, textarea');
        let isValid = true;
        
        inputs.forEach(input => {
            if (!this.validateField(input)) {
                isValid = false;
            }
        });
        
        return isValid;
    }

    /**
     * Bind global events
     */
    bindGlobalEvents() {
        // Handle modal show events
        document.addEventListener('show.bs.modal', (e) => {
            const modal = e.target;
            const modalId = modal.id;
            
            // Auto-focus first input
            modal.addEventListener('shown.bs.modal', () => {
                const firstInput = modal.querySelector('input:not([type="hidden"]), select, textarea');
                if (firstInput) {
                    firstInput.focus();
                }
            });
        });

        // Handle delete button clicks
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-action="delete"]') || e.target.closest('[data-action="delete"]')) {
                e.preventDefault();
                const button = e.target.matches('[data-action="delete"]') ? e.target : e.target.closest('[data-action="delete"]');
                const message = button.dataset.message || 'Are you sure you want to delete this item?';
                const url = button.dataset.url || button.href;
                
                this.confirmDelete(message, async () => {
                    try {
                        await this.makeRequest(url, { method: 'DELETE' });
                        this.showToast('Item deleted successfully', 'success');
                        
                        // Reload page or remove element
                        if (button.dataset.reload !== 'false') {
                            window.location.reload();
                        } else {
                            const row = button.closest('tr, .card, .list-group-item');
                            if (row) row.remove();
                        }
                    } catch (error) {
                        this.showToast(error.message, 'error');
                    }
                });
            }
        });
    }

    /**
     * Utility method to get CSRF token
     */
    getCSRFToken() {
        return document.querySelector('meta[name="csrf-token"]')?.content ||
               document.querySelector('input[name="csrf_token"]')?.value ||
               '';
    }

    /**
     * Request a copilot matchmaker pitch for a customer.
     * @param {number|string} customerId - Customer id
     * @param {Object} payload - Optional scoring filters
     */
    async generateCopilotPitch(customerId, payload = {}) {
        const id = Number(customerId);
        if (!Number.isFinite(id) || id <= 0) {
            throw new Error('Valid customer id is required.');
        }
        return this.makeRequest(`/api/v1/copilot/matchmaker/${id}`, {
            method: 'POST',
            body: {
                max_results: Number(payload.max_results) > 0 ? Number(payload.max_results) : 3,
                min_property_score: Number(payload.min_property_score) >= 0 ? Number(payload.min_property_score) : 50
            }
        });
    }

    /**
     * Utility method to format validation errors for display
     * @param {Object} errors - Validation errors object
     */
    formatErrors(errors) {
        if (!errors || typeof errors !== 'object') return '';
        
        return Object.entries(errors)
            .map(([field, messages]) => {
                const fieldName = field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                const errorList = Array.isArray(messages) ? messages : [messages];
                return `${fieldName}: ${errorList.join(', ')}`;
            })
            .join('\n');
    }
}

// Store the original class for module exports
const CRUDUtilsClass = CRUDUtils;

// Initialize global instance
const crudUtilsInstance = new CRUDUtilsClass();
window.crudUtils = crudUtilsInstance;

// Create a wrapper object that exposes instance methods as if they were static
window.CRUDUtils = {
    // Expose all instance methods
    loadModal: (...args) => crudUtilsInstance.loadModal(...args),
    loadEditModal: (...args) => crudUtilsInstance.loadEditModal(...args),
    showModal: (...args) => crudUtilsInstance.showModal(...args),
    hideModal: (...args) => crudUtilsInstance.hideModal(...args),
    showToast: (...args) => crudUtilsInstance.showToast(...args),
    confirmDelete: (...args) => crudUtilsInstance.confirmDelete(...args),
    submitForm: (...args) => crudUtilsInstance.submitForm(...args),
    makeRequest: (...args) => crudUtilsInstance.makeRequest(...args),
    showFormErrors: (...args) => crudUtilsInstance.showFormErrors(...args),
    clearFormErrors: (...args) => crudUtilsInstance.clearFormErrors(...args),
    bindFormSubmission: (...args) => crudUtilsInstance.bindFormSubmission(...args),
    validateForm: (...args) => crudUtilsInstance.validateForm(...args),
    validateField: (...args) => crudUtilsInstance.validateField(...args),
    showLoadingIndicator: (...args) => crudUtilsInstance.showLoadingIndicator(...args),
    hideLoadingIndicator: (...args) => crudUtilsInstance.hideLoadingIndicator(...args),
    announceToScreenReader: (...args) => crudUtilsInstance.announceToScreenReader(...args),
    getCSRFToken: (...args) => crudUtilsInstance.getCSRFToken(...args),
    generateCopilotPitch: (...args) => crudUtilsInstance.generateCopilotPitch(...args),
    formatErrors: (...args) => crudUtilsInstance.formatErrors(...args),
    
    // Also expose the instance itself for advanced usage
    instance: crudUtilsInstance
};

// Ensure the methods are available (for debugging)
if (typeof window.CRUDUtils.loadModal !== 'function') {
    console.error('loadModal method not found on CRUDUtils');
} else {
    console.log('CRUDUtils methods successfully exposed');
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CRUDUtilsClass;
}
} else {
    console.warn('crud-utils.js already initialized; skipping duplicate bootstrap.');
}
