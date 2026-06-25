/**
 * Simple Node.js test for CRUD Utilities (without Jest)
 * Real Estate CRM System
 */

// Mock environment setup
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
            contains: () => false,
            toggle: () => {}
        },
        setAttribute: () => {},
        getAttribute: () => null,
        hasAttribute: () => false
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
    fetch: () => Promise.resolve({ 
        ok: true, 
        json: () => Promise.resolve({}),
        text: () => Promise.resolve(''),
        headers: { get: () => 'application/json' }
    })
};

global.console = { log: console.log, error: console.error, warn: console.warn };

global.FormData = function() {
    return {
        append: () => {},
        get: () => null,
        has: () => false,
        delete: () => {}
    };
};

// Simple test framework
class SimpleTest {
    constructor() {
        this.tests = [];
        this.passed = 0;
        this.failed = 0;
    }

    test(name, testFn) {
        this.tests.push({ name, testFn });
    }

    async run() {
        console.log('Running CRUD Utils Tests...\n');
        
        for (const { name, testFn } of this.tests) {
            try {
                await testFn();
                console.log(`✓ ${name}`);
                this.passed++;
            } catch (error) {
                console.log(`✗ ${name}`);
                console.log(`  Error: ${error.message}`);
                this.failed++;
            }
        }
        
        console.log(`\nTest Results: ${this.passed} passed, ${this.failed} failed`);
        return this.failed === 0;
    }
}

// Simple assertion functions
function assert(condition, message = 'Assertion failed') {
    if (!condition) {
        throw new Error(message);
    }
}

function assertEqual(actual, expected, message = 'Values are not equal') {
    if (actual !== expected) {
        throw new Error(`${message}. Expected: ${expected}, Actual: ${actual}`);
    }
}

function assertNotNull(value, message = 'Value is null') {
    if (value === null || value === undefined) {
        throw new Error(message);
    }
}

// Try to load CRUDUtils
let CRUDUtils;
try {
    // For Node.js environment, we need to simulate module loading
    const fs = require('fs');
    const path = require('path');
    
    // Read the CRUDUtils file
    const crudUtilsPath = path.join(__dirname, '..', 'static', 'js', 'crud-utils.js');
    const crudUtilsCode = fs.readFileSync(crudUtilsPath, 'utf8');
    
    // Create a simple module context
    const moduleContext = {
        exports: {},
        module: { exports: {} },
        require: () => ({}),
        global: global,
        window: global.window,
        document: global.document
    };
    
    // Execute the code in our context
    const vm = require('vm');
    vm.createContext(moduleContext);
    vm.runInContext(crudUtilsCode, moduleContext);
    
    // Extract CRUDUtils class
    CRUDUtils = moduleContext.CRUDUtils || moduleContext.module.exports.CRUDUtils || moduleContext.exports.CRUDUtils;
    
    if (!CRUDUtils) {
        // Try to find it in global scope
        vm.runInContext('if (typeof CRUDUtils !== "undefined") { module.exports = CRUDUtils; }', moduleContext);
        CRUDUtils = moduleContext.module.exports;
    }
    
} catch (error) {
    console.error('Failed to load CRUDUtils:', error.message);
    process.exit(1);
}

