import random
import re
from board import GoBoard
import traceback
from gtp_connection import GtpConnection
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
        "W": WHITE,
        1: BLACK,
        2: WHITE
    }

    def __init__(self, board):
        """
        Gomoku player select moves randomly from the set of legal moves and simulate the chances of winning in each
        position in a round.
        Then returns the recommendation of here to play in this round.
        """
        self.board = board
        
    def get_move(self, board, color):
        return GoBoardUtil.generate_random_move(board, color)
    
    def genmove(self, policy, color):
        """
        Get moves goes over all the empty points and create a score for all of them, and then returns the best scored
        position as recommendation.

        Parameters
        ----------
        color - our player

        Returns - the recommended position
        -------

        """
        throwaway, moves = self.get_rule_moves(policy)
        numMoves = len(moves)
        higherStates = numMoves + numMoves  # padding values cause the total number of values to increase
        score = [0] * higherStates

        # the board position is the array index, so pos=9's score is stored in score[9]
        for i in range(numMoves):
            pos = int(moves[i])
            score[int(pos)] = self.simulate_score(color, pos, policy)

        bestIndex = score.index(max(score))
        assert bestIndex in self.board.get_empty_points()

        return bestIndex

    def simulate_score(self, color, move, policy):
        """
        move is a specific move from where we need to run the simulation, so after playing one round on move, we
        simulate 10 times to get an average chance of winning for the current player
        ----------
        move - the move we want to evaluate the score

        Returns - the evaluated score for @param move.
        -------

        """
        print(color)
        our_player = self.color_scheme[color]
        stats = [0] * 3
        TOTAL_SIMULATION = 10
        self.board.play_move(move, self.board.current_player)  # 1 ply sim so first round is fix
        all_moves = self.get_rule_moves(policy)

        # run sim and keep the total score
        for simulation in range(10):
            winner = self.simulate(policy)
            stats[winner] = stats[winner] + 1

            # getting all the moves that were used in previous simulation
            leftover_moves = self.get_rule_moves(policy)
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

    def simulate(self, policy):
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

            all_moves = self.get_rule_moves(policy)
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

    def random(self):
        return self.get_move(self.board, self.board.current_player)

    def get_win(self, line_of_stones, pattern):
        score_list = []
        index_to_play = []
        one_winning_move_pattern = pattern
        # Get each rows

        for r in line_of_stones:
            # Get each stone in a row
            for values in r:
                score_list.append(self.board.get_color(values))

            list_to_string = "".join(map(str, score_list))

            # match each pattern in the text
            for pattern in one_winning_move_pattern:
                match_object = re.search(pattern, list_to_string)
                # if pattern is present inside a text
                if pattern in list_to_string:
                    index_start = match_object.span()[0]
                    index_end = match_object.span()[1]
                    # process the match
                    for i in range(index_start, index_end):
                        if score_list[i] == 0:
                            index_to_play.append(r[i])

            score_list.clear()

        if not index_to_play:
            return None
        else:
            return index_to_play

    def win_wrapper(self):
        if self.board.current_player == BLACK:
            pattern = ['11110', '11101', '11011', '10111', '01111']
        else:
            pattern = ['22220', '22202', '22022', '20222', '02222']

        row_value = self.get_win(self.board.table_rows(), pattern)
        col_value = self.get_win(self.board.table_cols(), pattern)
        diag_value = self.get_win(self.board.table_diags(), pattern)
        total_pos = []
        if row_value is not None:
            row_value = list(set(row_value))
            for row in row_value:
                total_pos.append(row)

        if col_value is not None:
            col_value = list(set(col_value))
            for col in col_value:
                total_pos.append(col)
            
        if diag_value is not None:
            diag_value = list(set(diag_value))
            for diag in diag_value:
                total_pos.append(diag)

        if total_pos is not None:
            return total_pos
        else:
            return None

    def block_win(self):
        self.board.current_player = GoBoardUtil.opponent(self.board.current_player)
        win_list = self.win_wrapper()
        self.board.current_player = GoBoardUtil.opponent(self.board.current_player)
        return win_list

    def has_open_four_in_list(self, list, player):
        """
        Returns a list of open four moves if any open fours for the current player exist in the list.
        Returns an empty list otherwise.
        """
        moves = []

        # list_len = len(list)
        pattern = ""
        # use the counter to determine the playable positions
        counter = -1
        for stone in list:
            counter += 1
            if self.board.get_color(stone) == GoBoardUtil.opponent(player):
                pattern += "o"
            elif self.board.get_color(stone) == EMPTY:
                pattern += "."
            elif self.board.get_color(stone) == player:
                pattern += "x"
            if len(pattern) >= 6 and pattern[-6:] in [".xxx..", "..xxx.", ".x.xx.", ".xx.x."]:
                if pattern[-6:] == ".xxx..":
                    point = list[counter - 1]
                    moves.append(point)
                elif pattern[-6:] == "..xxx.":
                    point = list[counter - 4]
                    moves.append(point)
                elif pattern[-6:] == ".x.xx.":
                    point = list[counter - 3]
                    moves.append(point)
                elif pattern[-6:] == ".xx.x.":
                    point = list[counter - 2]
                    moves.append(point) 
        return moves

    
    def open_four(self):
        result = []
        for r in self.board.rows:
            result.extend(self.has_open_four_in_list(r, self.board.current_player))
        for c in self.board.cols:
            result.extend(self.has_open_four_in_list(c, self.board.current_player))
        for d in self.board.diags:
            result.extend(self.has_open_four_in_list(d, self.board.current_player))
        return result


    def block_open_four(self):
        result = []
        for r in self.board.rows:
            result.extend(self.has_open_four_in_list(r, GoBoardUtil.opponent(self.board.current_player)))
        for c in self.board.cols:
            result.extend(self.has_open_four_in_list(c, GoBoardUtil.opponent(self.board.current_player)))
        for d in self.board.diags:
            result.extend(self.has_open_four_in_list(d, GoBoardUtil.opponent(self.board.current_player)))
        return result

    def get_rule_moves(self, policy):
        
        if policy == "random":
            return "Random", GoBoardUtil.generate_legal_moves(self.board, self.board.current_player)
            
        else:
            win = self.win_wrapper()
            block_win = self.block_win()
            open_four = self.open_four()
            block_open_four = self.block_open_four()
            
            print(win)
            print(block_win)
            if len(win) != 0:
                return "Win", win
            elif len(block_win) != 0:
                return "BlockWin", block_win
            elif len(open_four) != 0:
                return "OpenFour", open_four
            elif len(block_open_four) != 0:
                return "BlockOpenFour", block_open_four
            else:
                return "Random", GoBoardUtil.generate_legal_moves(self.board, self.board.current_player)



def run():
    """
    start the gtp connection and wait for commands.
    """
    board = GoBoard(7)
    con = GtpConnection(FlatMonteCarloSimulation(board), board)
    con.start_connection()

if __name__ == "__main__":
    run()
