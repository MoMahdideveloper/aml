/**
 * Analysis Dashboard JavaScript
 * Handles project analysis UI interactions and API calls
 */

const AnalysisDashboard = {
    
    currentAnalysisId: null,
    progressInterval: null,
    
    /**
     * Initialize the dashboard
     */
    init() {
        console.log('Initializing Analysis Dashboard');
        this.bindEvents();
        this.loadDashboardData();
    },

    /**
     * Bind event listeners
     */
    bindEvents() {
        // Analysis type change handler
        document.getElementById('analysisType').addEventListener('change', this.handleAnalysisTypeChange);
        
        // Start analysis form submission
        document.getElementById('startAnalysisSubmit').addEventListener('click', this.handleStartAnalysis.bind(this));
        
        // Refresh reports button (if exists)
        const refreshBtn = document.getElementById('refreshReports');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', this.loadReports.bind(this));
        }
    },

    /**
     * Handle analysis type dropdown change
     */
    handleAnalysisTypeChange() {
        const analysisType = document.getElementById('analysisType').value;
        const targetAreasGroup = document.getElementById('targetAreasGroup');
        
        if (analysisType === 'targeted') {
            targetAreasGroup.style.display = 'block';
        } else {
            targetAreasGroup.style.display = 'none';
        }
    },

    /**
     * Load dashboard summary data
     */
    async loadDashboardData() {
        try {
            // Load recent reports to calculate summary stats
            const reports = await this.apiCall('/api/analysis/reports?limit=10');
            this.updateDashboardCards(reports);
            
            // Load reports table
            this.loadReports();
            
            // Load top suggestions
            this.loadTopSuggestions();
            
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            this.showError('Failed to load dashboard data');
        }
    },

    /**
     * Update dashboard summary cards
     */
    updateDashboardCards(reportsData) {
        const reports = reportsData.reports || [];
        
        // Calculate overall score (average of completed reports)
        const completedReports = reports.filter(r => r.status === 'completed');
        const averageScore = completedReports.length > 0 
            ? completedReports.reduce((sum, r) => sum + r.total_score, 0) / completedReports.length 
            : 0;
        
        document.getElementById('overallScore').textContent = averageScore > 0 ? averageScore.toFixed(1) : '--';
        document.getElementById('totalReports').textContent = reports.length;
        
        // Count active suggestions (would need separate API call in real implementation)
        const totalSuggestions = reports.reduce((sum, r) => sum + (r.suggestion_count || 0), 0);
        document.getElementById('activeSuggestions').textContent = totalSuggestions;
        
        // Critical issues (mock calculation)
        document.getElementById('criticalIssues').textContent = Math.floor(totalSuggestions * 0.2);
    },

    /**
     * Load and display reports table
     */
    async loadReports() {
        try {
            const reportsData = await this.apiCall('/api/analysis/reports');
            const reports = reportsData.reports || [];
            
            const tbody = document.getElementById('reportsTableBody');
            tbody.innerHTML = '';
            
            reports.forEach(report => {
                const row = this.createReportTableRow(report);
                tbody.appendChild(row);
            });
            
        } catch (error) {
            console.error('Failed to load reports:', error);
            this.showError('Failed to load analysis reports');
        }
    },

    /**
     * Create a table row for a report
     */
    createReportTableRow(report) {
        const row = document.createElement('tr');
        
        // Status badge
        const statusBadge = this.createStatusBadge(report.status);
        
        // Score badge
        const scoreBadge = report.total_score 
            ? `<span class="badge bg-${this.getScoreColor(report.total_score)}">${report.total_score.toFixed(1)}</span>`
            : '<span class="badge bg-secondary">--</span>';
        
        row.innerHTML = `
            <td>${this.escapeHtml(report.project_name)}</td>
            <td>${new Date(report.analysis_date).toLocaleDateString()}</td>
            <td>${statusBadge}</td>
            <td>${scoreBadge}</td>
            <td>
                <span class="badge bg-primary">${report.suggestion_count || 0}</span>
            </td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="AnalysisDashboard.viewReport(${report.id})">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-outline-success" onclick="AnalysisDashboard.exportReport(${report.id})">
                        <i class="fas fa-download"></i>
                    </button>
                </div>
            </td>
        `;
        
        return row;
    },

    /**
     * Create status badge HTML
     */
    createStatusBadge(status) {
        const statusColors = {
            'completed': 'success',
            'in_progress': 'warning',
            'failed': 'danger'
        };
        
        const color = statusColors[status] || 'secondary';
        const text = status.replace('_', ' ').toUpperCase();
        
        return `<span class="badge bg-${color}">${text}</span>`;
    },

    /**
     * Get color class for score badge
     */
    getScoreColor(score) {
        if (score >= 80) return 'success';
        if (score >= 60) return 'warning';
        return 'danger';
    },

    /**
     * Load and display top suggestions
     */
    async loadTopSuggestions() {
        try {
            const suggestionsData = await this.apiCall('/api/analysis/suggestions?sort_by=priority_score&sort_order=desc');
            const suggestions = suggestionsData.suggestions || [];
            
            const container = document.getElementById('suggestionsList');
            container.innerHTML = '';
            
            if (suggestions.length === 0) {
                container.innerHTML = '<p class="text-muted">No suggestions available. Run an analysis to generate suggestions.</p>';
                return;
            }
            
            // Show top 5 suggestions
            suggestions.slice(0, 5).forEach(suggestion => {
                const card = this.createSuggestionCard(suggestion);
                container.appendChild(card);
            });
            
        } catch (error) {
            console.error('Failed to load suggestions:', error);
            document.getElementById('suggestionsList').innerHTML = 
                '<p class="text-danger">Failed to load suggestions</p>';
        }
    },

    /**
     * Create suggestion card element
     */
    createSuggestionCard(suggestion) {
        const card = document.createElement('div');
        card.className = 'card mb-3';
        
        const priorityColor = this.getScoreColor(suggestion.priority_score);
        const categoryBadge = `<span class="badge bg-secondary">${suggestion.category.replace('_', ' ').toUpperCase()}</span>`;
        
        card.innerHTML = `
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="card-title mb-0">${this.escapeHtml(suggestion.title)}</h6>
                    <span class="badge bg-${priorityColor}">${suggestion.priority_score.toFixed(1)}</span>
                </div>
                <div class="mb-2">
                    ${categoryBadge}
                    ${suggestion.tags ? suggestion.tags.map(tag => `<span class="badge bg-light text-dark">${tag}</span>`).join(' ') : ''}
                </div>
                <p class="card-text small text-muted">${this.truncateText(suggestion.description, 150)}</p>
                <div class="d-flex justify-content-between align-items-center">
                    <small class="text-muted">
                        ${suggestion.estimated_hours ? `${suggestion.estimated_hours}h effort` : 'TBD effort'}
                    </small>
                    <button class="btn btn-sm btn-outline-primary" onclick="AnalysisDashboard.viewSuggestion(${suggestion.id})">
                        Details
                    </button>
                </div>
            </div>
        `;
        
        return card;
    },

    /**
     * Handle start analysis form submission
     */
    async handleStartAnalysis() {
        try {
            const projectName = document.getElementById('projectName').value.trim();
            const analysisType = document.getElementById('analysisType').value;
            
            if (!projectName) {
                this.showError('Project name is required');
                return;
            }
            
            const payload = {
                project_name: projectName,
                analysis_type: analysisType
            };
            
            // Add target areas for targeted analysis
            if (analysisType === 'targeted') {
                const targetAreas = [];
                document.querySelectorAll('#targetAreasGroup input[type="checkbox"]:checked').forEach(checkbox => {
                    targetAreas.push(checkbox.value);
                });
                
                if (targetAreas.length === 0) {
                    this.showError('Please select at least one target area for targeted analysis');
                    return;
                }
                
                payload.target_areas = targetAreas;
            }
            
            // Close analysis modal and show progress modal
            const analysisModal = bootstrap.Modal.getInstance(document.getElementById('analysisModal'));
            analysisModal.hide();
            
            // Start analysis
            const response = await this.apiCall('/api/analysis/trigger', 'POST', payload);
            
            if (response.analysis_id) {
                this.currentAnalysisId = response.analysis_id;
                this.showProgressModal(response.estimated_duration);
                this.startProgressTracking();
            }
            
        } catch (error) {
            console.error('Failed to start analysis:', error);
            this.showError('Failed to start analysis: ' + error.message);
        }
    },

    /**
     * Show progress modal and start tracking
     */
    showProgressModal(estimatedDuration) {
        const progressModal = new bootstrap.Modal(document.getElementById('progressModal'));
        progressModal.show();
        
        document.getElementById('estimatedTime').textContent = `Estimated time: ${estimatedDuration} seconds`;
        document.getElementById('progressText').textContent = 'Analysis in progress...';
        document.getElementById('progressBar').style.width = '10%';
    },

    /**
     * Start progress tracking interval
     */
    startProgressTracking() {
        let progress = 10;
        
        this.progressInterval = setInterval(async () => {
            try {
                const status = await this.apiCall(`/api/analysis/reports/${this.currentAnalysisId}/status`);
                
                if (status.status === 'completed') {
                    this.handleAnalysisComplete();
                } else if (status.status === 'failed') {
                    this.handleAnalysisFailed();
                } else {
                    // Update progress
                    progress = Math.min(progress + 10, 90);
                    document.getElementById('progressBar').style.width = progress + '%';
                    document.getElementById('progressText').textContent = status.current_task || 'Analysis in progress...';
                }
                
            } catch (error) {
                console.error('Failed to check analysis status:', error);
            }
        }, 2000);
    },

    /**
     * Handle analysis completion
     */
    handleAnalysisComplete() {
        clearInterval(this.progressInterval);
        
        document.getElementById('progressBar').style.width = '100%';
        document.getElementById('progressText').textContent = 'Analysis completed successfully!';
        
        // Close progress modal after a short delay
        setTimeout(() => {
            const progressModal = bootstrap.Modal.getInstance(document.getElementById('progressModal'));
            progressModal.hide();
            
            // Refresh dashboard data
            this.loadDashboardData();
            this.showSuccess('Analysis completed successfully!');
        }, 1500);
    },

    /**
     * Handle analysis failure
     */
    handleAnalysisFailed() {
        clearInterval(this.progressInterval);
        
        const progressModal = bootstrap.Modal.getInstance(document.getElementById('progressModal'));
        progressModal.hide();
        
        this.showError('Analysis failed. Please try again.');
    },

    /**
     * View detailed report
     */
    async viewReport(reportId) {
        try {
            const report = await this.apiCall(`/api/analysis/reports/${reportId}`);
            this.showReportModal(report);
        } catch (error) {
            console.error('Failed to load report:', error);
            this.showError('Failed to load report details');
        }
    },

    /**
     * Export report
     */
    async exportReport(reportId, format = 'pdf') {
        try {
            const url = `/api/analysis/export/${reportId}?format=${format}&include_suggestions=true`;
            
            // Create a temporary link to download the file
            const link = document.createElement('a');
            link.href = url;
            link.download = `analysis_report_${reportId}.${format}`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            this.showSuccess('Report export started');
        } catch (error) {
            console.error('Failed to export report:', error);
            this.showError('Failed to export report');
        }
    },

    /**
     * View suggestion details
     */
    async viewSuggestion(suggestionId) {
        try {
            // For now, find the suggestion in the current suggestions list
            const allSuggestions = await this.apiCall('/api/analysis/suggestions');
            const suggestion = allSuggestions.suggestions.find(s => s.id === suggestionId);
            
            if (suggestion) {
                this.showSuggestionModal(suggestion);
            } else {
                this.showError('Suggestion not found');
            }
        } catch (error) {
            console.error('Failed to load suggestion:', error);
            this.showError('Failed to load suggestion details');
        }
    },

    /**
     * Make API call
     */
    async apiCall(url, method = 'GET', data = null) {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
            throw new Error(errorData.error || `HTTP ${response.status}`);
        }
        
        return await response.json();
    },

    /**
     * Show success message
     */
    showSuccess(message) {
        this.showAlert(message, 'success');
    },

    /**
     * Show error message
     */
    showError(message) {
        this.showAlert(message, 'danger');
    },

    /**
     * Show alert message
     */
    showAlert(message, type) {
        // Remove existing alerts
        document.querySelectorAll('.analysis-alert').forEach(alert => alert.remove());
        
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show analysis-alert`;
        alertDiv.style.position = 'fixed';
        alertDiv.style.top = '20px';
        alertDiv.style.right = '20px';
        alertDiv.style.zIndex = '9999';
        alertDiv.style.minWidth = '300px';
        
        alertDiv.innerHTML = `
            ${this.escapeHtml(message)}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    },

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Truncate text to specified length
     */
    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    },

    /**
     * Show report details in modal
     */
    showReportModal(report) {
        const modalContent = `
            <div class="modal fade" id="reportModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Analysis Report - ${this.escapeHtml(report.project_name)}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="row mb-3">
                                <div class="col-md-4">
                                    <strong>Overall Score:</strong><br>
                                    <span class="badge bg-${this.getScoreColor(report.total_score)} fs-6">${report.total_score || '--'}</span>
                                </div>
                                <div class="col-md-4">
                                    <strong>Analysis Date:</strong><br>
                                    ${new Date(report.analysis_date).toLocaleString()}
                                </div>
                                <div class="col-md-4">
                                    <strong>Codebase Size:</strong><br>
                                    ${report.codebase_size || 0} lines
                                </div>
                            </div>
                            <div class="mb-3">
                                <h6>Suggestions (${report.suggestions ? report.suggestions.length : 0})</h6>
                                <div class="suggestions-list">
                                    ${report.suggestions ? report.suggestions.map(suggestion => `
                                        <div class="card mb-2">
                                            <div class="card-body p-3">
                                                <div class="d-flex justify-content-between">
                                                    <h6 class="mb-1">${this.escapeHtml(suggestion.title)}</h6>
                                                    <span class="badge bg-${this.getScoreColor(suggestion.priority_score)}">${suggestion.priority_score}</span>
                                                </div>
                                                <p class="mb-1 text-muted small">${this.escapeHtml(suggestion.description)}</p>
                                                <span class="badge bg-secondary">${suggestion.category.replace('_', ' ').toUpperCase()}</span>
                                            </div>
                                        </div>
                                    `).join('') : '<p class="text-muted">No suggestions available</p>'}
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-success" onclick="AnalysisDashboard.exportReport(${report.id})">
                                <i class="fas fa-download"></i> Export Report
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal and add new one
        const existingModal = document.getElementById('reportModal');
        if (existingModal) {
            existingModal.remove();
        }

        document.body.insertAdjacentHTML('beforeend', modalContent);
        const modal = new bootstrap.Modal(document.getElementById('reportModal'));
        modal.show();
    },

    /**
     * Show suggestion details in modal
     */
    showSuggestionModal(suggestion) {
        const modalContent = `
            <div class="modal fade" id="suggestionModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Suggestion Details</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <h6>${this.escapeHtml(suggestion.title)}</h6>
                                <span class="badge bg-${this.getScoreColor(suggestion.priority_score)}">Priority: ${suggestion.priority_score}</span>
                                <span class="badge bg-secondary ms-2">${suggestion.category.replace('_', ' ').toUpperCase()}</span>
                            </div>
                            <div class="mb-3">
                                <strong>Description:</strong>
                                <p>${this.escapeHtml(suggestion.description)}</p>
                            </div>
                            <div class="row">
                                <div class="col-6">
                                    <strong>Business Impact:</strong> ${suggestion.business_impact}/5<br>
                                    <strong>Technical Impact:</strong> ${suggestion.technical_impact}/5
                                </div>
                                <div class="col-6">
                                    <strong>Risk Level:</strong> ${suggestion.risk_level}/5<br>
                                    <strong>Estimated Hours:</strong> ${suggestion.estimated_hours || 'TBD'}
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button type="button" class="btn btn-primary" onclick="AnalysisDashboard.markSuggestionCompleted(${suggestion.id})">
                                Mark as Completed
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Remove existing modal and add new one
        const existingModal = document.getElementById('suggestionModal');
        if (existingModal) {
            existingModal.remove();
        }

        document.body.insertAdjacentHTML('beforeend', modalContent);
        const modal = new bootstrap.Modal(document.getElementById('suggestionModal'));
        modal.show();
    },

    /**
     * Mark suggestion as completed
     */
    async markSuggestionCompleted(suggestionId) {
        try {
            await this.apiCall(`/api/analysis/suggestions/${suggestionId}`, 'PUT', { status: 'completed' });
            this.showSuccess('Suggestion marked as completed');
            
            // Close modal and refresh data
            const modal = bootstrap.Modal.getInstance(document.getElementById('suggestionModal'));
            modal.hide();
            this.loadDashboardData();
        } catch (error) {
            console.error('Failed to update suggestion:', error);
            this.showError('Failed to update suggestion');
        }
    }
};

// Export for global use
window.AnalysisDashboard = AnalysisDashboard;