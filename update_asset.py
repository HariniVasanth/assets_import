
import os
import logging
import csv

from typing import Union
from typing import Tuple

from utils import logger

import planon

import utils.logger as logger


log = logging.getLogger(__name__)

# ============================================================
# SETUP
# ============================================================


# Planon API configuration
planon.PlanonResource.set_site(site=os.environ['PLANON_API_URL'])
planon.PlanonResource.set_header(jwt=os.environ['PLANON_API_KEY'])

item_groups = planon.ItemGroup.find()

tbd_group = next(item_group for item_group in item_groups if item_group.Name == 'To be determined')


import requests
log.debug("Setting up REST API session")
session = requests.Session()
session.params = {"accesskey": os.environ.get("PLANON_API_KEY")  }

# ============================================================
# FUNCTIONS
# ============================================================

def get_planon_location(property_code: str, space_number: str='') -> Tuple[int,Union[int,None]]:
    
    #Property Filter
    property_filter = {
        "filter": {
            "Code": {"eq": property_code}
        }
    }
    pln_properties = planon.Property.find(property_filter)
    if pln_properties:
        pln_property_id = pln_properties[0].Syscode
    else:
        raise Exception(f"No Planon property found for code {property_code}")

    #Space Filter
    if space_number:
        space_filter = {
            "filter": {
                "Code": {"eq": space_number},
                "PropertyRef": {"eq": pln_property_id},
            }
        }
        pln_spaces = planon.Space.find(space_filter)
        if pln_spaces:
            pln_space_id = pln_spaces[0].Syscode
        else:
            pln_space_id = None
    else:
        pln_space_id = None

    return (pln_property_id, pln_space_id)


# ============================================================
# MAIN
# Get the list of common assets between Famis & Planon in csv 
# Primary key will be Code which is already generated when the asset is created 
# concatenation between 2 or more field can act as PK
# Filter assets with the keys mentioned in asset_filter using find
# 
# ============================================================

AssetList = []
with open(file='input/load_common_assets.csv') as file:
    reader = csv.DictReader(file, delimiter=',')

    for row in reader:
            AssetList.append(row)

    failed = []
    success = []
  
    success_count=0
    fail_count=0
    nobarcode_count=0
    exception_count=0

for row in AssetList:
        
        log.info(f"Processing asset {row['CODE']} with {row['ASSET_TAG']} for {row['BUILDING_ID']} with {row['EQUIPMENT_NUMBER']}")
        try:        
            property_code = row['BUILDING_ID']
            space_number = row['ROOM']
            # blank= ""
            barcode = int(row['CODE']) if row['CODE'] else None #Primary key
            # barcode = int(row['ASSET_TAG']) if row['ASSET_TAG'] else None
            log.info(f"Found asset {row['CODE']}")

            if barcode:
                propertyRef, spaceRef = get_planon_location(property_code, space_number)

                # READ FILTER
                asset_filter = {
                        "filter": {
                            # "Code": {"eq": asset['CODE']}
                            # 'Code': {'eq': '0072340'},                           
                            'AssetTag': {'eq': row['ASSET_TAG']},
                            'Code': {'eq': row['CODE']}
                            
                        }
                }

                # UPDATE ASSETS
                (me_asset,) = planon.UsrMEAsset.find(asset_filter)

              
                me_asset.LegacyDescription =row['EQUIPMENT_NUMBER']   #LegacyDescription                
                me_asset.Name=row['DESCRIPTION']  #Description                
                me_asset.Dossier=row['CONCATENATION']  # Remark               
                me_asset.save() #save

                log.info(f"Updated {row['EQUIPMENT_NUMBER']},{row['DESCRIPTION']},{row['CONCATENATION']} for {row['CODE']}")
                
                # log.info(f"{mea_assets}")
                success_count+=1    
                    
            else:
                log.error('No barcode provided')
                failed.append({
                    'error': 'No barcode',
                    'asset': row
                })
                
                nobarcode_count+=1
                log.info(f"No barcode")
        except Exception as e:
            failed.append({
                'error': repr(e),
                'asset': row,
                
            })
            log.info(f"{repr(e)}")
            fail_count+=1

total_succeeded_assets = str((success_count))
total_failed_assets = str((fail_count))
total_nobarcode_assets = str((nobarcode_count))

log.info(f"Total number of assets_updated :  {total_succeeded_assets}")
log.info(f"Total number of assets failed t0 update :  {total_failed_assets}")
log.info(f"Total number ofwith no barcode :  {total_nobarcode_assets}")



