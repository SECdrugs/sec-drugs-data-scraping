from pytrials.client import ClinicalTrials
import json
from datetime import datetime
from chembl_webresource_client.new_client import new_client
import requests
import pprint


pp = pprint.PrettyPrinter(depth=10)

DATE_FORMAT = "%B %d, %Y"
# Set base URL of GraphQL API endpoint
OPENTARGETS_BASE_URL = "https://api.platform.opentargets.org/api/v4/graphql"
# Build query string to get general information about AR and genetic constraint and tractability assessments
OPENTARGETS_QUERY_STRING = """
  query drug($chemblId: String!) {
  drug(chemblId: $chemblId) {
    name
    id
    maximumClinicalTrialPhase
    isApproved
    synonyms
    hasBeenWithdrawn
    tradeNames
    yearOfFirstApproval
    drugType
    hasBeenWithdrawn
    description
    mechanismsOfAction {
      rows {
        mechanismOfAction
        targetName
      }
    }
    indications {
      rows {
        disease {
          name
        }
      }
      approvedIndications
    }
    linkedDiseases {
      rows {
        name
      }
    }
    linkedTargets {
      rows {
				id
        approvedName
        approvedSymbol
        pathways {
          pathway
        }
      }
    }
  }
}
"""


class CompoundSearch:
    def __init__(self, db_instance):
        self._db = db_instance
        self._ct = ClinicalTrials()

    def _get_chembl_data(self, drug_name):
        # TODO remember to cite:
        # https://github.com/chembl/chembl_webresource_client#citing
        molecule = new_client.molecule
        mols = molecule.filter(
            molecule_synonyms__molecule_synonym__iexact=drug_name)
        if not len(mols):
            return None
        mol = mols[0]
        chembl_id = mol["molecule_chembl_id"]
        max_phase = mol["max_phase"]
        names = list(
            map(lambda s: s["molecule_synonym"], mol["molecule_synonyms"]))
        return (chembl_id, max_phase, names)

    def _get_clinical_trials_data(self, drug_name):
        res = self._ct.get_full_studies(search_expr=drug_name, max_studies=50)
        companies_phases = {}
        if not res["FullStudiesResponse"]["NStudiesReturned"]:
            return None
        studies = res["FullStudiesResponse"]["FullStudies"]
        for study_dict in studies:
            study = study_dict["Study"]
            protocol = study["ProtocolSection"]
            # The actual data we care about
            company = protocol["IdentificationModule"]["Organization"]["OrgFullName"]
            date = datetime.strptime(
                protocol["StatusModule"]["LastUpdateSubmitDate"], DATE_FORMAT
            )
            phase = int(protocol["DesignModule"]["PhaseList"]["Phase"][0][-1])

            if company in companies_phases:
                companies_phases[company]["phase"] = max(
                    companies_phases[company]["phase"], phase
                )
                companies_phases[company]["study_count"] += 1
                companies_phases[company]["latest_date"] = max(
                    companies_phases[company]["latest_date"], date
                )
            else:
                data = {"phase": phase, "study_count": 1, "lastest_date": date}
                companies_phases[company] = data

            return companies_phases

    def _get_open_targets_data(self, chembl_id):
        # Set variables object of arguments to be passed to endpoint
        variables = {"chemblId": chembl_id}

        # Perform POST request and check status code of response
        r = requests.post(
            OPENTARGETS_BASE_URL,
            json={"query": OPENTARGETS_QUERY_STRING, "variables": variables},
        )

        # Transform API response from JSON into Python dictionary and print in console
        print("OpenTargets Data:")
        api_response = json.loads(r.text)
        pp.pprint(api_response)
        return None

    def _analyze_compound(self, potential_compound):
        clin_trials_data = self._get_clinical_trials_data(
            potential_compound)
        print("\nClinical Trials Data:")
        pp.pprint(clin_trials_data)
        chembl_data = self._get_chembl_data(potential_compound)
        if not chembl_data:
            return
        (chembl_id, max_phase, names) = chembl_data
        open_targets_data = self._get_open_targets_data(chembl_id)
        print("\Open Targets Data:")
        pp.pprint(open_targets_data)
        # self._db.mark_compound_name_as_analyzed(potential_drug_name)
        # TODO save in database

    def analyze_potential_compounds(self):
        compounds = self._db.get_unanalyzed_compound_names()
        for id, potential_compound in compounds:
            self._analyze_compound(potential_compound)
            self._db.set_compound_analyzed(id)
