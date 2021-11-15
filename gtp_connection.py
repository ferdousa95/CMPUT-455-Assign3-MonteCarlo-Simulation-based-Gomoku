"""
gtp_connection.py
Module for playing games of Go using GoTextProtocol

Parts of this code were originally based on the gtp module 
in the Deep-Go project by Isaac Henrion and Amos Storkey 
at the University of Edinburgh.
"""
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
import numpy as np
import re
import random


# import Gomoku3


class GtpConnection:
    RANDOM = "random"
    RULE_BASED = "rule_based"

    def __init__(self, go_engine, board, debug_mode=False):
        """
        Manage a GTP connection for a Go-playing engine

        Parameters
        ----------
        go_engine:
            a program that can reply to a set of GTP commandsbelow
        board: 
            Represents the current board state.
        """
        self._debug_mode = debug_mode
        self.go_engine = go_engine
        self.board = board
        self.policytype = self.RANDOM
        self.simulateRandomMove = go_engine
        self.commands = {
            "protocol_version": self.protocol_version_cmd,
            "quit": self.quit_cmd,
            "name": self.name_cmd,
            "boardsize": self.boardsize_cmd,
            "showboard": self.showboard_cmd,
            "clear_board": self.clear_board_cmd,
            "komi": self.komi_cmd,
            "version": self.version_cmd,
            "known_command": self.known_command_cmd,
            "genmove": self.genmove_cmd,
            "list_commands": self.list_commands_cmd,
            "play": self.play_cmd,
            "legal_moves": self.legal_moves_cmd,
            "gogui-rules_game_id": self.gogui_rules_game_id_cmd,
            "gogui-rules_board_size": self.gogui_rules_board_size_cmd,
            "gogui-rules_legal_moves": self.gogui_rules_legal_moves_cmd,
            "gogui-rules_side_to_move": self.gogui_rules_side_to_move_cmd,
            "gogui-rules_board": self.gogui_rules_board_cmd,
            "gogui-rules_final_result": self.gogui_rules_final_result_cmd,
            "gogui-analyze_commands": self.gogui_analyze_cmd,

            # Leah here. Added both policy_moves and policy policy type to commands.
            "policy": self.policy_cmd,
            "policy_moves": self.policy_moves_cmd

        }

        # used for argument checking
        # values: (required number of arguments,
        #          error message on argnum failure)
        self.argmap = {
            "boardsize": (1, "Usage: boardsize INT"),
            "komi": (1, "Usage: komi FLOAT"),
            "known_command": (1, "Usage: known_command CMD_NAME"),
            "genmove": (1, "Usage: genmove {w,b}"),
            "play": (2, "Usage: play {b,w} MOVE"),
            "legal_moves": (1, "Usage: legal_moves {w,b}"),
            "policytype": (1, "Usage: setting policy type")
        }

    def write(self, data):
        stdout.write(data)

    def flush(self):
        stdout.flush()

    def start_connection(self):
        """
        Start a GTP connection. 
        This function continuously monitors standard input for commands.
        """
        line = stdin.readline()
        while line:
            self.get_cmd(line)
            line = stdin.readline()

    def get_cmd(self, command):
        """
        Parse command string and execute it
        """
        if len(command.strip(" \r\t")) == 0:
            return
        if command[0] == "#":
            return
        # Strip leading numbers from regression tests
        if command[0].isdigit():
            command = re.sub("^\d+", "", command).lstrip()

        elements = command.split()
        if not elements:
            return
        command_name = elements[0]
        args = elements[1:]
        if self.has_arg_error(command_name, len(args)):
            return
        if command_name in self.commands:
            try:
                self.commands[command_name](args)
            except Exception as e:
                self.debug_msg("Error executing command {}\n".format(str(e)))
                self.debug_msg("Stack Trace:\n{}\n".format(traceback.format_exc()))
                raise e
        else:
            self.debug_msg("Unknown command: {}\n".format(command_name))
            self.error("Unknown command")
            stdout.flush()

    def has_arg_error(self, cmd, argnum):
        """
        Verify the number of arguments of cmd.
        argnum is the number of parsed arguments
        """
        if cmd in self.argmap and self.argmap[cmd][0] != argnum:
            self.error(self.argmap[cmd][1])
            return True
        return False

    def debug_msg(self, msg):
        """ Write msg to the debug stream """
        if self._debug_mode:
            stderr.write(msg)
            stderr.flush()

    def error(self, error_msg):
        """ Send error msg to stdout """
        stdout.write("? {}\n\n".format(error_msg))
        stdout.flush()

    def respond(self, response=""):
        """ Send response to stdout """
        stdout.write("= {}\n\n".format(response))
        stdout.flush()

    def reset(self, size):
        """
        Reset the board to empty board of given size
        """
        self.board.reset(size)

    def board2d(self):
        return str(GoBoardUtil.get_twoD_board(self.board))

    def protocol_version_cmd(self, args):
        """ Return the GTP protocol version being used (always 2) """
        self.respond("2")

    def quit_cmd(self, args):
        """ Quit game and exit the GTP interface """
        self.respond()
        exit()

    def name_cmd(self, args):
        """ Return the name of the Go engine """
        self.respond(self.go_engine.name)

    def version_cmd(self, args):
        """ Return the version of the  Go engine """
        self.respond(self.go_engine.version)

    def clear_board_cmd(self, args):
        """ clear the board """
        self.reset(self.board.size)
        self.respond()

    def boardsize_cmd(self, args):
        """
        Reset the game with new boardsize args[0]
        """
        self.reset(int(args[0]))
        self.respond()

    def showboard_cmd(self, args):
        self.respond("\n" + self.board2d())

    def komi_cmd(self, args):
        """
        Set the engine's komi to args[0]
        """
        self.go_engine.komi = float(args[0])
        self.respond()

    def known_command_cmd(self, args):
        """
        Check if command args[0] is known to the GTP interface
        """
        if args[0] in self.commands:
            self.respond("true")
        else:
            self.respond("false")

    def list_commands_cmd(self, args):
        """ list all supported GTP commands """
        self.respond(" ".join(list(self.commands.keys())))

    def legal_moves_cmd(self, args):
        """
        List legal moves for color args[0] in {'b','w'}
        """
        board_color = args[0].lower()
        color = color_to_int(board_color)
        moves = GoBoardUtil.generate_legal_moves(self.board, color)
        gtp_moves = []
        for move in moves:
            coords = point_to_coord(move, self.board.size)
            gtp_moves.append(format_point(coords))
        sorted_moves = " ".join(sorted(gtp_moves))
        self.respond(sorted_moves)

    def play_cmd(self, args):
        """
        play a move args[1] for given color args[0] in {'b','w'}
        """
        try:
            board_color = args[0].lower()
            board_move = args[1]
            color = color_to_int(board_color)
            if args[1].lower() == "pass":
                self.board.play_move(PASS, color)
                self.board.current_player = GoBoardUtil.opponent(color)
                self.respond()
                return
            coord = move_to_coord(args[1], self.board.size)
            if coord:
                move = coord_to_point(coord[0], coord[1], self.board.size)
            else:
                self.respond("unknown: {}".format(args[1]))
                return
            if not self.board.play_move(move, color):
                self.respond("illegal move: \"{}\" occupied".format(args[1].lower()))
                return
            else:
                self.debug_msg(
                    "Move: {}\nBoard:\n{}\n".format(board_move, self.board2d())
                )
            self.respond()
        except Exception as e:
            self.respond("illegal move: {}".format(str(e).replace('\'', '')))

    def genmove_cmd(self, args):
        """
        Generate a move for the color args[0] in {'b', 'w'}, for the game of gomoku.
        """
        result = self.board.detect_five_in_a_row()
        if result == GoBoardUtil.opponent(self.board.current_player):
            self.respond("resign")
            return
        if self.board.get_empty_points().size == 0:
            self.respond("pass")
            return
        board_color = args[0].lower()
        color = color_to_int(board_color)
        
        move = self.go_engine.genmove(self.policytype, color)
        
        throwaway, moves = self.get_rule_moves()
        numMoves = len(moves)
        higherStates = numMoves + numMoves  # padding values cause the total number of values to increase
        score = [0] * higherStates

        # the board position is the array index, so pos=9's score is stored in score[9]
        for i in range(numMoves):
            pos = int(moves[i])
            score[int(pos)] = self.simulate_score(color, self, pos)

        bestIndex = score.index(max(score))
        assert bestIndex in self.board.get_empty_points()

        
        move_coord = point_to_coord(move, self.board.size)
        move_as_string = format_point(move_coord)
        if self.board.is_legal(move, color):
            self.board.play_move(move, color)
            self.respond(move_as_string.lower())
        else:
            self.respond("Illegal move: {}".format(move_as_string))

    def gogui_rules_game_id_cmd(self, args):
        self.respond("Gomoku")

    def gogui_rules_board_size_cmd(self, args):
        self.respond(str(self.board.size))

    def gogui_rules_legal_moves_cmd(self, args):
        if self.board.detect_five_in_a_row() != EMPTY:
            self.respond("")
            return
        empty = self.board.get_empty_points()
        output = []
        for move in empty:
            move_coord = point_to_coord(move, self.board.size)
            output.append(format_point(move_coord))
        output.sort()
        output_str = ""
        for i in output:
            output_str = output_str + i + " "
        self.respond(output_str.lower())
        return

    def gogui_rules_side_to_move_cmd(self, args):
        color = "black" if self.board.current_player == BLACK else "white"
        self.respond(color)

    def gogui_rules_board_cmd(self, args):
        size = self.board.size
        str = ''
        for row in range(size - 1, -1, -1):
            start = self.board.row_start(row + 1)
            for i in range(size):
                # str += '.'
                point = self.board.board[start + i]
                if point == BLACK:
                    str += 'X'
                elif point == WHITE:
                    str += 'O'
                elif point == EMPTY:
                    str += '.'
                else:
                    assert False
            str += '\n'
        self.respond(str)

    def gogui_rules_final_result_cmd(self, args):
        if self.board.get_empty_points().size == 0:
            self.respond("draw")
            return
        result = self.board.detect_five_in_a_row()
        if result == BLACK:
            self.respond("black")
        elif result == WHITE:
            self.respond("white")
        else:
            self.respond("unknown")

    def gogui_analyze_cmd(self, args):
        self.respond("pstring/Legal Moves For ToPlay/gogui-rules_legal_moves\n"
                     "pstring/Side to Play/gogui-rules_side_to_move\n"
                     "pstring/Final Result/gogui-rules_final_result\n"
                     "pstring/Board Size/gogui-rules_board_size\n"
                     "pstring/Rules GameID/gogui-rules_game_id\n"
                     "pstring/Show Board/gogui-rules_board\n"
                     )

    # Leah - This function will be the setter for changing policy.
    #      - Input sanitizing will be done by who calls it
    def set_policy(self, policytype):
        self.policytype = policytype

    # Leah code here.
    # Implementing the policy policy type GTP Command function
    # Idea is that it checks that its one of the two inputs, then calls the setter in board to change it
    def policy_cmd(self, args):
        if args[0] == self.RANDOM or args[0] == self.RULE_BASED:
            self.set_policy(args[0])

    def get_coord_from_point(self, number):
        move = number
        move_coord = point_to_coord(move, self.board.size)
        move_as_string = format_point(move_coord)
        return move_as_string
    '''
    def random(self):
        return self.go_engine.get_move(self.board, self.board.current_player)

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
            self.respond("{row}".format(row=row_value))

        if col_value is not None:
            col_value = list(set(col_value))
            for col in col_value:
                total_pos.append(col)
            self.respond("{col}".format(col=col_value))
            
        if diag_value is not None:
            diag_value = list(set(diag_value))
            for diag in diag_value:
                total_pos.append(diag)
            self.respond("{diag}".format(diag=diag_value))

        if total_pos is not None:
            self.respond(str(total_pos))
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

    def get_rule_moves(self):
        
        if self.policytype == self.RANDOM:
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
        '''
    # Implementing the policy_moves GTP Command function
    def policy_moves_cmd(self, args):

        movetype, move_list = self.go_engine.get_rule_moves(self.policytype)
        format_moves = [0] * len(move_list)
        if len(move_list) != 0:
            for i in range(0, len(move_list)):
                format_moves[i] = format_point(point_to_coord(move_list[i], self.board.size))
            self.respond("{move_type} {pos}".format(move_type = movetype, pos= ' '.join(map(str,format_moves))))
        


