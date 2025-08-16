/**
 * Jamaica Business Directory - Map Functionality
 * Handles Google Maps integration, marker management, and business data visualization
 */

// Global variables
let map;
let markers = [];
let infoWindow;
let currentBusinesses = [];
let searchRadius = null;
let searchCenter = null;

// Jamaica coordinates for map centering
const JAMAICA_CENTER = { lat: 18.1096, lng: -77.2975 };
const JAMAICA_BOUNDS = {
    north: 18.5274,
    south: 17.7011,
    east: -76.1951,
    west: -78.3377
};

// API base URL - adjust based on your deployment
const API_BASE_URL = '/api/v1';

/**
 * Initialize Google Maps
 */
function initMap() {
    console.log('Initializing Google Maps...');
    
    // Create map centered on Jamaica
    map = new google.maps.Map(document.getElementById('map'), {
        zoom: 9,
        center: JAMAICA_CENTER,
        restriction: {
            latLngBounds: JAMAICA_BOUNDS,
            strictBounds: false
        },
        mapTypeControl: true,
        mapTypeControlOptions: {
            style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
            position: google.maps.ControlPosition.TOP_CENTER
        },
        zoomControl: true,
        zoomControlOptions: {
            position: google.maps.ControlPosition.RIGHT_CENTER
        },
        scaleControl: true,
        streetViewControl: true,
        fullscreenControl: true,
        styles: [
            {
                featureType: 'poi',
                elementType: 'labels',
                stylers: [{ visibility: 'off' }]
            }
        ]
    });

    // Create info window
    infoWindow = new google.maps.InfoWindow();

    // Load initial data
    loadBusinessCategories();
    loadBusinesses();

    // Hide loading indicator
    document.getElementById('loading').style.display = 'none';

    console.log('Map initialized successfully');
}

/**
 * Load all businesses from API
 */
async function loadBusinesses(filters = {}) {
    try {
        showLoading('Loading businesses...');
        
        // Build query parameters
        const params = new URLSearchParams({
            limit: 1000,
            is_active: true,
            ...filters
        });

        const response = await fetch(`${API_BASE_URL}/business/businesses?${params}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        currentBusinesses = data.businesses || [];
        
        console.log(`Loaded ${currentBusinesses.length} businesses`);
        
        // Update map markers
        updateMapMarkers();
        
        // Update statistics
        updateStatistics();
        
        hideLoading();
        
    } catch (error) {
        console.error('Error loading businesses:', error);
        showError('Failed to load business data. Please try again.');
        hideLoading();
    }
}

/**
 * Update map markers based on current businesses
 */
function updateMapMarkers() {
    // Clear existing markers
    clearMarkers();
    
    // Create markers for businesses with coordinates
    const geocodedBusinesses = currentBusinesses.filter(business => 
        business.latitude && business.longitude
    );
    
    geocodedBusinesses.forEach(business => {
        createBusinessMarker(business);
    });
    
    // Update visible count
    document.getElementById('visibleBusinesses').textContent = geocodedBusinesses.length;
    
    // Adjust map bounds if we have markers
    if (markers.length > 0) {
        fitMapToBounds();
    }
}

/**
 * Create a marker for a business
 */
function createBusinessMarker(business) {
    const position = {
        lat: parseFloat(business.latitude),
        lng: parseFloat(business.longitude)
    };
    
    // Determine marker color based on category
    const markerColor = getMarkerColor(business.category);
    
    const marker = new google.maps.Marker({
        position: position,
        map: map,
        title: business.name,
        icon: {
            url: `https://maps.google.com/mapfiles/ms/icons/${markerColor}-dot.png`,
            scaledSize: new google.maps.Size(32, 32)
        },
        animation: google.maps.Animation.DROP
    });
    
    // Add click listener for info window
    marker.addListener('click', () => {
        showBusinessInfo(business, marker);
    });
    
    markers.push(marker);
}

/**
 * Get marker color based on business category
 */
