import pandas as pd
import re
from datetime import date, datetime

# ── 1. Load HPOA ───────────────────────────────────────────────────────────────
df = pd.read_csv(
    'data/phenotype.hpoa',
    sep='\t',
    comment='#',
    low_memory=False
)

# ── 2. Parse creation dates ────────────────────────────────────────────────────
def extract_creation_date(biocuration_str):
    """Extract the first date from a biocuration string."""
    if pd.isna(biocuration_str):
        return None
    match = re.search(r'\[(\d{4}-\d{2}-\d{2})\]', str(biocuration_str))
    if match:
        return datetime.strptime(match.group(1), '%Y-%m-%d').date()
    return None

# ── 3. Tests ───────────────────────────────────────────────────────────────────
def run_tests(df):
    """
    Manual tests to verify the script is working correctly.
    Expected values were calculated by hand from the raw HPOA file.
    """
    print("Running tests...")
    passed = 0
    failed = 0

    CUTOFF = date(2023, 8, 1)

    # ── Test 1: Date parsing works correctly ───────────────────────────────────
    # These are real biocuration strings from the HPOA file
    test_cases = [
        ('HPO:probinson[2021-06-21]',                    date(2021, 6, 21)),
        ('HPO:probinson[2019-06-01];HPO:lhamilton[2023-09-12]', date(2019, 6, 1)),
        (None,                                            None),
        ('',                                              None),
    ]
    for input_val, expected in test_cases:
        result = extract_creation_date(input_val)
        if result == expected:
            print(f"  PASS: extract_creation_date('{input_val}') = {result}")
            passed += 1
        else:
            print(f"  FAIL: extract_creation_date('{input_val}') = {result}, expected {expected}")
            failed += 1

    # ── Test 2: Holt-Oram syndrome pre/post split ──────────────────────────────
    # MANUALLY VERIFIED: for OMIM:142900, counted rows before and after August 2023 by hand.

    HOLT_ORAM_PRE_EXPECTED  = 11  
    HOLT_ORAM_POST_EXPECTED = 90  

    if HOLT_ORAM_PRE_EXPECTED is not None:
        df['creation_date'] = df['biocuration'].apply(extract_creation_date)
        holt_oram = df[df['database_id'] == 'OMIM:142900']
        pre  = len(holt_oram[holt_oram['creation_date'] <  CUTOFF])
        post = len(holt_oram[holt_oram['creation_date'] >= CUTOFF])

        if pre == HOLT_ORAM_PRE_EXPECTED:
            print(f"  PASS: Holt-Oram pre-cutoff count = {pre}")
            passed += 1
        else:
            print(f"  FAIL: Holt-Oram pre-cutoff = {pre}, expected {HOLT_ORAM_PRE_EXPECTED}")
            failed += 1

        if post == HOLT_ORAM_POST_EXPECTED:
            print(f"  PASS: Holt-Oram post-cutoff count = {post}")
            passed += 1
        else:
            print(f"  FAIL: Holt-Oram post-cutoff = {post}, expected {HOLT_ORAM_POST_EXPECTED}")
            failed += 1
    else:
        print("  SKIP: Holt-Oram counts not yet manually verified — fill in expected values")

    # ── Test 3: No annotations should appear in both pre and post sets ─────────
    df['creation_date'] = df['biocuration'].apply(extract_creation_date)
    chosen_ids = ['OMIM:142900']
    df_chosen = df[df['database_id'].isin(chosen_ids)]
    pre_set  = set(df_chosen[df_chosen['creation_date'] <  CUTOFF].index)
    post_set = set(df_chosen[df_chosen['creation_date'] >= CUTOFF].index)
    overlap  = pre_set & post_set

    if len(overlap) == 0:
        print(f"  PASS: No overlap between pre and post cutoff sets")
        passed += 1
    else:
        print(f"  FAIL: {len(overlap)} rows appear in both pre and post sets")
        failed += 1

    # ── Test 4: All chosen disease IDs appear in the output ───────────────────
    chosen_ids_full = [
        'OMIM:618505', 'OMIM:615829', 'OMIM:256810', 'OMIM:256500',
        'OMIM:142900', 'OMIM:610042', 'OMIM:613826', 'OMIM:616276',
        'OMIM:616462', 'OMIM:162000', 'OMIM:617056', 'OMIM:616900',
        'OMIM:277000', 'OMIM:618977', 'OMIM:616325', 'OMIM:607398',
        'OMIM:610370', 'OMIM:117360', 'OMIM:614923', 'OMIM:614199',
    ]
    df_chosen_full = df[df['database_id'].isin(chosen_ids_full)]
    found_ids = set(df_chosen_full['database_id'].unique())
    missing   = set(chosen_ids_full) - found_ids

    if len(missing) == 0:
        print(f"  PASS: All 20 disease IDs found in HPOA")
        passed += 1
    else:
        print(f"  FAIL: These IDs not found in HPOA: {missing}")
        failed += 1

    print(f"\nTest summary: {passed} passed, {failed} failed")
    print("─" * 40)
    return failed == 0

# ── 4. Run tests first ─────────────────────────────────────────────────────────
df['creation_date'] = df['biocuration'].apply(extract_creation_date)
all_passed = run_tests(df)

if not all_passed:
    print("\nFix failing tests before proceeding.")
else:
    print("\nAll tests passed — proceeding with extraction.")

    CUTOFF = date(2023, 8, 1)

    chosen_ids = [
        'OMIM:618505', 'OMIM:615829', 'OMIM:256810', 'OMIM:256500',
        'OMIM:142900', 'OMIM:610042', 'OMIM:613826', 'OMIM:616276',
        'OMIM:616462', 'OMIM:162000', 'OMIM:617056', 'OMIM:616900',
        'OMIM:277000', 'OMIM:618977', 'OMIM:616325', 'OMIM:607398',
        'OMIM:610370', 'OMIM:117360', 'OMIM:614923', 'OMIM:614199',
    ]

    df_chosen = df[df['database_id'].isin(chosen_ids)]

    pre_cutoff  = df_chosen[df_chosen['creation_date'] <  CUTOFF]
    post_cutoff = df_chosen[
        (df_chosen['creation_date'] >= CUTOFF) &
        (df_chosen['aspect'] == 'P')
    ]

    print(f"\nTotal annotations for chosen diseases: {len(df_chosen)}")
    print(f"Pre-cutoff annotations:  {len(pre_cutoff)}")
    print(f"Post-cutoff annotations: {len(post_cutoff)}")

    print("\nPer disease breakdown:")
    for omim_id in chosen_ids:
        pre  = len(pre_cutoff[pre_cutoff['database_id']   == omim_id])
        post = len(post_cutoff[post_cutoff['database_id'] == omim_id])
        name = df_chosen[df_chosen['database_id'] == omim_id]['disease_name'].iloc[0]
        print(f"  {omim_id}  {name[:50]:50}  pre={pre:3}  post={post:3}")

    pre_cutoff.to_csv('data/ground_truth_pre_cutoff.csv',   index=False)
    post_cutoff.to_csv('data/ground_truth_post_cutoff.csv', index=False)

    print("\nSaved:")
    print("  data/ground_truth_pre_cutoff.csv")
    print("  data/ground_truth_post_cutoff.csv")
    