import xml.etree.ElementTree as ET


class PlayoffsService(object):

    def __init__(self):
        pass

    @staticmethod
    def getByFile(filePath):
        tree = ET.parse(filePath)
        root = tree.getroot()
        playoffsList = []
        for item in root.findall("i"):
            playoffsId_Q = item.find("PlayoffsID").text
            name_J = item.find("Name_J").text
            name_F = item.find("Name_F").text
            name_E = item.find("Name_E").text
            matchSeason = item.find("MatchSeason").text
            leagueID = item.find("SclassID").text
            if item.find("IsGroup").text == "True":
                isGroup = 1
            else:
                isGroup = 0
            if item.find("IsCurrGroup").text == "True":
                isCurrGroup = 1
            else:
                isCurrGroup = 0
            groupNum = item.find("GroupNum").text
            numberSort = item.find("NumberSort").text
            countRound = item.find("CountRound").text
            playoffs = {'playoffsId_Q': playoffsId_Q, 'name_J': name_J, 'name_F': name_F, 'name_E': name_E,
                        'matchSeason': matchSeason, 'leagueID': leagueID, 'isGroup': isGroup,
                        'isCurrGroup': isCurrGroup,
                        'groupNum': groupNum, 'numberSort': numberSort, 'countRound': countRound}
            # print(playoffs)
            playoffsList.append(playoffs)
        return playoffsList
