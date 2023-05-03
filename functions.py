from datetime import date
import json
import os
import logging
import typing
import pickle

import zeep
import requests

import utils.logger
import libplanon
from utils.dart_api import get_resource_by_query, login_jwt

# ============================================================
# LOGGING
# ============================================================

log = logging.getLogger(__name__)

# ============================================================
# SETUP
# ============================================================

log.debug("Setting up REST API session")
session = requests.Session()
session.params = {
    "accesskey": os.environ.get("PLN_REST_KEY")
}

try:
    response = session.get(url=os.environ.get("PLN_REST_URL"))
    response.raise_for_status()
except Exception as e:
    log.error(repr(e))

asset_group_cache_path = "cache/asset_groups.pickle"
properties_cache_path = "cache/properties.pickle"
spaces_cache_path = "cache/spaces.pickle"

ethernet_categories = set([
    "AnalogPhone",
    "Cat3",
    "Cat3-Shielded",
    "Cat3-Split",
    "Cat4",
    "Cat4-Shielded",
    "Cat4-Split",
    "Cat5",
    "Cat5-Shielded",
    "Cat5-Split",
    "Cat5e",
    "Cat5e-Shielded",
    "Cat5e-Split",
    "Cat6",
    "Cat6-Shielded",
    "Cat6-Split",
    "Cat6A",
    "Cat6A-Shielded",
    "Cat6A-Split",
    "Cat7",
    "Cat7-Shielded",
    "Cat8",
    "Cat8-Shielded",
    "Coaxial-50",
    "Coaxial-75",
    "Fiber-FDDI",
    "Fiber-OM1",
    "Fiber-OM2",
    "Fiber-OM3",
    "Fiber-OM4",
    "Fiber-OM5",
    "Fiber-Other",
    "Fiber-SMF",
    "Other",
])

get_token = libplanon.TokenManager(url=os.environ.get('PLN_URL'), username=os.environ.get('PLN_USR'), password=os.environ.get('PLN_PWD')).get_token

pln_client = libplanon.APIManager(url=os.environ.get('PLN_URL'), services=['ItemGroup','UsrAsset', 'UsrMEAsset', 'StandardAsset','BuildingElement','Property','Space'])

pln_asset_client = pln_client['UsrAsset']
pln_property_client = pln_client['Property']
pln_space_client = pln_client['Space']
pln_item_group_client = pln_client['ItemGroup']

# ============================================================
# FUNCTIONS
# ============================================================

def get_pln_asset_groups():
    # Cache asset group
    log.info("Caching planon asset groups")
    planon_asset_group_ids = pln_item_group_client.find(get_token(),{})

    index = 0
    chunk_size = 100
    planon_asset_groups = []
    for planon_asset_group_id in planon_asset_group_ids:
        end_chunk = index + chunk_size if index + chunk_size < len(planon_asset_group_ids) else len(planon_asset_group_ids)
        if index % chunk_size == 0:
            log.info(f"Processing chunk {index} through {end_chunk}")

        planon_asset_groups.append(zeep.helpers.serialize_object(pln_item_group_client.read(get_token(),planon_asset_group_id), dict))
        index += 1

    return planon_asset_groups


def get_planon_location(property_code: int, space_number: str) -> tuple():
    pln_property_ids = pln_property_client.find(get_token(),{
        'fieldFilters': [{
            'fieldName': 'Code',
            'filterValue': property_code,
            'operator': 'equals'
        }]
    })

    if len(pln_property_ids) == 1:
        pln_space_ids = pln_space_client.find(get_token(), {
            'fieldFilters': [{
                'fieldName': 'Code',
                'filterValue': space_number,
                'operator': 'equals'
            },
            {
                'fieldName': 'PropertyRef',
                'filterValue': pln_property_ids[0],
                'operator': 'equals'
            }]
        })
        if len(pln_space_ids) == 1:
            return pln_property_ids[0], pln_space_ids[0]
        else:
            return pln_property_ids[0], None
    else:
        return None, None



def update_asset(asset_id: int, code: str, name: str, property_ref: int, parent_ref: int=None, comments: str=None, asset_group: int =None, space_ref: int=None, start_date: date = None, attributes: dict = None) -> json:
    log.debug(f"Updating asset {code}")

    body = {
        "code": code,
        "name": name,
        "propertyRef": property_ref,
        "isSimple": True,
        "departmentRef": 167,
        "constructionDate": start_date,
        "itemGroupRef" : asset_group,
        "isArchived" : False,
        "dossier": comments,
        "parentRef": parent_ref,
    }

    if space_ref:
        body['spaceRef'] =  space_ref

    if attributes:
        body["attributeSet"] = 1
        body['attributes'] = {
            "NSJACKID": attributes['jack'],
        }

    if attributes.get('cable_type'):
        body['attributes']["NSCABLETYPE"] = attributes['cable_type']

    if attributes.get('legacy_patch'):
        body['attributes']["NSLEGACYPATCH"] = attributes['legacy_patch']

    log.debug(f"Payload body {body}")
    response = session.put(url=f"{os.environ.get('PLN_REST_URL')}asset/{asset_id}", json=body)

    return response


