# SEC Discontinued Drug Search

## Overview

This repo contains python code that analyzeses SEC filings for discontinued drugs.
The goal is to automate the process described in [this study](https://www.frontiersin.org/articles/10.3389/fcvm.2023.1033832/full), which consists of searching SEC filings for mentions of discontinued drugs and creating a database with the results.

The project is structured as a pipeline, each step of which serves a specific purpose.
The steps of the pipeline are organized as classes (one for each step) in their respective files and orchestrated by `SECPipeline` in `pipeline.py`. They all share a sqlite database managed by the `FilingMetadataDB` class in `data/filing_db.py`. This database contains a table for filings and one for potential names of discontinued compounds, in order to track each item's progress through the pipeline.

### Pipeline Components:
1. Download
2. Filing Analysis
3. Compound Name Analysis
4. TODO: Saving data to application database

## 1. Download
Uses the unofficial [sec-edgar-api](https://github.com/jadchaar/sec-edgar-api) API wrapper for the SEC Edgar database to get the links of 10-K, 10-Q, 20-F, 8-K, and 6-K filings for the given list of companies. Each filing is then downloaded and relevant metadata such as file path, company, etc. is saved to the database.

If the filing is already on disk or in the database, it will not be redownloaded.

## 2. Filing Analysis

Filings that have not yet been analyzed are searched for keywords associated with discontinuation (see regex in `analysis/sec_parsing.py`). Sections of text surrounding the matched keyword are included in a prompt to the OpenAI Chat API, asking for the following informaiton to be extracted:

```
{"discontinued": true,
"drug_name(s)": [__],
"reason_for_discontinuation": __}
If the text does not refer to the discontinuation of a drug, return
{"discontinued": false}
```

Once all matches have been searched, the filing is marked as analyzed. Each filing is in a one-to-many relationship with its compounds.

**Notes:** GPT-4 performs better than `gpt-3.5-turbo-16k`, but is 10x more expensive. Using 8k token context results in many errors, even when the number of characters surrounding the matched keywords is reduced (since characters in the prompt are also included).

## 3. Compound Analysis

**This section is not completed**

This step of the pipeline consists in taking potential compound names returned from the OpenAI API and searching whether clinical and biological data exists for a compound of that name.

1. Clinical trials data is looked up on clinicaltrials.gov using the unofficial [pytrials](`https://github.com/jvfe/pytrials`) API wrapper.
2. The Chembl API is called to retrieve the compound ID for a given compound name, if it exists. If not, this should terminate the analysis.
3. The Open Targets GraphQL API is called with the Chembl ID as its parameter to retrieve additional data on the compound.


## 4. Exporting Data

Data has to be saved to the application database once the pipeline is concluded. Relevant information will be in both `compound_names` and `filings` tables, but a simple join can match a compound with its filing and thus company.

## Usage

`python data-sourcing` from parent directory or `python .` from project directory.

`python data-sourcing --download` or `python data-sourcing -D` to download filings.


## Development

1. Obtain an OpenAI API key from https://platform.openai.com/ 
2. Ensure you have a recent version of python installed. **TODO:** Add `requirements.txt` with package names. In the meantime, `pip install` the missing packages when you get errors (sorry!).
3. Rename `.env_sample` to `.env`
  - Add your OpenAI API key
  - Add your SEC EDGAR database key, with format "Company Name Email" (sample in file)
4. `python .` to run the code from the current directory.

## TODOs

- [ ] Finish `CompoundSearch`, the last step of the pipeline, by saving the outputs to the application database.
- [ ] Expand number of companies (currently saved in `pipeline.py`).
- [ ] Filter compounds by indication to identify cardiovascular/renal/metabolic indications.