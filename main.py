# Library imports
import pandas
import datetime
import re

# File imports
import elo
import data

# Constants
K = 20 # 0 - 50
MAJOR_ELO = 1500
NONMAJOR_ELO = 1200 # 900 - 1500
REGRESSION = 0.333 # 0.0 - 0.5
HOMEFIELD = 25 # 0 - 50

# Read the data
games = data.get_games()
games = games[games['Season']>=1977]
teams = data.get_teams()

# Do ELO
print(datetime.datetime.now())
all_teams = set(games['Home'])|set(games['Away'])
elos = pandas.Series(NONMAJOR_ELO,index=all_teams)
games['Result'] = (games['Home'] == games['Winner']) + 0.5*games['Winner'].isna()
seasons = games.groupby('Season')
season_indexes = sorted(seasons.groups.keys())
for s in season_indexes:
    print(s, datetime.datetime.now())
    seasongames = seasons.get_group(s)
    majorteams = set(teams[teams['Season']==s]['Team'])
    # Regress everyone to their group mean
    ismajor = pandas.Series(elos.index.isin(majorteams),index=elos.index)
    averages = ismajor*MAJOR_ELO + (~ismajor)*NONMAJOR_ELO
    elos += REGRESSION*averages - REGRESSION*elos
    elos.name = 'Elo'
    # Run this season's games
    weeks = seasongames.groupby('Week')
    week_indexes = sorted(weeks.groups.keys())
    for w in week_indexes:
        weekgames = weeks.get_group(w)
        data = weekgames.join(elos,how='left',on='Home')\
                .join(elos,how='left',on='Away',lsuffix='_home',rsuffix='_away')
        gamedeltas = elo.elodelta(data['Elo_home'],data['Elo_away'],data['Result'],K)
        gamedeltas.name = 'Delta'
        data = data.join(gamedeltas)
        homedelta = data.groupby('Home')['Delta'].sum()
        awaydelta = -data.groupby('Away')['Delta'].sum()
        delta = homedelta.add(awaydelta,fill_value=0)
        elos = elos.add(delta,fill_value=0)
        elos.name = 'Elo'
print(datetime.datetime.now())
