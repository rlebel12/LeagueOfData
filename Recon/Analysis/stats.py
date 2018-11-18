"""
This module is responsible for the data aggregation
component of the application.
"""

from Recon.Aggregation import collect
from Recon.Utility import core
from Recon.Utility import database as db
import random
import multiprocessing
import threading
import json
import datetime

# TODO: Skip checking existing matches when collecting, rely on integrity
#       errors

changeTeam = {100: 0, 200: 1}
changeWin = {"Win": 1, "Fail": 0, "True": 1, "False": 0,
             bool(0): 0, bool(1): 1}
stat_keys_wanted = [
    'kills', 'deaths', 'assists', 'largestMultiKill',
    'largestKillingSpree',
    'totalTimeCrowdControlDealt', 'totalMinionsKilled', 'neutralMinionsKilled',
    'neutralMinionsKilledTeamJungle', 'neutralMinionsKilledEnemyJungle',
    'totalDamageDealtToChampions', 'goldEarned',
    'totalHeal', 'totalDamageTaken', 'turretKills']
# THIS ORDER MATTERS, MUST MATCH THE QUERY!!!


# Inserts stats into champion winrate table,
# taking dictionary containing list of wanted stats
def champ_stats_add(stats):
    print("Adding stats...")
    #print(stats)
    key = stats['game_key']
    lane = stats['lane']
    duration = stats['duration']
    win = stats['win']
    player_key = stats['player_key']
    champ_id = stats['champ_id']
    champ_stats = stats['champ_stats']
    conn = db.Connection()
    conn.champ_stats_save(key, champ_id, player_key, lane, duration, win, champ_stats)
    conn.close()

# For a list of matches, retrieves data for each match (either from my DB
# or using Riot API).  After retrieving data, parses out information
# to be used to track champion winrates.
def game_stats_add(games, region):
    for game in games:
        id = game
        #print(games.index(id))
        game_data, game_tier, game_key, players = collect.game_data_get(id, region)
        if game_data == -2:
            print("Returning to collect more matches...")
            del games
            return
        if game_data == -1:
            continue
        else:
            duration = game_data['gameDuration']
            for i in range(len(game_data['participants'])):
                try:
                    champ_stats = []
                    participant_data = game_data['participants'][i]
                    champ_id = participant_data['championId']
                    win = changeWin[participant_data['stats']['win']]
                    participant_id = participant_data['participant_id']
                    for participant in game_data['participantIdentities']:
                        if participant['participant_id'] == participant_id:
                            player_id = participant['player']['summonerId']
                            break
                    player_key = players[player_id]
                    lane = participant_data['timeline']['lane']
                    if lane == "BOTTOM":
                        role = participant_data['timeline']['role']
                        if role == "DUO_SUPPORT":
                            lane = "SUPPORT"
                        else:
                            lane = "BOT"

                    # For stat summary
                    '''champ_stats = {}
                    champ_stats_original = participant_data['stats']
                    for statKey in champ_stats_original:
                        if statKey not in wantedStatKeys:
                            continue
                        champ_stats[statKey] = champ_stats_original[statKey]'''
                    champ_stats_original = participant_data['stats']
                    for stat_key in stat_keys_wanted:
                        try:
                            champ_stats.append(champ_stats_original[stat_key])
                        except:
                            print("KEY NOT FOUND: " + stat_key)
                            raise "Error finding key"
                    # mastery = getChampMasteryCRS(
                    #   crs,player_id,region,
                    #   game_data['participants'][i]['championId'])
                    stats = {'game_key': game_key, 'champion': champ_id, 'duration': duration,
                             'win': win, 'lane': lane, 'player_key': player_key,
                             'champ_id': champ_id, 'champ_stats': champ_stats}
                    champ_stats_add(stats)
                except:
                    champ_stats.append(None)
                    continue


# Worker function for new threads (see below function)
def parse_stats_worker(games_master, region):
    conn = db.Connection()
    games_incomplete = []
    for game in games_master:
        full = conn.champ_stats_full(each['gameKey'])
        if not full:
            games_incomplete.append(each['gameID'])
    conn.close()
    game_stats_add(games_incomplete, region)


# Used to parse data from collected matches that have not been added to
# champion winrate table
def parse_stats(region):
    conn = db.Connection()
    games = conn.games_elite_get(region)
    conn.close()
    parse_stats_worker(games, region)
    core.sys.exit()  # TODO delete this and above line
    games_split = core.splitter(6, games)
    threads = []
    for game_group in games_split:
        thread = threading.Thread(target=parse_stats_worker,
                               args=(game_group, region))
        thread.daemon = True
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()
    # print("Done filling tracker.")