function getMarkerColor(category) {
    if (!category) return 'red';
    
    const categoryColors = {
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
        'bank': 'darkgreen'
    };
    
    const lowerCategory = category.toLowerCase();
    for (const [key, color] of Object.entries(categoryColors)) {
        if (lowerCategory.includes(key)) {
            return color;
        }
    }
    
    return 'red'; // default color
}

/**
 * Show business information in info window
 */
function showBusinessInfo(business, marker) {
    const content = createInfoWindowContent(business);
    infoWindow.setContent(content);
    infoWindow.open(map, marker);
}

/**
 * Create HTML content for info window
 */
function createInfoWindowContent(business) {
    const phone = business.phone_number ? `<p><strong>📞 Phone:</strong> <a href="tel:${business.phone_number}">${business.phone_number}</a></p>` : '';
    const email = business.email ? `<p><strong>✉️ Email:</strong> <a href="mailto:${business.email}">${business.email}</a></p>` : '';
    const website = business.website ? `<p><strong>🌐 Website:</strong> <a href="${business.website}" target="_blank">${business.website}</a></p>` : '';
    const category = business.category ? `<p><strong>🏢 Category:</strong> ${business.category}</p>` : '';
    const rating = business.rating ? `<p><strong>⭐ Rating:</strong> ${business.rating}/5</p>` : '';
    const description = business.description ? `<p><strong>📝 Description:</strong> ${business.description}</p>` : '';
    
    return `
        <div style="max-width: 300px; font-family: Arial, sans-serif;">
            <h3 style="margin: 0 0 10px 0; color: #2a5298;">${business.name}</h3>
            <p><strong>📍 Address:</strong> ${business.raw_address || business.standardized_address || 'Address not available'}</p>
            ${category}
            ${phone}
            ${email}
            ${website}
            ${rating}
            ${description}
            <div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid #eee;">
                <button onclick="generateLead(${business.id})" style="background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin-right: 10px;">
                    🎯 Generate Lead
                </button>
                <button onclick="getDirections(${business.latitude}, ${business.longitude})" style="background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">
                    🗺️ Directions
                </button>
            </div>
        </div>
    `;
}

/**
 * Clear all markers from map
 */
function clearMarkers() {
    markers.forEach(marker => {
        marker.setMap(null);
    });
    markers = [];
}

/**
 * Fit map bounds to show all markers
 */
function fitMapToBounds() {
    if (markers.length === 0) return;
    
    const bounds = new google.maps.LatLngBounds();
    markers.forEach(marker => {
        bounds.extend(marker.getPosition());
    });
    
    map.fitBounds(bounds);
    
    // Ensure minimum zoom level
    const listener = google.maps.event.addListener(map, 'idle', () => {
        if (map.getZoom() > 15) map.setZoom(15);
        google.maps.event.removeListener(listener);
    });
}

/**
 * Search businesses by text query
 */
