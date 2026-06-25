/**
 * Tests for enhanced property modal system
 */

describe('PropertyModalManager', () => {
    let modalManager;
    
    beforeEach(() => {
        // Reset DOM
        document.body.innerHTML = '';
        
        // Create fresh instance
        modalManager = new PropertyModalManager();
        
        // Mock fetch
        global.fetch = jest.fn();
        
        // Mock bootstrap Modal
        global.bootstrap = {
            Modal: jest.fn().mockImplementation(() => ({
                show: jest.fn(),
                hide: jest.fn()
            }))
        };
        
        // Mock console methods
        console.error = jest.fn();
        console.warn = jest.fn();
        console.log = jest.fn();
    });
    
    afterEach(() => {
        jest.clearAllMocks();
    });
    
    describe('showLoadingIndicator', () => {
        test('should create and show loading indicator', () => {
            const loadingId = modalManager.showLoadingIndicator('Test loading...');
            
            expect(loadingId).toBeTruthy();
            expect(document.getElementById(loadingId)).toBeTruthy();
            expect(modalManager.loadingIndicators.has(loadingId)).toBe(true);
        });
        
        test('should remove existing indicator before creating new one', () => {
            const loadingId = 'test-loading';
            modalManager.showLoadingIndicator('First', loadingId);
            
            expect(modalManager.loadingIndicators.size).toBe(1);
            
            modalManager.showLoadingIndicator('Second', loadingId);
            
            expect(modalManager.loadingIndicators.size).toBe(1);
        });
    });
    
    describe('hideLoadingIndicator', () => {
        test('should remove loading indicator from DOM and map', () => {
            const loadingId = modalManager.showLoadingIndicator('Test');
            
            expect(document.getElementById(loadingId)).toBeTruthy();
            expect(modalManager.loadingIndicators.has(loadingId)).toBe(true);
            
            modalManager.hideLoadingIndicator(loadingId);
            
            expect(document.getElementById(loadingId)).toBeFalsy();
            expect(modalManager.loadingIndicators.has(loadingId)).toBe(false);
        });
        
        test('should handle non-existent loading indicator gracefully', () => {
            expect(() => {
                modalManager.hideLoadingIndicator('non-existent');
            }).not.toThrow();
        });
    });
    
    describe('fetchWithRetry', () => {
        test('should succeed on first attempt', async () => {
            const mockResponse = { property: { id: 1, title: 'Test' } };
            global.fetch.mockResolvedValueOnce({
                ok: true,
                headers: { get: () => 'application/json' },
                json: () => Promise.resolve(mockResponse)
            });
            
            const result = await modalManager.fetchWithRetry('/test');
            
            expect(result).toEqual(mockResponse);
            expect(global.fetch).toHaveBeenCalledTimes(1);
        });
        
        test('should retry on failure and eventually succeed', async () => {
            const mockResponse = { property: { id: 1, title: 'Test' } };
            
            global.fetch
                .mockRejectedValueOnce(new Error('Network error'))
                .mockRejectedValueOnce(new Error('Network error'))
                .mockResolvedValueOnce({
                    ok: true,
                    headers: { get: () => 'application/json' },
                    json: () => Promise.resolve(mockResponse)
                });
            
            const result = await modalManager.fetchWithRetry('/test', {}, 3);
            
            expect(result).toEqual(mockResponse);
            expect(global.fetch).toHaveBeenCalledTimes(3);
        });
        
        test('should throw error after max retries', async () => {
            global.fetch.mockRejectedValue(new Error('Network error'));
            
            await expect(modalManager.fetchWithRetry('/test', {}, 2))
                .rejects.toThrow('Network error');
            
            expect(global.fetch).toHaveBeenCalledTimes(2);
        });
        
        test('should handle different HTTP status codes', async () => {
            global.fetch.mockResolvedValueOnce({
                ok: false,
                status: 404
            });
            
            await expect(modalManager.fetchWithRetry('/test'))
                .rejects.toThrow('Property not found (404)');
        });
    });
    
    describe('ensureModalTemplate', () => {
        test('should return existing modal if found', async () => {
            const existingModal = document.createElement('div');
            existingModal.id = 'testModal';
            document.body.appendChild(existingModal);
            
            const result = await modalManager.ensureModalTemplate('testModal');
            
            expect(result).toBe(existingModal);
        });
        
        test('should fetch and inject modal template if not found', async () => {
            const modalHtml = '<div id="testModal">Modal content</div>';
            
            global.fetch.mockResolvedValueOnce({
                ok: true,
                text: () => Promise.resolve(modalHtml)
            });
            
            const result = await modalManager.ensureModalTemplate('testModal', '/test-template');
            
            expect(result).toBeTruthy();
            expect(result.id).toBe('testModal');
            expect(document.getElementById('testModal')).toBeTruthy();
        });
        
        test('should handle template fetch failure gracefully', async () => {
            global.fetch.mockRejectedValueOnce(new Error('Template not found'));
            
            const result = await modalManager.ensureModalTemplate('testModal', '/test-template');
            
            expect(result).toBeFalsy();
            expect(console.warn).toHaveBeenCalled();
        });
    });
    
    describe('showErrorModal', () => {
        test('should create and show error modal', () => {
            modalManager.showErrorModal('Test Error', 'Error message', 'Stack trace');
            
            const errorModal = document.getElementById('propertyErrorModal');
            expect(errorModal).toBeTruthy();
            expect(errorModal.querySelector('.error-title').textContent).toBe('Test Error');
            expect(errorModal.querySelector('.error-message').textContent).toBe('Error message');
            expect(errorModal.querySelector('.error-details pre').textContent).toBe('Stack trace');
        });
        
        test('should reuse existing error modal', () => {
            modalManager.showErrorModal('First Error', 'First message');
            modalManager.showErrorModal('Second Error', 'Second message');
            
            const errorModals = document.querySelectorAll('#propertyErrorModal');
            expect(errorModals.length).toBe(1);
            expect(errorModals[0].querySelector('.error-title').textContent).toBe('Second Error');
        });
    });
});

