/**
 * Property View Modal - Enhanced functionality for comprehensive property display
 * Handles dynamic content population, state management, and accessibility
 */

// Global variables for modal state management
let currentPropertyId = null;
let modalRetryCount = 0;
const MAX_RETRY_ATTEMPTS = 3;

/**
 * Populate property view modal with data
 * @param {Object} property - Property data object
 */
function populatePropertyViewModal(property) {
    if (!property) {
        console.error('Property data is required');
        return;
    }

    try {
        // Store current property ID for actions
        currentPropertyId = property.id;

        // Update modal title and header
        document.getElementById('property-title').textContent = property.title || 'Property Details';
        
        // Update property type, category, and condition badges
        const typeElement = document.getElementById('property-type');
        const categoryElement = document.getElementById('property-category');
        const conditionElement = document.getElementById('property-condition');
        
        if (typeElement) typeElement.textContent = formatPropertyType(property.property_type);
        if (categoryElement) categoryElement.textContent = formatPropertyCategory(property.property_category);
        if (conditionElement) conditionElement.textContent = formatPropertyCondition(property.property_condition);

        // Update address and agent information
        const addressElement = document.getElementById('property-address');
        const agentElement = document.getElementById('property-agent');
        
        if (addressElement) addressElement.textContent = property.address || 'Address not available';
        if (agentElement) agentElement.textContent = property.agent_name || 'Unassigned';

        // Update pricing display based on listing type
        updatePricingDisplay(property);

        // Update overview tab content
        updateOverviewTab(property);

        // Update specifications tab
        updateSpecificationsTab(property);

        // Update features tab
        updateFeaturesTab(property);

        // Update location tab
        updateLocationTab(property);

        // Update footer information
        updateModalFooter(property);

        // Show success state
        showModalContent();

        // Announce to screen readers
        announceToScreenReader(`Property details loaded for ${property.title}`);

    } catch (error) {
        console.error('Error populating property view modal:', error);
        showModalError('Failed to display property information');
    }
}

/**
 * Update pricing display based on listing type
 * @param {Object} property - Property data
 */
function updatePricingDisplay(property) {
    const saleDisplay = document.getElementById('sale-price-display');
    const rentalDisplay = document.getElementById('rental-price-display');

    // Hide both displays first
    if (saleDisplay) saleDisplay.style.display = 'none';
    if (rentalDisplay) rentalDisplay.style.display = 'none';

    if (property.listing_type === 'sale') {
        // Show sale pricing
        if (saleDisplay) {
            saleDisplay.style.display = 'block';
            
            const salePriceElement = document.getElementById('sale-price');
            const salePricePerMeterElement = document.getElementById('sale-price-per-meter');
            
            if (salePriceElement) {
                salePriceElement.textContent = formatCurrency(property.price || property.sale_price);
            }
            
            if (salePricePerMeterElement && property.square_feet) {
                const pricePerMeter = (property.price || property.sale_price) / property.square_feet;
                salePricePerMeterElement.textContent = `${formatCurrency(pricePerMeter)}/m\u00B2`;
            }
        }
    } else if (property.listing_type === 'rental') {
        // Show rental pricing (Iranian system)
        if (rentalDisplay) {
            rentalDisplay.style.display = 'block';
            
            const rahnElement = document.getElementById('rahn-price');
            const ejareElement = document.getElementById('ejare-price');
            const rahnPerMeterElement = document.getElementById('rahn-per-meter');
            const ejarePerMeterElement = document.getElementById('ejare-per-meter');
            
            if (rahnElement) {
                rahnElement.textContent = formatTomanCurrency(property.rahn);
            }
            
            if (ejareElement) {
                ejareElement.textContent = formatTomanCurrency(property.ejare);
            }
            
            if (rahnPerMeterElement && property.square_feet && property.rahn) {
                const rahnPerMeter = property.rahn / property.square_feet;
                rahnPerMeterElement.textContent = `${formatTomanCurrency(rahnPerMeter)}/m\u00B2`;
            }
            
            if (ejarePerMeterElement && property.square_feet && property.ejare) {
                const ejarePerMeter = property.ejare / property.square_feet;
                ejarePerMeterElement.textContent = `${formatTomanCurrency(ejarePerMeter)}/m\u00B2`;
            }
        }
    }
}

