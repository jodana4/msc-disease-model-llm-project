import anthropic
import os
import time
from datetime import date

# ── Selected 20 diseases ───────────────────────────────────────────────────────────
DISEASES = [
    ("OMIM:618505", "Stolerman neurodevelopmental syndrome"),
    ("OMIM:615829", "Xia-Gibbs syndrome"),
    ("OMIM:256810", "Mitochondrial DNA depletion syndrome 6 (hepatocerebral type)"),
    ("OMIM:256500", "Netherton syndrome"),
    ("OMIM:142900", "Holt-Oram syndrome"),
    ("OMIM:610042", "Pitt-Hopkins like syndrome 1"),
    ("OMIM:613826", "Leber congenital amaurosis 6"),
    ("OMIM:616276", "Coenzyme Q10 deficiency, primary 7"),
    ("OMIM:616462", "Acrofacial dysostosis, Cincinnati type"),
    ("OMIM:162000", "Tubulointerstitial kidney disease, autosomal dominant 1"),
    ("OMIM:617056", "Tubulointerstitial kidney disease, autosomal dominant 5"),
    ("OMIM:616900", "Hypotonia, infantile, with psychomotor retardation and characteristic facies 3"),
    ("OMIM:277000", "Mayer-Rokitansky-Kuster-Hauser syndrome"),
    ("OMIM:618977", "Optic atrophy 12"),
    ("OMIM:616325", "Myasthenic syndrome, congenital 9"),
    ("OMIM:607398", "Glucocorticoid deficiency 2"),
    ("OMIM:610370", "Diarrhea 4, malabsorptive, congenital"),
    ("OMIM:117360", "Spinocerebellar ataxia 29, congenital nonprogressive"),
    ("OMIM:614923", "Branched-chain keto acid dehydrogenase kinase deficiency"),
    ("OMIM:614199", "Nephrotic syndrome, type 5, with or without ocular abnormalities"),
]

# ── The Skill prompt (2 API calls) ────────────────────────────────────────────────────────────────
def build_research_prompt(disease_name, omim_id):
    return f"""Search PubMed for published clinical cohort studies describing the phenotypic features of {disease_name} ({omim_id}).

Find studies with at least 10 patients. For each phenotype, record:
1. The phenotype name
2. The frequency (as a ratio e.g. 45/50 or percentage)
3. The PMID of the paper

Only include phenotypes present in 80% or more of patients.
Do NOT search hpo.jax.org or the HPOA database.
Return your findings as a simple list."""

def build_format_prompt(disease_name, omim_id, research_findings):
    today = date.today().strftime('%Y-%m-%d')
    return f"""You are an expert HPOA biocurator. Format the following research findings into valid HPOA annotations.

RESEARCH FINDINGS:
{research_findings}

For each phenotype:
1. Find the most specific valid HPO term ID using https://www.ebi.ac.uk/ols4
2. Format as a tab-separated HPOA row

HPOA COLUMN ORDER:
database_id\tdisease_name\tqualifier\thpo_id\treference\tevidence\tonset\tfrequency\tsex\tmodifier\taspect\tbiocuration

EXAMPLE ROW:
OMIM:256500\tNetherton syndrome\t\tHP:0004395\tPMID:34138484\tPCS\t\t2/2\t\t\tP\tORCID:0000-0002-0736-9199[2025-11-03]

Output format:
--- PHENOTYPE SUMMARY ---
HP:XXXXXXX | Term Name | Frequency | PMID
--- END SUMMARY ---

Then the HPOA rows.

RULES:
- Every HPO term must be validated via OLS
- Use PCS as evidence code
- Use biocuration format: LLM:claude-sonnet-4-6-agentic[{today}]
- Output ONLY the summary and HPOA rows, nothing else
- Do not search the web — use only the research findings provided above
- Use HPO term IDs from your training knowledge
- Output the summary and HPOA rows immediately with no reasoning

Disease: {disease_name} ({omim_id})"""

def main():
    client = anthropic.Anthropic()

    os.makedirs('outputs/experiment/part2/summaries', exist_ok=True)
    os.makedirs('outputs/experiment/part2/hpoa_rows', exist_ok=True)

    all_hpoa_rows = []

    for omim_id, disease_name in DISEASES:
        print(f"Processing: {disease_name} ({omim_id})...")

        try:
            # ── Call 1: Research with web search ──────────────────────────────
            print("  Step 1 — Searching literature...")
            research_response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4000,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": build_research_prompt(disease_name, omim_id)}]
            )

            # Extract research findings text
            research_findings = ""
            for block in research_response.content:
                if hasattr(block, 'text'):
                    research_findings += block.text

            print(f"  Research findings: {len(research_findings)} characters")

            # Small pause between calls
            time.sleep(10)

            # ── Call 2: Format into HPOA without web search ───────────────────
            print("  Step 2 — Formatting into HPOA...")
            format_response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4000,
                messages=[{"role": "user", "content": build_format_prompt(disease_name, omim_id, research_findings)}]
            )

            output = ""
            for block in format_response.content:
                if hasattr(block, 'text'):
                    output += block.text

            # Save full output
            safe_name = omim_id.replace(':', '_')
            with open(f'outputs/experiment/part2/summaries/{safe_name}.txt', 'w') as f:
                f.write(f"Disease: {disease_name} ({omim_id})\n")
                f.write("=" * 60 + "\n")
                f.write(f"RESEARCH FINDINGS:\n{research_findings}\n\n")
                f.write(f"FORMATTED OUTPUT:\n{output}\n")

            # Extract HPOA rows
            hpoa_lines = [
                line for line in output.split('\n')
                if line.strip().startswith('OMIM:')
            ]
            hpoa_section = '\n'.join(hpoa_lines)

            with open(f'outputs/experiment/part2/hpoa_rows/{safe_name}.tsv', 'w') as f:
                f.write(hpoa_section)

            all_hpoa_rows.append(hpoa_section)

            print(f"  HPOA rows extracted: {len(hpoa_lines)}")
            print()
            print("=== OUTPUT PREVIEW ===")
            print(output[:800])
            print("=== END PREVIEW ===")

        except Exception as e:
            print(f"  ERROR for {omim_id}: {e}")

        time.sleep(180)

    with open('outputs/experiment/part2/all_diseases_part2.tsv', 'w') as f:
        f.write('\n'.join(all_hpoa_rows))

    print("\nDone.")

if __name__ == "__main__":
    main()