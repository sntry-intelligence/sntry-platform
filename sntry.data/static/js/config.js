/**
 * Jamaica Business Directory - Configuration
 * Contains API endpoints, settings, and configuration
 */

// Configuration object
const CONFIG = {
    // API Configuration
    API_BASE_URL: '/api/v1',
    
    // Google Maps Configuration
    GOOGLE_MAPS_API_KEY: 'AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw', // Replace with your actual API key
    
    // Jamaica geographic bounds
    JAMAICA_CENTER: { lat: 18.1096, lng: -77.2975 },
    JAMAICA_BOUNDS: {
        north: 18.5274,
        south: 17.7011,
        east: -76.1951,
        west: -78.3377
    },
    
    // Map settings
    DEFAULT_ZOOM: 9,
    MAX_ZOOM: 18,
    MIN_ZOOM: 7,
    
    // Data limits
    MAX_BUSINESSES_LOAD: 1000,
    MAX_EXPORT_RECORDS: 5000,
    
    // UI settings
    LOADING_DELAY: 300, // ms
    SUCCESS_MESSAGE_DURATION: 3000, // ms
    ERROR_MESSAGE_DURATION: 5000, // ms
    
    // Export settings
    SUPPORTED_EXPORT_FORMATS: ['csv', 'xlsx', 'kml', 'geojson'],
    
    // Lead generation settings
    DEFAULT_MIN_LEAD_SCORE: 50.0,
    
    // Category colors for markers
    CATEGORY_COLORS: {
        'restaurant': 'orange',
        'food': 'orange',
        'hotel': 'purple',
        'accommodation': 'purple',
        'retail': 'green',
        'shopping': 'green',
        'service': 'blue',
        'automotive': 'yellow',
        'health': 'pink',
        'medical': 'pink',
        'education': 'ltblue',
        'entertainment': 'red',
        'finance': 'darkgreen',
        'bank': 'darkgreen',
        'default': 'red'
    },
    
    // Feature flags
    FEATURES: {
        ENABLE_LEAD_GENERATION: true,
        ENABLE_CUSTOMER_360: true,
        ENABLE_MYMAPS_INTEGRATION: true,
        ENABLE_ANALYTICS: true,
        ENABLE_BULK_EXPORT: true
    }
};

// Make config globally available
window.CONFIG = CONFIG;

// Update API_BASE_URL in map.js for backward compatibility
if (typeof API_BASE_URL === 'undefined') {
    window.API_BASE_URL = CONFIG.API_BASE_URL;
}

console.log('Configuration loaded:', CONFIG);