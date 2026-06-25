/**
 * Preference Storage Utilities
 * Handles user preference storage and retrieval for dual view options
 */

class PreferenceStorage {
    constructor() {
        this.storageKey = 'crm_view_preferences';
        this.defaultPreferences = {
            global: 'modal',
            property: null,
            customer: null,
            agent: null,
            deal: null,
            task: null
        };
        
        // Initialize preferences if not exists
        this.initializePreferences();
    }
    
    /**
     * Initialize preferences in localStorage if they don't exist
     */
    initializePreferences() {
        try {
            const existing = localStorage.getItem(this.storageKey);
            if (!existing) {
                const initialPreferences = {
                    ...this.defaultPreferences,
                    lastUpdated: new Date().toISOString()
                };
                localStorage.setItem(this.storageKey, JSON.stringify(initialPreferences));
            }
        } catch (error) {
            console.warn('Failed to initialize preferences in localStorage:', error);
            // Fallback to session storage
            this.useSessionStorage = true;
        }
    }
    
    /**
     * Get all preferences
     * @returns {Object} All user preferences
     */
    getAllPreferences() {
        try {
            const storage = this.useSessionStorage ? sessionStorage : localStorage;
            const preferences = storage.getItem(this.storageKey);
            
            if (preferences) {
                return JSON.parse(preferences);
            }
            
            return { ...this.defaultPreferences };
        } catch (error) {
            console.warn('Failed to retrieve preferences:', error);
            return { ...this.defaultPreferences };
        }
    }
    
    /**
     * Get preference for specific entity type
     * @param {string} entityType - The entity type (property, customer, agent, deal, task)
     * @returns {string|null} The preferred view mode or null if not set
     */
    getPreference(entityType) {
        try {
            const preferences = this.getAllPreferences();
            
            // Return entity-specific preference if set
            if (preferences[entityType]) {
                return preferences[entityType];
            }
            
            // Fall back to global preference
            return preferences.global || 'modal';
        } catch (error) {
            console.warn('Failed to get preference for', entityType, ':', error);
            return 'modal'; // Safe default
        }
    }
    
    /**
     * Set preference for specific entity type
     * @param {string} entityType - The entity type (property, customer, agent, deal, task, global)
     * @param {string} viewMode - The view mode (modal, tab)
     * @returns {boolean} Success status
     */
    setPreference(entityType, viewMode) {
        try {
            // Validate inputs
            if (!entityType || !viewMode) {
                throw new Error('Entity type and view mode are required');
            }
            
            const validEntityTypes = ['global', 'property', 'customer', 'agent', 'deal', 'task'];
            const validViewModes = ['modal', 'tab'];
            
            if (!validEntityTypes.includes(entityType)) {
                throw new Error(`Invalid entity type: ${entityType}`);
            }
            
            if (!validViewModes.includes(viewMode)) {
                throw new Error(`Invalid view mode: ${viewMode}`);
            }
            
            // Get current preferences
            const preferences = this.getAllPreferences();
            
            // Update preference
            preferences[entityType] = viewMode;
            preferences.lastUpdated = new Date().toISOString();
            
            // Save to storage
            const storage = this.useSessionStorage ? sessionStorage : localStorage;
            storage.setItem(this.storageKey, JSON.stringify(preferences));
            
            // Dispatch custom event for other components to listen
            this.dispatchPreferenceChangeEvent(entityType, viewMode);
            
            return true;
        } catch (error) {
            console.error('Failed to set preference:', error);
            return false;
        }
    }
    
    /**
     * Remove preference for specific entity type (falls back to global)
     * @param {string} entityType - The entity type
     * @returns {boolean} Success status
     */
    removePreference(entityType) {
        try {
            if (entityType === 'global') {
                // Cannot remove global preference, reset to default
                return this.setPreference('global', 'modal');
            }
            
            const preferences = this.getAllPreferences();
            delete preferences[entityType];
            preferences.lastUpdated = new Date().toISOString();
            
            const storage = this.useSessionStorage ? sessionStorage : localStorage;
            storage.setItem(this.storageKey, JSON.stringify(preferences));
            
            this.dispatchPreferenceChangeEvent(entityType, null);
            
            return true;
        } catch (error) {
            console.error('Failed to remove preference:', error);
            return false;
        }
    }
    