describe('viewPropertyModal', () => {
    let modalManager;
    
    beforeEach(() => {
        document.body.innerHTML = '';
        
        // Mock global functions
        global.showNotification = jest.fn();
        global.populatePropertyViewModal = jest.fn();
        global.PropertyModalManager = new PropertyModalManager();
        
        global.fetch = jest.fn();
        global.bootstrap = {
            Modal: jest.fn().mockImplementation(() => ({
                show: jest.fn(),
                hide: jest.fn()
            }))
        };
        
        console.error = jest.fn();
        console.log = jest.fn();
    });
    
    test('should handle missing property ID', async () => {
        await viewPropertyModal();
        
        expect(console.error).toHaveBeenCalledWith('Property ID is required');
        expect(global.showNotification).toHaveBeenCalledWith('Property ID is required', 'error');
    });
    
    test('should handle invalid property ID format', async () => {
        await viewPropertyModal('invalid');
        
        expect(global.showNotification).toHaveBeenCalledWith(
            expect.stringContaining('Invalid property ID'),
            'error'
        );
    });
    
    test('should successfully load and show modal', async () => {
        const mockProperty = { id: 1, title: 'Test Property' };
        const mockModal = document.createElement('div');
        mockModal.id = 'propertyViewModal';
        document.body.appendChild(mockModal);
        
        global.fetch.mockResolvedValueOnce({
            ok: true,
            headers: { get: () => 'application/json' },
            json: () => Promise.resolve({ property: mockProperty })
        });
        
        await viewPropertyModal(1);
        
        expect(global.populatePropertyViewModal).toHaveBeenCalledWith(mockProperty);
        expect(global.bootstrap.Modal).toHaveBeenCalled();
    });
    
    test('should handle property not found error', async () => {
        global.fetch.mockResolvedValueOnce({
            ok: false,
            status: 404
        });
        
        await viewPropertyModal(999);
        
        expect(global.showNotification).toHaveBeenCalledWith(
            expect.stringContaining('Property not found'),
            'error'
        );
    });
    
    test('should handle server error', async () => {
        global.fetch.mockResolvedValueOnce({
            ok: false,
            status: 500
        });
        
        await viewPropertyModal(1);
        
        expect(global.showNotification).toHaveBeenCalledWith(
            expect.stringContaining('Server error'),
            'error'
        );
    });
    
    test('should handle network error', async () => {
        global.fetch.mockRejectedValueOnce(new Error('Network error'));
        
        await viewPropertyModal(1);
        
        expect(global.showNotification).toHaveBeenCalledWith(
            expect.stringContaining('Failed to load property details'),
            'error'
        );
    });
});

