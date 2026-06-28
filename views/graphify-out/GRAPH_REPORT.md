# Graph Report - views  (2026-06-27)

## Corpus Check
- 21 files · ~13,036 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 210 nodes · 262 edges · 17 communities (15 shown, 2 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `84438eac`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]

## God Nodes (most connected - your core abstractions)
1. `_wants_json()` - 8 edges
2. `get_current_admin_user()` - 6 edges
3. `_serialize_property_for_json()` - 6 edges
4. `_serialize_property_for_json()` - 5 edges
5. `_serialize_property_for_json()` - 5 edges
6. `property_detail()` - 5 edges
7. `_safe_attr()` - 5 edges
8. `_utcnow_naive()` - 4 edges
9. `share_property()` - 4 edges
10. `update_property()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `view_property()` --calls--> `_serialize_property_for_json()`  [EXTRACTED]
  property_details.py → property_helpers.py
- `view_property()` --calls--> `_wants_json()`  [EXTRACTED]
  property_details.py → property_helpers.py
- `property_detail()` --calls--> `_format_datetime()`  [EXTRACTED]
  property_details.py → property_helpers.py
- `property_detail()` --calls--> `_safe_attr()`  [EXTRACTED]
  property_details.py → property_helpers.py
- `property_detail()` --calls--> `_wants_json()`  [EXTRACTED]
  property_details.py → property_helpers.py

## Import Cycles
- 1-file cycle: `auth.py -> auth.py`
- 1-file cycle: `notifications.py -> notifications.py`

## Communities (17 total, 2 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.09
Nodes (23): check_environment_health(), create_environment_variable(), delete_environment_variable(), environment(), environment_history(), get_current_admin_user(), get_environment_variable_details(), get_validation_summary() (+15 more)

### Community 1 - "Community 1"
Cohesion: 0.12
Nodes (21): _format_datetime(), _is_mock_value(), _normalize_numeric_input(), _parse_optional_toman(), rate_limit(), Share property endpoint, Redis-backed rate limiting decorator.     Args:         max_requests: Maximum nu, _safe_attr() (+13 more)

### Community 2 - "Community 2"
Cohesion: 0.10
Nodes (20): create_analysis_template(), export_analysis_report(), get_analysis_report(), get_analysis_report_status(), get_analysis_reports(), get_analysis_templates(), get_suggestions(), Get list of analysis templates (+12 more)

### Community 3 - "Community 3"
Cohesion: 0.11
Nodes (20): admin_notifications_dashboard(), broadcast_system_notification(), cleanup_agent_notifications(), create_system_notification(), dismiss_notification(), get_agent_notification_summary(), get_agent_notifications(), mark_all_notifications_read() (+12 more)

### Community 4 - "Community 4"
Cohesion: 0.12
Nodes (17): delete_property_ai_history(), _format_datetime(), get_property_ai_history(), _is_mock_value(), map_view(), _normalize_numeric_input(), _parse_optional_toman(), properties() (+9 more)

### Community 5 - "Community 5"
Cohesion: 0.25
Nodes (15): edit_property(), get_edit_modal_html(), property_detail(), Handle property edit form request (AJAX), Return HTML for property edit modal (AJAX endpoint), Get property details for viewing modal with enhanced error handling, Full property details page with enhanced features and robust error handling, view_property() (+7 more)

### Community 6 - "Community 6"
Cohesion: 0.13
Nodes (14): export_report(), generate_mock_report(), get_report(), list_reports(), list_suggestions(), Generate a mock analysis report, Start a new project analysis, List all analysis reports (+6 more)

### Community 7 - "Community 7"
Cohesion: 0.16
Nodes (11): inject_current_user(), _is_safe_next_url(), login(), datetime, Authentication Blueprint Handles user registration, login, logout and session m, Make current_user available in all templates, Update profile information, User registration page (+3 more)

### Community 8 - "Community 8"
Cohesion: 0.19
Nodes (13): add_property(), delete_property(), _format_datetime(), _is_mock_value(), _normalize_numeric_input(), _parse_optional_toman(), rate_limit(), Update property data with comprehensive validation and error handling (+5 more)

## Knowledge Gaps
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `update_property()` connect `Community 8` to `Community 1`?**
  _High betweenness centrality (0.005) - this node is a cross-community bridge._
- **What connects `Admin Environment Settings Blueprint Provides web interface for managing enviro`, `Decorator to require admin authentication for environment operations`, `Get current authenticated admin user` to the rest of the system?**
  _63 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.09230769230769231 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.12318840579710146 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.09523809523809523 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.11428571428571428 - nodes in this community are weakly interconnected._
- **Should `Community 4` be split into smaller, more focused modules?**
  _Cohesion score 0.11904761904761904 - nodes in this community are weakly interconnected._