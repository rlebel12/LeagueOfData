from Recon.Utility import core
from Recon.Utility import database as db
from Recon.Utility import queue as Queue
import threading


def updatePlayerRank(players, target_player, target_found, queue, tier, region_base, region, league_id, verbose=False):
    updated = 0
    added = 0
    for player in players:
        div = db.division_from_api[player['rank']]
        player_id = int(player['playerOrTeamId'])
        if player_id == target_player:
            target_found = True
            queue.put(target_found)
        name = player['playerOrTeamName']
        if verbose:
            print("Adding/Updating: " + str(player_id))
        # Champion mastery stats, not currently in use, but was functional
        '''url = "https://" + region_base + ".api.riotgames.com/championmastery/location/" + region + "/player/" + player_id + "/champions?api_key=" + KEY
        masteryData = api_get(url).json()
        keys = ['chestGranted','championPoints','playerId','championPointsUntilNextLevel','championPointsSinceLastLevel','lastPlayTime','tokensEarned']
        for i in range(len(masteryData)):
            for key in keys:
                if key in masteryData[i]: del masteryData[i][key]
        #masteryData = json.dumps(masteryData)'''
        conn = db.Connection(0)
        action = conn.player_save(player_id, name,
                                      tier, div, region_base)
        conn.close()
        if action == 0:
            added += 1
        elif action == 1:
            updated += 1
    if verbose:
        print("Updated: " + str(updated))
        print("Added: " + str(added))
    return target_found


def getRanksFromLeague(region, player):
    queue = Queue.Queue()
    target_found = False
    url = "https://" + region.lower() + ".api.riotgames.com/lol/league/v3/positions/by-summoner/" + str(player)
    player_leagues = core.api_get(url)
    if player_leagues is None:
        return target_found
    league = player_leagues.json()
    region_base = region
    if region in ['BR', 'OC', 'JP', 'NA', 'EUN', 'EUW', 'TR']:
        region = region + "1"
    for each in league:
        if each['queueType'] != 'RANKED_SOLO_5x5':
            continue
        print("Pulling data from league.  This might take a little while...")
        tier = db.tier_from_api[each['tier']]
        league_id = each['leagueId']
        url = "https://" + region.lower() + ".api.riotgames.com/lol/league/v3/leagues/" + str(league_id)
        league_data = core.api_get(url).json()
        # Prepare for threading
        threads = []
        arrs = core.splitter(5, league_data['entries'])
        # target_found = updatePlayerRank(each['entries'], player, target_found, queue, tier,
                                # region_base, region)
        # print(("Creating threads to get player ranks in PID " + str(os.getpid()))
        for leaguePlayer in arrs:
            t = threading.Thread(target=updatePlayerRank,
                                   args=(leaguePlayer, player, target_found, queue,
                                         tier, region_base, region, league_id))
            # t.daemon = True
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        target_found = queue.get()

        '''
        for entry in each['entries']:
            div = entry['division']
            player_id = entry['playerOrTeamId']
            if player_id == player:
                target_found = 1
            name = entry['playerOrTeamName']

            # Champion mastery stats
            url = "https://" + region_base + ".api.riotgames.com/championmastery/location/" + region + "/player/" + player_id + "/champions?api_key=" + KEY
            masteryData = api_get(url).json()
            keys = ['chestGranted','championPoints','player_id','championPointsUntilNextLevel','championPointsSinceLastLevel','lastPlayTime','tokensEarned']
            for i in range(len(masteryData)):
                for key in keys:
                    if key in masteryData[i]: del masteryData[i][key]
            #masteryData = json.dumps(masteryData)
            #action = player_saveCRS(crs, player_id, name, tier, div, region_base, masteryData)


            action = player_saveCRS(crs, player_id, name, tier, div, region_base, None)
            if action == 0: added+=1
            elif action == 1: updated+=1
        #print(("Updated: " + str(updated))
        #print(("Added: " + str(added))
        '''
        break
    return target_found
