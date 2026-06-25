/**
 * Button Fixes - Common solutions for button response issues
 */

class ButtonFixes {
    constructor() {
        this.init();
    }

    init() {
        console.log('Button Fixes initialized');
        this.setupGlobalErrorHandling();
        this.fixCommonIssues();
    }

    /**
     * Fix buttons that don't respond
     */
    fixUnresponsiveButtons() {
        console.log('Fixing unresponsive buttons...');
        
        // Find buttons without event listeners
        const buttons = document.querySelectorAll('button, input[type="button"], input[type="submit"]');
        
        buttons.forEach(button => {
            if (!this.hasEventListener(button) && !button.disabled) {
                console.log('Found unresponsive button:', button);
                
                // Add basic click handler if missing
                if (!button.onclick && !button.getAttribute('data-bs-toggle')) {
                    button.addEventListener('click', function(e) {
                        console.log('Button clicked (fixed):', e.target);
                        
                        // Handle form submission buttons
                        if (this.type === 'submit' && this.form) {
                            this.form.submit();
                        }
                        
                        // Handle modal triggers
                        if (this.getAttribute('data-bs-target')) {
                            const targetModal = document.querySelector(this.getAttribute('data-bs-target'));
                            if (targetModal) {
                                const modal = new bootstrap.Modal(targetModal);
                                modal.show();
                            }
                        }
                    });
                }
            }
        });
    }

