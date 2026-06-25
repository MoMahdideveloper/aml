// Jest setup file for CRUD utilities tests

// Mock global objects that would be available in browser
global.bootstrap = {
    Modal: jest.fn().mockImplementation((element, options) => ({
        element,
        options,
        show: jest.fn(),
        hide: jest.fn(),
        dispose: jest.fn()
    })),
    Toast: jest.fn().mockImplementation((element, options) => ({
        element,
        options,
        show: jest.fn(),
        hide: jest.fn(),
        dispose: jest.fn()
    }))
};

// Mock DOM methods
global.document = {
    createElement: jest.fn((tag) => ({
        tagName: tag.toUpperCase(),
        className: '',
        style: {},
        innerHTML: '',
        textContent: '',
        appendChild: jest.fn(),
        insertAdjacentHTML: jest.fn(),
        addEventListener: jest.fn(),
        querySelector: jest.fn(() => null),
        querySelectorAll: jest.fn(() => []),
        remove: jest.fn(),
        classList: {
            add: jest.fn(),
            remove: jest.fn(),
            contains: jest.fn(() => false),
            toggle: jest.fn()
        },
        setAttribute: jest.fn(),
        getAttribute: jest.fn(),
        hasAttribute: jest.fn(() => false)
    })),
    getElementById: jest.fn(() => null),
    querySelector: jest.fn(() => null),
    querySelectorAll: jest.fn(() => []),
    body: {
        appendChild: jest.fn(),
        insertAdjacentHTML: jest.fn()
    },
    addEventListener: jest.fn()
};

global.window = {
    location: { 
        href: 'http://localhost',
        reload: jest.fn()
    },
    fetch: jest.fn(() => Promise.resolve({
        ok: true,
        json: () => Promise.resolve({}),
        text: () => Promise.resolve(''),
        headers: {
            get: jest.fn(() => 'application/json')
        }
    }))
};

global.console = {
    log: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    info: jest.fn()
};

// Mock FormData
global.FormData = jest.fn(() => ({
    append: jest.fn(),
    get: jest.fn(),
    has: jest.fn(),
    delete: jest.fn()
}));

// Reset all mocks before each test
beforeEach(() => {
    jest.clearAllMocks();
});