def create_asset(code: str, name: str, property_ref: int, parent_ref: int=None, comments: str=None, asset_group: int=None, space_ref: int=None, start_date: date = None, attributes: dict = None) -> json:

    body = {
        "code": code,
        "name": name,
        "propertyRef": property_ref,
        "isSimple": True,
        "departmentRef": 167,
        "constructionDate": start_date,
        "itemGroupRef": asset_group,
        "isArchived": False,
        "dossier": comments,
        "parentRef": parent_ref,
    }

    if space_ref:
        body['spaceRef'] =  space_ref

    if attributes:
        body["attributeSet"] = 1
        body['attributes'] = {
            "NSCABLETYPE": attributes.get('cable_type', None),
            "NSJACKID": attributes.get('jack', None),
        }

    response = session.post(url=f"{os.environ.get('PLN_REST_URL')}asset", json=body)

    return response


def get_asset(id_=None, asset_code=None):
    url = f"{os.environ['PLN_REST_URL']}asset/{id_}"
    
    response = session.get(url=url)
    response.raise_for_status()

    return response.json()


def get_pln_asset(asset_code):
    pln_asset_ids = pln_asset_client.find(get_token(),{
    'fieldFilters': [{
        'fieldName': 'Code',
        'filterValue': asset_code,
        'operator': 'equals'
        }]
    })
    if len(pln_asset_ids) > 0:
        return pln_asset_ids[0]
    else:
        return None


def validate_network_jack(source_network_jack: dict) -> tuple():
    issues: list = []

    warnings: int = 0
    errors: int = 0

    # RULE 1
    # jack must have a valid building reference number
    if not source_network_jack['building_ref']:
        errors += 1

        issues.append("Missing building ref")
    elif source_network_jack['building_ref'] and str(source_network_jack['building_ref']).zfill(4) not in property_codes:
        errors += 1

        issues.append("Invalid building code")

    # RULE 2:
    # jack must have a jack number
    if not source_network_jack['jack'] or source_network_jack['jack'].isspace():
        errors += 1

        issues.append("Jack is is null or empty")

    # RULE 3:
    # jack must have a jack id
    if not source_network_jack['jack_id'] or source_network_jack['jack_id'].isspace():
        errors += 1

        issues.append("Jack ID is null or empty")

    # RULE 4:
    # there should be no spaces in the jack
    if source_network_jack['jack'] and " " in source_network_jack['jack']:
        warnings += 1

        issues.append("Space in jack")

    # RULE 5:
    # there should be no spaces in the jack id
    if source_network_jack['jack_id'] and " " in source_network_jack['jack_id']:
        warnings += 1

        issues.append("Space in jack id")

    # RULE 6:
    # enforce certain cable categories
    if source_network_jack['cable_type'] and source_network_jack['cable_type'].upper() not in ethernet_categories:
        warnings += 1

        issues.append("Invalid ethernet cable category")

    # RULE 7:
    # Verify the space is a valid Planon space
    space_code = f"{str(source_network_jack['building_ref']).zfill(4)}-{source_network_jack['space_id']}"
    if space_code not in space_codes:
        warnings += 1

        issues.append("Space is not a valid Planon space")

    return issues, warnings, errors


def transform_network_jack(source_network_jack: dict) -> dict:
    issues, warnings, errors = validate_network_jack(source_network_jack)

    if not errors:
        transformed_network_jack = {}

        transformed_network_jack['id'] = source_network_jack['id']
        transformed_network_jack['building_ref'] = str(source_network_jack['building_ref']).zfill(4)
        transformed_network_jack['jack'] = f"{' '.join(source_network_jack['jack'].split()).replace(' ', '')}-{' '.join(source_network_jack['jack_id'].split())}"
        transformed_network_jack['comments'] = source_network_jack['comments']
        transformed_network_jack['legacy_patch'] = source_network_jack['legacy_patch']

        # If not a valid space_id then null the input value
        if "Space is not a valid Planon space" in issues:
            transformed_network_jack['space_id'] = None
        else:
            transformed_network_jack['space_id'] = source_network_jack['space_id']

        transformed_network_jack['cable_type'] = source_network_jack['cable_type']
        transformed_network_jack['wiring_date'] = source_network_jack['wiring_date'].isoformat() if source_network_jack.get('wiring_date') else None

        return transformed_network_jack


# ============================================================
# CACHING
# ============================================================

jwt = login_jwt(f"{os.environ.get('API_BASE_URL')}/jwt", os.environ.get("API_KEY"), "api:facilities:properties:read")

# Dartmouth Properties
if os.path.exists(properties_cache_path):
    with open(properties_cache_path, "rb") as file:
        properties = pickle.load(file)

    property_codes = [code['id'] for code in properties]
else:
    properties = get_resource_by_query(f"{os.environ.get('API_BASE_URL')}/facilities/properties", jwt)
    property_codes = [code['id'] for code in properties]

    with open(properties_cache_path, "wb") as file:

        pickle.dump(properties, file)

# Dartmouth Spaces
if os.path.exists(spaces_cache_path):
    with open(spaces_cache_path, "rb") as file:
        spaces = pickle.load(file)

    space_codes = [f"{code['property_id']}-{code['number']}" for code in spaces]
else:
    spaces = get_resource_by_query(f"{os.environ.get('API_BASE_URL')}/facilities/spaces", jwt)
    space_codes = [f"{code['property_id']}-{code['number']}" for code in spaces]

    with open(spaces_cache_path, "wb") as file:

        pickle.dump(spaces, file)

# Planon Asset Groups
if os.path.exists(asset_group_cache_path):
    with open(asset_group_cache_path, "rb") as file:
        planon_asset_groups = pickle.load(file)
else:
    planon_asset_groups = get_pln_asset_groups()

    with open(asset_group_cache_path, "wb") as file:

        pickle.dump(planon_asset_groups, file)