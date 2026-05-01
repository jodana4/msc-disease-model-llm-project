import pandas as pd
import re
from datetime import date

# ── 1. Load ────────────────────────────────────────────────────────────────────

df = pd.read_csv(
    'data/phenotype.hpoa',
    sep='\t',
    comment='#',
    low_memory=False
)

# ── 2. Parse creation dates ────────────────────────────────────────────────────

def extract_creation_date(biocuration_str):
    if pd.isna(biocuration_str):
        return None
    match = re.search(r'\[(\d{4}-\d{2}-\d{2})\]', str(biocuration_str))
    if match:
        return pd.to_datetime(match.group(1)).date()
    return None

df['creation_date'] = df['biocuration'].apply(extract_creation_date)

# ── 3. Define the cutoff ───────────────────────────────────────────────────────

CUTOFF = date(2023, 8, 1)

pre  = df[df['creation_date'] <  CUTOFF]
post = df[df['creation_date'] >= CUTOFF]

print(f"Total annotations:         {len(df):,}")
print(f"Created before Aug 2023:   {len(pre):,}")
print(f"Created on/after Aug 2023: {len(post):,}")

# ── 4. Focus: OMIM diseases, phenotype annotations only ───────────────────────

post_omim_phenotypes = post[
    (post['aspect'] == 'P') &
    (post['database_id'].str.startswith('OMIM:'))
]

print(f"\nPost-cutoff OMIM phenotype annotations: {len(post_omim_phenotypes):,}")

# ── 5. Identify hallmark annotations ──────────────────────────────────────────
# The frequency column uses a mix of HPO terms AND raw ratios.
# We need to catch both patterns:
#   HP:0040280 = Obligate (100%) — rarely used as a term in this file
#   HP:0040281 = Very frequent (80-99%)
#   1/1, 2/2, 3/3 etc = raw ratios where numerator == denominator (i.e. 100%)

def is_hallmark(freq):
    """Returns True if a frequency value indicates an obligate or very frequent phenotype."""
    if pd.isna(freq):
        return False
    freq = str(freq).strip()

    # HPO frequency terms
    if freq in ('HP:0040280', 'HP:0040281'):
        return True

    # Raw ratio where n/n means 100% (e.g. 1/1, 2/2, 7/7, 15/15)
    ratio_match = re.match(r'^(\d+)/(\d+)$', freq)
    if ratio_match:
        numerator   = int(ratio_match.group(1))
        denominator = int(ratio_match.group(2))
        if denominator > 0:
            proportion = numerator / denominator
            # Obligate = 100%, Very frequent = 80%+
            if proportion >= 0.80:
                return True

    return False

post_omim_phenotypes = post_omim_phenotypes.copy()
post_omim_phenotypes['is_hallmark'] = post_omim_phenotypes['frequency'].apply(is_hallmark)
post_hallmarks = post_omim_phenotypes[post_omim_phenotypes['is_hallmark']]

print(f"Post-cutoff OMIM hallmark annotations:  {len(post_hallmarks):,}")

# ── 6. Group by disease ────────────────────────────────────────────────────────

summary = (
    post_hallmarks
    .groupby(['database_id', 'disease_name'])
    .agg(
        new_hallmark_count=('hpo_id', 'count'),
        new_hpo_ids=('hpo_id', lambda x: '; '.join(sorted(x.unique())))
    )
    .reset_index()
    .sort_values('new_hallmark_count', ascending=False)
)

print(f"\nDiseases with new hallmark annotations since Aug 2023: {len(summary):,}")
print("\nTop 20 candidates:")
print(summary.head(20).to_string(index=False))

# ── 7. Save ────────────────────────────────────────────────────────────────────

summary.to_csv('data/candidate_diseases.csv', index=False)
print("\nSaved → data/candidate_diseases.csv")