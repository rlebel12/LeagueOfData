"""
Creates two dictionaries located in the bin/ directory mapping championIDs to champion names
"""

import inspect
import database as db
import Header as H


def test():
    path = str(H.Path(H.os.getcwd()).parent) + '\data'
    champs = H.loadJSON(path, "champIdToName")
    ids = H.loadJSON(path, "champNameToId")
    '''x = input("Enter Champ ID: ")
    print(champs[x])
    x = input("Enter champ name: ")
    print(ids[x])'''

    conn = db.Connection()
    query = "INSERT INTO ChampCache (champ, patchMajor, patchMinor, region, totalWRStats) VALUES (%s, 7, %s, 'NA1', 0)"
    for id in champs.keys():
        for patch in [17,16]:
            conn.execute(query,(id,patch))


if __name__ == '__main__':
    url = ("https://na1.api.riotgames.com/lol/static-data/v3/" +
           "champions?locale=en_US&dataById=false")
    response = H.api_get(url).json()
    path = str(H.Path(H.os.getcwd()).parent) + "\data"
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
    H.saveFile(path, "champNameToId", "json", nameToId)
    H.saveFile(path, "champIdToName", "json", idToName)
