/**
 * Property Edit Modal Enhanced Validation and Functionality
 * Implements real-time validation, error handling, and user feedback
 */

/**
 * Enhanced Property Edit Modal System
 */
class PropertyEditModal {
    constructor() {
        this.modal = document.getElementById('propertyEditModal');
        this.form = document.getElementById('propertyEditForm');
        this.isInitialized = false;
        
        if (this.modal) {
            this.init();
        }
    }
    
    init() {
        // Initialize modal functionality when shown
        this.modal.addEventListener('shown.bs.modal', () => {
            if (!this.isInitialized) {
                this.initializeComponents();
                this.isInitialized = true;
            }
            this.focusFirstInput();
        });
        
        // Reset initialization flag when modal is hidden
        this.modal.addEventListener('hidden.bs.modal', () => {
            this.isInitialized = false;
            this.clearValidationStates();
        });
    }
    
    initializeComponents() {
        this.initializePricingToggle();
        this.initializeRealTimeValidation();
        this.initializeCharacterCounters();
        this.initializePriceCalculations();
        this.initializeFormSubmission();
        this.initializeAgentDropdown();
    }
    
    focusFirstInput() {
        const firstInput = this.modal.querySelector('input[type="text"]');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }
    
    /**
     * Initialize pricing section toggle functionality
     */
    initializePricingToggle() {
        const saleRadio = document.getElementById('edit_listing_sale');
        const rentalRadio = document.getElementById('edit_listing_rental');
        const salePricing = document.getElementById('edit-sale-pricing');
        const rentalPricing = document.getElementById('edit-rental-pricing');
        
        const togglePricingSection = () => {
            if (saleRadio && rentalRadio && salePricing && rentalPricing) {
                if (saleRadio.checked) {
                    salePricing.style.display = 'block';
                    rentalPricing.style.display = 'none';
                    // Clear rental validation errors
                    this.clearFieldErrors(['edit_rahn', 'edit_ejare']);
                    const rentalError = document.getElementById('rental_pricing_error');
                    if (rentalError) rentalError.textContent = '';
                } else {
                    salePricing.style.display = 'none';
                    rentalPricing.style.display = 'block';
                    // Clear sale validation errors
                    this.clearFieldErrors(['edit_sale_price']);
                }
                // Recalculate prices and revalidate
                this.calculatePricePerMeter();
                this.validatePricing();
            }
        };
        
        if (saleRadio && rentalRadio) {
            saleRadio.addEventListener('change', togglePricingSection);
            rentalRadio.addEventListener('change', togglePricingSection);
            // Initial toggle
            togglePricingSection();
        }
    }
    
    /**
     * Initialize real-time field validation
     */
    initializeRealTimeValidation() {
        if (!this.form) return;
        
        // Add validation to all fields with data-validate attribute
        const validatedFields = this.form.querySelectorAll('[data-validate]');
        
        validatedFields.forEach(field => {
            // Validate on blur (when user leaves field)
            field.addEventListener('blur', () => this.validateField(field));
            
            // Validate on input for certain field types
            if (field.type === 'text' || field.type === 'number' || field.tagName === 'TEXTAREA') {
                field.addEventListener('input', this.debounce(() => this.validateField(field), 500));
            }
            
            // Validate immediately on change for selects and radios
            if (field.type === 'select-one' || field.type === 'radio') {
                field.addEventListener('change', () => this.validateField(field));
            }
        });
        
        // Special validation for pricing fields
        ['edit_sale_price', 'edit_rahn', 'edit_ejare'].forEach(id => {
            const field = document.getElementById(id);
            if (field) {
                field.addEventListener('input', this.debounce(() => {
                    this.validateField(field);
                    this.validatePricing();
                    this.calculatePricePerMeter();
                }, 300));
            }
        });
        
        // Validate form button
        const validateBtn = document.getElementById('validateFormBtn');
        if (validateBtn) {
            validateBtn.addEventListener('click', () => {
                const isValid = this.validateEntireForm();
                this.showNotification(
                    isValid ? 'Form validation passed!' : 'Please fix validation errors before submitting',
                    isValid ? 'success' : 'warning'
                );
            });
        }
    }
    
