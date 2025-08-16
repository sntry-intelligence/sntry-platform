/**
 * Jamaica Business Directory - Customer 360 Dashboard Integration
 * Handles customer profiles, behavior tracking, and sales pipeline integration
 */

// Customer 360 state
let currentCustomer360 = null;
let customerDashboardVisible = false;
let realTimeNotifications = [];

/**
 * Show customer 360 profile overlay
 */
async function showCustomer360Profile(businessId) {
    try {
        showLoading('Loading customer 360 profile...');
        
        // First, try to find customer associated with this business
        const customerResponse = await fetch(`${API_BASE_URL}/customer/leads/by-location?lat=${currentBusinesses.find(b => b.id === businessId)?.latitude}&lon=${currentBusinesses.find(b => b.id === businessId)?.longitude}&radius=0.1&limit=1`);
        
        if (!customerResponse.ok) {
            throw new Error(`HTTP error! status: ${customerResponse.status}`);
        }
        
        const customerData = await customerResponse.json();
        
        if (customerData.leads && customerData.leads.length > 0) {
            const customerId = customerData.leads[0].customer_id;
            await loadCustomer360View(customerId);
        } else {
            // Create a potential customer profile based on business data
            await createPotentialCustomerProfile(businessId);
        }
        
        hideLoading();
        
    } catch (error) {
        console.error('Error loading customer 360 profile:', error);
        hideLoading();
        showError('Failed to load customer profile. Please try again.');
    }
}

/**
 * Load comprehensive customer 360 view
 */
