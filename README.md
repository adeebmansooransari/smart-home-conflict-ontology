# Smart Home Automation Rule Conflict & Safety Violation Ontology Evaluation

This repository provides the formal OWL 2 ontologies, SWRL reasoning rules, and automated evaluation pipeline supporting the manuscript submitted to the *International Journal of Human-Computer Interaction* (Taylor & Francis).

## 1. Repository Structure

```text
├── .github/
│   └── workflows/
│       └── evaluate.yml           # One-click GitHub Actions reproducibility workflow
├── ontologies/
│   ├── baseline_ontology.owl      # Space-agnostic baseline ontology (global rule evaluation)
│   └── proposed_ontology.owl      # Space-aware proposed ontology (SmartSpaces + Functional Semantics)
├── scripts/
│   └── evaluate_conflicts.py      # Automated Pellet/SWRL reasoner and SPARQL comparison runner
├── results/                       # Generated summary tables and detected rule pairs (.csv / .md)
└── requirements.txt               # Python runtime dependencies
