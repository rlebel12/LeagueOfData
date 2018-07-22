import Header as H
import database as db


# Updates every summoner that has not been updated in a week
def updateSumm(playerID, region):
    conn = db.Connection()
    select = '''
    SELECT * FROM Player
    WHERE id = %s, region = %s
    '''
    update = '''
    UPDATE Player
    SET tier = %s, division = %s, name = %s
    WHERE id = %s AND region = %s
    '''

    players = conn.execute(select, (playerID, region))
    for each in players:
        id = each['playerID']
        tier, division = conn.getPlayerRank(id,region)
        name = each['playerName'].encode('utf-8')
        if tier in ['CHALLENGER','MASTER']: pass
        print("Updating " + str(name) + ", ID: " + str(id) + ": " + tier)
        execute(crs, update,(tier,division,name,id,region))

    conn.__del__()


def updateSumms(region):
    db = connect()
    crs = db.cursor()

    select = '''
    SELECT playerID FROM players WHERE DATEDIFF(current_date(), lastUpdated) > 7 AND playerRegion = %s ORDER BY DATEDIFF(current_date(), lastUpdated) ASC;
    '''

    update = '''
    UPDATE players
    SET playerTier = %s, playerDivision = %s, playerName = %s, lastUpdated = CURRENT_TIMESTAMP
    WHERE playerID = %s AND playerRegion = %s
    '''

    execute(crs, select,(region))
    summs = crs.fetchall()
    for each in summs:
        id = int(each['playerID'])
        print("Updating player " + str(id))
        #print("Old data for " + each['playerName'] + ": " + each['playerTier'] + " " + each['playerDivision'])
        name, tier, div = H.getPlayerInfo(id, region)
        print("New data for " + name + ": " + tier + " " + div + "\n")
        execute(crs, update,(tier,div,name,id,region))
    crs.close()
    db.close()


# Clears old Master/Challenger entries, updates summoners already in table who are now M/C, then adds remaining M/C
def updateTopSumms(region):
    conn = db.connect()
    crs = conn.cursor()
    updated = 0
    added = 0

    delete = '''
    DELETE FROM Playerss
    WHERE (tier = 7 OR playerTier = 6) AND playerRegion = %s;
    '''

    getTop = '''
    SELECT * FROM Player
    WHERE (tier = 7 OR tier = 6) AND region = %s;
    '''

    add = '''
    INSERT INTO players(playerID, playerName, playerTier, playerRegion, playerDivision) VALUES (%s, %s, %s, %s, 'I')
    '''

    update = '''
    UPDATE players
    SET playerTier = %s, playerName = %s, playerDivision = 'I'
    WHERE playerID = %s
    '''

    print("Updating " + region + "...")

    topSumms = conn.execute(getTop, (region))
    allSummoners = getSumms(crs, region)
    masters = api_get("https://" + region + ".api.pvp.net/api/lol/" + region + "/v2.5/league/master?type=RANKED_SOLO_5x5&api_key=" + KEY).json()
    for each in masters['entries']:
        tier = 'MASTER'
        name = each['playerOrTeamName']
        id = int(each['playerOrTeamId'])
        if id in allSummoners:
            execute(crs, update,(tier, name, id))
            updated+=1
        else:
            allSummoners.append(id)
            execute(crs, add,(id, name, tier, region))
            added+=1
    print("Masters updated: " + str(updated))
    print("Masters added: " + str(added))
    updated = added = 0
    challengers = api_get("https://" + region + ".api.pvp.net/api/lol/" + region + "/v2.5/league/challenger?type=RANKED_SOLO_5x5&api_key=" + KEY).json()
    for each in challengers['entries']:
        tier = 'CHALLENGER'
        name = each['playerOrTeamName']
        id = int(each['playerOrTeamId'])
        if id in allSummoners:
            execute(crs, update,(tier, name, id))
            updated+=1
        else:
            allSummoners.append(id)
            execute(crs, add,(id, name, tier, region))
            added+=1
    print("Challengers updated: " + str(updated))
    print("Challengers added: " + str(added))
    crs.close()
    db.close()


def getCharacterTuples():
    conn = db.Connection()
    query = '''
    SELECT key, champ FROM ChampMatch
    ORDER BY key'''
    try:
        results = conn.execute(query)
        print("Character tuples worked")
    except db.pymysql.err.ProgrammingError as err:
        print("Programming error encountered: ")
        print(err)
    return results


def getHeraldEntities():
    db = connect()
    crs = db.cursor()

    query = '''
    SELECT matchKey FROM winlossheraldtracker
    ORDER BY matchKey'''

    execute(crs, query)
    results = crs.fetchall()
    crs.close()
    db.close()
    resultlist = []
    for each in results:
        resultlist.append(each['matchKey'])
    return resultlist


def getWardKeys():
    db = connect()
    crs = db.cursor()

    query = '''
    SELECT matchKey FROM wardWR
    ORDER BY matchKey'''

    execute(crs, query)
    results = crs.fetchall()
    crs.close()
    db.close()
    resultlist = []
    for each in results:
        resultlist.append(each['matchKey'])
    return resultlist


def getHeraldKeys():
    db = connect()
    crs = db.cursor()

    query = '''
    SELECT matchKey FROM heraldWR
    ORDER BY matchKey'''

    execute(crs, query)
    results = crs.fetchall()
    crs.close()
    db.close()
    resultlist = []
    for each in results:
        resultlist.append(each['matchKey'])
    return resultlist
