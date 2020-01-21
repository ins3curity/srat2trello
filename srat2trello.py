#!/usr/bin/env python3

import yaml
import requests
import os
import sys

import config

labels = {}

# usage
def usage():
    print("\n  Usage: {} filename\n".format(sys.argv[0]))
# Read YAML output from securityRAT tool


def import_requirements(filename):
    if not os.path.isfile(filename):
        print("Could not open {}".format(filename))
        sys.exit(1)

    with open(filename) as f:
        requirements = {}
        data = yaml.safe_load(f)
        for cat in data.get('requirementCategories'):
            for req in cat['requirements']:
                id          = req['shortName']
                description = req['description']
                strategy    = req['statusColumns'][0]['value']
                more_info   = req['optColumns'][0]['content'][0]['content']
                requirements[id] = [description, strategy, more_info]
    return requirements


def create_list(list_name):
    url = "https://api.trello.com/1/lists"
    list_name = "Security Requirements"
    querystring = {"name":list_name, "idBoard":config.board_id, "key":config.api_key, "token":config.api_secret}
    try:
        response = requests.request("POST", url, params=querystring)
    except:
        print("Could not create list")
    if response.status_code == 200:
        return response.json()["id"]
    else:
        print("Error creating list {}".format(list_name))
        sys.exit(1)


def create_requirements(requirements, list_id):
    # We need to get current labels and their IDs
    url = "https://api.trello.com/1/boards/" + config.board_id + "/labels"
    querystring = {"fields":"all","limit":"50","key":config.api_key,"token":config.api_secret}
    response = requests.request("GET", url, params=querystring)
    if response:
        for label in response.json():
            if label["color"] == None:
                labels[label["name"]] = (label["id"])

    # Create missing labels
    # We will create a label for each strategy
    for strategy in config.strategies:
        if strategy not in labels:
            url = "https://api.trello.com/1/labels"
            querystring = {"name":strategy,
                "color": None,
                "idBoard":config.board_id,
                "key":config.api_key,"token":config.api_secret}
            response = requests.request("POST", url, params=querystring)
            labels[strategy] = response.json()["id"]

    # Get current cards
    url = "https://api.trello.com/1/lists/" + list_id + "/cards"
    querystring = {"fields":"name,labels","key":config.api_key,"token":config.api_secret}
    response = requests.request("GET", url, params=querystring)

    # Create cards
    for id in requirements.keys():
        url = "https://api.trello.com/1/cards"
        card_name = str(id) + " " + requirements[id][0]
        querystring = {"name":card_name,
            "desc":requirements[id][2],
            "idList":list_id,
            "idLabels":labels[requirements[id][1]],
            "key":config.api_key,"token":config.api_secret}
        response = requests.request("POST", url, params=querystring)
        card_id = response.json()["id"]
        # Add comment to the card:
        url = "https://api.trello.com/1/cards/" + card_id + "/actions/comments"
        querystring = {"text":requirements[id][1],
          "key":config.api_key,"token":config.api_secret}
        print("Creating requirement: {}".format(card_name))
        response = requests.request("POST", url, params=querystring)


def attach_yaml_file(list_id, filename):
    # Create card
    url = "https://api.trello.com/1/cards"
    querystring = {"name": "Summary",
        "desc":"Security requirements YAML file",
        "idList":list_id,
        "key":config.api_key,"token":config.api_secret}
    response = requests.request("POST", url, params=querystring)
    card_id = response.json()["id"]
    # Add YAML file as attachment
    url = "https://api.trello.com/1/cards/" + card_id + "/attachments"
    querystring = {"key":config.api_key,"token":config.api_secret}
    files = {'file': open(filename, 'rb')}
    response = requests.request("POST", url, params=querystring, files=files)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        usage()
        sys.exit(1)
    filename = sys.argv[1]

    # Import requirements from file
    requirements = import_requirements(filename)

    # Create a list
    list_name = os.path.splitext(filename)[0]
    list_id = create_list(list_name)


    # Create cards
    create_requirements(requirements, list_id)
    attach_yaml_file(list_id, filename)
