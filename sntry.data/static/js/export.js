/**
 * Jamaica Business Directory - Export Functionality
 * Handles data export in various formats (CSV, Excel, KML, GeoJSON)
 */

/**
 * Export visible businesses in specified format
 */
async function exportData(format) {
    try {
        showLoading(`Preparing ${format.toUpperCase()} export...`);
        
        // Get current filter parameters
        const filterSummary = getFilterSummary();
        
        // Build export parameters
        const params = new URLSearchParams({
            is_active: true
        });
        
        // Add search filters
        if (filterSummary.search_query) {
            params.append('query', filterSummary.search_query);
        }
        
        // Add category filters
        if (filterSummary.categories.length > 0) {
            params.append('category', filterSummary.categories.join(','));
        }
        
        // Add location filters if we have a search center
        if (searchCenter) {
            params.append('latitude', searchCenter.lat);
            params.append('longitude', searchCenter.lng);
            params.append('radius', filterSummary.radius_km);
        }
        
        // Determine export endpoint
        let endpoint;
        let filename;
        
        switch (format.toLowerCase()) {
            case 'csv':
                endpoint = `${API_BASE_URL}/export/businesses/csv`;
                filename = 'jamaica_businesses.csv';
                break;
            case 'xlsx':
            case 'excel':
                endpoint = `${API_BASE_URL}/export/businesses/xlsx`;
                filename = 'jamaica_businesses.xlsx';
                break;
            case 'kml':
                endpoint = `${API_BASE_URL}/map_data/kml`;
                filename = 'jamaica_businesses.kml';
                break;
            case 'geojson':
                endpoint = `${API_BASE_URL}/export/businesses/geojson`;
                filename = 'jamaica_businesses.geojson';
                break;
            default:
                throw new Error(`Unsupported export format: ${format}`);
        }
        
        // Make export request
        const response = await fetch(`${endpoint}?${params}`);
        
        if (!response.ok) {
            throw new Error(`Export failed: ${response.status} ${response.statusText}`);
        }
        
        // Handle different response types
        if (format.toLowerCase() === 'geojson') {
            // GeoJSON returns JSON data
            const data = await response.json();
            downloadJSON(data, filename);
        } else {
            // Other formats return file data
            const blob = await response.blob();
            downloadBlob(blob, filename);
        }
        
        hideLoading();
        showSuccess(`Successfully exported ${filterSummary.visible_businesses} businesses as ${format.toUpperCase()}`);
        
        // Track export analytics
        trackExportEvent(format, filterSummary.visible_businesses);
        
    } catch (error) {
        console.error(`Error exporting ${format}:`, error);
        showError(`Failed to export ${format.toUpperCase()}. Please try again.`);
        hideLoading();
    }
}

/**
 * Download blob as file
 */
