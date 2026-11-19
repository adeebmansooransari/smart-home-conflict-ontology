import re
import sys
import tempfile
import pathlib
import pandas as pd
from owlready2 import World, sync_reasoner_pellet

# Properties to evaluate across Baseline and Proposed ontologies
SYMMETRIC_METRICS = {
    "Direct / Cross-Execution Conflicts": ["CrossExecutionConflict", "conflicts"],
    "Environment Cross-Conflicts": ["EnvironmentCrossConflict", "Environment_Conflicts"],
    "Environment Redundancy Conflicts": ["EnvironmentRedundancyConflicts"],
    "Safety Policy Violations": ["SafetyPolicyViolated"],
    "Direct Loop Rules": ["LoopRules"],
    "Indirect Loop Rules": ["IndirectLoopRules"],
}

DIRECTIONAL_METRICS = {
    "Rule Redundancies": ["RuleRedundancy"],
    "Configuration Alerts (Room-Level)": ["ConfigAlert"],
}

def normalize_xsd_time_literals(owl_path: str) -> str:
    """Converts string-wrapped xsd:time("HH:MM:SS") literals to standard typed xsd:time."""
    raw = pathlib.Path(owl_path).read_text(encoding="utf-8")
    pattern = r'rdf:datatype="http://www\.w3\.org/2000/01/rdf-schema#Literal">xsd:time\("?([0-9:]+)"?\)'
    fixed = re.sub(
        pattern,
        r'rdf:datatype="http://www.w3.org/2001/XMLSchema#time">\1',
        raw
    )
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".owl", mode="w", encoding="utf-8")
    tmp.write(fixed)
    tmp.close()
    return tmp.name

def evaluate_ontology(owl_path: str, label: str):
    print(f"\n--- Evaluating {label} ({owl_path}) ---")
    clean_path = normalize_xsd_time_literals(owl_path)
    
    # Use an isolated World per ontology so inferences do not bleed across runs
    world = World()
    onto = world.get_ontology(f"file://{clean_path}").load()
    base_iri = onto.base_iri
    if not base_iri.endswith("#"):
        base_iri += "#"

    print("Running Pellet reasoner & SWRL rules...")
    with onto:
        sync_reasoner_pellet(world, infer_property_values=True, infer_data_property_values=True)

    counts = {}
    detailed_rows = []

    # 1. Query Symmetric Conflict Properties (counted once per unordered pair)
    for metric_name, prop_candidates in SYMMETRIC_METRICS.items():
        pair_set = set()
        for prop in prop_candidates:
            query = f"""
                PREFIX : <{base_iri}>
                SELECT DISTINCT ?x ?y
                WHERE {{
                    ?x :{prop} ?y .
                    FILTER(?x != ?y && STR(?x) < STR(?y))
                }}
            """
            try:
                for row in world.sparql(query):
                    x_name = row[0].name if hasattr(row[0], "name") else str(row[0]).split("#")[-1]
                    y_name = row[1].name if hasattr(row[1], "name") else str(row[1]).split("#")[-1]
                    pair_set.add((x_name, y_name))
                    detailed_rows.append({
                        "Ontology": label,
                        "Category": metric_name,
                        "Property": prop,
                        "Entity_1": x_name,
                        "Entity_2": y_name
                    })
            except Exception:
                pass
        counts[metric_name] = len(pair_set)

    # 2. Query Directional Properties
    for metric_name, prop_candidates in DIRECTIONAL_METRICS.items():
        pair_set = set()
        for prop in prop_candidates:
            query = f"""
                PREFIX : <{base_iri}>
                SELECT DISTINCT ?x ?y
                WHERE {{
                    ?x :{prop} ?y .
                    FILTER(?x != ?y)
                }}
            """
            try:
                for row in world.sparql(query):
                    x_name = row[0].name if hasattr(row[0], "name") else str(row[0]).split("#")[-1]
                    y_name = row[1].name if hasattr(row[1], "name") else str(row[1]).split("#")[-1]
                    pair_set.add((x_name, y_name))
                    detailed_rows.append({
                        "Ontology": label,
                        "Category": metric_name,
                        "Property": prop,
                        "Entity_1": x_name,
                        "Entity_2": y_name
                    })
            except Exception:
                pass
        counts[metric_name] = len(pair_set)

    counts["Total Detected Conflicts & Violations"] = sum(
        v for k, v in counts.items() if k != "Configuration Alerts (Room-Level)"
    )
    return counts, detailed_rows

if __name__ == "__main__":
    baseline_file = sys.argv[1]
    proposed_file = sys.argv[2]

    base_counts, base_details = evaluate_ontology(baseline_file, "Baseline Ontology")
    prop_counts, prop_details = evaluate_ontology(proposed_file, "Proposed Ontology")

    df_summary = pd.DataFrame([base_counts, prop_counts], index=["Baseline Ontology", "Proposed Ontology"]).T
    df_summary["Net Improvement / Difference"] = df_summary["Proposed Ontology"] - df_summary["Baseline Ontology"]

    df_details = pd.DataFrame(base_details + prop_details)

    print("\n================ COMPARATIVE EVALUATION RESULTS ================")
    print(df_summary.to_markdown())

    pathlib.Path("results").mkdir(exist_ok=True)
    df_summary.to_csv("results/comparison_summary.csv")
    df_details.to_csv("results/detected_conflict_pairs.csv", index=False)

    with open("results/summary.md", "w", encoding="utf-8") as f:
        f.write("## Automated SWRL Conflict Detection Comparison\n\n")
        f.write("### 1. Aggregated Conflict Counts\n\n")
        f.write(df_summary.to_markdown() + "\n\n")
        f.write("### 2. Sample Detected Rule Pairs & Policy Violations\n\n")
        if not df_details.empty:
            f.write(df_details.to_markdown(index=False) + "\n")
