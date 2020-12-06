import sys
import ast
import re
import os

from collections import defaultdict

from typing import Dict

args = sys.argv
abs_path = str(args[1])


def extract_file_path(param):
    if os.path.isfile(param) and param.endswith('.py'):
        analyze_file(param)
        return
    if os.path.isdir(param):
        sub_files = os.listdir(param)
        for k in sub_files:
            extract_file_path(f'{param}{os.sep}{k}')
        return


class PepAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.stats: Dict[str, Dict[int, list]] = {
            "variables": defaultdict(list),
            "parameters": defaultdict(list),
            "is_constant_default": defaultdict(list),
        }

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.stats["variables"][node.lineno].append(node.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        for a in node.args.args:
            self.stats["parameters"][node.lineno].append(a.arg)
        for a in node.args.defaults:
            self.stats["is_constant_default"][node.lineno].append(isinstance(a, ast.Constant))
        self.generic_visit(node)

    def get_parameters(self, lineno: int) -> list:
        return self.stats["parameters"][lineno]

    def get_variables(self, lineno: int) -> list:
        return self.stats["variables"][lineno]

    def get_mutable_defaults(self, lineno: int) -> str:
        for param_name, is_default in zip(self.stats["parameters"][lineno], self.stats["is_constant_default"][lineno]):
            if not is_default:
                return param_name
        return ""


class CodeAnalyser:
    @staticmethod
    def check_error_1(line, error_path):
        if len(line) > 79:
            print(error_path, "S001 Too long")

    @staticmethod
    def check_error_2(line, error_path):
        if re.match(r"(?!^( {4})*[^ ])", line):
            print(error_path, "S002 Indentation is not a multiple of four")

    @staticmethod
    def check_error_3(line, error_path):
        if re.search(r"^([^#])*;(?!\S)", line):
            print(error_path, "S003 Unnecessary semicolon")

    @staticmethod
    def check_error_4(line, error_path):
        if re.match(r"[^#]*[^ ]( ?#)", line):
            print(error_path, "S004 At least two spaces before inline comment required")

    @staticmethod
    def check_error_5(line, error_path):
        if re.search(r"(?i)# *todo", line):
            print(error_path, "S005 TODO found")

    @staticmethod
    def check_error_7(line, error_path):
        if re.match(r"^([ ]*(?:class|def) ( )+)", line):
            print(error_path, "S007 Too many spaces after construction_name (def or class)")

    @staticmethod
    def check_error_8(line, error_path):
        if matches := re.match(r"^(?:[ ]*class (?P<name>\w+))", line):
            if not re.match(r"(?:[A-Z][a-z0-9]+)+", matches["name"]):
                print(error_path, f'S008 Class name {matches["name"]} should use CamelCase')

    @staticmethod
    def check_error_9(line, error_path):
        if matches := re.match(r"^(?:[ ]*def (?P<name>\w+))", line):
            if not re.match(r"[a-z_]+", matches["name"]):
                print(error_path, f'S009 Function name {matches["name"]} should use snake_case')


def analyze_file(filename: str):
    preceding_blank_line_counter: int = 0

    with open(filename) as f:
        tree = ast.parse(f.read())

        code_analyser = CodeAnalyser()
        pep_analyzer = PepAnalyzer()
        pep_analyzer.visit(tree)

        f.seek(0)
        for i, line in enumerate(f, start=1):
            if line == "\n":
                preceding_blank_line_counter += 1
                continue

            error_path: str = f"{filename}: Line {i}:"

            code_analyser.check_error_1(line, error_path)
            code_analyser.check_error_2(line, error_path)
            code_analyser.check_error_3(line, error_path)
            code_analyser.check_error_4(line, error_path)
            code_analyser.check_error_5(line, error_path)

            if preceding_blank_line_counter > 2:
                print(error_path, "S006 More than two blank lines used before this line")
            preceding_blank_line_counter = 0

            code_analyser.check_error_7(line, error_path)
            code_analyser.check_error_8(line, error_path)
            code_analyser.check_error_9(line, error_path)

            for parameter in pep_analyzer.get_parameters(i):
                if not re.match(r"[a-z_]+", parameter):
                    print(error_path, f"S010 Argument name '{parameter}' should be snake_case")
                    break

            for variable in pep_analyzer.get_variables(i):
                if not re.match(r"[a-z_]+", variable):
                    print(error_path, f"S011 Variable '{variable}' in function should be snake_case")
                    break

            if pep_analyzer.get_mutable_defaults(i):
                print(error_path, "S012 Default argument value is mutable")


def main():
    extract_file_path(abs_path)


if __name__ == "__main__":
    main()