async function loadCustomer360View(customerId) {
    try {
        const response = await fetch(`${API_BASE_URL}/customer/customers/${customerId}/360-view`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const customer360Data = await response.json();
        currentCustomer360 = customer360Data;
        
        // Display customer 360 overlay
        displayCustomer360Overlay(customer360Data);
        
    } catch (error) {
        console.error('Error loading customer 360 view:', error);
        throw error;
    }
}

/**
 * Create potential customer profile from business data
 */
async function createPotentialCustomerProfile(businessId) {
    const business = currentBusinesses.find(b => b.id === businessId);
    if (!business) return;
    
    const potentialCustomer = {
        customer_id: null,
        customer: {
            id: null,
            company_name: business.name,
            email: business.email,
            phone_number: business.phone_number,
            industry: business.category,
            lead_status: 'potential',
            lead_score: calculateLeadScore(business),
            customer_type: 'prospect'
        },
        interactions: [],
        business_relationships: [{
            business_id: business.id,
            business_name: business.name,
            relationship_type: 'prospect',
            status: 'active'
        }],
        connected_businesses: [business],
        metrics: {
            total_interactions: 0,
            last_interaction_date: null,
            interaction_frequency: 0,
            engagement_score: 0,
            recency_score: 0,
            frequency_score: 0
        },
        social_media_presence: {},
        predictive_analytics: {
            churn_probability: 0,
            lifetime_value_prediction: 0,
            next_best_action: 'Initial Contact'
        }
    };
    
    currentCustomer360 = potentialCustomer;
    displayCustomer360Overlay(potentialCustomer);
}

/**
 * Display customer 360 overlay
 */
function displayCustomer360Overlay(customer360Data) {
    // Remove existing overlay if present
    const existingOverlay = document.getElementById('customer360Overlay');
    if (existingOverlay) {
        existingOverlay.remove();
    }
    
    const overlay = document.createElement('div');
    overlay.id = 'customer360Overlay';
    overlay.className = 'customer360-overlay';
    overlay.innerHTML = createCustomer360HTML(customer360Data);
    
    document.body.appendChild(overlay);
    customerDashboardVisible = true;
    
    // Add event listeners
    setupCustomer360EventListeners();
    
    // Start real-time updates if this is an existing customer
    if (customer360Data.customer_id) {
        startRealTimeCustomerTracking(customer360Data.customer_id);
    }
}

/**
 * Create customer 360 HTML content
 */
function createCustomer360HTML(customer360Data) {
    const customer = customer360Data.customer;
    const metrics = customer360Data.metrics;
    const predictive = customer360Data.predictive_analytics;
    
    const leadScoreColor = getLeadScoreColor(customer.lead_score || 0);
    const churnRisk = predictive.churn_probability > 0.7 ? 'High' : 
                     predictive.churn_probability > 0.4 ? 'Medium' : 'Low';
    const churnColor = churnRisk === 'High' ? '#dc3545' : 
                      churnRisk === 'Medium' ? '#ffc107' : '#28a745';
    
    return `
        <div class="customer360-content">
            <div class="customer360-header">
                <div class="customer-info">
                    <h2>${customer.company_name || customer.first_name + ' ' + customer.last_name || 'Unknown Customer'}</h2>
                    <div class="customer-badges">
                        <span class="badge" style="background: ${leadScoreColor};">
                            Lead Score: ${customer.lead_score || 0}
                        </span>
                        <span class="badge badge-${customer.lead_status || 'unknown'}">
                            ${(customer.lead_status || 'potential').toUpperCase()}
                        </span>
                        <span class="badge" style="background: ${churnColor};">
                            Churn Risk: ${churnRisk}
                        </span>
                    </div>
                </div>
                <div class="customer360-actions">
                    <button class="btn btn-primary" onclick="createInteraction()">📞 Log Interaction</button>
                    <button class="btn btn-secondary" onclick="updateLeadStatus()">📊 Update Status</button>
                    <button class="btn btn-secondary" onclick="closeCustomer360()">✕ Close</button>
                </div>
            </div>
            
            <div class="customer360-body">
                <div class="customer360-grid">
                    <!-- Contact Information -->
                    <div class="customer360-card">
                        <h3>📞 Contact Information</h3>
                        <div class="contact-info">
                            <p><strong>Email:</strong> ${customer.email || 'Not available'}</p>
                            <p><strong>Phone:</strong> ${customer.phone_number || 'Not available'}</p>
                            <p><strong>Industry:</strong> ${customer.industry || 'Not specified'}</p>
                            <p><strong>Type:</strong> ${customer.customer_type || 'Prospect'}</p>
                        </div>
                    </div>
                    
                    <!-- Engagement Metrics -->
                    <div class="customer360-card">
                        <h3>📈 Engagement Metrics</h3>
                        <div class="metrics-grid">
                            <div class="metric">
                                <div class="metric-value">${metrics.total_interactions || 0}</div>
                                <div class="metric-label">Total Interactions</div>
                            </div>
                            <div class="metric">
                                <div class="metric-value">${metrics.engagement_score || 0}%</div>
                                <div class="metric-label">Engagement Score</div>
                            </div>
                            <div class="metric">
                                <div class="metric-value">${metrics.recency_score || 0}%</div>
                                <div class="metric-label">Recency Score</div>
                            </div>
                            <div class="metric">
                                <div class="metric-value">${metrics.frequency_score || 0}%</div>
                                <div class="metric-label">Frequency Score</div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Recent Interactions -->
                    <div class="customer360-card">
                        <h3>💬 Recent Interactions</h3>
                        <div class="interactions-list">
                            ${createInteractionsList(customer360Data.interactions)}
                        </div>
                        <button class="btn btn-sm btn-primary" onclick="viewAllInteractions()">View All</button>
                    </div>
                    
                    <!-- Connected Businesses -->
                    <div class="customer360-card">
                        <h3>🏢 Connected Businesses</h3>
                        <div class="businesses-list">
                            ${createBusinessesList(customer360Data.connected_businesses)}
                        </div>
                    </div>
                    
                    <!-- Sales Pipeline -->
                    <div class="customer360-card">
                        <h3>🎯 Sales Pipeline</h3>
                        <div class="pipeline-info">
                            <div class="pipeline-stage">
                                <strong>Current Stage:</strong> ${customer.lead_status || 'Prospect'}
                            </div>
                            <div class="pipeline-probability">
                                <strong>Conversion Probability:</strong> ${Math.round((100 - (predictive.churn_probability * 100)))}%
                            </div>
                            <div class="pipeline-value">
                                <strong>Predicted LTV:</strong> $${predictive.lifetime_value_prediction || 0}
                            </div>
                            <div class="next-action">
                                <strong>Next Best Action:</strong> ${predictive.next_best_action || 'Contact customer'}
                            </div>
                        </div>
                    </div>
                    
                    <!-- Real-time Activity -->
                    <div class="customer360-card">
                        <h3>⚡ Real-time Activity</h3>
                        <div id="realTimeActivity" class="activity-feed">
                            <p class="no-activity">No recent activity</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Real-time Notifications -->
            <div id="customer360Notifications" class="customer360-notifications">
                <!-- Notifications will appear here -->
            </div>
        </div>
    `;
}

/**
 * Create interactions list HTML
 */
function createInteractionsList(interactions) {
    if (!interactions || interactions.length === 0) {
        return '<p class="no-data">No interactions recorded</p>';
    }
    
    return interactions.slice(0, 3).map(interaction => `
        <div class="interaction-item">
            <div class="interaction-type">${interaction.interaction_type}</div>
            <div class="interaction-date">${new Date(interaction.interaction_date).toLocaleDateString()}</div>
            <div class="interaction-notes">${interaction.notes || 'No notes'}</div>
        </div>
    `).join('');
}

/**
 * Create businesses list HTML
 */
function createBusinessesList(businesses) {
    if (!businesses || businesses.length === 0) {
        return '<p class="no-data">No connected businesses</p>';
    }
    
    return businesses.slice(0, 3).map(business => `
        <div class="business-item">
            <div class="business-name">${business.name}</div>
            <div class="business-category">${business.category || 'Unknown'}</div>
            <button class="btn btn-sm btn-outline" onclick="focusOnBusiness(${business.id})">View on Map</button>
        </div>
    `).join('');
}

/**
 * Setup customer 360 event listeners
 */
function setupCustomer360EventListeners() {
    // Close overlay when clicking outside
    document.addEventListener('click', function(e) {
        const overlay = document.getElementById('customer360Overlay');
        if (overlay && e.target === overlay) {
            closeCustomer360();
        }
    });
    
    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (customerDashboardVisible && e.key === 'Escape') {
            closeCustomer360();
        }
    });
}

