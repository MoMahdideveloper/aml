/**
 * Unit Tests for CRUD Utilities
 * Real Estate CRM System
 */

// Mock Bootstrap components for testing
global.bootstrap = {
    Modal: class {
        constructor(element, options) {
            this.element = element;
            this.options = options;
        }
        show() { this.element.style.display = 'block'; }
        hide() { this.element.style.display = 'none'; }
    },
    Toast: class {
        constructor(element, options) {
            this.element = element;
            this.options = options;
        }
        show() { this.element.style.display = 'block'; }
        hide() { this.element.style.display = 'none'; }
    }
};

// Mock DOM environment
global.document = {
    createElement: (tag) => ({
        tagName: tag.toUpperCase(),
        className: '',
        style: {},
        innerHTML: '',
        textContent: '',
        appendChild: () => {},
        insertAdjacentHTML: () => {},
        addEventListener: () => {},
        querySelector: () => null,
        querySelectorAll: () => [],
        remove: () => {},
        classList: {
            add: () => {},
            remove: () => {},
            contains: () => false
        }
    }),
    getElementById: () => null,
    querySelector: () => null,
    querySelectorAll: () => [],
    body: {
        appendChild: () => {},
        insertAdjacentHTML: () => {}
    },
    addEventListener: () => {}
};

global.window = {
    location: { href: 'http://localhost', reload: () => {} },
    fetch: () => Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
};

global.console = { log: () => {}, error: () => {}, warn: () => {} };

// Import the CRUDUtils class (for Node.js environment)
let CRUDUtils;
try {
    // Try CommonJS require for Node.js
    CRUDUtils = require('../static/js/crud-utils.js');
} catch (e) {
    // Fallback for browser environment
    if (typeof window !== 'undefined' && window.CRUDUtils) {
        CRUDUtils = window.CRUDUtils;
    } else {
        console.error('CRUDUtils not available in this environment');
    }
}