function downloadBlob(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

/**
 * Download JSON data as file
 */
function downloadJSON(data, filename) {
    const jsonString = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    downloadBlob(blob, filename);
}

/**
 * Export qualified leads
 */
async function exportLeads(minScore = 50.0) {
    try {
        showLoading('Exporting qualified leads...');
        
        const params = new URLSearchParams({
            min_lead_score: minScore
        });
        
        // Add current filters if any
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
        
        const response = await fetch(`${API_BASE_URL}/export/leads/csv?${params}`);
        
        if (!response.ok) {
            throw new Error(`Lead export failed: ${response.status} ${response.statusText}`);
        }
        
        const blob = await response.blob();
        downloadBlob(blob, 'qualified_leads.csv');
        
        hideLoading();
        showSuccess(`Successfully exported qualified leads (min score: ${minScore})`);
        
    } catch (error) {
        console.error('Error exporting leads:', error);
        showError('Failed to export leads. Please try again.');
        hideLoading();
    }
}

/**
 * Export customer 360 data
 */
async function exportCustomer360() {
    try {
        showLoading('Exporting customer 360 data...');
        
        const response = await fetch(`${API_BASE_URL}/export/customer-360/xlsx`);
        
        if (!response.ok) {
            throw new Error(`Customer 360 export failed: ${response.status} ${response.statusText}`);
        }
        
        const blob = await response.blob();
        downloadBlob(blob, 'customer_360_export.xlsx');
        
        hideLoading();
        showSuccess('Successfully exported customer 360 data');
        
    } catch (error) {
        console.error('Error exporting customer 360 data:', error);
        showError('Failed to export customer 360 data. Please try again.');
        hideLoading();
    }
}

/**
 * Export dashboard analytics data
 */
async function exportDashboardData(format = 'json') {
    try {
        showLoading('Exporting dashboard analytics...');
        
        const params = new URLSearchParams({ format });
        const response = await fetch(`${API_BASE_URL}/export/analytics/dashboard-data?${params}`);
        
        if (!response.ok) {
            throw new Error(`Dashboard export failed: ${response.status} ${response.statusText}`);
        }
        
        if (format === 'json') {
            const data = await response.json();
            downloadJSON(data, 'dashboard_analytics.json');
        } else {
            const blob = await response.blob();
            downloadBlob(blob, 'dashboard_analytics.csv');
        }
        
        hideLoading();
        showSuccess(`Successfully exported dashboard data as ${format.toUpperCase()}`);
        
    } catch (error) {
        console.error('Error exporting dashboard data:', error);
        showError('Failed to export dashboard data. Please try again.');
        hideLoading();
    }
}

/**
 * Create and download Google MyMaps KML
 */
async function createMyMapsExport() {
    try {
        showLoading('Creating Google MyMaps export...');
        
        // Get current filter parameters
        const filterSummary = getFilterSummary();
        
        const params = new URLSearchParams({
            is_active: true
        });
        
        // Add current filters
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
        
        const response = await fetch(`${API_BASE_URL}/map_data/kml?${params}`);
        
        if (!response.ok) {
            throw new Error(`MyMaps export failed: ${response.status} ${response.statusText}`);
        }
        
        const blob = await response.blob();
        downloadBlob(blob, 'jamaica_businesses_mymaps.kml');
        
        hideLoading();
        
        // Show instructions for importing to MyMaps
        showMyMapsInstructions();
        
    } catch (error) {
        console.error('Error creating MyMaps export:', error);
        showError('Failed to create MyMaps export. Please try again.');
        hideLoading();
    }
}

/**
 * Show instructions for importing KML to Google MyMaps
 */
function showMyMapsInstructions() {
    const instructions = `
        <div style="background: #e8f4fd; border: 1px solid #bee5eb; border-radius: 6px; padding: 1rem; margin: 1rem 0;">
            <h4 style="margin: 0 0 0.5rem 0; color: #0c5460;">📍 Import to Google MyMaps</h4>
            <ol style="margin: 0; padding-left: 1.5rem; font-size: 0.9rem;">
                <li>Go to <a href="https://mymaps.google.com" target="_blank">mymaps.google.com</a></li>
                <li>Click "Create a New Map"</li>
                <li>Click "Import" in the left panel</li>
                <li>Upload the downloaded KML file</li>
                <li>Customize your map title and styling</li>
                <li>Share or embed your map as needed</li>
            </ol>
            <button onclick="this.parentElement.remove()" style="background: #007bff; color: white; border: none; padding: 0.3rem 0.8rem; border-radius: 4px; cursor: pointer; margin-top: 0.5rem; font-size: 0.8rem;">
                Got it!
            </button>
        </div>
    `;
    
    // Insert instructions after the first sidebar section
    const firstSection = document.querySelector('.sidebar-section');
    if (firstSection) {
        firstSection.insertAdjacentHTML('afterend', instructions);
    }
}

/**
 * Bulk export multiple formats
 */
async function bulkExport(formats = ['csv', 'xlsx', 'kml']) {
    try {
        showLoading('Preparing bulk export...');
        
        const results = [];
        
        for (const format of formats) {
            try {
                await exportData(format);
                results.push({ format, status: 'success' });
                
                // Small delay between exports
                await new Promise(resolve => setTimeout(resolve, 1000));
                
            } catch (error) {
                console.error(`Failed to export ${format}:`, error);
                results.push({ format, status: 'failed', error: error.message });
            }
        }
        
        hideLoading();
        
        // Show bulk export results
        const successful = results.filter(r => r.status === 'success').length;
        const failed = results.filter(r => r.status === 'failed').length;
        
        if (failed === 0) {
            showSuccess(`Successfully exported all ${successful} formats`);
        } else {
            showError(`Exported ${successful} formats successfully, ${failed} failed`);
        }
        
    } catch (error) {
        console.error('Error in bulk export:', error);
        showError('Bulk export failed. Please try again.');
        hideLoading();
    }
}

/**
 * Track export events for analytics
 */
function trackExportEvent(format, recordCount) {
    // This would integrate with analytics service
    console.log(`Export tracked: ${format}, ${recordCount} records`);
    
    // In a real implementation, this might send data to Google Analytics, etc.
    // gtag('event', 'export', {
    //     'event_category': 'data_export',
    //     'event_label': format,
    //     'value': recordCount
    // });
}

/**
 * Show export options modal/menu
 */
function showExportMenu() {
    const menu = document.createElement('div');
    menu.className = 'export-menu';
    menu.style.cssText = `
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        padding: 2rem;
        z-index: 10000;
        min-width: 300px;
    `;
    
    menu.innerHTML = `
        <h3 style="margin: 0 0 1rem 0;">Export Options</h3>
        <div style="display: grid; gap: 0.5rem;">
            <button onclick="exportData('csv')" class="btn btn-primary">📊 Export CSV</button>
            <button onclick="exportData('xlsx')" class="btn btn-primary">📈 Export Excel</button>
            <button onclick="exportData('kml')" class="btn btn-primary">🗺️ Export KML</button>
            <button onclick="exportData('geojson')" class="btn btn-primary">🌍 Export GeoJSON</button>
            <button onclick="exportLeads()" class="btn btn-secondary">🎯 Export Leads</button>
            <button onclick="createMyMapsExport()" class="btn btn-secondary">📍 MyMaps Export</button>
        </div>
        <button onclick="this.parentElement.remove()" style="position: absolute; top: 0.5rem; right: 0.5rem; background: none; border: none; font-size: 1.2rem; cursor: pointer;">×</button>
    `;
    
    document.body.appendChild(menu);
    
    // Close menu when clicking outside
    setTimeout(() => {
        document.addEventListener('click', function closeMenu(e) {
            if (!menu.contains(e.target)) {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            }
        });
    }, 100);
}

/**
 * Initialize export functionality
 */
function initializeExports() {
    // Add keyboard shortcuts for exports
    document.addEventListener('keydown', function(e) {
        if (e.ctrlKey || e.metaKey) {
            switch (e.key) {
                case 'e':
                    e.preventDefault();
                    showExportMenu();
                    break;
                case 's':
                    e.preventDefault();
                    exportData('csv');
                    break;
            }
        }
    });
    
    console.log('Export functionality initialized');
}

// Initialize exports when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    setTimeout(initializeExports, 100);
});