# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#
# 42Crunch Support - support@42crunch.com
# Tested with Python 3.9

# See README for instructions.

import sys
import json
import requests
import time
import base64
import os

CONTENT = {
            "host": "", 
            "security": {
            },
            "customHeaders":  {
                "target-url" : "",
            },
            "settings":{
                "memoryLimit": 2147483648,
                "memoryTimeSpan": 30,
                "maxIssue": 1000,
                "logger": "error",
                "securityDisabled": False
            },
            "flowrate":100,
            "maxScanTime": 3600
            }

def retrieveCollectionId():
    url = API_ENDPOINT + "/api/v1/collections/technicalName"

    headers = {"accept": "application/json", "X-API-KEY": credential}
    #headers = {"accept": "application/json", "Cookie": "sessionid="+credential}

    mapPayload = {}
    mapPayload["technicalName"]=collection_technical_name
    payload = json.dumps(mapPayload)

    r = requests.post(url, data=payload, headers=headers)

    if r.status_code != 200:
        raise Exception("Bad response code while retrieving collection Id: ", r.status_code)

    return r.json()["id"]

def retrieveApisUUIDs():
    url = API_ENDPOINT + "/api/v1/collections/"+ collection_id +"/apis"

    headers = {"accept": "application/json", "X-API-KEY": credential}
    #headers = {"accept": "application/json", "Cookie": "sessionid="+credential}

    r = requests.get(url, headers=headers)

    if r.status_code != 200:
        raise Exception("Bad response code while retrieving apis Ids: ", r.status_code)

    apis = []
    for c in r.json()['list']:
        apis.append(c['desc']['id'])

    return apis
    
def retrieveScanConf(api_uuid):
    url = API_ENDPOINT + "/api/v1/apis/"+ api_uuid +"/scanConfigurations"

    headers = {"accept": "application/json", "X-API-KEY": credential}
    #headers = {"accept": "application/json", "Cookie": "sessionid="+credential}

    r = requests.get(url, headers=headers)

    if r.status_code == 200: # configuration found
        return True, r.json()["tokenId"]
    elif r.status_code == 404: #configuration not found
        return False, ""
    else: # error
        raise Exception("Bad response code while retrieving scan config: ", r.status_code)

def createScanConf(api_uuid, config):
    url = API_ENDPOINT + "/api/v1/apis/" + api_uuid + "/scanConfigurations"

    headers = {"accept": "application/json", "X-API-KEY": credential}
    #headers = {"accept": "application/json", "Cookie": "sessionid="+credential}

    json_content = json.dumps(config).encode('utf-8')

    b64_content = base64.b64encode(json_content).decode('utf-8')
    data = json.dumps({'scanConfiguration': b64_content})

    r = requests.post(url, headers=headers, data=data)

    if r.status_code != 200:
        raise Exception("can't create scan config while creating scan conf: ", r.status_code)

def getReference(github_reference: str):
    
  BRANCH_PREFIX = "refs/heads/";
  TAG_PREFIX = "refs/tags/";
  PR_PREFIX = "refs/pull/";

  if (github_reference.startswith(BRANCH_PREFIX)):
    branch = github_reference[len(BRANCH_PREFIX):]
    return branch

  if (github_reference.startswith(TAG_PREFIX)):
    tag = github_reference[len(TAG_PREFIX):]
    return tag

  if (github_reference.startswith(PR_PREFIX)):
    pr_id = github_reference[len(PR_PREFIX):-len("/merge")]
    pr_info = f"PR:{pr_id}"
    return pr_info

def createSpecs(api_uuid):
    conf = CONTENT.copy()
    conf["customHeaders"]["target-url"] = target_url

    url = f"{API_ENDPOINT}/api/v1/apis/{api_uuid}/specs"

    payload = '{"filter": 256}'

    headers = {"accept": "application/json", "content-type": "application/json","X-API-KEY": credential}
    #headers = {"accept": "application/json", "content-type": "application/json","Cookie": "sessionid="+credential}

    r = requests.post(url, data=payload, headers=headers)
    if r.status_code != 200:
        raise Exception("can't read api specs: ", r.status_code)

    security_section =  r.json()["securitySchemes"]

    if security_section:
        for key in security_section.keys():
            if security_section[key]["type"] == "oauth2":
                security_section[key]["oAuthAccessToken"] = access_token
                del security_section[key]["apiKeyIn"]
                del security_section[key]["apiKeyName"]
            else:
                security_section[key]['apiKeyValue'] = access_token

        conf["security"] = security_section

    # We do not support multi-servers at this point.
    if len(sys.argv) == 8:
        conf["host"] = sys.argv[7]
    else:
        conf["host"] = r.json()["endpoints"][0]["url"]
    
    return conf


# -------------- Main Section ----------------------

API_ENDPOINT = "https://demolabs.42crunch.cloud"

if len(sys.argv) != 6:
    raise Exception("Bad number or args")

collection_repo_name = sys.argv[1]
collection_repo_branch = sys.argv[2]
credential = sys.argv[3]
access_token = sys.argv[4]
target_url = sys.argv[5]

collection_repo_reference = getReference(collection_repo_branch)
collection_technical_name = collection_repo_name+"@@"+ collection_repo_reference

collection_id = retrieveCollectionId()
apis_uuids = retrieveApisUUIDs()

for uuid in apis_uuids:
    config_found, token = retrieveScanConf(uuid)
    if not config_found:
        conf_specs = createSpecs(uuid) # create specs
        createScanConf(uuid, conf_specs) # upload specs
        time.sleep(2) #delay two seconds
        _, token = retrieveScanConf(uuid) # get token

#send to stdout
print(token)