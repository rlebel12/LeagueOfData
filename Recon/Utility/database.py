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
        self.delF = 0
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

    def __del__(self):
        if not self.delF:
            if self.commit == 0:
                self.db.commit()
            self.crs.close()
            self.db.close()
            self.delF = 1

    def execute(self, *args):
        query = args[0]
        argsFlag = 0
        if len(args) > 1:
            argsFlag = 1
            variables = args[1]
        try:
            if argsFlag:
                self.crs.execute(query, args[1])
            else:
                self.crs.execute(query)
            return self.crs.fetchall()
        except:
            e = sys.exc_info()
            errInsert = '''
            INSERT INTO ErrorLog(errorMsg, queryText, queryVariables)
            VALUES (%s, %s, %s)
            '''
            if argsFlag:
                self.crs.execute(errInsert,
                                 (str(e), str(query), str(variables)))
            else:
                self.crs.execute(errInsert, (str(e), str(query), None))
            getKey = "SELECT LAST_INSERT_ID();"
            errorKey = self.execute(getKey, ())[0]['LAST_INSERT_ID()']
            print("SQL Error Encountered.  errorKey: " + str(errorKey))
            return None

    def addOrUpdateSumm(self, id, name, tier, div, region):
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

    def getSumm(self, id, region):
        query = '''
        SELECT * FROM Player
        WHERE summonerID = %s AND region = %s
        LIMIT 1
        '''
        return self.execute(query, (id, region))

    # Returns list of all summoner IDs
    def getSumms(self, region):
        summList = []
        query = "SELECT * FROM Player WHERE region = %s LIMIT 1;"
        summs = self.execute(query, (region))
        for each in summs:
            summList.append(each['id'])
        return summList

    def getSummsComp(self, region):
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

    def getCompMatches(self, region):
        query = '''
        SELECT gameKey, gameID, dateAdded FROM Game
        WHERE rank >= 4
        AND patchMajor = %s AND patchMinor = %s AND region = %s
        ORDER BY dateAdded DESC
        '''
        return self.execute(
            query, (core.PATCH_MAJOR, core.PATCH_MINOR, region))

    def match_data_get(self, key):
        query = '''
        SELECT data from GameData
        WHERE gameKey = %s
        LIMIT 1;
        '''
        results = self.execute(query, (key))
        return json.loads(results[0]['data'])

    def match_add(self, id, rank, patchMajor, patchMinor, region, data):
        query = '''
        INSERT INTO Game(gameID, rank, patchMajor, patchMinor, region)
        VALUES (%s,%s,%s,%s,%s);
        '''
        getKey = "SELECT LAST_INSERT_ID();"
        self.execute(query, (id, rank, patchMajor, patchMinor, region))
        gameKey = self.execute(getKey, ())[0]['LAST_INSERT_ID()']
        insertData = "INSERT INTO GameData(gameKey, data) VALUES (%s, %s)"
        self.execute(insertData, (gameKey, data))
        return gameKey

    def match_exists(self, id, region):
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

    def match_info_get(self, id, region):
        query = '''
        SELECT gameKey, rank FROM Game
        WHERE gameID = %s AND region = %s
        LIMIT 1;
        '''
        return self.execute(query, (id, region))

    def match_stats_full(self, key):
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

    def getCompMatchesByChamp(self, patchMajor, patchMinor, region, champ):
        query = '''SELECT s.* FROM Game g INNER JOIN ChampStats s
            ON g.gameKey = s.gameKey
            WHERE g.rank >= 4 AND g.patchMajor = %s
            AND g.patchMinor = %s
            AND g.region = %s AND s.champ = %s
            ORDER BY g.gameKey DESC;
            '''
        return self.execute(query, (core.PATCH_MAJOR,
                            core.PATCH_MINOR, region, champ))

    def champ_stats_insert(self, key, champId, playerKey, role,
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
        args = [key, champId, playerKey, role, duration, win]
        for each in stats:
            args.append(each)
        args = tuple(args)
        self.execute(query, (args,))


divisionDB = {5: 'V', 4: 'IV', 3: 'III', 2: 'II', 1: 'I'}
tierDB = {
    1: 'BRONZE', 2: 'SILVER', 3: 'GOLD', 4: 'PLATINUM',
    5: 'DIAMOND', 6: 'MASTER', 7: 'CHALLENGER'
}
divisionAPI = {v: k for k, v in divisionDB.items()}
tierAPI = {v: k for k, v in tierDB.items()}
