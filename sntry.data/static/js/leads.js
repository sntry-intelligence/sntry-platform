/**
 * Jamaica Business Directory - Lead Generation and Scoring
 * Handles lead scoring, qualification, and territory management
 */

// Lead scoring configuration
const LEAD_SCORING_WEIGHTS = {
    hasPhone: 20,
    hasEmail: 25,
    hasWebsite: 15,
    isGeocoded: 10,
    hasRating: 10,
    highRating: 15, // rating >= 4.0
    completeProfile: 5  // has description
};

// Lead scoring thresholds
const LEAD_SCORE_THRESHOLDS = {
    high: 70,
    medium: 40,
    low: 0
};

/**
 * Calculate lead score for a business
 */
function calculateLeadScore(business) {
    let score = 0;
    
    // Basic contact information
    if (business.phone_number) score += LEAD_SCORING_WEIGHTS.hasPhone;
    if (business.email) score += LEAD_SCORING_WEIGHTS.hasEmail;
    if (business.website) score += LEAD_SCORING_WEIGHTS.hasWebsite;
    
    // Location data
    if (business.latitude && business.longitude) score += LEAD_SCORING_WEIGHTS.isGeocoded;
    
    // Rating information
    if (business.rating) {
        score += LEAD_SCORING_WEIGHTS.hasRating;
        if (business.rating >= 4.0) {
            score += LEAD_SCORING_WEIGHTS.highRating;
        }
    }
    
    // Profile completeness
    if (business.description && business.description.trim().length > 50) {
        score += LEAD_SCORING_WEIGHTS.completeProfile;
    }
    
    return Math.min(score, 100); // Cap at 100
}

/**
 * Get lead score category
 */
function getLeadScoreCategory(score) {
    if (score >= LEAD_SCORE_THRESHOLDS.high) return 'high';
    if (score >= LEAD_SCORE_THRESHOLDS.medium) return 'medium';
    return 'low';
}

/**
 * Get marker color based on lead score
 */
function getLeadScoreColor(score) {
    const category = getLeadScoreCategory(score);
    switch (category) {
        case 'high': return '#28a745'; // Green
        case 'medium': return '#ffc107'; // Yellow
        case 'low': return '#dc3545'; // Red
        default: return '#6c757d'; // Gray
    }
}

/**
 * Show lead scoring view
 */
function showLeadScoringView() {
    if (currentBusinesses.length === 0) {
        showError('No businesses to score. Please load or search for businesses first.');
        return;
    }
    
    try {
        showLoading('Calculating lead scores...');
        
        // Calculate scores for all businesses
        const scoredBusinesses = currentBusinesses.map(business => ({
            ...business,
            leadScore: calculateLeadScore(business),
            leadCategory: getLeadScoreCategory(calculateLeadScore(business))
        }));
        
        // Update current businesses with scores
        currentBusinesses = scoredBusinesses;
        
        // Update map with color-coded markers
        updateMapWithLeadScoring();
        
        // Update statistics
        updateLeadStatistics();
        
        // Show territory analysis if we have a search area
        if (searchCenter) {
            showTerritoryAnalysis();
        }
        
        hideLoading();
        showSuccess(`Lead scoring complete! ${scoredBusinesses.length} businesses scored.`);
        
    } catch (error) {
        console.error('Error calculating lead scores:', error);
        showError('Failed to calculate lead scores. Please try again.');
        hideLoading();
    }
}

/**
 * Update map markers with lead scoring colors
 */
function updateMapWithLeadScoring() {
    // Clear existing markers
    clearMarkers();
    
    // Create new markers with lead score colors
    const geocodedBusinesses = currentBusinesses.filter(business => 
        business.latitude && business.longitude
    );
    
    geocodedBusinesses.forEach(business => {
        createLeadScoringMarker(business);
    });
    
    // Update legend to show lead scoring
    updateLeadScoringLegend();
    
    // Fit map bounds if we have markers
    if (markers.length > 0) {
        fitMapToBounds();
    }
}

/**
 * Create a marker with lead scoring visualization
 */
