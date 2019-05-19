'''
CLI - command line interpreter.
Support commands:

1. cat [FILE] (or stdin)
2. echo
3. wc [FILE] (or stdin)
4. pwd
5. exit
6. grep

Сonsists of 2 structs:

1. Command
2. Argument
3. CLI

Command:

1.next - next command in pipe
2.args - argument for this command (Argument object)
3.name - name of this command
4.std - input is stdin or not

Argument:

1.next - next argument for current command
2.name - string, body of this argument

CLI:

This class has only one method:
start - which starts up this CLI


Command sequence:

1. input()
2. lex_and_parse -> parse_for_one_part_of_pipe (for one part of pipe) -> quotes (for parsing in quotes)
3. expansions -> expansion_of_one_part (for one part of command)
4. execution -> exec_part_of_pipe (for execution one part of pipe) ->
                                                                        1.cat
                                                                        2.echo
                                                                        3.wc
                                                                        4.pwd
                                                                        5.grep

Command grep support 3 keys:
1. -i - ignore-case
2. -w - word-regexp
3. -A - after-context

'''


import subprocess
import sys
import os
import re
import argparse


# names of possible commands
commands = ["cat", "echo", "wc", "pwd", "exit", "grep", "cd", "ls" ]

# names and values of variables
variables = {}

CURRENT_DIRECTORY = ""

# class for final command with all its arguments
class Command:
    def __init__(self, name, arguments=None, next=None, std=False):
        self.next = next  # sub command
        self.args = arguments  # arguments of this command
        self.name = name  # name of command
        self.std = std  # if std input


# class for arguments of same command
class Argument:
    def __init__(self, name, next=None):
        self.next = next  # next argument
        self.name = name  # what argument is


# function for processing something in quotes (double or single)
# i - number of current token
# j - number if charecter in current line
# splited_cl - part of line, which has already dismantled
# return new state of input parametrs
def quotes(i, j, splited_cl, line, quotes):
    if j != 0:
        i += 1
        splited_cl.append("")
    splited_cl[i] = quotes
    j += 1
    char = line[j]
    while char != quotes:
        splited_cl[i] += char
        j += 1
        char = line[j]
    splited_cl[i] += char
    j += 1
    i += 1
    splited_cl.append("")
    return (splited_cl, j, i)


# function for parsing one part of pipe-line
# return new instance of Command
def parse_for_one_part_of_pipe(part_of_pipe):
    # split_for_one_quotes = part_of_pipe.split("'")
    # splited_cl = part_of_pipe.split()
    splited_cl = []
    i = 0  # current number of token
    j = 0  # current char of line
    char = part_of_pipe[0]
    splited_cl.append("")
    while j < len(part_of_pipe) - 1:
        if char == "'":
            (splited_cl, j, i) = quotes(i, j, splited_cl, part_of_pipe, "'")
            if j < len(part_of_pipe) and part_of_pipe[j] != " ":
                char = part_of_pipe[j]
            else:
                splited_cl.pop()
                break

        elif char == '"':
            (splited_cl, j, i) = quotes(i, j, splited_cl, part_of_pipe, '"')
            if j < len(part_of_pipe) and part_of_pipe[j] != " ":
                char = part_of_pipe[j]
            else:
                splited_cl.pop()
                break

        elif char == " ":
            start = j
            while char == " ":
                j += 1
                char = part_of_pipe[j]
            if char != "'" and char != '"' and start != 0:
                i += 1
                splited_cl.append("")

        else:
            splited_cl[i] += char
            j += 1
            char = part_of_pipe[j]

    if char != "'" and char != '"' and char != " ":
        splited_cl[i] += char

    if splited_cl[0] == "exit":
        return False
    new_comm = Command(str(splited_cl[0]))

    # if this command has same arguments
    if len(splited_cl) != 1:
        arg_first = Argument(str(splited_cl[1]))
        new_comm.args = arg_first
        arg_next = arg_first
        for arg in splited_cl[2:]:
            arg_next.next = Argument(str(arg))
            arg_next = arg_next.next

    return new_comm


# lexical analise and parse
# result - First Command in Pipe
def lex_and_parse(command_line):

    splited_for_pipes = list(command_line.split("|"))
    command_first_in_pipe = parse_for_one_part_of_pipe(splited_for_pipes[0])
    commands_in_pipe = command_first_in_pipe
    for splited_cl in splited_for_pipes[1:]:
        commands_in_pipe.next = parse_for_one_part_of_pipe(splited_cl)
        commands_in_pipe = commands_in_pipe.next
    if not command_first_in_pipe:
        return False

    return command_first_in_pipe


# do expansion in one token: command or it's argument
def expansion_of_one_part(word):
    if not word:
        return
    if word.name[0] == word.name[-1] == '"' or word.name[0] == word.name[-1] == "'":
        word.name = word.name[1:-1]
    var = word.name.split("=")
    variables[var[0]] = '='.join(var[1:])
    if len(var) > 1:
        word.name = "initialize"
    i = 0
    while i < len(word.name):
        if word.name[i] == "$":
            var_curr = ""
            start = i
            i += 1
            while i < len(word.name) and word.name[i] != " " and word.name[i] != "$":
                var_curr += word.name[i]
                i += 1
            if var_curr in variables.keys():
                word.name = word.name[:start] + variables[var_curr] + word.name[i:]
            else:
                word.name = word.name[:start] + word.name[i:]
        i += 1


