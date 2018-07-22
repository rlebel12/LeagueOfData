"""
Creates two dictionaries located in the bin/ directory mapping championIDs to champion names
"""

from Recon.Utility import database as db
from Recon.Utility import core
import pathblib
import os



def update():
    url = ("https://na1.api.riotgames.com/lol/static-data/v3/" +
           "champions?locale=en_US&dataById=false")
    response = core.api_get(url).json()
    path = str(pathlib.Path(core.os.getcwd()).parent) + "\data"
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