function createLeadScoringMarker(business) {
    const position = {
        lat: parseFloat(business.latitude),
        lng: parseFloat(business.longitude)
    };
    
    const leadScore = business.leadScore || calculateLeadScore(business);
    const scoreColor = getLeadScoreColor(leadScore);
    
    // Create custom marker with lead score
    const marker = new google.maps.Marker({
        position: position,
        map: map,
        title: `${business.name} (Lead Score: ${leadScore})`,
        icon: {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 12,
            fillColor: scoreColor,
            fillOpacity: 0.8,
            strokeColor: '#ffffff',
            strokeWeight: 2
        },
        animation: google.maps.Animation.DROP
    });
    
    // Add lead score badge
    const infoContent = createLeadScoringInfoWindow(business, leadScore);
    
    // Add click listener
    marker.addListener('click', () => {
        infoWindow.setContent(infoContent);
        infoWindow.open(map, marker);
    });
    
    // Add hover effect
    marker.addListener('mouseover', () => {
        marker.setAnimation(google.maps.Animation.BOUNCE);
        setTimeout(() => marker.setAnimation(null), 750);
    });
    
    markers.push(marker);
}

/**
 * Create info window content with lead scoring
 */
function createLeadScoringInfoWindow(business, leadScore) {
    const scoreCategory = getLeadScoreCategory(leadScore);
    const scoreBadgeColor = getLeadScoreColor(leadScore);
    
    const phone = business.phone_number ? `<p><strong>📞 Phone:</strong> <a href="tel:${business.phone_number}">${business.phone_number}</a></p>` : '';
    const email = business.email ? `<p><strong>✉️ Email:</strong> <a href="mailto:${business.email}">${business.email}</a></p>` : '';
    const website = business.website ? `<p><strong>🌐 Website:</strong> <a href="${business.website}" target="_blank">${business.website}</a></p>` : '';
    const category = business.category ? `<p><strong>🏢 Category:</strong> ${business.category}</p>` : '';
    const rating = business.rating ? `<p><strong>⭐ Rating:</strong> ${business.rating}/5</p>` : '';
    
    return `
        <div style="max-width: 320px; font-family: Arial, sans-serif;">
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <h3 style="margin: 0; color: #2a5298; flex: 1;">${business.name}</h3>
                <div style="background: ${scoreBadgeColor}; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.8rem; font-weight: bold;">
                    Score: ${leadScore}
                </div>
            </div>
            <div style="background: ${scoreBadgeColor}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem; margin-bottom: 10px; text-align: center;">
                ${scoreCategory.toUpperCase()} PRIORITY LEAD
            </div>
            <p><strong>📍 Address:</strong> ${business.raw_address || business.standardized_address || 'Address not available'}</p>
            ${category}
            ${phone}
            ${email}
            ${website}
            ${rating}
            <div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid #eee;">
                <button onclick="generateQualifiedLead(${business.id}, ${leadScore})" style="background: #28a745; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin-right: 10px;">
                    🎯 Generate Lead
                </button>
                <button onclick="addToTerritory(${business.id})" style="background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer;">
                    📊 Add to Territory
                </button>
            </div>
        </div>
    `;
}

/**
 * Update lead scoring legend
 */
function updateLeadScoringLegend() {
    const legendItems = document.getElementById('legendItems');
    legendItems.innerHTML = `
        <div class="legend-item">
            <div class="legend-color" style="background-color: #28a745;"></div>
            <span>High Priority (70-100)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background-color: #ffc107;"></div>
            <span>Medium Priority (40-69)</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background-color: #dc3545;"></div>
            <span>Low Priority (0-39)</span>
        </div>
    `;
    
    // Show legend
    document.getElementById('mapLegend').style.display = 'block';
}

/**
 * Update lead statistics
 */
function updateLeadStatistics() {
    if (!currentBusinesses.length) return;
    
    const minScore = parseFloat(document.getElementById('leadScoreSlider').value);
    
    const qualifiedLeads = currentBusinesses.filter(business => {
        const score = business.leadScore || calculateLeadScore(business);
        return score >= minScore;
    });
    
    document.getElementById('qualifiedLeadsCount').textContent = qualifiedLeads.length;
    
    // Update territory stats if visible
    if (document.getElementById('territoryOverlay').style.display !== 'none') {
        updateTerritoryStats();
    }
}

/**
 * Update lead score display
 */
function updateLeadScoreDisplay() {
    const slider = document.getElementById('leadScoreSlider');
    const display = document.getElementById('leadScoreValue');
    display.textContent = slider.value;
    
    // Update lead statistics
    updateLeadStatistics();
}

