import pandas as pd
import re
from datetime import date, datetime

df = pd.read_csv(
    'data/phenotype.hpoa',
    sep='\t',
    comment='#',
    low_memory=False
)

def extract_creation_date(biocuration_str):
    if pd.isna(biocuration_str):
        return None
    match = re.search(r'\[(\d{4}-\d{2}-\d{2})\]', str(biocuration_str))
    if match:
        return datetime.strptime(match.group(1), '%Y-%m-%d').date()
    return None

df['creation_date'] = df['biocuration'].apply(extract_creation_date)

CUTOFF = date(2023, 8, 1)

omim_phenotypes = df[
    (df['aspect'] == 'P') &
    (df['database_id'].str.startswith('OMIM:'))
].copy()

summary = (
    omim_phenotypes
    .groupby(['database_id', 'disease_name'])
    .apply(lambda g: pd.Series({
        'total_annotations':   len(g),
        'post_cutoff_count':   (g['creation_date'] >= CUTOFF).sum(),
        'pre_cutoff_count':    (g['creation_date'] <  CUTOFF).sum(),
    }))
    .reset_index()
)

summary['pct_post_cutoff'] = (
    summary['post_cutoff_count'] / summary['total_annotations'] * 100
).round(1)

summary['omim_number'] = (
    summary['database_id']
    .str.replace('OMIM:', '', regex=False)
    .astype(int)
)

# Filter for diseases with 80%+ post-cutoff annotations and at least 10 total annotations
target_diseases = summary[
    (summary['pct_post_cutoff'] >= 80) &
    (summary['pre_cutoff_count'] >= 2) &
    (summary['total_annotations'] >= 10) &
    (summary['omim_number'] < 622000)
].sort_values('total_annotations', ascending=False)

print(f"Target diseases: {len(target_diseases)}")
print()
print(target_diseases[[
    'database_id', 'disease_name', 'omim_number',
    'total_annotations', 'pre_cutoff_count', 'post_cutoff_count', 'pct_post_cutoff'
]].to_string(index=False))

target_diseases.to_csv('data/target_diseases.csv', index=False)
print("\nSaved → data/target_diseases.csv")

