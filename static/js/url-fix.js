/**
 * URL Fix - Handle query parameter redirects
 */

(function() {
    // Check if we're on the recommendations page with a customer query parameter
    if (window.location.pathname === '/recommendations' && window.location.search.includes('customer=')) {
        const urlParams = new URLSearchParams(window.location.search);
        const customerId = urlParams.get('customer');
        
        if (customerId && !isNaN(customerId)) {
            // Redirect to the correct URL format
            const newUrl = `/recommendations/${customerId}`;
            console.log('Redirecting from query parameter to path parameter:', newUrl);
            window.location.replace(newUrl);
        }
    }
})();