# do all expansions in a pipe-line
def expansions(command):
    curr_command = command
    while curr_command:
        expansion_of_one_part(curr_command)
        curr_arg = curr_command.args
        while curr_arg:
            expansion_of_one_part(curr_arg)
            curr_arg = curr_arg.next
        curr_command = curr_command.next


# execution one command in pipe
def exec_part_of_pipe(command):
    if command.name == "cat":
        return cat(command.args, command.std)
    if command.name == "echo":
        return echo(command.args)
    if command.name == "wc":
        return wc(command.args, command.std)
    if command.name == "pwd":
        return pwd()
    if command.name == "grep":
        return grep(command.args)
    if command.name == "cd":
        return cd(command.args)
    if command.name == "ls":
        return ls(command.args)
    if command.name == "initialize":
        return ""
    try:
        list_of_args = []
        next_arg = command.args
        while next_arg:
            list_of_args.append(next_arg)
            next_arg = next_arg.next
        return subprocess.call([command.name] + list_of_args)
    except TypeError:
        print(command.name + ": command not found")


# Execution of all commands
def execution(command):
    next_comm = command
    while next_comm:
        arg = exec_part_of_pipe(next_comm)
        if not next_comm.args and (next_comm.name == "wc" or next_comm.name == "cat"):
            next_comm.args = Argument(arg)
            next_comm.std = True
        next_comm = next_comm.next
    #print(arg)
    return arg


# cat function, std=False if cat for stdin
def cat(args, std):
    if std:
        return args.name
    new_arg = ""
    next_arg = args
    while next_arg:
        print(next_arg.name)
        try:
            f = open(next_arg.name)

            for line in f:
                new_arg += '\n' + line
            f.close()
        except FileNotFoundError:
            return (next_arg.name + ": no such file or directory")
        next_arg = next_arg.next
    return new_arg


# echo-function
def echo(args):
    next_arg = args
    new_arg = ""
    while next_arg:
        new_arg += next_arg.name + " "
        next_arg = next_arg.next
    #print(new_arg)
    return new_arg


# wc - function
def wc(args, std):
    #print(std)
    l = 0
    c = 0
    b = 0
    if std:
        print(args.name)
        print(args.name.count("\n"))
        l = args.name.count("\n") + 1
        c = len(args.name.split())
        b = sys.getsizeof(args.name)
        #print(args.name)
        return '{0} {1} {2}'.format(l, c, b)

    new_arg = ""
    next_arg = args
    while next_arg:
        f = open(next_arg.name)
        for line in f:
            l += args.name.count("\n") + 1
            c += len(line.split())
            b += sys.getsizeof(line)
        f.close()
        new_arg += '{0} {1} {2}'.format(l, c, b) + '\n'
        next_arg = next_arg.next
    return new_arg


# pwd - function
def pwd():
    if CURRENT_DIRECTORY:
        return CURRENT_DIRECTORY
    return os.path.abspath(os.curdir)


# grep - function
def grep(args):
    next_arg = args
    new_arg = []
    not_propose_arg = 0
    while next_arg:
        new_arg.append(next_arg.name)
        if next_arg.name.startswith("-"):
            not_propose_arg += 1
        next_arg = next_arg.next
    prop = len(new_arg) - 2 * not_propose_arg
    print(new_arg)
    file = None
    if prop > 1:
        file = new_arg[-1]
        new_arg.pop()
    parser = argparse.ArgumentParser()
    parser.add_argument("reg", type=str, help="regex")
    parser.add_argument("-A", "--after_context", dest="A", type=int, default=0,
                        help="Print  NUM  lines  of  trailing  context  after  matching lines.")
    parser.add_argument("-i", "--ignore_case", action="store_true",
                        help="Ignore case distinctions, so that \
                        characters that differ only in case match each other.")
    parser.add_argument("-w", "--word_regexp", action="store_true",
                        help="Select  only  those  lines  containing \
                         matches  that form whole words.")

    args_from_parse = parser.parse_args(new_arg)
    answer = ""
    print(file)
    if file:
        f = open(file)
        last_str = 0
        numb = 0
        for line in f:
            numb += 1
            if args_from_parse.ignore_case and args_from_parse.word_regexp:
                res = re.findall(" " + args_from_parse.reg + " ", line, re.IGNORECASE)
            elif args_from_parse.ignore_case:
                res = re.findall(args_from_parse.reg, line, re.IGNORECASE)
            elif args_from_parse.word_regexp:
                res = re.findall(" " + args_from_parse.reg + " ", line)
            else:
                res = re.findall(args_from_parse.reg, line)
            if res:
                last_str = numb
                answer += line + "\n"

        if last_str:
            print(file[last_str - 1:])
        f.close()
    else:
        numb = 0
        need_to_print = False
        if args.A:
            numb = 1
        while True:
            line = input()
            if not line:
                return "Exit grep"
            if need_to_print:
                print(line)
                need_to_print -= 1
            if args.ignore_case and args.word_regexp:
                res = re.findall(" " + args.reg + " ", line, re.IGNORECASE)
            elif args.ignore_case:
                res = re.findall(args.reg, line, re.IGNORECASE)
            elif args.word_regexp:
                res = re.findall(" " + args.reg + " ", line)
            else:
                res = re.findall(args.reg, line)
            if res:
                need_to_print = args.A
                numb += 1
                print(line)
    return answer

