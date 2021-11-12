class FlatMonteCarloSimulation(object):

    def __init__(self, no_of_simulations):
        self.no_of_simulations = no_of_simulations

    def genmove(self, color):
        pass
        # TODO: checks all the position and gives them a score (runs simulate_score), then returns the best score move

    def simulate_score(self, move):
        pass
        # TODO: runs simulate function multiple times and evaluates the score on that move

    def simulate(self):
        pass
        # TODO: runs ONE simulation on the move that is selected.

    def undo(self):
        pass
        # TODO: undo last move

