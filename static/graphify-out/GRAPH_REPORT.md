# Graph Report - static  (2026-06-27)

## Corpus Check
- 13 files · ~19,131 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 247 nodes · 409 edges · 13 communities (4 shown, 9 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.8)
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
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]

## God Nodes (most connected - your core abstractions)
1. `CRUDUtils` - 43 edges
2. `AccessibilityEnhancements` - 24 edges
3. `PropertyEditModal` - 23 edges
4. `DualViewHandler` - 22 edges
5. `RecommendationsManager` - 21 edges
6. `PreferenceStorage` - 14 edges
7. `ButtonFixes` - 13 edges
8. `populatePropertyViewModal()` - 13 edges
9. `ButtonDiagnostics` - 11 edges
10. `viewPropertyModal()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `retryLoadProperty()` --calls--> `viewPropertyModal()`  [INFERRED]
  js/property-view-modal.js → js/property-modal-system.js

## Import Cycles
- None detected.

## Communities (13 total, 9 thin omitted)

### Community 1 - "Community 1"
Cohesion: 0.10
Nodes (16): Animate, API, convertToCSV(), currentDate, debounce(), exportToCSV(), initializeAIAutofill(), initializeApp() (+8 more)

### Community 5 - "Community 5"
Cohesion: 0.18
Nodes (20): announceToScreenReader(), escapeHtml(), formatCurrency(), formatListingType(), formatPropertyCategory(), formatPropertyCondition(), formatPropertyType(), formatTomanCurrency() (+12 more)

### Community 9 - "Community 9"
Cohesion: 0.31
Nodes (7): getManager(), isDomAvailable(), notify(), populatePropertyViewModalFallback(), PropertyModalManager, setText(), viewPropertyModal()

## Knowledge Gaps
- **5 isolated node(s):** `AnalysisDashboard`, `currentDate`, `Storage`, `API`, `Animate`
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `sharePropertyFromModal()` connect `Community 6` to `Community 5`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **What connects `AnalysisDashboard`, `currentDate`, `Storage` to the rest of the system?**
  _5 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.09513742071881606 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.09971509971509972 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.12666666666666668 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.12318840579710146 - nodes in this community are weakly interconnected._
- **Should `Community 6` be split into smaller, more focused modules?**
  _Cohesion score 0.14624505928853754 - nodes in this community are weakly interconnected._