describe('populatePropertyViewModal', () => {
    let modal;
    
    beforeEach(() => {
        document.body.innerHTML = `
            <div id="propertyViewModal">
                <div class="modal-title"></div>
                <h4 class="text-primary"></h4>
                <p class="text-muted"></p>
                <div data-field="property_type"></div>
                <div data-field="bedrooms"></div>
                <div data-field="bathrooms"></div>
                <div class="card bg-success">
                    <div class="card-body"></div>
                </div>
                <div data-field="agent_name"></div>
                <div class="features-list"></div>
                <div data-field="description"></div>
                <button onclick="editProperty()"></button>
                <button onclick="shareProperty()"></button>
                <a data-action="details"></a>
            </div>
        `;
        
        modal = document.getElementById('propertyViewModal');
        console.error = jest.fn();
        console.warn = jest.fn();
        console.log = jest.fn();
    });
    
    test('should handle null property gracefully', () => {
        expect(() => {
            populatePropertyViewModal(null);
        }).not.toThrow();
        
        expect(console.error).toHaveBeenCalledWith('Property data is null or undefined');
    });
    
    test('should handle missing modal gracefully', () => {
        document.body.innerHTML = '';
        
        expect(() => {
            populatePropertyViewModal({ id: 1, title: 'Test' });
        }).not.toThrow();
        
        expect(console.error).toHaveBeenCalledWith('Property view modal not found');
    });
    
    test('should populate modal with complete property data', () => {
        const property = {
            id: 1,
            title: 'Test Property',
            address: '123 Test St',
            property_type: 'house',
            bedrooms: 3,
            bathrooms: 2,
            price: 100000,
            listing_type: 'sale',
            agent_name: 'Test Agent',
            property_features: 'garage, pool, garden',
            description: 'Beautiful property'
        };
        
        populatePropertyViewModal(property);
        
        expect(modal.querySelector('.modal-title').textContent).toContain('Test Property');
        expect(modal.querySelector('h4.text-primary').textContent).toBe('Test Property');
        expect(modal.querySelector('[data-field="property_type"]').textContent).toBe('HOUSE');
        expect(modal.querySelector('[data-field="bedrooms"]').textContent).toBe('3');
        expect(modal.querySelector('[data-field="agent_name"]').textContent).toBe('Test Agent');
        expect(modal.querySelector('.features-list').innerHTML).toContain('garage');
        expect(modal.querySelector('[data-field="description"]').textContent).toBe('Beautiful property');
    });
    
    test('should handle missing property fields with fallbacks', () => {
        const property = {
            id: 1,
            title: '',
            address: null,
            bedrooms: undefined,
            agent_name: null
        };
        
        populatePropertyViewModal(property);
        
        expect(modal.querySelector('h4.text-primary').textContent).toBe('Untitled Property');
        expect(modal.querySelector('[data-field="bedrooms"]').textContent).toBe('N/A');
        expect(modal.querySelector('[data-field="agent_name"]').textContent).toBe('Unassigned');
    });
    
    test('should handle rental property pricing', () => {
        const property = {
            id: 1,
            title: 'Rental Property',
            listing_type: 'rental',
            rahn: 50000000,
            ejare: 2000000
        };
        
        populatePropertyViewModal(property);
        
        const priceCard = modal.querySelector('.card.bg-success .card-body');
        expect(priceCard.innerHTML).toContain('Rental Pricing');
        expect(priceCard.innerHTML).toContain('50,000,000');
        expect(priceCard.innerHTML).toContain('2,000,000');
    });
    
    test('should update action buttons with property ID', () => {
        const property = { id: 123, title: 'Test' };
        
        populatePropertyViewModal(property);
        
        expect(modal.querySelector('button[onclick*="editProperty"]').getAttribute('onclick')).toBe('editProperty(123)');
        expect(modal.querySelector('button[onclick*="shareProperty"]').getAttribute('onclick')).toBe('shareProperty(123)');
        expect(modal.querySelector('a[data-action="details"]').getAttribute('href')).toBe('/properties/123/detail');
    });
});

// Integration tests
describe('Modal System Integration', () => {
    beforeEach(() => {
        document.body.innerHTML = '';
        global.fetch = jest.fn();
        global.bootstrap = { Modal: jest.fn(() => ({ show: jest.fn() })) };
        global.showNotification = jest.fn();
        global.PropertyModalManager = new PropertyModalManager();
    });
    
    test('should handle complete modal loading workflow', async () => {
        const mockProperty = {
            id: 1,
            title: 'Integration Test Property',
            address: '123 Integration St',
            price: 200000,
            listing_type: 'sale'
        };
        
        // Mock successful API response
        global.fetch.mockResolvedValueOnce({
            ok: true,
            headers: { get: () => 'application/json' },
            json: () => Promise.resolve({ property: mockProperty })
        });
        
        // Mock modal template injection
        global.fetch.mockResolvedValueOnce({
            ok: true,
            text: () => Promise.resolve('<div id="propertyViewModal"><div class="modal-title"></div></div>')
        });
        
        await viewPropertyModal(1);
        
        expect(document.getElementById('propertyViewModal')).toBeTruthy();
        expect(global.bootstrap.Modal).toHaveBeenCalled();
    });
});

// Performance tests
describe('Modal System Performance', () => {
    test('should handle multiple concurrent modal requests', async () => {
        global.fetch = jest.fn().mockResolvedValue({
            ok: true,
            headers: { get: () => 'application/json' },
            json: () => Promise.resolve({ property: { id: 1, title: 'Test' } })
        });
        
        global.bootstrap = { Modal: jest.fn(() => ({ show: jest.fn() })) };
        global.showNotification = jest.fn();
        global.PropertyModalManager = new PropertyModalManager();
        
        const promises = [
            viewPropertyModal(1),
            viewPropertyModal(2),
            viewPropertyModal(3)
        ];
        
        await Promise.all(promises);
        
        expect(global.fetch).toHaveBeenCalledTimes(3);
    });
});

// Export for use in other test files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        PropertyModalManager
    };
}