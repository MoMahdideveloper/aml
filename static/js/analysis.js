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
            this._hideEl(document.getElementById('analysisModal'));

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
    _showEl(el) {
        if (!el) return;
        if (window.PHModal) window.PHModal.show(el);
        else {
            el.classList.remove('hidden');
            el.style.display = '';
            document.body.style.overflow = 'hidden';
        }
    },

    _hideEl(el) {
        if (!el) return;
        if (window.PHModal) window.PHModal.hide(el);
        else {
            el.classList.add('hidden');
            el.style.display = 'none';
            document.body.style.overflow = '';
        }
        if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
            try {
                const inst = bootstrap.Modal.getInstance(el);
                if (inst) inst.hide();
            } catch (_) { /* ignore */ }
        }
    },

    showProgressModal(estimatedDuration) {
        const progressModal = document.getElementById('progressModal');
        this._showEl(progressModal);

        const est = document.getElementById('estimatedTime');
        const text = document.getElementById('progressText');
        const bar = document.getElementById('progressBar');
        if (est) est.textContent = `Estimated time: ${estimatedDuration} seconds`;
        if (text) text.textContent = 'Analysis in progress...';
        if (bar) bar.style.width = '10%';
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
            this._hideEl(document.getElementById('progressModal'));

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

        this._hideEl(document.getElementById('progressModal'));

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
        const suggestionsHtml = report.suggestions && report.suggestions.length
            ? report.suggestions.map(suggestion => `
                <div class="rounded-lg border border-outline-variant p-3 mb-2 bg-background">
                    <div class="flex justify-between gap-2 mb-1">
                        <h3 class="text-sm font-semibold text-primary">${this.escapeHtml(suggestion.title)}</h3>
                        <span class="text-xs font-medium px-2 py-0.5 rounded-full bg-primary/10 text-primary">${suggestion.priority_score}</span>
                    </div>
                    <p class="text-xs text-on-surface-variant mb-2">${this.escapeHtml(suggestion.description || '')}</p>
                    <span class="text-[10px] uppercase tracking-wide text-on-surface-variant">${(suggestion.category || '').replace('_', ' ')}</span>
                </div>
            `).join('')
            : '<p class="text-sm text-on-surface-variant">No suggestions available</p>';

        const modalContent = `
            <div id="reportModal" class="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-on-surface/40 backdrop-blur-[2px]" data-modal role="dialog" aria-modal="true">
                <div class="bg-surface-container-lowest rounded-lg border border-outline-variant shadow-ph w-full max-w-3xl max-h-[90vh] flex flex-col" onclick="event.stopPropagation()">
                    <div class="flex items-center justify-between gap-3 px-5 py-4 border-b border-outline-variant">
                        <h2 class="text-lg font-semibold text-primary truncate">Analysis — ${this.escapeHtml(report.project_name || 'Report')}</h2>
                        <button type="button" class="p-2 rounded-lg text-on-surface-variant hover:bg-surface-container" data-analysis-close aria-label="Close">
                            <span class="material-symbols-outlined text-[20px]">close</span>
                        </button>
                    </div>
                    <div class="px-5 py-4 overflow-y-auto flex-1 space-y-4 text-sm">
                        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            <div class="rounded-lg border border-outline-variant p-3 bg-background">
                                <div class="text-xs text-on-surface-variant uppercase tracking-wide">Score</div>
                                <div class="text-xl font-semibold text-primary mt-1">${report.total_score ?? '—'}</div>
                            </div>
                            <div class="rounded-lg border border-outline-variant p-3 bg-background">
                                <div class="text-xs text-on-surface-variant uppercase tracking-wide">Date</div>
                                <div class="font-medium text-on-surface mt-1">${report.analysis_date ? new Date(report.analysis_date).toLocaleString() : '—'}</div>
                            </div>
                            <div class="rounded-lg border border-outline-variant p-3 bg-background">
                                <div class="text-xs text-on-surface-variant uppercase tracking-wide">Size</div>
                                <div class="font-medium text-on-surface mt-1">${report.codebase_size || 0} lines</div>
                            </div>
                        </div>
                        <div>
                            <h3 class="text-sm font-semibold text-primary mb-2">Suggestions (${report.suggestions ? report.suggestions.length : 0})</h3>
                            ${suggestionsHtml}
                        </div>
                    </div>
                    <div class="px-5 py-4 border-t border-outline-variant flex justify-end gap-2">
                        <button type="button" class="px-4 py-2 rounded-lg border border-outline-variant text-sm font-medium text-primary hover:bg-surface-container" data-analysis-close>Close</button>
                        <button type="button" class="px-4 py-2 rounded-lg bg-primary text-on-primary text-sm font-medium hover:opacity-90" onclick="AnalysisDashboard.exportReport(${report.id})">Export</button>
                    </div>
                </div>
            </div>
        `;

        const existingModal = document.getElementById('reportModal');
        if (existingModal) existingModal.remove();

        document.body.insertAdjacentHTML('beforeend', modalContent);
        const modal = document.getElementById('reportModal');
        if (window.PHModal) window.PHModal.show(modal);
        else document.body.style.overflow = 'hidden';
        modal.querySelectorAll('[data-analysis-close]').forEach(btn => {
            btn.addEventListener('click', () => {
                if (window.PHModal) window.PHModal.hide(modal);
                modal.remove();
                document.body.style.overflow = '';
            });
        });
    },

    /**
     * Show suggestion details in modal
     */
    showSuggestionModal(suggestion) {
        const modalContent = `
            <div id="suggestionModal" class="fixed inset-0 z-[70] flex items-center justify-center p-4 bg-on-surface/40 backdrop-blur-[2px]" data-modal role="dialog" aria-modal="true">
                <div class="bg-surface-container-lowest rounded-lg border border-outline-variant shadow-ph w-full max-w-lg max-h-[90vh] flex flex-col" onclick="event.stopPropagation()">
                    <div class="flex items-center justify-between gap-3 px-5 py-4 border-b border-outline-variant">
                        <h2 class="text-lg font-semibold text-primary">Suggestion</h2>
                        <button type="button" class="p-2 rounded-lg text-on-surface-variant hover:bg-surface-container" data-analysis-close aria-label="Close">
                            <span class="material-symbols-outlined text-[20px]">close</span>
                        </button>
                    </div>
                    <div class="px-5 py-4 overflow-y-auto space-y-3 text-sm">
                        <h3 class="font-semibold text-primary">${this.escapeHtml(suggestion.title || '')}</h3>
                        <div class="flex flex-wrap gap-2 text-xs">
                            <span class="px-2 py-0.5 rounded-full bg-primary/10 text-primary">Priority ${suggestion.priority_score ?? '—'}</span>
                            <span class="px-2 py-0.5 rounded-full border border-outline-variant text-on-surface-variant uppercase tracking-wide">${(suggestion.category || '').replace('_', ' ')}</span>
                        </div>
                        <p class="text-on-surface">${this.escapeHtml(suggestion.description || '')}</p>
                        <div class="grid grid-cols-2 gap-3 text-xs text-on-surface-variant">
                            <div>Business impact: <span class="text-on-surface font-medium">${suggestion.business_impact ?? '—'}/5</span></div>
                            <div>Technical impact: <span class="text-on-surface font-medium">${suggestion.technical_impact ?? '—'}/5</span></div>
                            <div>Risk: <span class="text-on-surface font-medium">${suggestion.risk_level ?? '—'}/5</span></div>
                            <div>Hours: <span class="text-on-surface font-medium">${suggestion.estimated_hours || 'TBD'}</span></div>
                        </div>
                    </div>
                    <div class="px-5 py-4 border-t border-outline-variant flex justify-end gap-2">
                        <button type="button" class="px-4 py-2 rounded-lg border border-outline-variant text-sm font-medium text-primary hover:bg-surface-container" data-analysis-close>Close</button>
                        <button type="button" class="px-4 py-2 rounded-lg bg-primary text-on-primary text-sm font-medium hover:opacity-90" onclick="AnalysisDashboard.markSuggestionCompleted(${suggestion.id})">Mark completed</button>
                    </div>
                </div>
            </div>
        `;

        const existingModal = document.getElementById('suggestionModal');
        if (existingModal) existingModal.remove();

        document.body.insertAdjacentHTML('beforeend', modalContent);
        const modal = document.getElementById('suggestionModal');
        if (window.PHModal) window.PHModal.show(modal);
        else document.body.style.overflow = 'hidden';
        modal.querySelectorAll('[data-analysis-close]').forEach(btn => {
            btn.addEventListener('click', () => {
                if (window.PHModal) window.PHModal.hide(modal);
                modal.remove();
                document.body.style.overflow = '';
            });
        });
    },

    /**
     * Mark suggestion as completed
     */
    async markSuggestionCompleted(suggestionId) {
        try {
            await this.apiCall(`/api/analysis/suggestions/${suggestionId}`, 'PUT', { status: 'completed' });
            this.showSuccess('Suggestion marked as completed');

            const modal = document.getElementById('suggestionModal');
            if (modal) {
                if (window.PHModal) window.PHModal.hide(modal);
                modal.remove();
                document.body.style.overflow = '';
            }
            this.loadDashboardData();
        } catch (error) {
            console.error('Failed to update suggestion:', error);
            this.showError('Failed to update suggestion');
        }
    }
};

// Export for global use
window.AnalysisDashboard = AnalysisDashboard;