/**
 * Update overview tab content
 * @param {Object} property - Property data
 */
function updateOverviewTab(property) {
    // Update description
    const descriptionElement = document.getElementById('property-description');
    if (descriptionElement) {
        if (property.description && property.description.trim()) {
            const safeDescription = escapeHtml(property.description).replace(/\n/g, '</p><p>');
            descriptionElement.innerHTML = `<p>${safeDescription}</p>`;
        } else {
            descriptionElement.innerHTML = '<p class="text-muted fst-italic">No description available for this property.</p>';
        }
    }

    // Update key metrics
    const sizeElement = document.getElementById('property-size');
    const bedroomsElement = document.getElementById('property-bedrooms');
    const bathroomsElement = document.getElementById('property-bathrooms');
    const parkingElement = document.getElementById('property-parking');

    if (sizeElement) sizeElement.textContent = property.square_feet || '0';
    if (bedroomsElement) bedroomsElement.textContent = property.bedrooms || '0';
    if (bathroomsElement) bathroomsElement.textContent = property.bathrooms || '0';
    if (parkingElement) parkingElement.textContent = property.parking_spaces || '0';
}

/**
 * Update specifications tab
 * @param {Object} property - Property data
 */
function updateSpecificationsTab(property) {
    const specElements = {
        'spec-property-type': formatPropertyType(property.property_type),
        'spec-category': formatPropertyCategory(property.property_category),
        'spec-condition': formatPropertyCondition(property.property_condition),
        'spec-year-built': property.year_built || 'Not specified',
        'spec-floors': property.floors || 'Not specified',
        'spec-units': property.units || 'Not specified',
        'spec-size': property.square_feet ? `${property.square_feet} m\u00B2` : 'Not specified',
        'spec-bedrooms': property.bedrooms || 'Not specified',
        'spec-bathrooms': property.bathrooms || 'Not specified',
        'spec-parking': property.parking_spaces || 'Not specified',
        'spec-neighborhood': property.neighborhood || 'Not specified',
        'spec-listing-type': formatListingType(property.listing_type)
    };

    Object.entries(specElements).forEach(([elementId, value]) => {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = value;
        }
    });
}

/**
 * Update features tab
 * @param {Object} property - Property data
 */
function updateFeaturesTab(property) {
    const featuresContainer = document.getElementById('property-features-list');
    if (!featuresContainer) return;

    if (property.property_features && property.property_features.trim()) {
        const features = property.property_features.split(',').map(f => f.trim()).filter(f => f);
        
        if (features.length > 0) {
            const featuresHTML = features.map(feature => `
                <div class="col-md-6 col-lg-4 mb-2">
                    <div class="d-flex align-items-center">
                        <i class="fas fa-check-circle text-success me-2"></i>
                        <span>${escapeHtml(feature)}</span>
                    </div>
                </div>
            `).join('');

            featuresContainer.innerHTML = `
                <div class="row">
                    ${featuresHTML}
                </div>
            `;
        } else {
            showNoFeaturesMessage(featuresContainer);
        }
    } else {
        showNoFeaturesMessage(featuresContainer);
    }
}

/**
 * Show no features message
 * @param {HTMLElement} container - Features container element
 */
function showNoFeaturesMessage(container) {
    container.innerHTML = `
        <div class="text-muted text-center py-4">
            <i class="fas fa-list text-muted fs-1 mb-3"></i>
            <p>No features listed for this property</p>
            <small>Features will be displayed here when available</small>
        </div>
    `;
}

/**
 * Update location tab
 * @param {Object} property - Property data
 */
