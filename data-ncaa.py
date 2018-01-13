import requests
import datetime
import bs4
import re
import urllib
import pandas
import time

def _delay_get(delay=1, *args, **kwargs):
    """Sleeps for delay seconds then calls requests.get"""
    time.sleep(delay)
    return requests.get(*args, **kwargs)
    

def _get_season_page(season,division):
    """Returns the page for all teams in the given division/year as a requests
    Response object.
    
    season - an integer
    division - one of 'FBS', 'FCS', 'D2', or 'D3'"""
    url = 'http://stats.ncaa.org/team/inst_team_list'
    division_codes = {'FBS':11,'FCS':12,'D2':2,'D3':3}
    params = {'sport_code': 'MFB',
              'conf_id': -1,
              'academic_year': int(season) + 1,
              'division': division_codes[division]}
    return requests.get(url, params=params)

def _get_team_urls(season,division):
    """Returns a pandas DataFrame of all teams and divisions each year, and
    a URL where to find the games for that team/year.
    
    season - an integer
    division - one of 'FBS', 'FCS', 'D2', or 'D3'"""
    # Get the text and url from the response
    response = _get_season_page(season,division)
    page_text = response.text
    soup = bs4.BeautifulSoup(page_text,'lxml')
    page_url = response.url
    # Create the dataframe of all teams in this division this year
    team_links = soup.find_all('a',href=re.compile('^/team/\d+'))
    teamnames = list(map(lambda x: x.get_text().strip(), team_links))
    teamurls = list(map(lambda x: urllib.parse.urljoin(page_url,x['href']), team_links))
    return pandas.DataFrame({'Team':teamnames,'Season':season,'Division':division,'URL':teamurls})
    # Crawl each team link and extract season data
    #gameslist = []
    #for tl in team_links:
    #    print('{} - {} - '.format(season,tl.get_text()),end='')
    #    linkurl = urllib.parse.urljoin(page_url,tl['href'])
    #    teamgames = _get_team_games(linkurl)
    #    teamgames['Team'] = tl.get_text()
    #    gameslist.append(teamgames)
    #    print('{} games'.format(len(teamgames)))
    #if len(gameslist) == 0:
    #    all_games = pandas.concat(gameslist)
    #else:
    #    all_games = pandas.DataFrame()
    #return teams, all_games.reset_index()[all_games.columns]
        
def _get_team_games(url):
    """Loads the page at url and returns a pandas DataFrame of games found there.
    The dataframe will be missing some information - most notably, the name of
    the team whose page this is. That will be added on by the calling function."""
    # What does an "empty" table look like?
    emptydf = pandas.DataFrame({'Date':[],'HomeAway':[],'Site':[],'Opponent':[],
                                'Result':[],'TeamPts':[],'OppPts':[],'Overtimes':[]})
    response = requests.get(url)
    page_text = response.text
    soup = bs4.BeautifulSoup(page_text,'lxml')
    # Find the appropriate table
    games_table = None
    table_candidates = soup.find_all('table',class_='mytable')
    for table in table_candidates:
        heading = table.find('tr',class_='heading')
        if 'Schedule/Results' in heading.get_text():
            games_table = table
            break
    else:
        # No games found on this page
        return emptydf
    # Now search our table for games
    rows = games_table.find_all('tr')
    if len(rows) < 3:
        # No games found on this page
        return emptydf
    games = []
    for r in rows[2:]: #ignore headers
        data = {}
        cells = r.find_all('td')
        # Check if there's enough data
        if len(cells) < 3:
            continue
        # Date in the first cell
        datestring = cells[0].get_text().strip()
        data['Date'] = datetime.datetime.strptime(datestring,'%m/%d/%Y').date()
        # Opponent and location in second cell
        oppstring = cells[1].get_text().strip()
        oppfilter = re.compile('^(@)?\s*(.+?)\s*(@.+?)?$')
        oppmatch = oppfilter.match(oppstring).groups()
        if oppmatch[0] is None:
            data['HomeAway'] = 'vs.'
        else:
            data['HomeAway'] = '@'
        data['Opponent'] = oppmatch[1]
        if oppmatch[2] is None:
            data['Site'] = ''
        else:
            data['Site'] = oppmatch[2]
        # Score and result in third cell
        scorestring = cells[2].get_text().strip()
        scorefilter = re.compile('^([WLTD])\s*(\d+)\s*-\s*(\d+)(?:\s*\((\d+)OT\))?')
        scorematch = scorefilter.match(scorestring)
        if scorematch is None:
            data['Result'] = None
            data['TeamPts'] = None
            data['OppPts'] = None
            data['Overtimes'] = None
        else:
            data['Result'] = scorematch.group(1)
            data['TeamPts'] = int(scorematch.group(2))
            data['OppPts'] = int(scorematch.group(3))
            data['Overtimes'] = 0 if scorematch.group(4) is None else int(scorematch.group(4))
        # Add this game to our list
        games.append(data)
    return pandas.DataFrame(games)



if __name__=='__main__':
    import itertools
    import os
    
    # Get the team pages URLS if we don't already have it
    teamurls_file = 'Data/NCAA/team_urls.csv'
    if not os.path.isfile(teamurls_file):
        years = range(2017,2001,-1)
        divisions = ['FBS','FCS','D2','D3']
        to_crawl = list(itertools.product(years,divisions))
        all_teams_list = []
        for y,d in to_crawl:
            print(y,d,end=' - ')
            seasonteams = _get_team_urls(y,d)
            all_teams_list.append(seasonteams)
            print('{} teams'.format(len(seasonteams)))
        all_teams = pandas.concat(all_teams_list)
        all_teams.to_csv(teamurls_file,index=False)
    else:
        print('\n{} already exists\n'.format(teamurls_file))
        
    # Get the games for each team and save them to individual team files
    allgames_file = 'Data/NCAA/games.csv'
    teamfiles_folder = 'Data/NCAA/TeamFiles/'
    if not os.path.isfile(allgames_file):
        all_teams = pandas.read_csv(teamurls_file)
        teamgames_list = []
        for i in all_teams.index:
            teamfile_name = '{}-{}-{}.csv'.format(all_teams.loc[i,'Team'],
                    all_teams.loc[i,'Season'],all_teams.loc[i,'Division'])
            teamfile = os.path.join(teamfiles_folder,teamfile_name)
            if not os.path.isfile(teamfile):
                print(all_teams.loc[i,'Team'], all_teams.loc[i,'Season'],
                        all_teams.loc[i,'Division'], all_teams.loc[i,'URL'],
                        end=' - ')
                teamgames = _get_team_games(all_teams.loc[i,'URL'])
                teamgames.to_csv(teamfile,index=False)
                print('{} games'.format(len(teamgames)))
            else:
                teamgames = pandas.read_csv(teamfile)
            # Add missing data elements
            teamgames['Team'] = all_teams.loc[i,'Team']
            teamgames['Season'] = all_teams.loc[i,'Season']
            teamgames_list.append(teamgames)
        all_games = pandas.concat(teamgames_list)
        all_games.to_csv(allgames_file,index=False)
    else:
        print('\n{} already exists\n'.format(allgames_file))
    