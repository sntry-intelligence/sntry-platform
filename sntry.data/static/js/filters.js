/**
 * Jamaica Business Directory - Filtering Functionality
 * Handles category filters, location search, and advanced filtering
 */

// Global filter state
let availableCategories = [];
let selectedCategories = new Set();
let currentFilters = {};

/**
 * Load business categories from API
 */
async function loadBusinessCategories() {
    try {
        const response = await fetch(`${API_BASE_URL}/business/businesses/categories`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        availableCategories = data.categories || [];
        
        // Populate category checkboxes
        populateCategoryFilters();
        
        console.log(`Loaded ${availableCategories.length} business categories`);
        
    } catch (error) {
        console.error('Error loading business categories:', error);
        showError('Failed to load business categories');
    }
}

/**
 * Populate category filter checkboxes
 */
function populateCategoryFilters() {
    const container = document.getElementById('categoryFilters');
    container.innerHTML = '';
    
    if (availableCategories.length === 0) {
        container.innerHTML = '<p style="color: #666; font-style: italic;">No categories available</p>';
        return;
    }
    
    availableCategories.forEach(category => {
        const checkboxItem = document.createElement('div');
        checkboxItem.className = 'checkbox-item';
        
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `category-${category.replace(/\s+/g, '-').toLowerCase()}`;
        checkbox.value = category;
        checkbox.addEventListener('change', onCategoryFilterChange);
        
        const label = document.createElement('label');
        label.htmlFor = checkbox.id;
        label.textContent = category;
        
        checkboxItem.appendChild(checkbox);
        checkboxItem.appendChild(label);
        container.appendChild(checkboxItem);
    });
}

/**
 * Handle category filter changes
 */
function onCategoryFilterChange(event) {
    const category = event.target.value;
    
    if (event.target.checked) {
        selectedCategories.add(category);
    } else {
        selectedCategories.delete(category);
    }
    
    // Apply filters
    applyFilters();
}

/**
 * Select all categories
 */
function selectAllCategories() {
    const checkboxes = document.querySelectorAll('#categoryFilters input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = true;
        selectedCategories.add(checkbox.value);
    });
    
    applyFilters();
}

/**
 * Clear all category selections
 */
function clearAllCategories() {
    const checkboxes = document.querySelectorAll('#categoryFilters input[type="checkbox"]');
    checkboxes.forEach(checkbox => {
        checkbox.checked = false;
    });
    
    selectedCategories.clear();
    applyFilters();
}

/**
 * Apply current filters to business data
 */