function updateLocationTab(property) {
    const locationAddressElement = document.getElementById('location-address');
    const locationNeighborhoodElement = document.getElementById('location-neighborhood');

    if (locationAddressElement) {
        locationAddressElement.textContent = property.address || 'Address not available';
    }

    if (locationNeighborhoodElement) {
        locationNeighborhoodElement.textContent = property.neighborhood || 'Not specified';
    }
}

/**
 * Update modal footer information
 * @param {Object} property - Property data
 */
function updateModalFooter(property) {
    const updatedElement = document.getElementById('property-updated');
    if (updatedElement) {
        if (property.updated_at) {
            const date = new Date(property.updated_at);
            updatedElement.textContent = date.toLocaleDateString();
        } else {
            updatedElement.textContent = 'Unknown';
        }
    }
}

/**
 * Show modal content and hide loading state
 */
function showModalContent() {
    const loadingElement = document.getElementById('propertyViewModal_loading');
    const contentElement = document.getElementById('propertyViewModal_content');
    const errorElement = document.getElementById('propertyViewModal_error');

    if (loadingElement) loadingElement.style.display = 'none';
    if (errorElement) errorElement.classList.add('d-none');
    if (contentElement) contentElement.style.display = 'block';
}

/**
 * Show modal error state
 * @param {string} message - Error message to display
 */
function showModalError(message) {
    const loadingElement = document.getElementById('propertyViewModal_loading');
    const contentElement = document.getElementById('propertyViewModal_content');
    const errorElement = document.getElementById('propertyViewModal_error');
    const errorMessageElement = document.getElementById('propertyViewModal_error_message');

    if (loadingElement) loadingElement.style.display = 'none';
    if (contentElement) contentElement.style.display = 'none';
    if (errorElement) errorElement.classList.remove('d-none');
    if (errorMessageElement) errorMessageElement.textContent = message;

    // Announce error to screen readers
    announceToScreenReader(`Error: ${message}`);
}

/**
 * Show modal loading state
 */
function showModalLoading() {
    const loadingElement = document.getElementById('propertyViewModal_loading');
    const contentElement = document.getElementById('propertyViewModal_content');
    const errorElement = document.getElementById('propertyViewModal_error');

    if (loadingElement) loadingElement.style.display = 'block';
    if (contentElement) contentElement.style.display = 'none';
    if (errorElement) errorElement.classList.add('d-none');
}

/**
 * Retry loading property data
 */
function retryLoadProperty() {
    if (currentPropertyId && modalRetryCount < MAX_RETRY_ATTEMPTS) {
        modalRetryCount++;
        showModalLoading();
        
        // Call the main viewPropertyModal function to retry
        if (typeof viewPropertyModal === 'function') {
            viewPropertyModal(currentPropertyId);
        } else {
            showModalError('Unable to retry - viewPropertyModal function not available');
        }
    } else {
        showModalError('Maximum retry attempts reached. Please try again later.');
    }
}

/**
 * Open property full details page
 */
function openPropertyFullDetails() {
    if (currentPropertyId) {
        const url = `/properties/${currentPropertyId}/detail`;
        window.open(url, '_blank', 'noopener,noreferrer');
    }
}

/**
 * Edit property from modal
 */
function editPropertyFromModal() {
    if (currentPropertyId && typeof editProperty === 'function') {
        // Close the view modal first
        const modal = bootstrap.Modal.getInstance(document.getElementById('propertyViewModal'));
        if (modal) {
            modal.hide();
        }
        
        // Open edit modal
        setTimeout(() => {
            editProperty(currentPropertyId);
        }, 300);
    }
}

/**
 * Share property from modal
 */
function sharePropertyFromModal() {
    if (currentPropertyId && typeof shareProperty === 'function') {
        shareProperty(currentPropertyId);
    }
}

// Utility Functions

/**
 * Format property type for display
 * @param {string} type - Property type
 * @returns {string} Formatted type
 */