/**
 * Close customer 360 overlay
 */
function closeCustomer360() {
    const overlay = document.getElementById('customer360Overlay');
    if (overlay) {
        overlay.remove();
    }
    
    customerDashboardVisible = false;
    currentCustomer360 = null;
    
    // Stop real-time tracking
    stopRealTimeCustomerTracking();
}

/**
 * Create new customer interaction
 */
async function createInteraction() {
    if (!currentCustomer360 || !currentCustomer360.customer_id) {
        showError('Cannot log interaction for potential customer. Please create customer profile first.');
        return;
    }
    
    const interactionType = prompt('Interaction type (call, email, meeting, etc.):');
    const notes = prompt('Interaction notes:');
    
    if (!interactionType) return;
    
    try {
        showLoading('Logging interaction...');
        
        const response = await fetch(`${API_BASE_URL}/customer/customers/${currentCustomer360.customer_id}/interactions`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                interaction_type: interactionType,
                interaction_date: new Date().toISOString(),
                notes: notes || '',
                channel: 'map_interface'
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Reload customer 360 view
        await loadCustomer360View(currentCustomer360.customer_id);
        
        hideLoading();
        showSuccess('Interaction logged successfully!');
        
    } catch (error) {
        console.error('Error creating interaction:', error);
        hideLoading();
        showError('Failed to log interaction. Please try again.');
    }
}

/**
 * Update lead status
 */
async function updateLeadStatus() {
    if (!currentCustomer360) return;
    
    const newStatus = prompt('New lead status (prospect, qualified, opportunity, customer, closed):');
    if (!newStatus) return;
    
    try {
        showLoading('Updating lead status...');
        
        if (currentCustomer360.customer_id) {
            const response = await fetch(`${API_BASE_URL}/customer/customers/${currentCustomer360.customer_id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    lead_status: newStatus
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Reload customer 360 view
            await loadCustomer360View(currentCustomer360.customer_id);
        } else {
            // Update local potential customer data
            currentCustomer360.customer.lead_status = newStatus;
            displayCustomer360Overlay(currentCustomer360);
        }
        
        hideLoading();
        showSuccess('Lead status updated successfully!');
        
    } catch (error) {
        console.error('Error updating lead status:', error);
        hideLoading();
        showError('Failed to update lead status. Please try again.');
    }
}

/**
 * Focus on business on map
 */
function focusOnBusiness(businessId) {
    const business = currentBusinesses.find(b => b.id === businessId);
    if (business && business.latitude && business.longitude) {
        map.setCenter({ lat: parseFloat(business.latitude), lng: parseFloat(business.longitude) });
        map.setZoom(16);
        
        // Find and animate the marker
        const marker = markers.find(m => m.getTitle().includes(business.name));
        if (marker) {
            marker.setAnimation(google.maps.Animation.BOUNCE);
            setTimeout(() => marker.setAnimation(null), 2000);
        }
        
        showSuccess(`Focused on ${business.name}`);
    }
}

/**
 * Start real-time customer behavior tracking
 */
function startRealTimeCustomerTracking(customerId) {
    // Simulate real-time updates (in a real implementation, this would use WebSockets or Server-Sent Events)
    const trackingInterval = setInterval(() => {
        if (!customerDashboardVisible) {
            clearInterval(trackingInterval);
            return;
        }
        
        // Simulate random customer activities
        if (Math.random() < 0.1) { // 10% chance of activity
            const activities = [
                'Viewed website',
                'Opened email',
                'Downloaded brochure',
                'Visited location',
                'Called business',
                'Left review'
            ];
            
            const activity = activities[Math.floor(Math.random() * activities.length)];
            addRealTimeNotification(activity, customerId);
        }
    }, 5000); // Check every 5 seconds
}

/**
 * Stop real-time customer tracking
 */
function stopRealTimeCustomerTracking() {
    // Clear any tracking intervals (handled in startRealTimeCustomerTracking)
}

/**
 * Add real-time notification
 */
function addRealTimeNotification(activity, customerId) {
    const notification = {
        id: Date.now(),
        activity: activity,
        timestamp: new Date(),
        customerId: customerId
    };
    
    realTimeNotifications.unshift(notification);
    
    // Update activity feed
    updateRealTimeActivityFeed();
    
    // Show notification popup
    showCustomerNotification(notification);
}

/**
 * Update real-time activity feed
 */
function updateRealTimeActivityFeed() {
    const activityFeed = document.getElementById('realTimeActivity');
    if (!activityFeed) return;
    
    if (realTimeNotifications.length === 0) {
        activityFeed.innerHTML = '<p class="no-activity">No recent activity</p>';
        return;
    }
    
    activityFeed.innerHTML = realTimeNotifications.slice(0, 5).map(notification => `
        <div class="activity-item">
            <div class="activity-text">${notification.activity}</div>
            <div class="activity-time">${notification.timestamp.toLocaleTimeString()}</div>
        </div>
    `).join('');
}

/**
 * Show customer notification popup
 */
function showCustomerNotification(notification) {
    const notificationsContainer = document.getElementById('customer360Notifications');
    if (!notificationsContainer) return;
    
    const notificationElement = document.createElement('div');
    notificationElement.className = 'customer-notification';
    notificationElement.innerHTML = `
        <div class="notification-content">
            <strong>Customer Activity:</strong> ${notification.activity}
            <div class="notification-time">${notification.timestamp.toLocaleTimeString()}</div>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    notificationsContainer.appendChild(notificationElement);
    
    // Auto-remove after 10 seconds
    setTimeout(() => {
        if (notificationElement.parentElement) {
            notificationElement.remove();
        }
    }, 10000);
}

/**
 * View all interactions
 */
function viewAllInteractions() {
    if (!currentCustomer360 || !currentCustomer360.interactions) return;
    
    const interactions = currentCustomer360.interactions;
    const interactionsHTML = interactions.map(interaction => `
        <div class="interaction-detail">
            <h4>${interaction.interaction_type}</h4>
            <p><strong>Date:</strong> ${new Date(interaction.interaction_date).toLocaleString()}</p>
            <p><strong>Channel:</strong> ${interaction.channel || 'Unknown'}</p>
            <p><strong>Notes:</strong> ${interaction.notes || 'No notes'}</p>
        </div>
    `).join('');
    
    const popup = document.createElement('div');
    popup.className = 'interactions-popup';
    popup.innerHTML = `
        <div class="popup-content">
            <h3>All Customer Interactions</h3>
            <div class="interactions-container">
                ${interactionsHTML || '<p>No interactions found</p>'}
            </div>
            <button class="btn btn-primary" onclick="this.parentElement.parentElement.remove()">Close</button>
        </div>
    `;
    
    document.body.appendChild(popup);
}

/**
 * Show territory analysis dashboard
 */
async function showTerritoryAnalysis() {
    if (!searchCenter) {
        showError('Please perform a location search first to define a territory.');
        return;
    }
    
    try {
        showLoading('Analyzing territory performance...');
        
        const radius = parseFloat(document.getElementById('radiusSlider').value);
        const response = await fetch(`${API_BASE_URL}/customer/leads/territory-analysis?lat=${searchCenter.lat}&lon=${searchCenter.lng}&radius=${radius}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const territoryData = await response.json();
        displayTerritoryAnalysis(territoryData);
        
        hideLoading();
        
    } catch (error) {
        console.error('Error loading territory analysis:', error);
        hideLoading();
        showError('Failed to load territory analysis. Using local data.');
        
        // Fallback to local analysis
        displayLocalTerritoryAnalysis();
    }
}

/**
 * Display territory analysis dashboard
 */
function displayTerritoryAnalysis(territoryData) {
    const overlay = document.createElement('div');
    overlay.className = 'customer360-overlay';
    overlay.innerHTML = `
        <div class="customer360-content">
            <div class="customer360-header">
                <div class="customer-info">
                    <h2>Territory Analysis Dashboard</h2>
                    <p>Performance metrics for your sales territory</p>
                </div>
                <div class="customer360-actions">
                    <button class="btn btn-primary" onclick="exportTerritoryReport()">📊 Export Report</button>
                    <button class="btn btn-secondary" onclick="this.closest('.customer360-overlay').remove()">✕ Close</button>
                </div>
            </div>
            <div class="customer360-body">
                <div class="customer360-grid">
                    <div class="customer360-card">
                        <h3>🎯 Territory Overview</h3>
                        <div class="metrics-grid">
                            <div class="metric">
                                <div class="metric-value">${territoryData.customer_metrics?.total_customers || 0}</div>
                                <div class="metric-label">Total Customers</div>
                            </div>
                            <div class="metric">
                                <div class="metric-value">${territoryData.market_context?.total_businesses || 0}</div>
                                <div class="metric-label">Total Businesses</div>
                            </div>
                            <div class="metric">
                                <div class="metric-value">${territoryData.customer_metrics?.customer_density_per_km2 || 0}</div>
                                <div class="metric-label">Customer Density</div>
                            </div>
                            <div class="metric">
                                <div class="metric-value">${territoryData.market_context?.market_penetration_rate || 0}%</div>
                                <div class="metric-label">Market Penetration</div>
                            </div>
                        </div>
                    </div>
                    <div class="customer360-card">
                        <h3>📈 Lead Performance</h3>
                        <div class="metrics-grid">
                            <div class="metric">
                                <div class="metric-value">${territoryData.customer_metrics?.high_value_leads || 0}</div>
                                <div class="metric-label">High Value Leads</div>
                            </div>
                            <div class="metric">
                                <div class="metric-value">${territoryData.customer_metrics?.average_lead_score || 0}</div>
                                <div class="metric-label">Avg Lead Score</div>
                            </div>
                            <div class="metric">
                                <div class="metric-value">${territoryData.activity_metrics?.total_interactions || 0}</div>
                                <div class="metric-label">Total Interactions</div>
                            </div>
                            <div class="metric">
                                <div class="metric-value">${territoryData.activity_metrics?.interaction_rate || 0}</div>
                                <div class="metric-label">Interaction Rate</div>
                            </div>
                        </div>
                    </div>
                    <div class="customer360-card">
                        <h3>🏢 Industry Distribution</h3>
                        <div class="industry-chart">
                            ${createIndustryChart(territoryData.customer_metrics?.industry_distribution || {})}
                        </div>
                    </div>
                    <div class="customer360-card">
                        <h3>💡 Recommendations</h3>
                        <div class="recommendations-list">
                            ${(territoryData.recommendations || []).map(rec => `<div class="recommendation-item">• ${rec}</div>`).join('')}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(overlay);
}

/**
 * Display local territory analysis (fallback)
 */
function displayLocalTerritoryAnalysis() {
    const totalBusinesses = currentBusinesses.length;
    const qualifiedLeads = currentBusinesses.filter(b => (calculateLeadScore(b) >= 50)).length;
    const avgScore = totalBusinesses > 0 ? Math.round(currentBusinesses.reduce((sum, b) => sum + calculateLeadScore(b), 0) / totalBusinesses) : 0;
    
    const localData = {
        customer_metrics: {
            total_customers: qualifiedLeads,
            customer_density_per_km2: Math.round(qualifiedLeads / (Math.PI * Math.pow(parseFloat(document.getElementById('radiusSlider').value), 2))),
            high_value_leads: currentBusinesses.filter(b => calculateLeadScore(b) >= 70).length,
            average_lead_score: avgScore,
            industry_distribution: getIndustryDistribution()
        },
        market_context: {
            total_businesses: totalBusinesses,
            market_penetration_rate: Math.round((qualifiedLeads / totalBusinesses) * 100)
        },
        activity_metrics: {
            total_interactions: 0,
            interaction_rate: 0
        },
        recommendations: [
            'Focus on high-scoring leads for better conversion',
            'Increase territory coverage in underserved areas',
            'Develop industry-specific sales strategies'
        ]
    };
    
    displayTerritoryAnalysis(localData);
}

/**
 * Get industry distribution from current businesses
 */
function getIndustryDistribution() {
    const distribution = {};
    currentBusinesses.forEach(business => {
        const industry = business.category || 'Unknown';
        distribution[industry] = (distribution[industry] || 0) + 1;
    });
    return distribution;
}

/**
 * Create industry chart HTML
 */
function createIndustryChart(industryData) {
    const total = Object.values(industryData).reduce((sum, count) => sum + count, 0);
    if (total === 0) return '<p class="no-data">No industry data available</p>';
    
    return Object.entries(industryData)
        .sort(([,a], [,b]) => b - a)
        .slice(0, 5)
        .map(([industry, count]) => {
            const percentage = Math.round((count / total) * 100);
            return `
                <div class="industry-item">
                    <div class="industry-name">${industry}</div>
                    <div class="industry-bar">
                        <div class="industry-fill" style="width: ${percentage}%; background: #2a5298;"></div>
                    </div>
                    <div class="industry-percentage">${percentage}%</div>
                </div>
            `;
        }).join('');
}

/**
 * Show sales performance dashboard
 */
function showSalesPerformance() {
    updateSalesMetrics();
    showSuccess('Sales performance metrics updated in sidebar');
}

/**
 * Update sales metrics in sidebar
 */
function updateSalesMetrics() {
    if (currentBusinesses.length === 0) return;
    
    const totalBusinesses = currentBusinesses.length;
    const qualifiedLeads = currentBusinesses.filter(b => calculateLeadScore(b) >= 50).length;
    const conversionRate = Math.round((qualifiedLeads / totalBusinesses) * 100);
    const avgLeadScore = Math.round(currentBusinesses.reduce((sum, b) => sum + calculateLeadScore(b), 0) / totalBusinesses);
    
    document.getElementById('conversionRate').textContent = conversionRate + '%';
    document.getElementById('avgLeadScore').textContent = avgLeadScore;
}

/**
 * Export territory report
 */
async function exportTerritoryReport() {
    try {
        showLoading('Generating territory report...');
        
        // Create a comprehensive report
        const report = {
            territory_summary: {
                center: searchCenter,
                radius: parseFloat(document.getElementById('radiusSlider').value),
                total_businesses: currentBusinesses.length,
                qualified_leads: currentBusinesses.filter(b => calculateLeadScore(b) >= 50).length,
                export_date: new Date().toISOString()
            },
            business_details: currentBusinesses.map(business => ({
                id: business.id,
                name: business.name,
                category: business.category,
                address: business.raw_address,
                phone: business.phone_number,
                email: business.email,
                website: business.website,
                lead_score: calculateLeadScore(business),
                coordinates: {
                    lat: business.latitude,
                    lng: business.longitude
                }
            }))
        };
        
        // Download as JSON
        const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `territory_report_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
        
        hideLoading();
        showSuccess('Territory report exported successfully!');
        
    } catch (error) {
        console.error('Error exporting territory report:', error);
        hideLoading();
        showError('Failed to export territory report.');
    }
}

/**
 * Initialize customer 360 functionality
 */
function initializeCustomer360() {
    // Update sales metrics when businesses change
    const originalUpdateStatistics = window.updateStatistics;
    window.updateStatistics = function() {
        originalUpdateStatistics();
        updateSalesMetrics();
    };
    
    console.log('Customer 360 functionality initialized');
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(initializeCustomer360, 100);
});