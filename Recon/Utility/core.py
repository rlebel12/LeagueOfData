"""
Contains basic utilities for entire application
"""

import urllib3
import requests
import json
import os
import time
import sys
import pathlib

urllib3.disable_warnings()

CURRENT_SEASON = 11
PATCH_MAJOR = 8
PATCH_MINOR = 15
LIMIT_10_SECOND = 500
LIMIT_10_MINUTE = 30000
KEY = os.environ['RECON_API_KEY']

# General getter for online JSON objects.  Keeps track of total calls and prints response codes
def api_get(url):
    headers = {"X-Riot-Token": KEY}
    response = requests.get(url, verify=False, headers=headers)

    # Double-checking rate limits using HTTP headers
    try:
        # check Method limits
        methodLimit = response.headers['X-Method-Rate-Limit'].split(':')
        methodCount = response.headers['X-Method-Rate-Limit-Count'].split(':')
        if methodCount[0] == methodLimit[0]:
            print("Method limit being reached.  Sleeping")
            time.sleep(2)
        # Check App limits
        limits = []
        limitCount = response.headers['X-App-Rate-Limit-Count'].split(',')
        for each in limitCount:
            limits.append(each.split(':'))
        if limitCount[0][0] == LIMIT_10_SECOND:
            print('About to hit 10-second rate limit.',
                  'Sleeping for 0.1 seconds.')
            print(response.headers['X-Method-Rate-Limit-Count'])
            time.sleep(0.1)
        if limitCount[1][0] == LIMIT_10_MINUTE:
            print('About to hit 10-minute rate limit.  Sleeping for 10 seconds.')
            print(response.headers['X-Method-Rate-Limit-Count'])
            time.sleep(10)
    except KeyError:
        pass
    if response.status_code == 403:
        print("Error 403.  Key potentially blacklisted.  Terminating process.")
        sys.exit()
    if response.status_code == 429:
        print("Rate limit reached.  X-Rate-Limit-Count: " + str(response.headers['X-Rate-Limit-Count']))
        if 'Retry-After' in response.headers:
            timer = int(response.headers['Retry-After'])
            if timer == 0:
                timer = 2
            print("Trying again in " + str(timer) + " seconds...")
            time.sleep(timer)
        else:
            print("Underlying service rate limit reached.  Trying again in 2 seconds...")
            time.sleep(2)
        response = api_get(url)
    if response.status_code == 500 or response.status_code == 503:
        print("Riot-side error " + str(response.status_code) + ".  Waiting 10 seconds, then trying again...")
        time.sleep(10)
        response = api_get(url)
    if response.status_code == 404:
        print("404: Not Found")
        return response
    if response.status_code != 200:
        print("Other error: " + str(response.status_code) + ".  Trying again in 10 seconds...")
        time.sleep(10)
        response = api_get(url)
    return response


def windowsDirToLinux(directory):
    directory = directory.split('\\')
    directory = '/'.join(directory)
    return directory


# Stores JSON object to given location
def saveFile(path, name, format, data):
    completeName = os.path.join(path, name+"."+format)
    with open(completeName, 'w') as file:
        if format == "json": json.dump(data, file)
        else: file.write(data)

#Loads file from given directory.
def loadJSON(directory, file):
    directory = directory + "\\" + file + ".json"
    try:
        with open(directory) as file:
            data = json.load(file)
    except FileNotFoundError:
        directory = windowsDirToLinux(directory)
        with open(directory) as file:
            data = json.load(file)
    return data

def getChampIdToNameDict():
    return loadJSON(str(pathlib.Path(os.getcwd())) + "\Data", 'champIdToName')

def getChampNameToIdDict():
    return loadJSON(str(pathlib.Path(os.getcwd())) + "\Data", 'champNameToId')


# Prepares groups of variables for threading (or multiprocessing)
def threader(numThreads, arrayToSplit):
    length = int(len(arrayToSplit)/numThreads)
    i = 0
    arrs = []
    while i != numThreads:
        j = i+1
        if j != numThreads:
            arrs.append(arrayToSplit[i*length:j*length])
        else:
            arrs.append(arrayToSplit[i*length:])
        i+=1
    return arrs

champMasterList = list(getChampNameToIdDict().keys())
