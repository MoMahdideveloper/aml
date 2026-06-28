# Graph Report - C:\Users\LifeCycle\Desktop\gptvli\static\js  (2026-06-27)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 238 nodes · 399 edges · 13 communities (11 shown, 2 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `84438eac`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 11|Community 11]]

## God Nodes (most connected - your core abstractions)
1. `RecommendationsManager` - 21 edges
2. `populatePropertyViewModal()` - 13 edges
3. `viewPropertyModal()` - 10 edges
4. `initializeApp()` - 7 edges
5. `PropertyModalManager` - 7 edges
6. `updateSpecificationsTab()` - 6 edges
7. `isDomAvailable()` - 5 edges
8. `populatePropertyViewModalFallback()` - 4 edges
9. `updatePricingDisplay()` - 4 edges
10. `showModalError()` - 4 edges

## Surprising Connections (you probably didn't know these)
- `retryLoadProperty()` --calls--> `viewPropertyModal()`  [INFERRED]
  property-view-modal.js → property-modal-system.js

## Import Cycles
- None detected.

## Communities (13 total, 2 thin omitted)

### Community 1 - "Community 1"
Cohesion: 0.10
Nodes (16): Animate, API, convertToCSV(), currentDate, debounce(), exportToCSV(), initializeAIAutofill(), initializeApp() (+8 more)

### Community 4 - "Community 4"
Cohesion: 0.18
Nodes (20): announceToScreenReader(), escapeHtml(), formatCurrency(), formatListingType(), formatPropertyCategory(), formatPropertyCondition(), formatPropertyType(), formatTomanCurrency() (+12 more)

### Community 7 - "Community 7"
Cohesion: 0.31
Nodes (7): getManager(), isDomAvailable(), notify(), populatePropertyViewModalFallback(), PropertyModalManager, setText(), viewPropertyModal()

## Knowledge Gaps
- **5 isolated node(s):** `AnalysisDashboard`, `currentDate`, `Storage`, `API`, `Animate`
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `sharePropertyFromModal()` connect `Community 5` to `Community 4`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `retryLoadProperty()` connect `Community 4` to `Community 7`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **What connects `AnalysisDashboard`, `currentDate`, `Storage` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.09856035437430787 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.09971509971509972 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.13405797101449277 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.13043478260869565 - nodes in this community are weakly interconnected._