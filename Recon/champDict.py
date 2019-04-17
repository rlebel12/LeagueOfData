"""
Creates two dictionaries located in the bin/ directory mapping championIDs to champion names
"""

from Recon import database as db
from Recon import core

import pathlib
import os



def update():
    url = ("https://na1.api.riotgames.com/lol/static-data/v4/" +
           "champions?locale=en_US&dataById=false")
    response = core.api_get(url).json()
    path = str(pathlib.Path(core.os.getcwd())) + "\\Data"
    nameToId = {}
    idToName = {}
    conn = db.Connection()
    conn.execute("DELETE FROM ChampHash",)
    query = "INSERT INTO ChampHash (champID, champName) VALUES (%s, %s)"
    for each in response['data'].keys():
        data = response['data'][each]
        id = data['id']
        name = data['name']
        conn.execute(query, (id, name))
        nameToId[response['data'][each]['name']] = response['data'][each]['id']
        idToName[response['data'][each]['id']] = response['data'][each]['name']
    core.saveFile(path, "champNameToId", "json", nameToId)
    core.saveFile(path, "champIdToName", "json", idToName)
