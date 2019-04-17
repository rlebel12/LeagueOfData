"""
Creates two dictionaries located in the bin/ directory mapping itemIDs to item names
"""

from Recon import core

import os
import pathlib

def update():
    url = "https://global.api.pvp.net/api/lol/static-data/na/v1.2/item?api_key=" + core.KEY
    response = core.api_get(url).json()
    path = str(pathlib.Path(os.getcwd()).parent) + "\data"
    nameToId = {}
    idToName = {}
    for each in response['data']:
        try:
            itemName = response['data'][each]['name']
            nameToId[itemName] = each
            idToName[each] = itemName
        except KeyError: pass
    core.saveFile(path, "itemNameToId", "json", nameToId)
    core.saveFile(path, "itemIdToName", "json", idToName)
