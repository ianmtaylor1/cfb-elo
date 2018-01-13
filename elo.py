

def winprob(elo, oppelo):
    """Calculates the win probability for a competitor based on its and its 
    opponent's Elo.
    """
    return 1 / (1 + 10**((oppelo-elo)/400))
    
def elodelta(elo, oppelo, S, K):
    """Calculates the change in Elo when a competitor with elo plays a
    competitor with oppelo. K is the rating change constant. S indicates the
    outcome relative to the first competitor: 0=lose, 0.5=draw, 1=win
    The returned delta is *added* to competitor 1 and *subtracted* from
    competitor 2.
    """
    return K*(S-winprob(elo,oppelo))

def runlist(games, K, wincol='Winner', losecol='Loser', startelos=None,
            defaultelo=1500, addnew=None):
    """Compute Elo for a list games. Returns a dict-like of competitors' ratings.
    
    games - an *ordered* pandas DataFrame of games. One row is processed at a time.
    K - the rating change constant to use.
    wincol - the name of the column containing the game's winner.
    losecol - the name of the column containing the game's loser.
    startelos - dict-like structure with starting Elo ratings for competitors.
    defaultelo - Elo to use for a competitor who is not in startelos.
    addnew - whether to add any new competitors in games to the returned elos.
    """
    # Default behavior
    if startelos is None:
        startelos = {}
        addnew = True
    else:
        addnew = False
    # Create a copy of the original Elos to modify
    elos = startelos.copy()
    for game_idx in games.index:
        # Find competitor's Elo ratings, subbing default if necessary
        winner = games.loc[game_idx,wincol]
        loser = games.loc[game_idx,losecol]
        if winner in elos:
            winelo = elos[winner]
        else:
            winelo = defaultelo
        if loser in elos:
            loseelo = elos[loser]
        else:
            loseelo = defaultelo
        # Compute the delta, and apply it to the relevant competitors' ratings
        delta = _elodelta(winelo,loseelo,K)
        if (winner in elos) or (addnew == True):
            elos[winner] = winelo + delta
        if (loser in elos) or (addnew == True):
            elos[loser] = loseelo - delta
    return elos