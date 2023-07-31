import json
import re
import os
import requests

SHIELDS_IO_URL: str     = "https://img.shields.io"

def extractFilename (url: str):
    filename = os.path.basename(url)
    # Replace the dot with an underscore in the filename
    filename = filename.replace(".", "_")

    return filename

def renderBadge (text: str, status: str, color: str):
    # Use shields.io to render badges added to PR comment

    url =  f"{SHIELDS_IO_URL}/badge/{text}-{status}-{color}"
    response = requests.get(url)
    if response.status_code == 200:
      svg_payload = response.content.decode ('UTF-8')
    print (f'{svg_payload}')

    return svg_payload

renderBadge ("Audit_State", "Success", "green")

# # Read JSON data from file
# with open('audit-report.json', 'r') as file:
#     json_data = file.read()

# # Parse JSON data
# data = json.loads(json_data)

# # Extract apiID from each entry under the "report" field and store them in a dictionary
# report = data["audit"]["report"]
# api_ids = {extractFilename(key): report[key]["apiId"] for key in report}

# # Print the apiID for each entry
# for key, api_id in api_ids.items():
#     print(f"File: {key}, apiID: {api_id}")



   

