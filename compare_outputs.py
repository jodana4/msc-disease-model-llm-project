import pandas as pd
import re as re2

ground_truth = pd.read_csv(
    'data/ground_truth_post_cutoff.csv',
    low_memory=False
)

hpo_names = {}
with open('data/hp.obo', 'r') as f:
    current_id = None
    for line in f:
        line = line.strip()
        if line.startswith('[Term]'):
            current_id = None
        elif line.startswith('id: HP:'):
            current_id = line.replace('id: ', '')
        elif line.startswith('name: ') and current_id:
            hpo_names[current_id] = line.replace('name: ', '')


llm_output = pd.read_csv(
    'outputs/experiment/part1b/hpoa_rows/OMIM_142900.tsv',
    sep='\t',
    header=None,
    names=['database_id', 'disease_name', 'qualifier', 'hpo_id',
           'reference', 'evidence', 'onset', 'frequency',
           'sex', 'modifier', 'aspect', 'biocuration']
)

omim_id = 'OMIM:142900'
gt_disease = ground_truth[ground_truth['database_id'] == omim_id]

# ── Filter ground truth to hallmarks only ─────────────────────────────────────
import re

def is_hallmark(freq):
    if pd.isna(freq):
        return False
    freq = str(freq).strip()
    if freq in ('HP:0040280', 'HP:0040281'):
        return True
    match = re.match(r'^(\d+)/(\d+)$', freq)
    if match:
        n, d = int(match.group(1)), int(match.group(2))
        if d > 0 and n/d >= 0.80:
            return True
    return False

gt_hallmarks = gt_disease[gt_disease['frequency'].apply(is_hallmark)]

gt_terms  = set(gt_hallmarks['hpo_id'].dropna().unique())
llm_terms = set(llm_output['hpo_id'].dropna().unique())

matched    = gt_terms & llm_terms
only_in_gt = gt_terms - llm_terms
only_in_llm = llm_terms - gt_terms

print(f"Disease: {omim_id}")
print(f"Ground truth HALLMARK terms: {len(gt_terms)}")
print(f"LLM output HPO terms:        {len(llm_terms)}")
print(f"Matched terms:               {len(matched)}")
print()

if matched:
    print("✓ MATCHED:")
    for t in sorted(matched):
        print(f"  {t} — {hpo_names.get(t, 'unknown')}")

print()
if only_in_gt:
    print("✗ ONLY IN GROUND TRUTH (LLM missed):")
    for t in sorted(only_in_gt):
        print(f"  {t} — {hpo_names.get(t, 'unknown')}")

print()
if only_in_llm:
    print("? ONLY IN LLM (not in post-cutoff hallmarks):")
    for t in sorted(only_in_llm):
        print(f"  {t} — {hpo_names.get(t, 'unknown')}")