    /**
     * Validate individual field
     */
    validateField(field) {
        const validationType = field.getAttribute('data-validate');
        const value = field.value.trim();
        let isValid = true;
        let errorMessage = '';
        
        // Clear previous validation state
        field.classList.remove('is-valid', 'is-invalid');
        
        switch (validationType) {
            case 'required':
                if (!value) {
                    isValid = false;
                    errorMessage = `${this.getFieldLabel(field)} is required`;
                }
                break;
                
            case 'length':
                const maxLength = parseInt(field.getAttribute('data-max')) || 255;
                if (value.length > maxLength) {
                    isValid = false;
                    errorMessage = `${this.getFieldLabel(field)} must be ${maxLength} characters or less`;
                }
                break;
                
            case 'range':
                const min = parseInt(field.getAttribute('data-min')) || 0;
                const max = parseInt(field.getAttribute('data-max')) || 999999;
                const numValue = parseFloat(value);
                if (value && (isNaN(numValue) || numValue < min || numValue > max)) {
                    isValid = false;
                    errorMessage = `${this.getFieldLabel(field)} must be between ${min} and ${max}`;
                }
                break;
                
            case 'year':
                const currentYear = new Date().getFullYear();
                const yearValue = parseInt(value);
                if (value && (isNaN(yearValue) || yearValue < 1800 || yearValue > currentYear + 10)) {
                    isValid = false;
                    errorMessage = `Year must be between 1800 and ${currentYear + 10}`;
                }
                break;
                
            case 'price':
                const priceValue = parseFloat(value);
                if (value && (isNaN(priceValue) || priceValue < 0)) {
                    isValid = false;
                    errorMessage = 'Price must be a positive number';
                }
                break;
                
            case 'rental-price':
                const rentalValue = parseFloat(value);
                if (value && (isNaN(rentalValue) || rentalValue < 0)) {
                    isValid = false;
                    errorMessage = 'Amount must be a positive number';
                }
                break;
        }
        
        // Apply validation state
        if (isValid && value) {
            field.classList.add('is-valid');
        } else if (!isValid) {
            field.classList.add('is-invalid');
            const feedback = field.parentNode.querySelector('.invalid-feedback') || 
                           field.closest('.input-group')?.querySelector('.invalid-feedback');
            if (feedback) {
                feedback.textContent = errorMessage;
            }
        }
        
        return isValid;
    }
    
    /**
     * Validate pricing based on listing type
     */
    validatePricing() {
        const listingType = document.querySelector('input[name="listing_type"]:checked')?.value;
        const salePrice = document.getElementById('edit_sale_price');
        const rahn = document.getElementById('edit_rahn');
        const ejare = document.getElementById('edit_ejare');
        const rentalError = document.getElementById('rental_pricing_error');
        
        if (listingType === 'sale') {
            // Validate sale price is required and positive
            if (salePrice && (!salePrice.value || parseFloat(salePrice.value) <= 0)) {
                salePrice.classList.add('is-invalid');
                const feedback = salePrice.closest('.input-group')?.querySelector('.invalid-feedback');
                if (feedback) {
                    feedback.textContent = 'Sale price is required and must be greater than 0';
                }
                return false;
            }
        } else if (listingType === 'rental') {
            // Validate at least one rental price is provided
            const rahnValue = parseFloat(rahn?.value || 0);
            const ejareValue = parseFloat(ejare?.value || 0);
            
            if (rahnValue <= 0 && ejareValue <= 0) {
                if (rentalError) {
                    rentalError.textContent = 'Either Rahn (deposit) or Ejare (monthly rent) must be provided';
                    rentalError.style.display = 'block';
                }
                return false;
            } else {
                if (rentalError) {
                    rentalError.textContent = '';
                    rentalError.style.display = 'none';
                }
            }
        }
        
        return true;
    }
    
    /**
     * Validate entire form
     */
    validateEntireForm() {
        if (!this.form) return false;
        
        let isValid = true;
        const validatedFields = this.form.querySelectorAll('[data-validate]');
        
        // Validate all fields
        validatedFields.forEach(field => {
            if (!this.validateField(field)) {
                isValid = false;
            }
        });
        
        // Validate pricing
        if (!this.validatePricing()) {
            isValid = false;
        }
        
        // Validate required radio buttons
        const listingTypeChecked = this.form.querySelector('input[name="listing_type"]:checked');
        const listingTypeError = document.getElementById('listing_type_error');
        if (!listingTypeChecked) {
            if (listingTypeError) listingTypeError.textContent = 'Please select a listing type';
            isValid = false;
        } else {
            if (listingTypeError) listingTypeError.textContent = '';
        }
        
        return isValid;
    }
    