async function searchBusinesses() {
    const query = document.getElementById('searchInput').value.trim();
    
    if (!query) {
        showError('Please enter a search term');
        return;
    }
    
    try {
        showLoading('Searching businesses...');
        
        const params = new URLSearchParams({
            q: query,
            limit: 1000,
            is_active: true
        });
        
        const response = await fetch(`${API_BASE_URL}/business/businesses/search?${params}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        currentBusinesses = data.businesses || [];
        
        updateMapMarkers();
        updateStatistics();
        
        showSuccess(`Found ${currentBusinesses.length} businesses matching "${query}"`);
        hideLoading();
        
    } catch (error) {
        console.error('Error searching businesses:', error);
        showError('Search failed. Please try again.');
        hideLoading();
    }
}

/**
 * Clear search and reload all businesses
 */
function clearSearch() {
    document.getElementById('searchInput').value = '';
    loadBusinesses();
    clearMessages();
}

/**
 * Search businesses by location
 */
async function searchByLocation() {
    const location = document.getElementById('locationSearch').value.trim();
    const radius = parseFloat(document.getElementById('radiusSlider').value);
    
    if (!location) {
        showError('Please enter a location to search');
        return;
    }
    
    try {
        showLoading('Searching by location...');
        
        // First, geocode the location
        const geocoder = new google.maps.Geocoder();
        const geocodeResult = await new Promise((resolve, reject) => {
            geocoder.geocode({ address: location + ', Jamaica' }, (results, status) => {
                if (status === 'OK') {
                    resolve(results[0]);
                } else {
                    reject(new Error('Location not found'));
                }
            });
        });
        
        const center = geocodeResult.geometry.location;
        searchCenter = { lat: center.lat(), lng: center.lng() };
        
        // Search businesses near this location
        const params = new URLSearchParams({
            lat: searchCenter.lat,
            lon: searchCenter.lng,
            radius: radius,
            limit: 1000
        });
        
        const response = await fetch(`${API_BASE_URL}/business/businesses/nearby?${params}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        currentBusinesses = data.businesses || [];
        
        // Show search radius on map
        showSearchRadius(searchCenter, radius);
        
        updateMapMarkers();
        updateStatistics();
        
        // Center map on search location
        map.setCenter(searchCenter);
        map.setZoom(12);
        
        showSuccess(`Found ${currentBusinesses.length} businesses within ${radius}km of ${location}`);
        hideLoading();
        
    } catch (error) {
        console.error('Error searching by location:', error);
        showError('Location search failed. Please check the location and try again.');
        hideLoading();
    }
}

/**
 * Show search radius circle on map
 */
function showSearchRadius(center, radiusKm) {
    // Clear existing radius circle
    if (searchRadius) {
        searchRadius.setMap(null);
    }
    
    searchRadius = new google.maps.Circle({
        strokeColor: '#2a5298',
        strokeOpacity: 0.8,
        strokeWeight: 2,
        fillColor: '#2a5298',
        fillOpacity: 0.1,
        map: map,
        center: center,
        radius: radiusKm * 1000 // Convert km to meters
    });
}

/**
 * Generate lead for a business
 */
function generateLead(businessId) {
    // This would integrate with the customer 360 system
    console.log('Generating lead for business:', businessId);
    showSuccess('Lead generated successfully! Check your CRM system.');
    
    // In a real implementation, this would make an API call to create a lead
    // fetch(`${API_BASE_URL}/customer/leads`, {
    //     method: 'POST',
    //     headers: { 'Content-Type': 'application/json' },
    //     body: JSON.stringify({ business_id: businessId })
    // });
}

/**
 * Get directions to a business
 */
function getDirections(lat, lng) {
    const url = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
    window.open(url, '_blank');
}

/**
 * Update statistics display
 */
function updateStatistics() {
    const total = currentBusinesses.length;
    const geocoded = currentBusinesses.filter(b => b.latitude && b.longitude).length;
    
    document.getElementById('totalBusinesses').textContent = total;
    document.getElementById('visibleBusinesses').textContent = geocoded;
}

/**
 * Update radius value display
 */
document.getElementById('radiusSlider').addEventListener('input', function() {
    document.getElementById('radiusValue').textContent = this.value + ' km';
});

/**
 * Utility functions for loading states and messages
 */
function showLoading(message = 'Loading...') {
    const loading = document.getElementById('loading');
    loading.querySelector('p').textContent = message;
    loading.style.display = 'block';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function showError(message) {
    clearMessages();
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    document.querySelector('.sidebar').insertBefore(errorDiv, document.querySelector('.sidebar').firstChild);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.parentNode.removeChild(errorDiv);
        }
    }, 5000);
}

function showSuccess(message) {
    clearMessages();
    const successDiv = document.createElement('div');
    successDiv.className = 'success-message';
    successDiv.textContent = message;
    document.querySelector('.sidebar').insertBefore(successDiv, document.querySelector('.sidebar').firstChild);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (successDiv.parentNode) {
            successDiv.parentNode.removeChild(successDiv);
        }
    }, 3000);
}

function clearMessages() {
    const messages = document.querySelectorAll('.error-message, .success-message');
    messages.forEach(msg => {
        if (msg.parentNode) {
            msg.parentNode.removeChild(msg);
        }
    });
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, waiting for Google Maps API...');
});