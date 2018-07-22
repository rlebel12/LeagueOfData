"""
Creates two dictionaries located in the bin/ directory mapping itemIDs to item names
"""

from Vitals import *

if __name__ == '__main__'::
    url = "https://global.api.pvp.net/api/lol/static-data/na/v1.2/item?api_key=" + KEY
    response = api_get(url).json()
    path = str(Path(os.getcwd()).parent) + "\data"
    nameToId = {}
    idToName = {}
    for each in response['data']:
        try:
            itemName = response['data'][each]['name']
            nameToId[itemName] = each
            idToName[each] = itemName
        except KeyError: pass
    saveFile(path, "itemNameToId", "json", nameToId)
    saveFile(path, "itemIdToName", "json", idToName)

main()
