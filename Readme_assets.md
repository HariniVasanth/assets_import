# Assets Import
Source venv/bin/activate
pip install -r requirements.txt

## Environment Setup
export INDEX_TOKEN_NAME="API"
export INDEX_TOKEN="**************" (Gitlab Cybeark package)
export INDEX_PROJECT_ID="2790"

### Main
```.env
export PLANON_API_URL="https://facilities-dev03.dartmouth.edu/sdk/system/rest/v1/"
export PLANON_API_KEY="**************"

### create_asset.py
This will create a new asset.
If you want to avoid the duplication os assets - asset tag will have to be set to Isunique :Yes
Field definer>Base assets> M&E Asset>AssetTag> IsUnique:Yes

## update_asset.py
This will update a already created  and exisiting asset .
update values should be added for assets found with filter asset_filter :
example: me_asset.LegacyDescription =row['EQUIP_NUMBER']