async function applyFilters() {
    try {
        showLoading('Applying filters...');
        
        // Build filter parameters
        const params = new URLSearchParams({
            limit: 1000,
            is_active: true
        });
        
        // Add category filters
        if (selectedCategories.size > 0) {
            params.append('categories', Array.from(selectedCategories).join(','));
        }
        
        // Add search query if present
        const searchQuery = document.getElementById('searchInput').value.trim();
        if (searchQuery) {
            params.append('query', searchQuery);
        }
        
        // Make API request
        const response = await fetch(`${API_BASE_URL}/business/businesses/search/advanced?${params}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        currentBusinesses = data.businesses || [];
        
        // Update map and statistics
        updateMapMarkers();
        updateStatistics();
        
        // Show filter results
        const filterCount = selectedCategories.size;
        if (filterCount > 0) {
            showSuccess(`Applied ${filterCount} category filter(s). Found ${currentBusinesses.length} businesses.`);
        }
        
        hideLoading();
        
    } catch (error) {
        console.error('Error applying filters:', error);
        showError('Failed to apply filters. Please try again.');
        hideLoading();
    }
}

/**
 * Reset all filters
 */
function resetAllFilters() {
    // Clear search inputs
    document.getElementById('searchInput').value = '';
    document.getElementById('locationSearch').value = '';
    
    // Clear category selections
    clearAllCategories();
    
    // Reset radius slider
    const radiusSlider = document.getElementById('radiusSlider');
    radiusSlider.value = 10;
    document.getElementById('radiusValue').textContent = '10 km';
    
    // Reset advanced filters
    document.getElementById('parishFilter').value = '';
    document.getElementById('hasPhone').checked = false;
    document.getElementById('hasEmail').checked = false;
    document.getElementById('hasWebsite').checked = false;
    document.getElementById('isGeocoded').checked = false;
    document.getElementById('minRating').value = 0;
    updateMinRatingDisplay();
    
    // Reset lead scoring
    document.getElementById('leadScoreSlider').value = 50;
    updateLeadScoreDisplay();
    
    // Clear search radius from map
    if (searchRadius) {
        searchRadius.setMap(null);
        searchRadius = null;
        searchCenter = null;
    }
    
    // Hide territory overlay
    if (typeof hideTerritory === 'function') {
        hideTerritory();
    }
    
    // Reset to show all businesses
    loadBusinesses();
    
    // Clear messages
    clearMessages();
    
    showSuccess('All filters cleared');
}

/**
 * Get current filter summary
 */
function getFilterSummary() {
    const summary = {
        categories: Array.from(selectedCategories),
        search_query: document.getElementById('searchInput').value.trim(),
        location_search: document.getElementById('locationSearch').value.trim(),
        radius_km: parseFloat(document.getElementById('radiusSlider').value),
        total_businesses: currentBusinesses.length,
        visible_businesses: currentBusinesses.filter(b => b.latitude && b.longitude).length
    };
    
    return summary;
}

/**
 * Apply quick category filter
 */
function applyQuickCategoryFilter(category) {
    // Clear existing selections
    clearAllCategories();
    
    // Find and check the specific category
    const checkbox = document.querySelector(`#categoryFilters input[value="${category}"]`);
    if (checkbox) {
        checkbox.checked = true;
        selectedCategories.add(category);
        applyFilters();
    }
}

/**
 * Search businesses by multiple criteria
 */
async function advancedSearch(searchParams) {
    try {
        showLoading('Performing advanced search...');
        
        const params = new URLSearchParams({
            limit: 1000,
            is_active: true,
            ...searchParams
        });
        
        const response = await fetch(`${API_BASE_URL}/business/businesses/search/advanced?${params}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        currentBusinesses = data.businesses || [];
        
        updateMapMarkers();
        updateStatistics();
        
        hideLoading();
        
        return data;
        
    } catch (error) {
        console.error('Error performing advanced search:', error);
        showError('Advanced search failed. Please try again.');
        hideLoading();
        throw error;
    }
}

/**
 * Filter businesses by data quality
 */
async function filterByDataQuality(options = {}) {
    const {
        hasPhone = null,
        hasEmail = null,
        hasWebsite = null,
        isGeocoded = null,
        minRating = null
    } = options;
    
    try {
        showLoading('Filtering by data quality...');
        
        const params = new URLSearchParams({
            limit: 1000,
            is_active: true
        });
        
        if (hasPhone !== null) params.append('has_phone', hasPhone);
        if (hasEmail !== null) params.append('has_email', hasEmail);
        if (hasWebsite !== null) params.append('has_website', hasWebsite);
        if (isGeocoded !== null) params.append('is_geocoded', isGeocoded);
        if (minRating !== null) params.append('min_rating', minRating);
        
        const response = await fetch(`${API_BASE_URL}/business/businesses/search/advanced?${params}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        currentBusinesses = data.businesses || [];
        
        updateMapMarkers();
        updateStatistics();
        
        const qualityFilters = Object.entries(options)
            .filter(([key, value]) => value !== null)
            .map(([key, value]) => `${key}: ${value}`)
            .join(', ');
        
        showSuccess(`Applied data quality filters (${qualityFilters}). Found ${currentBusinesses.length} businesses.`);
        hideLoading();
        
    } catch (error) {
        console.error('Error filtering by data quality:', error);
        showError('Data quality filtering failed. Please try again.');
        hideLoading();
    }
}

/**
 * Apply advanced filters
 */
async function applyAdvancedFilters() {
    try {
        showLoading('Applying advanced filters...');
        
        // Get filter values
        const parish = document.getElementById('parishFilter').value;
        const hasPhone = document.getElementById('hasPhone').checked;
        const hasEmail = document.getElementById('hasEmail').checked;
        const hasWebsite = document.getElementById('hasWebsite').checked;
        const isGeocoded = document.getElementById('isGeocoded').checked;
        const minRating = parseFloat(document.getElementById('minRating').value);
        
        // Build parameters
        const params = new URLSearchParams({
            limit: 1000,
            is_active: true
        });
        
        // Add text search if present
        const searchQuery = document.getElementById('searchInput').value.trim();
        if (searchQuery) {
            params.append('query', searchQuery);
        }
        
        // Add category filters
        if (selectedCategories.size > 0) {
            params.append('categories', Array.from(selectedCategories).join(','));
        }
        
        // Add parish filter
        if (parish) {
            params.append('parish', parish);
        }
        
        // Add data quality filters
        if (hasPhone) params.append('has_phone', 'true');
        if (hasEmail) params.append('has_email', 'true');
        if (hasWebsite) params.append('has_website', 'true');
        if (isGeocoded) params.append('is_geocoded', 'true');
        
        // Add rating filter
        if (minRating > 0) {
            params.append('min_rating', minRating);
        }
        
        // Add spatial filters if we have a search center
        if (searchCenter) {
            params.append('lat', searchCenter.lat);
            params.append('lon', searchCenter.lng);
            params.append('radius', document.getElementById('radiusSlider').value);
        }
        
        const response = await fetch(`${API_BASE_URL}/business/businesses/search/advanced?${params}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        currentBusinesses = data.businesses || [];
        
        updateMapMarkers();
        updateStatistics();
        updateLeadStatistics();
        
        const filterCount = getActiveFilterCount();
        showSuccess(`Applied ${filterCount} filter(s). Found ${currentBusinesses.length} businesses.`);
        
        hideLoading();
        
    } catch (error) {
        console.error('Error applying advanced filters:', error);
        showError('Failed to apply advanced filters. Please try again.');
        hideLoading();
    }
}

/**
 * Get count of active filters
 */
function getActiveFilterCount() {
    let count = 0;
    
    if (document.getElementById('searchInput').value.trim()) count++;
    if (selectedCategories.size > 0) count++;
    if (document.getElementById('parishFilter').value) count++;
    if (document.getElementById('hasPhone').checked) count++;
    if (document.getElementById('hasEmail').checked) count++;
    if (document.getElementById('hasWebsite').checked) count++;
    if (document.getElementById('isGeocoded').checked) count++;
    if (parseFloat(document.getElementById('minRating').value) > 0) count++;
    if (searchCenter) count++;
    
    return count;
}

/**
 * Update minimum rating display
 */
function updateMinRatingDisplay() {
    const slider = document.getElementById('minRating');
    const display = document.getElementById('minRatingValue');
    const value = parseFloat(slider.value);
    
    if (value === 0) {
        display.textContent = 'Any';
    } else {
        display.textContent = value + '★';
    }
}

/**
 * Initialize filter functionality
 */
function initializeFilters() {
    // Load categories on page load
    loadBusinessCategories();
    
    // Add event listeners for filter controls
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchBusinesses();
        }
    });
    
    document.getElementById('locationSearch').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchByLocation();
        }
    });
    
    // Add radius slider change listener
    document.getElementById('radiusSlider').addEventListener('change', function() {
        // If we have a search center, update the radius circle
        if (searchCenter) {
            const radius = parseFloat(this.value);
            showSearchRadius(searchCenter, radius);
        }
    });
    
    // Add rating slider listener
    document.getElementById('minRating').addEventListener('input', updateMinRatingDisplay);
    
    // Initialize displays
    updateMinRatingDisplay();
}

// Initialize filters when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Small delay to ensure other scripts are loaded
    setTimeout(initializeFilters, 100);
});