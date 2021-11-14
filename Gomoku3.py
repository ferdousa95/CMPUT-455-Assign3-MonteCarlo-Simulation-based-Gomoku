import random

from board import GoBoard
import traceback
from sys import stdin, stdout, stderr
from board_util import (
    GoBoardUtil,
    BLACK,
    WHITE,
    EMPTY,
    BORDER,
    PASS,
    MAXSIZE,
    coord_to_point,
)


class FlatMonteCarloSimulation:
    color_scheme = {
        "b": BLACK,
        "B": BLACK,
        "w": WHITE,
        "W": WHITE
    }

    def __init__(self):
        """
        Gomoku player select moves randomly from the set of legal moves and simulate the chances of winning in each
        position in a round.
        Then returns the recommendation of here to play in this round.
        """
        self.board = GoBoard(7)

    def recommend_a_move_for(self, color):
        """
        Get moves goes over all the empty points and create a score for all of them, and then returns the best scored
        position as recommendation.

        Parameters
        ----------
        color - our player

        Returns - the recommended position
        -------

        """
        moves = self.board.get_empty_points()
        numMoves = len(moves)
        higherStates = numMoves + numMoves  # padding values cause the total number of values to increase
        score = [0] * higherStates

        # the board position is the array index, so pos=9's score is stored in score[9]
        for i in range(numMoves):
            pos = int(moves[i])
            score[int(pos)] = self.simulate_score(color, pos)

        bestIndex = score.index(max(score))
        assert bestIndex in self.board.get_empty_points()

        return bestIndex

    def simulate_score(self, color, move):
        """
        move is a specific move from where we need to run the simulation, so after playing one round on move, we
        simulate 10 times to get an average chance of winning for the current player
        ----------
        move - the move we want to evaluate the score

        Returns - the evaluated score for @param move.
        -------

        """
        our_player = self.color_scheme[color]
        stats = [0] * 3
        TOTAL_SIMULATION = 10
        self.board.play_move(move, self.board.current_player)  # 1 ply sim so first round is fix
        all_moves = self.board.get_empty_points()

        # run sim and keep the total score
        for simulation in range(10):
            winner = self.simulate()
            stats[winner] = stats[winner] + 1

            # getting all the moves that were used in previous simulation
            leftover_moves = self.board.get_empty_points()
            undo_moves = set(all_moves) - set(leftover_moves)
            self.undo_multiple(list(undo_moves))

        assert sum(stats) == TOTAL_SIMULATION
        self.board.undo(move)
        # Current player winning chance if he plays the @param - move
        result = (stats[self.board.current_player] + 0.5 * stats[EMPTY]) / TOTAL_SIMULATION
        if our_player != self.board.current_player:
            return 1 - result
        return result

    def undo_multiple(self, list_of_moves):
        """
        Takes all the moves that needs to be undone. And loops to undo them

        Parameters
        ----------
        list_of_moves - all the undo moves

        Returns - nothing
        -------

        """
        for move in list_of_moves:
            self.board.undo(move)

    def simulate(self):
        """
        Runs one simulation of the game till end by randomly assigning values for both player and then evaluating
        who won the round.

        Returns - For Black - 1
                  For White - 2
                  For Draw -  0
        -------

        """
        if self.board.detect_five_in_a_row() == EMPTY and \
                len(self.board.get_empty_points()) != 0:  # the game is not over

            all_moves = self.board.get_empty_points()
            all_moves = list(all_moves)
            random.shuffle(all_moves)
            while self.board.detect_five_in_a_row() == EMPTY and len(all_moves) != 0:
                self.board.play_move(all_moves[-1], self.board.current_player)
                all_moves[0] = all_moves[-1]
                all_moves.pop()
        return self.board.detect_five_in_a_row()

    def print_board(self):
        """
        Prints the board
        """
        print(str(GoBoardUtil.get_twoD_board(self.board)))
        print("\n")


run = FlatMonteCarloSimulation()
run.recommend_a_move_for("w")