describe('CRUDUtils', () => {
    let crudUtils;

    beforeEach(() => {
        crudUtils = new CRUDUtils();
    });

    describe('Constructor and Initialization', () => {
        test('should initialize with default options', () => {
            expect(crudUtils.defaultOptions).toEqual({
                timeout: 5000,
                showProgress: true,
                confirmDelete: true,
                autoHideToasts: true
            });
        });

        test('should initialize activeModals Map', () => {
            expect(crudUtils.activeModals).toBeInstanceOf(Map);
            expect(crudUtils.activeModals.size).toBe(0);
        });

        test('should create toast container', () => {
            expect(crudUtils.toastContainer).toBeTruthy();
        });
    });

    describe('Modal Management', () => {
        test('showModal should return null for non-existent modal', () => {
            const result = crudUtils.showModal('nonexistent');
            expect(result).toBeNull();
        });

        test('hideModal should handle non-existent modal gracefully', () => {
            expect(() => crudUtils.hideModal('nonexistent')).not.toThrow();
        });

        test('should store modal instance in activeModals', () => {
            const mockModal = {
                id: 'testModal',
                querySelector: () => null,
                hasAttribute: () => false,
                setAttribute: () => {}
            };
            
            global.document.getElementById = (id) => id === 'testModal' ? mockModal : null;
            
            crudUtils.showModal('testModal');
            expect(crudUtils.activeModals.has('testModal')).toBe(true);
        });
    });

    describe('Toast Notifications', () => {
        test('showToast should create toast with correct message', () => {
            const toast = crudUtils.showToast('Test message', 'success');
            expect(toast).toBeTruthy();
        });

        test('showToast should use default type when not specified', () => {
            const toast = crudUtils.showToast('Test message');
            expect(toast).toBeTruthy();
        });

        test('showToast should handle different toast types', () => {
            const types = ['success', 'error', 'warning', 'info'];
            types.forEach(type => {
                const toast = crudUtils.showToast(`Test ${type}`, type);
                expect(toast).toBeTruthy();
            });
        });
    });

    describe('HTTP Requests', () => {
        test('makeRequest should handle successful response', async () => {
            global.window.fetch = jest.fn(() => 
                Promise.resolve({
                    ok: true,
                    headers: { get: () => 'application/json' },
                    json: () => Promise.resolve({ success: true })
                })
            );

            const result = await crudUtils.makeRequest('/test');
            expect(result).toEqual({ success: true });
        });

        test('makeRequest should handle error response', async () => {
            global.window.fetch = jest.fn(() => 
                Promise.resolve({
                    ok: false,
                    status: 400,
                    statusText: 'Bad Request',
                    headers: { get: () => 'application/json' },
                    json: () => Promise.resolve({ message: 'Validation error' })
                })
            );

            await expect(crudUtils.makeRequest('/test')).rejects.toThrow('Validation error');
        });

        test('makeRequest should handle network error', async () => {
            global.window.fetch = jest.fn(() => 
                Promise.reject(new TypeError('Failed to fetch'))
            );

            await expect(crudUtils.makeRequest('/test')).rejects.toThrow('Network error');
        });
    });

    describe('Form Handling', () => {
        test('submitForm should handle form submission', async () => {
            const mockForm = {
                method: 'POST',
                action: '/submit',
                querySelector: () => null,
                closest: () => null
            };

            global.FormData = jest.fn(() => ({}));
            global.window.fetch = jest.fn(() => 
                Promise.resolve({
                    ok: true,
                    headers: { get: () => 'application/json' },
                    json: () => Promise.resolve({ success: true })
                })
            );

            const result = await crudUtils.submitForm(mockForm);
            expect(result).toEqual({ success: true });
        });

        test('showFormErrors should handle validation errors', () => {
            const mockForm = {
                querySelectorAll: jest.fn(() => []),
                querySelector: jest.fn(() => ({
                    classList: { add: jest.fn() },
                    parentNode: { appendChild: jest.fn() }
                }))
            };

            const errors = { email: ['Email is required'] };
            
            expect(() => crudUtils.showFormErrors(mockForm, errors)).not.toThrow();
        });
    });

    describe('Utility Methods', () => {
        test('getCSRFToken should return empty string when no token found', () => {
            const token = crudUtils.getCSRFToken();
            expect(token).toBe('');
        });

        test('formatErrors should format validation errors correctly', () => {
            const errors = {
                email: ['Email is required'],
                password: ['Password too short', 'Password must contain numbers']
            };

            const formatted = crudUtils.formatErrors(errors);
            expect(formatted).toContain('Email: Email is required');
            expect(formatted).toContain('Password: Password too short, Password must contain numbers');
        });

        test('formatErrors should handle empty errors object', () => {
            const formatted = crudUtils.formatErrors({});
            expect(formatted).toBe('');
        });

        test('formatErrors should handle null/undefined errors', () => {
            expect(crudUtils.formatErrors(null)).toBe('');
            expect(crudUtils.formatErrors(undefined)).toBe('');
        });
    });

    describe('Response Parsing', () => {
        test('parseResponse should handle JSON response', async () => {
            const mockResponse = {
                headers: { get: () => 'application/json' },
                json: () => Promise.resolve({ data: 'test' })
            };

            const result = await crudUtils.parseResponse(mockResponse);
            expect(result).toEqual({ data: 'test' });
        });

        test('parseResponse should handle HTML response', async () => {
            const mockResponse = {
                headers: { get: () => 'text/html' },
                text: () => Promise.resolve('<html></html>')
            };

            const result = await crudUtils.parseResponse(mockResponse);
            expect(result).toBe('<html></html>');
        });

        test('parseResponse should handle plain text response', async () => {
            const mockResponse = {
                headers: { get: () => 'text/plain' },
                text: () => Promise.resolve('plain text')
            };

            const result = await crudUtils.parseResponse(mockResponse);
            expect(result).toBe('plain text');
        });
    });

    describe('Confirmation Dialog', () => {
        test('confirmDelete should create confirmation modal', () => {
            const onConfirm = jest.fn();
            const modal = crudUtils.confirmDelete('Are you sure?', onConfirm);
            expect(modal).toBeTruthy();
        });

        test('confirmDelete should use custom options', () => {
            const onConfirm = jest.fn();
            const options = {
                title: 'Custom Title',
                confirmText: 'Yes, Delete',
                cancelText: 'No, Cancel',
                warning: 'This action cannot be undone'
            };

            const modal = crudUtils.confirmDelete('Are you sure?', onConfirm, options);
            expect(modal).toBeTruthy();
        });
    });
});

// Test runner setup for browser environment
if (typeof window !== 'undefined') {
    // Browser test setup
    console.log('Running CRUD Utils tests in browser environment');
    
    // Simple test runner for browser
    window.runCRUDUtilsTests = function() {
        const results = {
            passed: 0,
            failed: 0,
            errors: []
        };

        try {
            // Test basic initialization
            const utils = new CRUDUtils();
            if (utils.activeModals instanceof Map) {
                results.passed++;
                console.log('✓ CRUDUtils initialization test passed');
            } else {
                results.failed++;
                results.errors.push('CRUDUtils initialization failed');
            }

            // Test toast creation
            try {
                utils.showToast('Test message', 'success');
                results.passed++;
                console.log('✓ Toast creation test passed');
            } catch (e) {
                results.failed++;
                results.errors.push('Toast creation failed: ' + e.message);
            }

            // Test error formatting
            const errors = { email: ['Required'] };
            const formatted = utils.formatErrors(errors);
            if (formatted.includes('Email: Required')) {
                results.passed++;
                console.log('✓ Error formatting test passed');
            } else {
                results.failed++;
                results.errors.push('Error formatting failed');
            }

        } catch (e) {
            results.failed++;
            results.errors.push('Test execution error: ' + e.message);
        }

        console.log(`\nTest Results: ${results.passed} passed, ${results.failed} failed`);
        if (results.errors.length > 0) {
            console.log('Errors:', results.errors);
        }

        return results;
    };
}