function formatPropertyType(type) {
    if (!type) return 'Not specified';
    return type.charAt(0).toUpperCase() + type.slice(1).replace('_', ' ');
}

/**
 * Format property category for display
 * @param {string} category - Property category
 * @returns {string} Formatted category
 */
function formatPropertyCategory(category) {
    if (!category) return 'Not specified';
    return category.charAt(0).toUpperCase() + category.slice(1);
}

/**
 * Format property condition for display
 * @param {string} condition - Property condition
 * @returns {string} Formatted condition
 */
function formatPropertyCondition(condition) {
    if (!condition) return 'Not specified';
    return condition.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());
}

/**
 * Format listing type for display
 * @param {string} listingType - Listing type
 * @returns {string} Formatted listing type
 */
function formatListingType(listingType) {
    if (!listingType) return 'Not specified';
    
    const types = {
        'sale': 'For Sale',
        'rental': 'For Rent (Iranian System)',
        'rent': 'For Rent'
    };
    
    return types[listingType] || listingType.charAt(0).toUpperCase() + listingType.slice(1);
}

/**
 * Format currency for display
 * @param {number} amount - Amount to format
 * @returns {string} Formatted currency
 */
function formatCurrency(amount) {
    if (!amount || isNaN(amount)) return '$0';
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

/**
 * Format Toman currency for Iranian system
 * @param {number} amount - Amount to format
 * @returns {string} Formatted Toman currency
 */
function formatTomanCurrency(amount) {
    if (!amount || isNaN(amount)) return '0 تومان';
    return new Intl.NumberFormat('fa-IR').format(amount) + ' تومان';
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Announce message to screen readers
 * @param {string} message - Message to announce
 */
function announceToScreenReader(message) {
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', 'polite');
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

// Enhanced Keyboard Navigation and Accessibility

document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('propertyViewModal');
    if (!modal) return;

    // Reset modal state when hidden
    modal.addEventListener('hidden.bs.modal', function() {
        currentPropertyId = null;
        modalRetryCount = 0;
        showModalLoading(); // Reset to loading state for next use
    });

    // Handle tab navigation within modal
    modal.addEventListener('keydown', function(e) {
        // Handle Escape key
        if (e.key === 'Escape') {
            const closeBtn = modal.querySelector('[data-bs-dismiss="modal"]');
            if (closeBtn) {
                closeBtn.click();
            }
            return;
        }

        // Handle Enter key on tab buttons
        if (e.key === 'Enter' && e.target.matches('[data-bs-toggle="tab"]')) {
            e.target.click();
        }
    });

    // Enhance tab accessibility
    const tabButtons = modal.querySelectorAll('[data-bs-toggle="tab"]');
    tabButtons.forEach((tab, index) => {
        tab.addEventListener('keydown', function(e) {
            let targetTab = null;
            
            switch(e.key) {
                case 'ArrowRight':
                case 'ArrowDown':
                    e.preventDefault();
                    targetTab = tabButtons[index + 1] || tabButtons[0];
                    break;
                case 'ArrowLeft':
                case 'ArrowUp':
                    e.preventDefault();
                    targetTab = tabButtons[index - 1] || tabButtons[tabButtons.length - 1];
                    break;
                case 'Home':
                    e.preventDefault();
                    targetTab = tabButtons[0];
                    break;
                case 'End':
                    e.preventDefault();
                    targetTab = tabButtons[tabButtons.length - 1];
                    break;
            }
            
            if (targetTab) {
                targetTab.focus();
                targetTab.click();
            }
        });
    });
});

// Make functions globally available
window.populatePropertyViewModal = populatePropertyViewModal;
window.retryLoadProperty = retryLoadProperty;
window.openPropertyFullDetails = openPropertyFullDetails;
window.editPropertyFromModal = editPropertyFromModal;
window.sharePropertyFromModal = sharePropertyFromModal;
