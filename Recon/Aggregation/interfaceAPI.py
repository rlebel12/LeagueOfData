from Recon.Utility import core
from Recon.Utility import database as db
from Recon.Utility import queue as Queue
import threading


def updatePlayerRank(summList, player, found, queue, tier, baseRegion, region, leagueID):
    updated = 0
    added = 0
    for entry in summList:
        div = db.divisionAPI[entry['rank']]
        playerID = int(entry['playerOrTeamId'])
        if playerID == player:
            found = 1
            queue.put(found)
        name = entry['playerOrTeamName']
        #print("Adding/Updating: " + str(playerID))

        # Champion mastery stats, not currently in use, but was functional
        '''url = "https://" + baseRegion + ".api.riotgames.com/championmastery/location/" + region + "/player/" + playerID + "/champions?api_key=" + KEY
        masteryData = api_get(url).json()
        keys = ['chestGranted','championPoints','playerId','championPointsUntilNextLevel','championPointsSinceLastLevel','lastPlayTime','tokensEarned']
        for i in range(len(masteryData)):
            for key in keys:
                if key in masteryData[i]: del masteryData[i][key]
        #masteryData = json.dumps(masteryData)'''
        conn = db.Connection(0)
        action = conn.addOrUpdateSumm(playerID, name,
                                      tier, div, baseRegion)
        #conn.__del__()
        del conn
        if action == 0:
            added += 1
        elif action == 1:
            updated += 1
    return found
    # print("Updated: " + str(updated))
    # print("Added: " + str(added))


def getRanksFromLeague(region, player):
    queue = Queue.Queue()
    found = -1
    foundF = -1
    url = "https://" + region.lower() + ".api.riotgames.com/lol/league/v3/positions/by-summoner/" + str(player)
    leagueData = core.api_get(url)
    if leagueData is None:
        return found
    league = leagueData.json()
    baseRegion = region
    if region in ['BR', 'OC', 'JP', 'NA', 'EUN', 'EUW', 'TR']:
        region = region + "1"
    for each in league:  # Only one loop
        if each['queueType'] != 'RANKED_SOLO_5x5':
            continue
        print("Pulling data from league.  This might take a little while...")
        tier = db.tierAPI[each['tier']]
        leagueID = each['leagueId']
        url = "https://" + region.lower() + ".api.riotgames.com/lol/league/v3/leagues/" + str(leagueID)
        leagueData = core.api_get(url).json()
        # Prepare for threading
        threads = []
        arrs = core.threader(5, leagueData['entries'])
        # found = updatePlayerRank(each['entries'], player, found, queue, tier,
                                # baseRegion, region)
        # print(("Creating threads to get player ranks in PID " + str(os.getpid()))
        for leaguePlayer in arrs:
            t = threading.Thread(target=updatePlayerRank,
                                   args=(leaguePlayer, player, found, queue,
                                         tier, baseRegion, region, leagueID))
            # t.daemon = True
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        found = queue.get()

        '''
        for entry in each['entries']:
            div = entry['division']
            playerID = entry['playerOrTeamId']
            if playerID == player:
                found = 1
            name = entry['playerOrTeamName']

            # Champion mastery stats
            url = "https://" + baseRegion + ".api.riotgames.com/championmastery/location/" + region + "/player/" + playerID + "/champions?api_key=" + KEY
            masteryData = api_get(url).json()
            keys = ['chestGranted','championPoints','playerId','championPointsUntilNextLevel','championPointsSinceLastLevel','lastPlayTime','tokensEarned']
            for i in range(len(masteryData)):
                for key in keys:
                    if key in masteryData[i]: del masteryData[i][key]
            #masteryData = json.dumps(masteryData)
            #action = addOrUpdateSummCRS(crs, playerID, name, tier, div, baseRegion, masteryData)


            action = addOrUpdateSummCRS(crs, playerID, name, tier, div, baseRegion, None)
            if action == 0: added+=1
            elif action == 1: updated+=1
        #print(("Updated: " + str(updated))
        #print(("Added: " + str(added))
        '''

    return found
