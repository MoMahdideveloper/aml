/**
 * Integration Tests for Property Edit Modal System
 * Tests the comprehensive property edit modal functionality including validation,
 * form submission, error handling, and user feedback
 */

describe('Property Edit Modal Integration Tests', () => {
    let mockProperty;
    let modal;
    let form;
    
    beforeEach(() => {
        // Setup DOM
        document.body.innerHTML = `
            <div id="propertyEditModal" class="modal">
                <div class="modal-content">
                    <form id="propertyEditForm">
                        <input type="hidden" name="property_id" value="">
                        <input type="text" id="edit_title" name="title" data-validate="required">
                        <select id="edit_property_type" name="property_type" data-validate="required">
                            <option value="">Select Type</option>
                            <option value="house">House</option>
                        </select>
                        <textarea id="edit_address" name="address" data-validate="required"></textarea>
                        <input type="radio" name="listing_type" id="edit_listing_sale" value="sale">
                        <input type="radio" name="listing_type" id="edit_listing_rental" value="rental">
                        <input type="number" id="edit_sale_price" name="sale_price" data-validate="price">
                        <input type="number" id="edit_rahn" name="rahn" data-validate="rental-price">
                        <input type="number" id="edit_ejare" name="ejare" data-validate="rental-price">
                        <input type="number" id="edit_square_feet" name="square_feet" data-validate="required">
                        <div id="propertyEditErrorContainer" class="d-none">
                            <span id="propertyEditErrorMessage"></span>
                        </div>
                        <div id="propertyEditSuccessContainer" class="d-none">
                            <span id="propertyEditSuccessMessage"></span>
                        </div>
                        <div id="listing_type_error"></div>
                        <div id="rental_pricing_error"></div>
                        <button type="submit" id="submitPropertyBtn">Submit</button>
                        <button type="button" id="validateFormBtn">Validate</button>
                    </form>
                </div>
            </div>
        `;
        
        // Mock property data
        mockProperty = {
            id: 1,
            title: 'Test Property',
            address: '123 Test St',
            property_type: 'house',
            listing_type: 'sale',
            price: 500000,
            square_feet: 2000,
            bedrooms: 3,
            bathrooms: 2
        };
        
        modal = document.getElementById('propertyEditModal');
        form = document.getElementById('propertyEditForm');
        
        // Mock global functions
        global.showNotification = jest.fn();
        global.bootstrap = {
            Modal: {
                getInstance: jest.fn(() => ({
                    hide: jest.fn()
                }))
            }
        };
        
        // Mock fetch
        global.fetch = jest.fn();
    });
    
    afterEach(() => {
        jest.clearAllMocks();
        document.body.innerHTML = '';
    });
    
    describe('Modal Initialization', () => {
        test('should initialize PropertyEditModal class', () => {
            // Load the PropertyEditModal class
            require('../static/js/property-edit-modal.js');
            
            expect(window.propertyEditModal).toBeDefined();
            expect(window.propertyEditModal.modal).toBe(modal);
            expect(window.propertyEditModal.form).toBe(form);
        });
        
        test('should setup event listeners on modal show', () => {
            require('../static/js/property-edit-modal.js');
            
            const spy = jest.spyOn(window.propertyEditModal, 'initializeComponents');
            
            // Trigger modal show event
            modal.dispatchEvent(new Event('shown.bs.modal'));
            
            expect(spy).toHaveBeenCalled();
        });
    });
    
    describe('Form Validation', () => {
        beforeEach(() => {
            require('../static/js/property-edit-modal.js');
            modal.dispatchEvent(new Event('shown.bs.modal'));
        });
        
        test('should validate required fields', () => {
            const titleField = document.getElementById('edit_title');
            
            // Test empty required field
            titleField.value = '';
            const isValid = window.propertyEditModal.validateField(titleField);
            
            expect(isValid).toBe(false);
            expect(titleField.classList.contains('is-invalid')).toBe(true);
        });
        
        test('should validate field length limits', () => {
            const titleField = document.getElementById('edit_title');
            titleField.setAttribute('data-validate', 'length');
            titleField.setAttribute('data-max', '10');
            
            // Test field exceeding max length
            titleField.value = 'This is a very long title that exceeds the limit';
            const isValid = window.propertyEditModal.validateField(titleField);
            
            expect(isValid).toBe(false);
            expect(titleField.classList.contains('is-invalid')).toBe(true);
        });
        
        test('should validate numeric ranges', () => {
            const squareFeetField = document.getElementById('edit_square_feet');
            squareFeetField.setAttribute('data-validate', 'range');
            squareFeetField.setAttribute('data-min', '1');
            squareFeetField.setAttribute('data-max', '10000');
            
            // Test value outside range
            squareFeetField.value = '15000';
            const isValid = window.propertyEditModal.validateField(squareFeetField);
            
            expect(isValid).toBe(false);
            expect(squareFeetField.classList.contains('is-invalid')).toBe(true);
        });
        
        test('should validate pricing based on listing type', () => {
            // Set listing type to sale
            document.getElementById('edit_listing_sale').checked = true;
            
            // Test missing sale price
            document.getElementById('edit_sale_price').value = '';
            const isValid = window.propertyEditModal.validatePricing();
            
            expect(isValid).toBe(false);
        });
        
        test('should validate rental pricing requirements', () => {
            // Set listing type to rental
            document.getElementById('edit_listing_rental').checked = true;
            
            // Test missing both rahn and ejare
            document.getElementById('edit_rahn').value = '';
            document.getElementById('edit_ejare').value = '';
            const isValid = window.propertyEditModal.validatePricing();
            
            expect(isValid).toBe(false);
            
            // Test with valid ejare
            document.getElementById('edit_ejare').value = '5000000';
            const isValidWithEjare = window.propertyEditModal.validatePricing();
            
            expect(isValidWithEjare).toBe(true);
        });
    });
    
    describe('Price Calculations', () => {
        beforeEach(() => {
            require('../static/js/property-edit-modal.js');
            modal.dispatchEvent(new Event('shown.bs.modal'));
            
            // Add calculated price display elements
            document.body.innerHTML += `
                <input type="text" id="edit_sale_price_per_meter" readonly>
                <input type="text" id="edit_rahn_per_meter" readonly>
                <input type="text" id="edit_ejare_per_meter" readonly>
            `;
        });
        
        test('should calculate sale price per square meter', () => {
            document.getElementById('edit_square_feet').value = '2000';
            document.getElementById('edit_sale_price').value = '500000';
            
            window.propertyEditModal.calculatePricePerMeter();
            
            const pricePerMeter = document.getElementById('edit_sale_price_per_meter');
            expect(pricePerMeter.value).toContain('250'); // 500000/2000 = 250
        });
        
        test('should calculate rental prices per square meter', () => {
            document.getElementById('edit_square_feet').value = '100';
            document.getElementById('edit_rahn').value = '1000000';
            document.getElementById('edit_ejare').value = '5000000';
            
            window.propertyEditModal.calculatePricePerMeter();
            
            const rahnPerMeter = document.getElementById('edit_rahn_per_meter');
            const ejarePerMeter = document.getElementById('edit_ejare_per_meter');
            
            expect(rahnPerMeter.value).toContain('10,000'); // 1000000/100 = 10000
            expect(ejarePerMeter.value).toContain('50,000'); // 5000000/100 = 50000
        });
    });
    
    describe('Form Submission', () => {
        beforeEach(() => {
            require('../static/js/property-edit-modal.js');
            modal.dispatchEvent(new Event('shown.bs.modal'));
        });
        
        test('should prevent submission with validation errors', async () => {
            // Setup invalid form
            document.getElementById('edit_title').value = '';
            form.querySelector('[name="property_id"]').value = '1';
            
            const submitEvent = new Event('submit');
            form.dispatchEvent(submitEvent);
            
            // Should not make fetch call due to validation errors
            expect(fetch).not.toHaveBeenCalled();
        });
        
        test('should submit valid form data', async () => {
            // Setup valid form
            document.getElementById('edit_title').value = 'Test Property';
            document.getElementById('edit_address').value = '123 Test St';
            document.getElementById('edit_property_type').value = 'house';
            document.getElementById('edit_listing_sale').checked = true;
            document.getElementById('edit_sale_price').value = '500000';
            document.getElementById('edit_square_feet').value = '2000';
            form.querySelector('[name="property_id"]').value = '1';
            
            // Mock successful response
            fetch.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ message: 'Property updated successfully!' })
            });
            
            const submitEvent = new Event('submit');
            form.dispatchEvent(submitEvent);
            
            // Wait for async operations
            await new Promise(resolve => setTimeout(resolve, 0));
            
            expect(fetch).toHaveBeenCalledWith('/properties/1', expect.objectContaining({
                method: 'POST',
                headers: expect.objectContaining({
                    'X-Requested-With': 'XMLHttpRequest'
                })
            }));
        });
        
        test('should handle server errors gracefully', async () => {
            // Setup valid form
            document.getElementById('edit_title').value = 'Test Property';
            document.getElementById('edit_address').value = '123 Test St';
            document.getElementById('edit_property_type').value = 'house';
            document.getElementById('edit_listing_sale').checked = true;
            document.getElementById('edit_sale_price').value = '500000';
            document.getElementById('edit_square_feet').value = '2000';
            form.querySelector('[name="property_id"]').value = '1';
            
            // Mock error response
            fetch.mockResolvedValueOnce({
                ok: false,
                status: 400,
                json: async () => ({ message: 'Validation error' })
            });
            
            const submitEvent = new Event('submit');
            form.dispatchEvent(submitEvent);
            
            // Wait for async operations
            await new Promise(resolve => setTimeout(resolve, 0));
            
            const errorContainer = document.getElementById('propertyEditErrorContainer');
            const errorMessage = document.getElementById('propertyEditErrorMessage');
            
            expect(errorContainer.classList.contains('d-none')).toBe(false);
            expect(errorMessage.textContent).toBe('Validation error');
        });
    });
    
    describe('Character Counters', () => {
        beforeEach(() => {
            require('../static/js/property-edit-modal.js');
            
            // Add character counter elements
            document.body.innerHTML += `
                <span id="edit_address_count">0</span>
                <span id="edit_features_count">0</span>
                <span id="edit_description_count">0</span>
                <textarea id="edit_property_features" maxlength="500"></textarea>
                <textarea id="edit_description" maxlength="1000"></textarea>
            `;
            
            modal.dispatchEvent(new Event('shown.bs.modal'));
        });
        
        test('should update character counters on input', () => {
            const addressField = document.getElementById('edit_address');
            const addressCounter = document.getElementById('edit_address_count');
            
            addressField.value = 'Test address';
            addressField.dispatchEvent(new Event('input'));
            
            expect(addressCounter.textContent).toBe('12');
        });
        
        test('should warn when approaching character limit', () => {
            const featuresField = document.getElementById('edit_property_features');
            const featuresCounter = document.getElementById('edit_features_count');
            
            // Set value close to limit (90% of 500 = 450)
            featuresField.value = 'a'.repeat(460);
            featuresField.dispatchEvent(new Event('input'));
            
            expect(featuresCounter.classList.contains('text-warning')).toBe(true);
        });
    });
    
    describe('Accessibility Features', () => {
        beforeEach(() => {
            require('../static/js/property-edit-modal.js');
            modal.dispatchEvent(new Event('shown.bs.modal'));
        });
        
        test('should focus first input when modal opens', (done) => {
            const titleField = document.getElementById('edit_title');
            const focusSpy = jest.spyOn(titleField, 'focus');
            
            modal.dispatchEvent(new Event('shown.bs.modal'));
            
            setTimeout(() => {
                expect(focusSpy).toHaveBeenCalled();
                done();
            }, 150);
        });
        
        test('should provide proper ARIA feedback for validation', () => {
            const titleField = document.getElementById('edit_title');
            
            // Add invalid feedback element
            const feedback = document.createElement('div');
            feedback.className = 'invalid-feedback';
            titleField.parentNode.appendChild(feedback);
            
            titleField.value = '';
            window.propertyEditModal.validateField(titleField);
            
            expect(titleField.classList.contains('is-invalid')).toBe(true);
            expect(feedback.textContent).toContain('required');
        });
    });
    
    describe('Integration with Main.js', () => {
        test('should populate form fields correctly', () => {
            // Mock the populatePropertyEditModal function
            global.populatePropertyEditModal = require('../static/js/main.js').populatePropertyEditModal;
            
            populatePropertyEditModal(mockProperty);
            
            expect(document.getElementById('edit_title').value).toBe(mockProperty.title);
            expect(document.getElementById('edit_address').value).toBe(mockProperty.address);
            expect(form.querySelector('[name="property_id"]').value).toBe(mockProperty.id.toString());
        });
        
        test('should trigger price calculations after population', (done) => {
            require('../static/js/property-edit-modal.js');
            
            const calculateSpy = jest.spyOn(window.propertyEditModal, 'calculatePricePerMeter');
            
            global.populatePropertyEditModal = require('../static/js/main.js').populatePropertyEditModal;
            populatePropertyEditModal(mockProperty);
            
            setTimeout(() => {
                expect(calculateSpy).toHaveBeenCalled();
                done();
            }, 150);
        });
    });
});