    /**
     * Fix modal buttons
     */
    fixModalButtons() {
        console.log('Fixing modal buttons...');
        
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            // Fix close buttons
            const closeButtons = modal.querySelectorAll('[data-bs-dismiss="modal"]');
            closeButtons.forEach(btn => {
                if (!this.hasEventListener(btn)) {
                    btn.addEventListener('click', () => {
                        const modalInstance = bootstrap.Modal.getInstance(modal);
                        if (modalInstance) {
                            modalInstance.hide();
                        }
                    });
                }
            });

            // Fix form submission in modals
            const forms = modal.querySelectorAll('form');
            forms.forEach(form => {
                if (!form.hasAttribute('data-crud-bound')) {
                    form.addEventListener('submit', async (e) => {
                        e.preventDefault();
                        
                        try {
                            const formData = new FormData(form);
                            const response = await fetch(form.action, {
                                method: form.method || 'POST',
                                body: formData,
                                headers: {
                                    'X-Requested-With': 'XMLHttpRequest'
                                }
                            });

                            if (response.ok) {
                                // Show success message
                                if (window.CRUDUtils) {
                                    window.CRUDUtils.showToast('Changes saved successfully!', 'success');
                                } else {
                                    alert('Changes saved successfully!');
                                }
                                
                                // Close modal
                                const modalInstance = bootstrap.Modal.getInstance(modal);
                                if (modalInstance) {
                                    modalInstance.hide();
                                }
                                
                                // Reload page
                                setTimeout(() => window.location.reload(), 1000);
                            } else {
                                throw new Error(`HTTP ${response.status}`);
                            }
                        } catch (error) {
                            console.error('Form submission error:', error);
                            if (window.CRUDUtils) {
                                window.CRUDUtils.showToast('Error saving changes', 'error');
                            } else {
                                alert('Error saving changes');
                            }
                        }
                    });
                    
                    form.setAttribute('data-crud-bound', 'true');
                }
            });
        });
    }

    /**
     * Fix AJAX buttons
     */
    fixAjaxButtons() {
        console.log('Fixing AJAX buttons...');
        
        // Fix buttons with data-url attributes
        const ajaxButtons = document.querySelectorAll('[data-url]');
        ajaxButtons.forEach(button => {
            if (!this.hasEventListener(button)) {
                button.addEventListener('click', async (e) => {
                    e.preventDefault();
                    
                    const url = button.getAttribute('data-url');
                    const method = button.getAttribute('data-method') || 'GET';
                    
                    try {
                        button.disabled = true;
                        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Loading...';
                        
                        const response = await fetch(url, {
                            method: method,
                            headers: {
                                'X-Requested-With': 'XMLHttpRequest',
                                'Content-Type': 'application/json'
                            }
                        });

                        if (response.ok) {
                            const data = await response.json();
                            console.log('AJAX response:', data);
                            
                            // Show success message
                            if (window.CRUDUtils) {
                                window.CRUDUtils.showToast(data.message || 'Action completed', 'success');
                            }
                            
                            // Reload if needed
                            if (button.getAttribute('data-reload') === 'true') {
                                setTimeout(() => window.location.reload(), 1000);
                            }
                        } else {
                            throw new Error(`HTTP ${response.status}`);
                        }
                    } catch (error) {
                        console.error('AJAX error:', error);
                        if (window.CRUDUtils) {
                            window.CRUDUtils.showToast('Action failed', 'error');
                        }
                    } finally {
                        button.disabled = false;
                        button.innerHTML = button.getAttribute('data-original-text') || 'Action';
                    }
                });
                
                // Store original text
                button.setAttribute('data-original-text', button.innerHTML);
            }
        });
    }

    /**
     * Fix delete buttons
     */
    fixDeleteButtons() {
        console.log('Fixing delete buttons...');
        
        const deleteButtons = document.querySelectorAll('[data-action="delete"], .btn-delete, .delete-btn');
        deleteButtons.forEach(button => {
            if (!this.hasEventListener(button)) {
                button.addEventListener('click', (e) => {
                    e.preventDefault();
                    
                    const confirmMessage = button.getAttribute('data-confirm') || 'Are you sure you want to delete this item?';
                    
                    if (confirm(confirmMessage)) {
                        const url = button.getAttribute('data-url') || button.href;
                        const form = button.closest('form');
                        
                        if (form) {
                            // Submit form
                            form.submit();
                        } else if (url) {
                            // AJAX delete
                            this.performDelete(url, button);
                        }
                    }
                });
            }
        });
    }

    /**
     * Perform AJAX delete
     */
    async performDelete(url, button) {
        try {
            button.disabled = true;
            
            const response = await fetch(url, {
                method: 'DELETE',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                // Remove element from DOM
                const row = button.closest('tr') || button.closest('.card') || button.closest('.list-group-item');
                if (row) {
                    row.remove();
                }
                
                if (window.CRUDUtils) {
                    window.CRUDUtils.showToast('Item deleted successfully', 'success');
                }
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.error('Delete error:', error);
            if (window.CRUDUtils) {
                window.CRUDUtils.showToast('Delete failed', 'error');
            }
            button.disabled = false;
        }
    }

    /**
     * Check if button has event listener
     */
    hasEventListener(button) {
        return !!(
            button.onclick ||
            button.getAttribute('data-bs-toggle') ||
            button.getAttribute('data-bs-dismiss') ||
            button.getAttribute('onclick') ||
            (button.type === 'submit' && button.form)
        );
    }

    /**
     * Setup global error handling
     */
    setupGlobalErrorHandling() {
        // Catch unhandled button click errors
        document.addEventListener('click', (e) => {
            if (e.target.tagName === 'BUTTON' || e.target.type === 'button') {
                setTimeout(() => {
                    // Check if button action caused any errors
                    if (window.lastError) {
                        console.error('Button action error:', window.lastError);
                        if (window.CRUDUtils) {
                            window.CRUDUtils.showToast('Button action failed', 'error');
                        }
                        window.lastError = null;
                    }
                }, 100);
            }
        });

        // Catch JavaScript errors
        window.addEventListener('error', (e) => {
            window.lastError = e.error;
        });
    }

    /**
     * Fix all common issues
     */
    fixCommonIssues() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.runAllFixes();
            });
        } else {
            this.runAllFixes();
        }
    }

    /**
     * Run all fixes
     */
    runAllFixes() {
        setTimeout(() => {
            this.fixUnresponsiveButtons();
            this.fixModalButtons();
            this.fixAjaxButtons();
            this.fixDeleteButtons();
            console.log('All button fixes applied');
        }, 500);
    }

    /**
     * Manual fix trigger
     */
    fixAllButtons() {
        console.log('Running manual button fixes...');
        this.runAllFixes();
    }
}

// Initialize button fixes
window.buttonFixes = new ButtonFixes();

// Expose fix function globally
window.fixAllButtons = () => window.buttonFixes.fixAllButtons();