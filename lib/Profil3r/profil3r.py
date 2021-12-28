import sys
from itertools import chain, combinations
from pathlib import Path

from profil3r import core
from profil3r.colors import Colors
from multiprocessing import Process

try:
    from utils.utils import get_project_root
except ModuleNotFoundError:
    def get_project_root():
        return Path(__file__).absolute().parent.parent.parent


CONFIG = get_project_root().joinpath('lib', 'Profil3r', 'config.json')

profil3r = core.Core(CONFIG, sys.argv[1:])
profil3r.get_permutations()

arguments = sys.argv[1:]

if not len(arguments):
    print('''Profil3r is an OSINT tool that allows you to find potential profiles of a person on social networks, as well as their email addresses. This program also alerts you to the presence of a data leak for the found emails.

Usage : ./main.py <arguments>
for exemple : ./main.py john doe
            ./main.py john doe 67''')

else:
    profil3r.run()
