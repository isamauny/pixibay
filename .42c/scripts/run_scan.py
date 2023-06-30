#!/usr/bin/env python3

import json
import argparse
import requests
import sys
import logging
#import subprocess
import os
import scan_v1_config
import scan_v2_config

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'DEBUG'))
log = logging.getLogger(__name__)  # __name__ is my_service.app, it will only log messages from this module

# A script to parse the audit report, find the list of APIs to be scanned and run the 
# scan for each of those

def retrieve_action_report (workspace_url :str, workflow_id: str):
  try:
      # Files are saved is the workspace 
      filename = f"{workspace_url}/audit-action-report-{workflow_id}.json"
      log.debug ("before open")
      with open(filename, 'r') as file:
          action_report_file = json.load (file)
      log.debug ("After open")
  except json.JSONDecodeError as e:
    print('Error: Invalid JSON in file')
    return None
  except FileNotFoundError as e:
    print('Error: File not found')
    return None
          
  report = action_report_file['audit']['report']
  sorted_report = sorted(report.items(), key=lambda x: x[1]['score'], reverse=True)

  return sorted_report


def gen_token (workspace_url:str, workflow_id:str):
   sorted_report = retrieve_action_report ()

   for item in sorted_report:
    uuid = item[1]['apiId']
    scan_v1_config.retrieveScanConf (uuid)


def setup():
   #Set platform endpoitn
   PLATFORM=sys.argv[0]     