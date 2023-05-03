import logging

import utils.logger

import requests

# *****************************************************************************
#
# *****************************************************************************

log = logging.getLogger(__name__)

#
# *************************************************************************************************
# *
# *************************************************************************************************
#
def login_jwt(login_url, api_key, scopes=None):
    headers={'Authorization': api_key}

    if scopes:
        url = login_url + '?scope=' + scopes
    else:
        url = login_url

    # print("url = "+url)
    response = requests.post(url,headers=headers)
    response.raise_for_status()
    response_json = response.json()
    jwt = response_json["jwt"]
    if scopes:
        accepted_scopes = response_json["accepted_scopes"]
        log.info(f"accepted scopes={str(accepted_scopes)}")
        for scope in scopes.split(' '):
            if scope not in accepted_scopes:
                raise ValueError(f'A requested scope {scope} is not in the set of accepted scopes.')
    return jwt


#
# *************************************************************************************************
# *
# *************************************************************************************************
#
def delete_resource_change_message(jwt, resource_change_url, queue_name, message_id):

  headers={'Authorization': 'Bearer '+jwt,'Content-Type':'application/json'}
  url = resource_change_url + '/' + message_id
  response = requests.delete(url, headers=headers)
  response.raise_for_status()
  return True


#
# *************************************************************************************************
# *
# *************************************************************************************************
#
def get_resource_by_query(resource_url, jwt, query_dict={}):

    headers = {'Authorization': 'Bearer '+jwt,
               'Content-Type': 'application/json'}

    # account_status can be = active, inactive, pending
    page_size = 1000
    page_number = 1

    resource_documents = []
    done = False

    while not done:
        params = {}
        if page_number == 1:
            query_dict['pagesize'] = str(page_size)
            query_dict['page'] = str(page_number)
            params = query_dict
            continuation_key = ''
        else:
            params['continuation_key'] = continuation_key
            params['pagesize'] = str(page_size)
            params['page'] = str(page_number)

        log.info(f'getting page {str(page_number)} of results')

        log.info(f'calling get with url={resource_url}')

        response = requests.get(resource_url, headers=headers, params=params)
        response.raise_for_status()

        if page_number == 1:
            continuation_key = response.headers.get("x-request-id")
            total_count = int(response.headers.get("x-total-count"))
            log.info(f'retrieving x-total-count documents of {str(total_count)}')

        response_list = response.json()
        for i in range(len(response_list)):
            resource_documents.append(response_list[i])

        page_number = page_number + 1

        if len(response_list) == 0 or len(resource_documents) == total_count:
            done = True
    # end while

    if len(resource_documents) != total_count:
        raise Exception(f"Number of resource documents retrieved {str(len(resource_documents))} do not match total number in payload header {str(total_count)}")

    return resource_documents


#
# *************************************************************************************************
# *
# *************************************************************************************************
#
def get_person(jwt, people_url, netid):

    headers={'Authorization': 'Bearer '+jwt,'Content-Type':'application/json'}

    url = people_url + "/" + netid

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        if response.status_code == 404:
            return False
        else:
            raise

    return response.json()
