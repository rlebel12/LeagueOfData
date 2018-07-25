"""
Contains basic functions for performing database transactions
"""

from Recon.Utility import core
import pymysql
import json
import time
import datetime
import os


class Connection:
    def __init__(self, commit=1):
        tries = 0
        conn_info = json.loads(os.environ['RECON_DB_CONNECTION'])
        try:
            tries += 1
            self.db = pymysql.connect(
                host=conn_info['host'],
                user=conn_info['user'], port=conn_info['port'],
                password=conn_info['password'], db=conn_info['db'],
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=commit, charset='utf8')
        except:
            print("DB connection failed.\nStack: ")
            time.sleep(1)
            self.__init__()
        # print("Connection established (" + str(tries) + " attempts)")
        self.crs = self.db.cursor()
        self.commit = commit
        self.is_closed = False

    def __del__(self):
        if not self.is_closed:
            if self.commit == 0:
                self.db.commit()
            self.crs.close()
            self.db.close()
            self.is_closed = True

    def execute(self, *args):
        query = args[0]
        extra_args = False
        if len(args) > 1:
            extra_args = True
            variables = args[1]
        try:
            if extra_args:
                self.crs.execute(query, args[1])
            else:
                self.crs.execute(query)
            return self.crs.fetchall()
        except:
            error = sys.exc_info()
            error_insert_query = '''
            INSERT INTO ErrorLog(errorMsg, queryText, queryVariables)
            VALUES (%s, %s, %s)
            '''
            if extra_args:
                self.crs.execute(error_insert_query,
                                 (str(error), str(query), str(variables)))
            else:
                self.crs.execute(errInsert, (str(error), str(query), None))
            error_key_query = "SELECT LAST_INSERT_ID();"
            error_key = self.execute(error_key_query, ())[0]['LAST_INSERT_ID()']
            print("SQL Error Encountered.  errorKey: " + str(error_key))
            return None

    def player_save(self, id, name, tier, div, region):
        query = '''
        SELECT playerKey FROM Player WHERE region = %s AND summonerID = %s;
        '''
        results = self.execute(query, (region, id))
        if len(results) == 0:
            url = ("https://" + region +
                   ".api.riotgames.com/lol/summoner/v3/summoners/" +
                   str(id))
            playerInfo = core.api_get(url).json()
            accountID = playerInfo['accountId']
            query = '''
            INSERT INTO Player(summonerID, accountID, summonerName,
            tier, division, region)
            VALUES (%s, %s, %s, %s, %s, %s);
            '''
            self.execute(query, (id, accountID, name, tier, div, region))
            return 0
        else:
            update = '''
            UPDATE Player SET summonerName = %s, tier = %s,
            division = %s, lastUpdated = %s
            WHERE summonerID = %s AND region = %s
            '''
            self.execute(update, (name, tier, div,
                                  datetime.datetime.now(), id, region))
            return 1

    def player_get(self, id, region):
        query = '''
        SELECT * FROM Player
        WHERE summonerID = %s AND region = %s
        LIMIT 1
        '''
        return self.execute(query, (id, region))

    def players_elite_get(self, region):
        summList = []
        query = '''
        SELECT summonerID, accountID FROM Player
        WHERE region = %s AND tier >= 4
        ORDER BY tier DESC, lastUpdated ASC;
        '''
        summs = self.execute(query, (region))
        for each in summs:
            summList.append({'playerID': each['summonerID'],
                             'accountID': each['accountID']})
        return summList

    def games_elite_get(self, region):
        query = '''
        SELECT gameKey, gameID, dateAdded FROM Game
        WHERE rank >= 4
        AND patchMajor = %s AND patchMinor = %s AND region = %s
        ORDER BY dateAdded DESC
        '''
        return self.execute(
            query, (core.PATCH_MAJOR, core.PATCH_MINOR, region))

    def game_data_get(self, key):
        query = '''
        SELECT data from GameData
        WHERE gameKey = %s
        LIMIT 1;
        '''
        results = self.execute(query, (key))
        return json.loads(results[0]['data'])

    def game_save(self, id, rank, patch_major, patch_minor, region, data):
        query = '''
        INSERT INTO Game(gameID, rank, patchMajor, patchMinor, region)
        VALUES (%s,%s,%s,%s,%s);
        '''
        key_query = "SELECT LAST_INSERT_ID();"
        self.execute(query, (id, rank, patch_major, patch_minor, region))
        key = self.execute(key_query, ())[0]['LAST_INSERT_ID()']
        query = "INSERT INTO GameData(gameKey, data) VALUES (%s, %s)"
        self.execute(query, (key, data))
        return key

    def game_exists(self, id, region):
        query = '''
        SELECT patchMajor, patchMinor FROM Game
        WHERE region = %s AND gameID = %s
        LIMIT 1;
        '''
        results = self.execute(query, (region, id))
        if not results:
            return -1, -1
        else:
            results = results[0]
            return results['patchMajor'], results['patchMinor']

    def game_info_get(self, id, region):
        query = '''
        SELECT gameKey, rank FROM Game
        WHERE gameID = %s AND region = %s
        LIMIT 1;
        '''
        return self.execute(query, (id, region))

    # Checks to see if there are 10 rows in the stats table corresponding
    # to the given match.  If False, then not all stats have been added yet.
    def champ_stats_full(self, key):
        query = '''
        SELECT COUNT(*) AS 'count' FROM ChampStats
        WHERE gameKey = %s GROUP BY gameKey
        '''
        results = self.execute(query, (key))
        if len(results) > 0:
            results = results[0]
            if results['count'] == 10:
                return True
        else:
            return False

    # Used by stat cache function.  Finds all stat rows for given champion
    # from a given region on a given patch.
    def champ_stats_get(self, patchMajor, patchMinor, region, champ):
        query = '''SELECT s.* FROM Game g INNER JOIN ChampStats s
            ON g.gameKey = s.gameKey
            WHERE g.rank >= 4 AND g.patchMajor = %s
            AND g.patchMinor = %s
            AND g.region = %s AND s.champ = %s
            ORDER BY g.gameKey DESC;
            '''
        return self.execute(query, (core.PATCH_MAJOR,
                            core.PATCH_MINOR, region, champ))

    def champ_stats_save(self, game_key, champ_id, player_key, role,
                      duration, win, stats):
        query = '''
        INSERT INTO ChampStats (gameKey, champ, playerKey, role, duration,
        result, kills, deaths, assists, largestMultiKill,
        largestKillingSpree, totalTimeCrowdControlDealt,
        totalMinionsKilled, neutralMinionsKilled,
        neutralMinionsKilledTeamJungle, neutralMinionsKilledEnemyJungle,
        totalDamageDealtToChampions, goldEarned,
        totalHeal, totalDamageTaken, turretKills) VALUES %s
        '''
        # THIS ORDER MATTERS, MUST MATCH KEYS FROM addWinStats()!
        args = [game_key, champ_id, player_key, role, duration, win]
        for each in stats:
            args.append(each)
        args = tuple(args)
        self.execute(query, (args,))


division_from_db = {5: 'V', 4: 'IV', 3: 'III', 2: 'II', 1: 'I'}
tier_from_db = {
    1: 'BRONZE', 2: 'SILVER', 3: 'GOLD', 4: 'PLATINUM',
    5: 'DIAMOND', 6: 'MASTER', 7: 'CHALLENGER'
}
division_from_api = {v: k for k, v in division_from_db.items()}
tier_from_api = {v: k for k, v in tier_from_db.items()}