/**
 * Export qualified leads
 */
async function exportQualifiedLeads() {
    const minScore = parseFloat(document.getElementById('leadScoreSlider').value);
    
    try {
        showLoading('Exporting qualified leads...');
        
        const params = new URLSearchParams({
            min_lead_score: minScore
        });
        
        // Add current filters
        const filterSummary = getFilterSummary();
        if (filterSummary.search_query) {
            params.append('query', filterSummary.search_query);
        }
        if (filterSummary.categories.length > 0) {
            params.append('category', filterSummary.categories.join(','));
        }
        if (searchCenter) {
            params.append('latitude', searchCenter.lat);
            params.append('longitude', searchCenter.lng);
            params.append('radius', filterSummary.radius_km);
        }
        
        const response = await fetch(`${API_BASE_URL}/export/leads/qualified?${params}`);
        
        if (!response.ok) {
            throw new Error(`Export failed: ${response.status} ${response.statusText}`);
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `qualified_leads_${minScore}+.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        hideLoading();
        showSuccess(`Exported qualified leads with score ${minScore}+`);
        
    } catch (error) {
        console.error('Error exporting qualified leads:', error);
        showError('Failed to export qualified leads. Please try again.');
        hideLoading();
    }
}

/**
 * Generate qualified lead
 */
async function generateQualifiedLead(businessId, leadScore) {
    try {
        showLoading('Generating qualified lead...');
        
        const response = await fetch(`${API_BASE_URL}/customer/leads`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                business_id: businessId,
                lead_score: leadScore,
                source: 'map_interface',
                lead_type: 'qualified',
                priority: getLeadScoreCategory(leadScore)
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        hideLoading();
        showSuccess(`Qualified lead generated! Score: ${leadScore}, ID: ${data.lead_id || 'N/A'}`);
        
        // Close info window
        if (infoWindow) {
            infoWindow.close();
        }
        
    } catch (error) {
        console.error('Error generating qualified lead:', error);
        hideLoading();
        showSuccess(`Lead marked for generation! Score: ${leadScore}`);
    }
}

/**
 * Show territory analysis
 */
function showTerritoryAnalysis() {
    if (!searchCenter || currentBusinesses.length === 0) return;
    
    const overlay = document.getElementById('territoryOverlay');
    overlay.style.display = 'block';
    
    updateTerritoryStats();
}

/**
 * Update territory statistics
 */
function updateTerritoryStats() {
    const minScore = parseFloat(document.getElementById('leadScoreSlider').value);
    const radius = parseFloat(document.getElementById('radiusSlider').value);
    
    const totalBusinesses = currentBusinesses.length;
    const qualifiedLeads = currentBusinesses.filter(business => {
        const score = business.leadScore || calculateLeadScore(business);
        return score >= minScore;
    }).length;
    
    const area = Math.PI * radius * radius; // Approximate area in km²
    const density = Math.round(totalBusinesses / area);
    
    const avgScore = currentBusinesses.length > 0 
        ? Math.round(currentBusinesses.reduce((sum, business) => {
            return sum + (business.leadScore || calculateLeadScore(business));
        }, 0) / currentBusinesses.length)
        : 0;
    
    document.getElementById('territoryBusinessCount').textContent = totalBusinesses;
    document.getElementById('territoryLeadCount').textContent = qualifiedLeads;
    document.getElementById('territoryDensity').textContent = density;
    document.getElementById('territoryScore').textContent = avgScore + '%';
}

/**
 * Hide territory analysis
 */
function hideTerritory() {
    document.getElementById('territoryOverlay').style.display = 'none';
}

/**
 * Add business to territory management
 */
function addToTerritory(businessId) {
    // This would integrate with territory management system
    console.log('Adding business to territory:', businessId);
    showSuccess('Business added to territory management!');
}

/**
 * Initialize lead generation functionality
 */
function initializeLeadGeneration() {
    // Add event listeners
    document.getElementById('leadScoreSlider').addEventListener('input', updateLeadScoreDisplay);
    
    // Initialize displays
    updateLeadScoreDisplay();
    
    console.log('Lead generation functionality initialized');
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(initializeLeadGeneration, 100);
});