    /**
     * Reset all preferences to defaults
     * @returns {boolean} Success status
     */
    resetPreferences() {
        try {
            const resetPreferences = {
                ...this.defaultPreferences,
                lastUpdated: new Date().toISOString()
            };
            
            const storage = this.useSessionStorage ? sessionStorage : localStorage;
            storage.setItem(this.storageKey, JSON.stringify(resetPreferences));
            
            // Dispatch reset event
            window.dispatchEvent(new CustomEvent('preferencesReset', {
                detail: { preferences: resetPreferences }
            }));
            
            return true;
        } catch (error) {
            console.error('Failed to reset preferences:', error);
            return false;
        }
    }
    
    /**
     * Export preferences as JSON string
     * @returns {string} JSON string of preferences
     */
    exportPreferences() {
        try {
            const preferences = this.getAllPreferences();
            return JSON.stringify(preferences, null, 2);
        } catch (error) {
            console.error('Failed to export preferences:', error);
            return null;
        }
    }
    
    /**
     * Import preferences from JSON string
     * @param {string} preferencesJson - JSON string of preferences
     * @returns {boolean} Success status
     */
    importPreferences(preferencesJson) {
        try {
            const preferences = JSON.parse(preferencesJson);
            
            // Validate structure
            if (typeof preferences !== 'object' || preferences === null) {
                throw new Error('Invalid preferences format');
            }
            
            // Merge with defaults to ensure all required fields exist
            const mergedPreferences = {
                ...this.defaultPreferences,
                ...preferences,
                lastUpdated: new Date().toISOString()
            };
            
            const storage = this.useSessionStorage ? sessionStorage : localStorage;
            storage.setItem(this.storageKey, JSON.stringify(mergedPreferences));
            
            // Dispatch import event
            window.dispatchEvent(new CustomEvent('preferencesImported', {
                detail: { preferences: mergedPreferences }
            }));
            
            return true;
        } catch (error) {
            console.error('Failed to import preferences:', error);
            return false;
        }
    }
    
    /**
     * Check if localStorage is available and working
     * @returns {boolean} Availability status
     */
    isLocalStorageAvailable() {
        try {
            const test = '__localStorage_test__';
            localStorage.setItem(test, test);
            localStorage.removeItem(test);
            return true;
        } catch (error) {
            return false;
        }
    }
    
    /**
     * Get storage statistics
     * @returns {Object} Storage usage information
     */
    getStorageStats() {
        try {
            const preferences = this.getAllPreferences();
            const jsonString = JSON.stringify(preferences);
            
            return {
                size: jsonString.length,
                sizeKB: (jsonString.length / 1024).toFixed(2),
                entityCount: Object.keys(preferences).filter(key => key !== 'lastUpdated').length,
                lastUpdated: preferences.lastUpdated,
                storageType: this.useSessionStorage ? 'sessionStorage' : 'localStorage'
            };
        } catch (error) {
            console.error('Failed to get storage stats:', error);
            return null;
        }
    }
    
    /**
     * Dispatch preference change event
     * @private
     * @param {string} entityType - The entity type that changed
     * @param {string|null} viewMode - The new view mode or null if removed
     */
    dispatchPreferenceChangeEvent(entityType, viewMode) {
        try {
            window.dispatchEvent(new CustomEvent('preferenceChanged', {
                detail: {
                    entityType,
                    viewMode,
                    timestamp: new Date().toISOString()
                }
            }));
        } catch (error) {
            console.warn('Failed to dispatch preference change event:', error);
        }
    }
    
    /**
     * Add event listener for preference changes
     * @param {Function} callback - Callback function to handle preference changes
     * @returns {Function} Cleanup function to remove the listener
     */
    onPreferenceChange(callback) {
        const handler = (event) => {
            if (typeof callback === 'function') {
                callback(event.detail);
            }
        };
        
        window.addEventListener('preferenceChanged', handler);
        
        // Return cleanup function
        return () => {
            window.removeEventListener('preferenceChanged', handler);
        };
    }
}

// Create global instance
window.PreferenceStorage = PreferenceStorage;

// Create default instance for immediate use
if (typeof window.preferenceStorage === 'undefined') {
    window.preferenceStorage = new PreferenceStorage();
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PreferenceStorage;
}