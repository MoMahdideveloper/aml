/**
 * Button Diagnostics - Debug and test button functionality
 */

class ButtonDiagnostics {
    constructor() {
        this.buttonTests = new Map();
        this.init();
    }

    init() {
        console.log('Button Diagnostics initialized');
        this.createDiagnosticPanel();
    }

    /**
     * Test all buttons on the page
     */
    testAllButtons() {
        const buttons = document.querySelectorAll('button, input[type="button"], input[type="submit"]');
        const results = [];

        buttons.forEach((button, index) => {
            const result = this.testButton(button, index);
            results.push(result);
        });

        console.table(results);
        return results;
    }

    /**
     * Test individual button
     */
    testButton(button, index) {
        const result = {
            index,
            id: button.id || `button-${index}`,
            text: button.textContent?.trim() || button.value || 'No text',
            type: button.type || 'button',
            classes: button.className,
            hasClickHandler: !!button.onclick,
            hasEventListeners: this.hasEventListeners(button),
            isDisabled: button.disabled,
            isVisible: this.isVisible(button),
            inModal: !!button.closest('.modal'),
            inForm: !!button.closest('form'),
            response: 'Not tested'
        };

        return result;
    }

    /**
     * Check if button has event listeners
     */
    hasEventListeners(button) {
        // Check for common event listener indicators
        const indicators = [
            button.onclick !== null,
            button.getAttribute('data-bs-toggle'),
            button.getAttribute('data-bs-dismiss'),
            button.getAttribute('onclick'),
            button.form && button.type === 'submit'
        ];

        return indicators.some(indicator => indicator);
    }

    /**
     * Check if button is visible
     */
    isVisible(button) {
        const style = window.getComputedStyle(button);
        return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
    }

    /**
     * Test button click response
     */
    async testButtonClick(buttonId) {
        const button = document.getElementById(buttonId);
        if (!button) {
            console.error(`Button ${buttonId} not found`);
            return { success: false, error: 'Button not found' };
        }

        return new Promise((resolve) => {
            let responseReceived = false;
            const timeout = setTimeout(() => {
                if (!responseReceived) {
                    resolve({ success: false, error: 'No response within 3 seconds' });
                }
            }, 3000);

            // Add temporary event listener to capture response
            const clickHandler = (e) => {
                responseReceived = true;
                clearTimeout(timeout);
                
                console.log('Button click captured:', {
                    button: e.target,
                    event: e,
                    timestamp: new Date().toISOString()
                });

                resolve({ 
                    success: true, 
                    response: 'Click event fired',
                    target: e.target.id || e.target.className,
                    timestamp: new Date().toISOString()
                });
            };

            button.addEventListener('click', clickHandler, { once: true });
            
            // Simulate click
            try {
                button.click();
            } catch (error) {
                clearTimeout(timeout);
                resolve({ success: false, error: error.message });
            }
        });
    }

    /**
     * Monitor button responses in real-time
     */
    startMonitoring() {
        console.log('Starting button response monitoring...');
        
        // Monitor all clicks
        document.addEventListener('click', (e) => {
            if (e.target.tagName === 'BUTTON' || e.target.type === 'button' || e.target.type === 'submit') {
                console.log('Button clicked:', {
                    id: e.target.id,
                    text: e.target.textContent?.trim(),
                    classes: e.target.className,
                    timestamp: new Date().toISOString(),
                    coordinates: { x: e.clientX, y: e.clientY }
                });
            }
        });

        // Monitor form submissions
        document.addEventListener('submit', (e) => {
            console.log('Form submitted:', {
                form: e.target.id || e.target.className,
                action: e.target.action,
                method: e.target.method,
                timestamp: new Date().toISOString()
            });
        });

        // Monitor AJAX requests
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            console.log('AJAX request:', args[0]);
            const response = await originalFetch(...args);
            console.log('AJAX response:', response.status, response.statusText);
            return response;
        };
    }

    /**
     * Create diagnostic panel
     */
    createDiagnosticPanel() {
        // Only create in development mode
        if (window.location.hostname === 'localhost' || window.location.hostname.includes('127.0.0.1')) {
            const panel = document.createElement('div');
            panel.id = 'button-diagnostics-panel';
            panel.style.cssText = `
                position: fixed;
                top: 10px;
                right: 10px;
                background: #fff;
                border: 2px solid #007bff;
                border-radius: 5px;
                padding: 10px;
                z-index: 10000;
                font-size: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 200px;
            `;
            
            panel.innerHTML = `
                <div style="font-weight: bold; margin-bottom: 5px;">Button Diagnostics</div>
                <button onclick="window.buttonDiagnostics.testAllButtons()" style="margin: 2px; padding: 4px 8px; font-size: 11px;">Test All</button>
                <button onclick="window.buttonDiagnostics.startMonitoring()" style="margin: 2px; padding: 4px 8px; font-size: 11px;">Monitor</button>
                <button onclick="document.getElementById('button-diagnostics-panel').remove()" style="margin: 2px; padding: 4px 8px; font-size: 11px;">Close</button>
            `;
            
            document.body.appendChild(panel);
        }
    }

    /**
     * Fix common button issues
     */
    fixCommonIssues() {
        console.log('Attempting to fix common button issues...');
        
        // Re-initialize Bootstrap components
        if (window.bootstrap) {
            // Re-initialize tooltips
            const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            tooltips.forEach(el => {
                new bootstrap.Tooltip(el);
            });
            
            // Re-initialize modals
            const modals = document.querySelectorAll('.modal');
            modals.forEach(el => {
                new bootstrap.Modal(el);
            });
        }
        
        // Re-bind form submissions
        if (window.CRUDUtils) {
            const forms = document.querySelectorAll('form:not([data-crud-bound])');
            forms.forEach(form => {
                window.CRUDUtils.bindFormSubmission(form);
            });
        }
        
        console.log('Common issues fix attempted');
    }
}

// Initialize diagnostics
window.buttonDiagnostics = new ButtonDiagnostics();

// Expose testing functions globally
window.testButton = (buttonId) => window.buttonDiagnostics.testButtonClick(buttonId);
window.testAllButtons = () => window.buttonDiagnostics.testAllButtons();