    /**
     * Initialize character counters
     */
    initializeCharacterCounters() {
        const counters = [
            { field: 'edit_address', counter: 'edit_address_count', max: 500 },
            { field: 'edit_property_features', counter: 'edit_features_count', max: 500 },
            { field: 'edit_description', counter: 'edit_description_count', max: 1000 }
        ];
        
        counters.forEach(({ field, counter, max }) => {
            const fieldEl = document.getElementById(field);
            const counterEl = document.getElementById(counter);
            
            if (fieldEl && counterEl) {
                const updateCounter = () => {
                    const length = fieldEl.value.length;
                    counterEl.textContent = length;
                    counterEl.className = length > max * 0.9 ? 'text-warning' : 'text-muted';
                };
                
                fieldEl.addEventListener('input', updateCounter);
                updateCounter(); // Initial count
            }
        });
    }
    
    /**
     * Initialize price calculations
     */
    initializePriceCalculations() {
        const calculatePricePerMeter = () => {
            const squareFeet = parseFloat(document.getElementById('edit_square_feet')?.value) || 0;
            
            if (squareFeet > 0) {
                // Sale price per meter
                const salePrice = parseFloat(document.getElementById('edit_sale_price')?.value) || 0;
                const salePricePerMeter = document.getElementById('edit_sale_price_per_meter');
                if (salePricePerMeter) {
                    if (salePrice > 0) {
                        salePricePerMeter.value = `$${(salePrice / squareFeet).toLocaleString(undefined, {maximumFractionDigits: 0})}/m²`;
                    } else {
                        salePricePerMeter.value = '';
                    }
                }
                
                // Rental price per meter
                const rahn = parseFloat(document.getElementById('edit_rahn')?.value) || 0;
                const ejare = parseFloat(document.getElementById('edit_ejare')?.value) || 0;
                
                const rahnPerMeter = document.getElementById('edit_rahn_per_meter');
                const ejarePerMeter = document.getElementById('edit_ejare_per_meter');
                
                if (rahnPerMeter) {
                    if (rahn > 0) {
                        rahnPerMeter.value = `${(rahn / squareFeet).toLocaleString()} تومان/m²`;
                    } else {
                        rahnPerMeter.value = '';
                    }
                }
                
                if (ejarePerMeter) {
                    if (ejare > 0) {
                        ejarePerMeter.value = `${(ejare / squareFeet).toLocaleString()} تومان/m²`;
                    } else {
                        ejarePerMeter.value = '';
                    }
                }
            } else {
                // Clear calculated fields
                ['edit_sale_price_per_meter', 'edit_rahn_per_meter', 'edit_ejare_per_meter'].forEach(id => {
                    const el = document.getElementById(id);
                    if (el) el.value = '';
                });
            }
        };
        
        // Store reference for external access
        this.calculatePricePerMeter = calculatePricePerMeter;
        
        // Add event listeners for price calculation
        ['edit_square_feet', 'edit_sale_price', 'edit_rahn', 'edit_ejare'].forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('input', this.debounce(calculatePricePerMeter, 300));
            }
        });
        
        // Initial calculation
        calculatePricePerMeter();
    }
    
    /**
     * Initialize form submission with enhanced error handling
     */
    initializeFormSubmission() {
        const submitBtn = document.getElementById('submitPropertyBtn');
        
        if (!this.form || !submitBtn) return;
        
        this.form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            // Clear previous alerts
            this.hideAlert('propertyEditErrorContainer');
            this.hideAlert('propertyEditSuccessContainer');
            
            // Validate form before submission
            if (!this.validateEntireForm()) {
                this.showAlert('propertyEditErrorContainer', 'Please fix all validation errors before submitting');
                return;
            }
            
            try {
                // Show loading state
                this.setSubmitButtonLoading(true);
                
                // Get property ID
                const propertyId = this.form.querySelector('[name="property_id"]').value;
                if (!propertyId) {
                    throw new Error('Property ID is missing');
                }
                
                // Prepare form data
                const formData = new FormData(this.form);
                
                // Submit form
                const response = await fetch(`/properties/${propertyId}`, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                const result = await response.json();
                
                if (!response.ok) {
                    throw new Error(result.message || `Server error: ${response.status}`);
                }
                
                // Show success message
                this.showAlert('propertyEditSuccessContainer', result.message || 'Property updated successfully!');
                
                // Show global notification
                this.showNotification('Property updated successfully!', 'success');
                
                // Close modal after delay
                setTimeout(() => {
                    const modalInstance = bootstrap.Modal.getInstance(this.modal);
                    if (modalInstance) {
                        modalInstance.hide();
                    }
                    
                    // Reload page to show updated data
                    setTimeout(() => {
                        window.location.reload();
                    }, 500);
                }, 1500);
                
            } catch (error) {
                console.error('Error updating property:', error);
                this.showAlert('propertyEditErrorContainer', error.message || 'Failed to update property');
                this.showNotification(error.message || 'Failed to update property', 'error');
            } finally {
                this.setSubmitButtonLoading(false);
            }
        });
    }
    
    /**
     * Initialize agent dropdown
     */
    async initializeAgentDropdown() {
        const agentSelect = document.getElementById('edit_agent_id');
        if (!agentSelect) return;
        
        // Load agents if not already populated
        if (agentSelect.children.length <= 1) {
            await this.loadAgents();
        }
    }
    
    /**
     * Load agents for dropdown
     */
    async loadAgents() {
        try {
            const response = await fetch('/api/agents', {
                headers: { 'Accept': 'application/json' }
            });
            
            if (response.ok) {
                const data = await response.json();
                const agentSelect = document.getElementById('edit_agent_id');
                
                if (data.agents && agentSelect) {
                    // Clear existing options except "Unassigned"
                    while (agentSelect.children.length > 1) {
                        agentSelect.removeChild(agentSelect.lastChild);
                    }
                    
                    // Add agent options
                    data.agents.forEach(agent => {
                        const option = document.createElement('option');
                        option.value = agent.id;
                        option.textContent = agent.name;
                        agentSelect.appendChild(option);
                    });
                }
            }
        } catch (error) {
            console.warn('Failed to load agents:', error);
        }
    }
    
    /**
     * Utility functions
     */
    getFieldLabel(field) {
        const label = field.closest('.mb-3')?.querySelector('label');
        return label ? label.textContent.replace('*', '').trim() : 'Field';
    }
    
    clearFieldErrors(fieldIds) {
        fieldIds.forEach(id => {
            const field = document.getElementById(id);
            if (field) {
                field.classList.remove('is-invalid');
                const feedback = field.parentNode.querySelector('.invalid-feedback') ||
                               field.closest('.input-group')?.querySelector('.invalid-feedback');
                if (feedback) feedback.textContent = '';
            }
        });
    }
    
    clearValidationStates() {
        if (!this.form) return;
        
        const fields = this.form.querySelectorAll('.is-valid, .is-invalid');
        fields.forEach(field => {
            field.classList.remove('is-valid', 'is-invalid');
        });
        
        const feedbacks = this.form.querySelectorAll('.invalid-feedback');
        feedbacks.forEach(feedback => {
            feedback.textContent = '';
        });
        
        // Clear alert containers
        this.hideAlert('propertyEditErrorContainer');
        this.hideAlert('propertyEditSuccessContainer');
    }
    
    setSubmitButtonLoading(loading) {
        const submitBtn = document.getElementById('submitPropertyBtn');
        const spinner = submitBtn?.querySelector('.spinner-border');
        
        if (submitBtn) {
            submitBtn.disabled = loading;
            if (spinner) {
                spinner.classList.toggle('d-none', !loading);
            }
        }
    }
    
    showAlert(containerId, message) {
        const container = document.getElementById(containerId);
        const messageEl = document.getElementById(containerId.replace('Container', 'Message'));
        
        if (container && messageEl) {
            messageEl.textContent = message;
            container.classList.remove('d-none');
        }
    }
    
    hideAlert(containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.classList.add('d-none');
        }
    }
    
    showNotification(message, type = 'info') {
        // Use global notification function if available
        if (typeof showNotification === 'function') {
            showNotification(message, type);
        } else {
            // Fallback to console
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }
    
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func.apply(this, args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Initialize the property edit modal system when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.propertyEditModal = new PropertyEditModal();
});