def calc_path(current_directory, addition_part):
    arg = addition_part
    if arg.startswith("/"):
        current_directory = "/"
        arg = arg[1:]
    path = arg.split("/")
    for next_path_part in path:
        if not next_path_part:
            continue
        if next_path_part == "..":
            current_directory = "/".join(current_directory.split("/")[:-1])
            continue
        if next_path_part == ".":
            continue
        current_directory = current_directory + next_path_part + "/"
        if not os.path.isdir(current_directory):
            raise FileNotFoundError()
    if not current_directory.endswith("/"):
        current_directory += "/"

    return current_directory

def ls(args):
    if not args:
        ls_directory = pwd()
    else:
        try:
            ls_directory = calc_path(pwd(), args.name)
        except FileNotFoundError:
            return "ls: " + args.name + ": No such file or directory"
    return "\t".join(os.listdir(ls_directory))

def cd(args):
    global CURRENT_DIRECTORY
    if not args:
        current_directory = "~"
    current_directory = pwd()
    arg = args.name
    try:
        current_directory = calc_path(current_directory, arg)
    except FileNotFoundError:
        return "cd: " + arg + ": No such file or directory"
    CURRENT_DIRECTORY = current_directory
    return ""


class CLI:
    def start(self):
        while True:
            command_line = input()
            command = lex_and_parse(command_line)
            if not command:
                break
            expansions(command)
            print(execution(command))


def main():
    cli = CLI()
    cli.start()


# Unit - tests
def test(command_line):
    command = lex_and_parse(command_line)
    expansions(command)
    return execution(command)


def echo_test():
    assert (test("echo 'Hello, world!'") == "Hello, world! ")
    assert (test("echo 123") == "123 ")
    assert (test("echo") == "")
    assert (test("var=r | echo $var") == "r ")


def cat_test():
    assert (test("cat name.txt") == "name.txt: no such file or directory")
    assert (test("echo dddd | cat") == "dddd ")


def wc_test():
    assert (test("echo aaaaaa|wc") == "1 1 32")
    assert (test("echo|wc") == "1 0 25")


def os_mock(current_dir, listdir_func=None):
    OS = namedtuple('OsMock', 'path curdir getcwd listdir')
    Path = namedtuple('Path', 'abspath isdir')
    os = OS(Path(lambda x: current_dir, lambda x: True), 'dir', \
        lambda _: current_dir, listdir_func)
    return os

def pwd_test():
    global os
    global CURRENT_DIRECTORY
    os = os_mock('current_dir')
    assert (test("pwd") == "current_dir")
    CURRENT_DIRECTORY = "current_dir2"
    assert (test("pwd") == "current_dir2")
    CURRENT_DIRECTORY = ""

def cd_test():
    global os
    global CURRENT_DIRECTORY
    os = os_mock('current_dir')
    test('cd /')
    assert (CURRENT_DIRECTORY == "/")
    CURRENT_DIRECTORY = ""
    test('cd current_dir2')
    assert (CURRENT_DIRECTORY == "current_dir/current_dir2")
    CURRENT_DIRECTORY = ""

def calc_path_test():
    global os
    global CURRENT_DIRECTORY
    os = os_mock('current_dir')
    assert (calc_path('/', 'hello') == '/hello')
    assert (calc_path('/hello', 'hello') == '/hello/hello')
    assert (calc_path('/hello', '/') == '/')
    assert (calc_path('/hello', '/other_hello') == '/other_hello')
    assert (calc_path('/hello/', 'other_hello') == '/hello/other_hello')
    assert (calc_path('/hello/', 'other_hello/') == '/hello/other_hello')
    CURRENT_DIRECTORY = ""


def grep_test():
    assert (test("grep 'a' name.txt") == "aaaa")
    assert (test("grep 'a' a") == "a")
    assert (test("grep 'aaa' a") == "")

def ls_test():
    global os
    global CURRENT_DIRECTORY
    os = os_mock('current_dir', lambda x: ["1", "2"] if x=="current_dir" else ["1"])
    assert (test("ls")=="1\t2")
    assert (test("ls /")=="1")
    CURRENT_DIRECTORY = ""



if __name__ == '__main__':
    main()
    # echo_test()
    # cat_test()
    # wc_test()
    # pwd_test()
    # grep_test()
    # ls_test()
    # cd_test()
    # calc_path_test()
