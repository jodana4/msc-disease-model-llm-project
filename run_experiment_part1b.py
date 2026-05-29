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

# ── The Skill prompt ───────────────────────────────────────────────────────────────
def build_prompt(disease_name, omim_id):
    today = date.today().strftime('%Y-%m-%d')
    return f"""You are an expert rare disease phenotype biocurator working in the style 
of the Human Phenotype Ontology Annotation (HPOA) project.

Your task is to generate hallmark phenotype annotations for a given rare 
genetic disease in valid HPOA format.

IMPORTANT: You MUST search the web and published literature to complete this task accurately.

STEP 1 — SEARCH FOR PAPERS
Search PubMed and biomedical literature for published clinical studies 
describing the phenotypic features of this disease. Focus on cohort studies 
rather than single case reports where possible.

STEP 2 — IDENTIFY HALLMARK PHENOTYPES
From the papers you find, identify phenotypes present in 80% or more of 
patients. Only include phenotypes with clear frequency evidence from 
the literature.

STEP 3 — VALIDATE HPO TERMS
For each hallmark phenotype, search https://www.ebi.ac.uk/ols4 to find 
the most specific valid HPO term. Confirm the term ID is real and current 
before including it. Never guess a HPO term ID.

STEP 4 — ASSIGN FREQUENCY
Assign frequency as a raw ratio (e.g. 15/20) based on paper evidence. 
If exact count is unavailable, use:
- HP:0040280 = Obligate (100% of patients)
- HP:0040281 = Very frequent (80-99% of patients)

STEP 5 — FORMAT OUTPUT
First output a human readable summary in this format:
--- PHENOTYPE SUMMARY ---
HP:XXXXXXX | Term Name | Frequency | PMID
--- END SUMMARY ---

Then output the tab separated HPOA rows in exact HPOA format below.
Use PCS as the evidence code.
Use today's date in the biocuration column in format:
LLM:claude-opus-4-7-agentic[{today}]

HPOA COLUMN ORDER:
database_id\tdisease_name\tqualifier\thpo_id\treference\tevidence\tonset\tfrequency\tsex\tmodifier\taspect\tbiocuration

EXAMPLE ROW:
OMIM:256500\tNetherton syndrome\t\tHP:0004395\tPMID:34138484\tPCS\t\t2/2\t\t\tP\tORCID:0000-0002-0736-9199[2025-11-03]

IMPORTANT RULES:
- Only include phenotypes with frequency 80% or above
- Every annotation must have a real PMID reference
- Every HPO term ID must be validated via OLS before inclusion
- Return ONLY the summary and tab separated rows, no other explanation
- Do not include a header row in the HPOA rows

Disease to annotate: {disease_name} ({omim_id})"""

# ── Run the pipeline ───────────────────────────────────────────────────────────────
def main():
    client = anthropic.Anthropic()

    # Create output folders
    os.makedirs('outputs/experiment/part1b/summaries', exist_ok=True)
    os.makedirs('outputs/experiment/part1b/hpoa_rows', exist_ok=True)

    all_hpoa_rows = []

    for omim_id, disease_name in DISEASES:
        print(f"Processing: {disease_name} ({omim_id})...")

        prompt = build_prompt(disease_name, omim_id)

        try:
            response = client.messages.create(
                model="claude-opus-4-7",
                max_tokens=2000,
                tools=[
                    {
                        "type": "web_search_20250305",
                        "name": "web_search"
                    }
                ],
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract all text content from response
            output = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    output += block.text

            # Save full output including summary
            safe_name = omim_id.replace(':', '_')
            with open(f'outputs/experiment/part1b/summaries/{safe_name}.txt', 'w') as f:
                f.write(f"Disease: {disease_name} ({omim_id})\n")
                f.write("=" * 60 + "\n")
                f.write(output)

            # Extract just the HPOA rows
            if '--- END SUMMARY ---' in output:
                hpoa_section = output.split('--- END SUMMARY ---')[1].strip()
            else:
                hpoa_section = output.strip()

            # Save individual HPOA rows file
            with open(f'outputs/experiment/part1b/hpoa_rows/{safe_name}.tsv', 'w') as f:
                f.write(hpoa_section)

            # Collect for combined file
            all_hpoa_rows.append(hpoa_section)

            print(f"  Done — saved to outputs/experiment/part1b/")

        except Exception as e:
            print(f"  ERROR for {omim_id}: {e}")

        # Small delay between API calls
        time.sleep(3)

    # Save combined HPOA file
    with open('outputs/experiment/part1b/all_diseases_part1b.tsv', 'w') as f:
        f.write('\n'.join(all_hpoa_rows))

    print("\nAll done — combined file saved to outputs/experiment/part1b/all_diseases_part1b.tsv")

if __name__ == "__main__":
    main()