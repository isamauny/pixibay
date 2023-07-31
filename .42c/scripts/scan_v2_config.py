#!/usr/bin/env python3

import json
import base64
import argparse
import requests
import re
import sys
import time
#    import subprocess - Uncomment for AzureDevOps Integration
import os

def set_output(name, value):
    with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
        print(f'{name}={value}', file=fh)

def testUUID(token):
    return re.match("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", token)

def testConfName(name):
    return re.match ("^[a-zA-Z0-9_\-]{5,128}$", name)

def testFileName (filename):
    return re.match ("^[a-zA-Z0-9\s_\-\/\.]{5,256}$", filename)

def extractFilename (url: str):
    filename = os.path.basename(url)
    # Replace the dot with an underscore in the filename
    filename = filename.replace(".", "_")

    return filename

def retrieveUUIDsListFromAuditReport(reportLocation: str):
    with open(reportLocation, 'r') as file:
        json_data = file.read()

    # Parse JSON data
    data = json.loads(json_data)

    # Extract apiID from each entry under the "report" field and store them in a dictionary
    report = data["audit"]["report"]
    api_ids = {extractFilename(key): report[key]["apiId"] for key in report}
    return api_ids

# This call updates a named scan configuration
def update_config(token: str, name: str, aid: str, workspace_location: str, scanconf_filename: str):
    url =  f"{PLATFORM}/api/v2/apis/{aid}/scanConfigurations"
    headers = {"accept": "application/json", "X-API-KEY": token}
    
    #Initialize scan token value
    scan_token = None

    # Build scanconf URL
    # Assumes scan configuration is stored under ./42c/scan/API_REF/scanconf.json
    scanconf_url = f"{workspace_location}/.42c/scan/{scanconf_filename}/scanconf.json"

    #Load file and base64 encode it.
    try:
        contents = open(scanconf_url, 'r')
        b64encoded_scanconf = base64.b64encode(contents.read().encode('utf-8')).decode('utf-8')
    finally:
        contents.close()

    payload = {"name": name, "file": b64encoded_scanconf }
    response = requests.post(url, data=json.dumps(payload), headers=headers) 

    if response.status_code != 200:
        print(f"Error: unable to update scan configuration {response.status_code}")
    else:
        # Let's retrieve the configuration and make sure its valid.
        # Get the async task ID - It will help us making sure we are viewing the new conf details.
        taskId = response.json()['id']

        if not quiet: print("[*] Verifying Scan Configuration...")
        conf_id = retrieve_config_id (token, name, aid)
        url =  f"{PLATFORM}/api/v2/scanConfigurations/{conf_id}"
        headers = {"accept": "application/json", "X-API-KEY": token}

        # local variables
        found_config = False
        # Initialize loop
        loop_counter = 0
        while not found_config:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                print(f"Error: unable to retrieve scan configuration details - Error Code: {response.status_code}")
                sys.exit(1)
            else:
                loop_counter+=1
                if debug: print(f"TaskID retrieval attempt #{loop_counter}")
                if response.json()['taskId'] == taskId:
                    found_config = True
                    break
                if loop_counter == 3:
                    print(f"Error: unable to find new configuration information.  Exiting")
                    sys.exit(1)
            time.sleep(.5)

        # If we get here, the conf report is for the conf we just updated.
        is_config_valid = response.json()['valid']
        scan_token = response.json()['token']
        if is_config_valid:
            if not quiet: print("[*] Configuration is valid and can be used")
        else:
            if not quiet: print("[*] Configuration is not valid - Printing report")
            #Load report and base64 decode it.
            report_filename = f"scanconf_analysis_report_{name}.json"
            report = response.json()['reportFile']
            contents = json.loads(base64.decodebytes(report.encode("utf-8")))
            try:
                with open (report_filename, 'w') as outfile:
                    json.dump (contents, outfile, indent=2)
                if not quiet: print(f"Saved scan configuration analysis report as: {report_filename}")
                if quiet: print(f"{report_filename}")
                if not quiet: print("[*] Done")
                sys.exit(1)
            finally:
                outfile.close()
    return scan_token

def retrieve_config_id(token: str, name: str, aid: str):
    # TODO: Validate name format
    # We need to use this call to retrieve the list of scan ids from the scan conf name.
    scan_conf_id = ""
    loop_counter = 0
    found_config_id = False
    url =  f"{PLATFORM}/api/v2/apis/{aid}/scanConfigurations"
    headers = {"accept": "application/json", "X-API-KEY": token}

    while not found_config_id:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Error: unable to retrieve scan lists {response.status_code}")
            return None
        else:
            loop_counter+=1
            if debug: print(f"ConfigID retrieval attempt #{loop_counter}")
            for c in response.json()['list']:
                if debug: print(f"Config Response: {c['configuration']['name']} is {c['configuration']['id']}")
                if c['configuration']['name'] == name:
                    scan_conf_id = c['configuration']['id']
                    found_config_id = True
                    break
                if loop_counter == 10:
                    print(f"Error: unable to find a scan configuration for name {name}.  Exiting")
                    sys.exit(1)
            time.sleep(.5)
    return scan_conf_id

def main():
    parser = argparse.ArgumentParser(
        description='42Crunch Update Scan Configuration'
    )
    parser.add_argument('APITOKEN',
                        help="42Crunch API token")
    parser.add_argument('audit_report_location',
                        help='Location of report generated by audit execution')
    parser.add_argument('workspace_location',
                        help="location of files")
    parser.add_argument('-n', "--config-name",
                        default="DefaultConfig",
                        help="Scan configuration friendly name", required=False)
    parser.add_argument('-p', '--platform', 
                        required=False, 
                        default='https://platform.42crunch.com', 
                        help="Default is https://platform.42crunch.com",
                        type=str)
    parser.add_argument('-q', "--quiet",
                        default=False,
                        action="store_true",
                        help="Quiet output. If invalid config, prints config error report file name")
    parser.add_argument('-d', '--debug',
                        default=False,
                        action="store_true",
                        help="debug level")
    parsed_cli = parser.parse_args()

    global quiet, debug, PLATFORM

    quiet = parsed_cli.quiet
    debug = parsed_cli.debug
    apitoken = parsed_cli.APITOKEN
    scanconf_name = parsed_cli.config_name
    scanconf_location = parsed_cli.workspace_location
    PLATFORM = parsed_cli.platform
    
    if not testConfName(scanconf_name):
        print("Error, wrong conf name - Only lowercase, uppercase, numbers, _ and - are accepted.")
        sys.exit(1)

    if not quiet: print(f"[*] Connecting to platform {PLATFORM}")
    if not quiet: print("[*] Updating Scan Configuration...")

    apis_list = retrieveUUIDsListFromAuditReport (parsed_cli.audit_report_location)
    for scanconf_ref, api_id in apis_list.items():
        scan_token = update_config (apitoken, scanconf_name, api_id, scanconf_location,scanconf_ref)
        print (scan_token)
        # Uncomment this for integration with GitHub actions
        set_output (f'{scanconf_ref}_TOKEN', {scan_token} )
    # Uncomment this for integration with Azure DevOps
    #subprocess.Popen(["echo", "##vso[task.setvariable variable=SCANV2_TOKEN;isoutput=true]{0}".format(scan_token)])
    
    if not quiet: print("[*] Done!")

# -------------- Main Section ----------------------
if __name__ == '__main__':
    main()