// Run tests
async function runTests() {
    const test = new SimpleTest();
    
    // Test 1: CRUDUtils initialization
    test.test('CRUDUtils should initialize correctly', () => {
        assertNotNull(CRUDUtils, 'CRUDUtils class should be available');
        const utils = new CRUDUtils();
        assertNotNull(utils, 'CRUDUtils instance should be created');
        assert(utils.activeModals instanceof Map, 'activeModals should be a Map');
        assertNotNull(utils.defaultOptions, 'defaultOptions should be defined');
    });
    
    // Test 2: Default options
    test.test('CRUDUtils should have correct default options', () => {
        const utils = new CRUDUtils();
        assertEqual(utils.defaultOptions.timeout, 5000, 'Default timeout should be 5000');
        assertEqual(utils.defaultOptions.showProgress, true, 'showProgress should be true by default');
        assertEqual(utils.defaultOptions.confirmDelete, true, 'confirmDelete should be true by default');
        assertEqual(utils.defaultOptions.autoHideToasts, true, 'autoHideToasts should be true by default');
    });
    
    // Test 3: Toast creation
    test.test('showToast should create toast element', () => {
        const utils = new CRUDUtils();
        const toast = utils.showToast('Test message', 'success');
        assertNotNull(toast, 'Toast should be created');
    });
    
    // Test 4: Error formatting
    test.test('formatErrors should format validation errors correctly', () => {
        const utils = new CRUDUtils();
        const errors = {
            email: ['Email is required'],
            password: ['Password too short', 'Password must contain numbers']
        };
        
        const formatted = utils.formatErrors(errors);
        assert(formatted.includes('Email: Email is required'), 'Should format single error correctly');
        assert(formatted.includes('Password: Password too short, Password must contain numbers'), 'Should format multiple errors correctly');
    });
    
    // Test 5: Error formatting edge cases
    test.test('formatErrors should handle edge cases', () => {
        const utils = new CRUDUtils();
        
        assertEqual(utils.formatErrors({}), '', 'Empty errors should return empty string');
        assertEqual(utils.formatErrors(null), '', 'Null errors should return empty string');
        assertEqual(utils.formatErrors(undefined), '', 'Undefined errors should return empty string');
    });
    
    // Test 6: CSRF token handling
    test.test('getCSRFToken should return string', () => {
        const utils = new CRUDUtils();
        const token = utils.getCSRFToken();
        assertEqual(typeof token, 'string', 'CSRF token should be a string');
    });
    
    // Test 7: Modal management
    test.test('Modal management should work correctly', () => {
        const utils = new CRUDUtils();
        
        // Test showModal with non-existent modal
        const result = utils.showModal('nonexistent');
        assertEqual(result, null, 'showModal should return null for non-existent modal');
        
        // Test hideModal with non-existent modal (should not throw)
        utils.hideModal('nonexistent'); // Should not throw
    });
    
    // Test 8: Response parsing
    test.test('parseResponse should handle different content types', async () => {
        const utils = new CRUDUtils();
        
        // Test JSON response
        const jsonResponse = {
            headers: { get: () => 'application/json' },
            json: () => Promise.resolve({ data: 'test' })
        };
        
        const jsonResult = await utils.parseResponse(jsonResponse);
        assertEqual(jsonResult.data, 'test', 'Should parse JSON response correctly');
        
        // Test HTML response
        const htmlResponse = {
            headers: { get: () => 'text/html' },
            text: () => Promise.resolve('<html></html>')
        };
        
        const htmlResult = await utils.parseResponse(htmlResponse);
        assertEqual(htmlResult, '<html></html>', 'Should parse HTML response correctly');
    });
    
    // Test 9: Confirmation dialog
    test.test('confirmDelete should create confirmation modal', () => {
        const utils = new CRUDUtils();
        let callbackCalled = false;
        
        const onConfirm = () => { callbackCalled = true; };
        const modal = utils.confirmDelete('Are you sure?', onConfirm);
        
        assertNotNull(modal, 'Confirmation modal should be created');
    });
    
    // Test 10: Custom options in confirmDelete
    test.test('confirmDelete should accept custom options', () => {
        const utils = new CRUDUtils();
        const onConfirm = () => {};
        const options = {
            title: 'Custom Title',
            confirmText: 'Yes, Delete',
            cancelText: 'No, Cancel',
            warning: 'This action cannot be undone'
        };
        
        const modal = utils.confirmDelete('Are you sure?', onConfirm, options);
        assertNotNull(modal, 'Confirmation modal with custom options should be created');
    });
    
    const success = await test.run();
    process.exit(success ? 0 : 1);
}

// Run the tests
runTests().catch(error => {
    console.error('Test execution failed:', error);
    process.exit(1);
});