// Test utilities for manual testing
if (typeof window !== 'undefined') {
    window.testPropertyEditModal = {
        // Test validation
        testValidation: () => {
            const modal = window.propertyEditModal;
            if (!modal) {
                console.error('Property edit modal not initialized');
                return;
            }
            
            console.log('Testing form validation...');
            const isValid = modal.validateEntireForm();
            console.log('Form is valid:', isValid);
            
            return isValid;
        },
        
        // Test price calculations
        testPriceCalculation: () => {
            const modal = window.propertyEditModal;
            if (!modal) {
                console.error('Property edit modal not initialized');
                return;
            }
            
            console.log('Testing price calculations...');
            modal.calculatePricePerMeter();
            console.log('Price calculation completed');
        },
        
        // Populate test data
        populateTestData: () => {
            const testProperty = {
                id: 999,
                title: 'Test Property for Validation',
                address: '123 Test Street, Test City',
                property_type: 'house',
                listing_type: 'sale',
                price: 750000,
                square_feet: 2500,
                bedrooms: 4,
                bathrooms: 3,
                parking_spaces: 2,
                floors: 2,
                units: 1,
                year_built: 2020,
                property_condition: 'excellent',
                neighborhood: 'Test Neighborhood',
                property_category: 'residential',
                property_features: 'Swimming Pool, Gym, Garden',
                description: 'A beautiful test property with all modern amenities.',
                agent_id: 1
            };
            
            if (typeof populatePropertyEditModal === 'function') {
                populatePropertyEditModal(testProperty);
                console.log('Test data populated successfully');
            } else {
                console.error('populatePropertyEditModal function not available');
            }
        }
    };
}