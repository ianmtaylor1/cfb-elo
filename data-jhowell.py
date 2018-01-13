import requests
import urllib
import time
import bs4
import lxml
import pandas
import re
import datetime
import os

def _pullandsave(url,savedir,throttle):
    """Fetches a webpage, saves the HTML under savedir (using the page's
    filename), and returns a BeautifulSoup object of the page."""
    # Note: this can't handle pages with no filename at the end 
    # (e.g. http://www.google.com/mail/) Fortunately this website doesn't have those.
    time.sleep(throttle)
    page = requests.get(url)
    urltail = urllib.parse.urlsplit(url).path[1:]
    filepath = os.path.join(savedir,urltail)
    os.makedirs(os.path.split(filepath)[0],exist_ok=True)
    with open(filepath,'w',errors='replace') as f:
        f.write(page.text)
    return bs4.BeautifulSoup(page.text,'lxml')

def _crawl(waittime,savedir):
    """Crawls Jim Howell's website and: 1) saves all the raw pages to an archive
    folder, 2) parses all the tables into a format that's usable by elo and
    saves that as a CSV. All saving is done uder the directory passed in as
    saveto."""
    # Make the directory into which we will save everything
    # Get the main page
    mainpage = 'http://www.jhowell.net/cf/scores/byName.htm'
    soup = _pullandsave(mainpage,savedir,waittime)
    # Save the notes page for good measure
    notespage = 'http://www.jhowell.net/cf/scores/Notes.htm'
    _ = _pullandsave(notespage,savedir,waittime)
    # Follow all the links on the page, parsing each one
    links = soup.find_all('a')
    gamedata = []
    for link in links:
        linkurl = urllib.parse.urljoin(mainpage,link.get('href'))
        if linkurl[:7] != 'mailto:':
            linksoup = _pullandsave(linkurl,savedir,waittime)
            pagedata = _parsepage(linksoup)
            gamedata += pagedata
    rawgamedf = pandas.concat(gamedata)
    rawgamedf = rawgamedf.reset_index()[rawgamedf.columns]
    rawgamedf.to_csv(os.path.join(savedir,'rawgames.csv'),index=False)
    return rawgamedf

def _parsepage(soup):
    """Takes a page's soup and returns a list of pandas DataFrames of <table>s
    in the page that contained game data."""
    # Find all tables and parse them for game info
    tables = soup.find_all('table')
    pagedata = []
    for t in tables:
        pagedata.append(_parsetable(t))
    return pagedata

def _colorverified(rgb):
    if rgb=='#00FF00':
        return 'V'
    elif rgb=='#FFFF00':
        return 'D'
    elif rgb=='#FF0000':
        return 'N'
    else:
        return ''
    
def _parsetable(table):
    """Parses a <table> element from a page's soup into a pandas DataFrame,
    doing minimal processing (usually just .strip())"""
    rows = table.find_all('tr')
    # Find the header text
    header = rows[0].text.strip()
    if header == 'Key':
        return None
    parsed_header = re.search('(\d+)\s*-\s*(.*?)\s*\(([^()]+)\)$',header)
    season = int(parsed_header.group(1))
    team = parsed_header.group(2)
    conference = parsed_header.group(3)
    # Get data from each of the rows (except header and total)
    gamelist = []
    gamenum = 0
    for r in rows[1:-1]:
        gamenum += 1
        info = {'Season':season, 'Team':team, 'Conference':conference, 'GameNum':gamenum}
        cells = r.find_all('td')
        info['MonthDay'] = cells[0].text.strip()
        info['MonthDay_verified'] = _colorverified(cells[0].get('bgcolor'))
        info['HomeAway'] = cells[1].text.strip()
        info['HomeAway_verified'] = _colorverified(cells[1].get('bgcolor'))
        info['Opponent'] = re.sub('^[*+]|\s*\([^()]*\)$','',cells[2].text.strip())
        info['Opponent_verified'] = _colorverified(cells[2].get('bgcolor'))
        info['Result'] = cells[3].text.strip()
        info['Result_verified'] = _colorverified(cells[3].get('bgcolor'))
        info['TeamPts'] = cells[4].text.strip()
        info['TeamPts_verified'] = _colorverified(cells[4].get('bgcolor'))
        info['OppPts'] = cells[5].text.strip()
        info['OppPts_verified'] = _colorverified(cells[5].get('bgcolor'))
        if len(cells) > 6:
            info['Site'] = cells[6].text.strip()
            info['Site_verified'] = _colorverified(cells[6].get('bgcolor'))
        else:
            info['Site'] = ''
            info['Site_verified'] = ''
        if len(cells) > 7:
            info['Notes'] = cells[7].text.strip()
            info['Notes_verified'] = _colorverified(cells[7].get('bgcolor'))
        else:
            info['Notes'] = ''
            info['Notes_verified'] = ''
        gamelist.append(info)
    return pandas.DataFrame(gamelist)

    