def point_to_coord(point, boardsize):
    """
    Transform point given as board array index
    to (row, col) coordinate representation.
    Special case: PASS is not transformed
    """
    if point == PASS:
        return PASS
    else:
        NS = boardsize + 1
        return divmod(point, NS)


def format_point(move):
    """
    Return move coordinates as a string such as 'A1', or 'PASS'.
    """
    assert MAXSIZE <= 25
    column_letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    if move == PASS:
        return "PASS"
    row, col = move
    if not 0 <= row < MAXSIZE or not 0 <= col < MAXSIZE:
        raise ValueError
    return column_letters[col - 1] + str(row)


def move_to_coord(point_str, board_size):
    """
    Convert a string point_str representing a point, as specified by GTP,
    to a pair of coordinates (row, col) in range 1 .. board_size.
    Raises ValueError if point_str is invalid
    """
    if not 2 <= board_size <= MAXSIZE:
        raise ValueError("board_size out of range")
    s = point_str.lower()
    if s == "pass":
        return PASS
    try:
        col_c = s[0]
        if (not "a" <= col_c <= "z") or col_c == "i":
            raise ValueError
        col = ord(col_c) - ord("a")
        if col_c < "i":
            col += 1
        row = int(s[1:])
        if row < 1:
            raise ValueError
    except (IndexError, ValueError):
        raise ValueError("invalid point: '{}'".format(s))
    if not (col <= board_size and row <= board_size):
        raise ValueError("\"{}\" wrong coordinate".format(s))
    return row, col


def color_to_int(c):
    """convert character to the appropriate integer code"""
    color_to_int = {"b": BLACK, "w": WHITE, "e": EMPTY, "BORDER": BORDER}

    try:
        return color_to_int[c]
    except:
        raise KeyError("\"{}\" wrong color".format(c))