def clean_raw(rawgames):
    """Transforms a 'raw game' dataframe as returned by _crawl() and transforms
    it into a standard format."""
    # Process the header
    def splitheader(h): return re.search('(\d+)\s*-\s*(.*?)\s*\(([^()]+)\)$',h)
    parsed_header = rawgames['Header'].map(splitheader)
    season = parsed_header.map(lambda x: int(x.group(1)))
    team = parsed_header.map(lambda x: x.group(2))
    conference = parsed_header.map(lambda x: x.group(3))
    # Extract the opponent
    def getopp(x): return re.sub('^[*+]|\s*\([^()]*\)$','',x)
    opponent = rawgames['Opponent'].map(getopp)
    # Date
    month = rawgames['MonthDay'].map(lambda x: int(x.split("/")[0]))
    day = rawgames['MonthDay'].map(lambda x: int(x.split("/")[1]))
    year = (month >= 8)*season + (month < 8)*(season + 1)
    dateparts = pandas.DataFrame({'month':month,'day':day,'year':year})
    gamedate = dateparts.apply(lambda r: datetime.date(r.year,r.month,r.day), axis=1)
    # Location
    neutralsite = (rawgames['Site'].fillna('') != '')
    home = (rawgames['HomeAway'] == 'vs.')
    # Points and Result
    teampoints = rawgames['TeamPts'].map(int)
    opppoints = rawgames['OppPts'].map(int)
    win = (rawgames['Result'] == 'W')
    lose = (rawgames['Result'] == 'L')
    # CONSTRUCT THE GAMES DF
    games = pandas.DataFrame(index=rawgames.index,
                             columns=['Date','Season','Home','Away','Winner',
                                      'HomePts','AwayPts','NeutralSite'])
    games['Season'] = season
    games['Date'] = gamedate
    teamishome = ((~neutralsite)&home)|(neutralsite&(team<opponent))
    games['Home'] = teamishome*team + (~teamishome)*opponent
    games['Away'] = teamishome*opponent + (~teamishome)*team
    games['HomePts'] = teamishome*teampoints + (~teamishome)*opppoints
    games['AwayPts'] = teamishome*opppoints + (~teamishome)*teampoints
    games['Winner'] = win*team + lose*opponent
    games['NeutralSite'] = neutralsite
    games = games.drop_duplicates().reset_index()[games.columns]
    # CONSTRUCT TEAMS DF
    teams = pandas.DataFrame({'Team':team,'Season':season,'Conference':conference})
    teams = teams.drop_duplicates().reset_index()[teams.columns]
    return games,teams

if __name__=='__main__':
    ###
    # If run as a program, crawl the web for the latest data, parse, and save
    # as CSVs.
    ###
    rawgames = _crawl(1,'Data/jhowell')
    #rawgames = pandas.read_csv('Data/2018-01-03-150026/rawgames.csv')
    #games,teams = clean_raw(rawgames)
    #games.to_csv('Data/games.csv',index=False)
    #teams.to_csv('Data/teams.csv',index=False)