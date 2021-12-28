import argparse
import os
import sys
from pathlib import Path
try:
    from utils.utils import get_project_root
except ModuleNotFoundError:
    def get_project_root():
        return Path(__file__).absolute().parent.parent

try:
    from lib.Profil3r.profil3r import core
except ModuleNotFoundError:
    sys.path.append(str(Path(__file__).absolute().parent.parent))
    from lib.Profil3r.profil3r import core
except:
    print("[INSTALL] Installing profiler")
    get_project_root().joinpath("")


class Profiler:
    def __init__(self, args: list):
        self.config = get_project_root().joinpath('lib', 'Profil3r', 'config.json')
        self.core = core.Core(self.config, args)
        self.core.get_permutations()

    def execute(self):
        try:
            self.core.run()
        except KeyboardInterrupt:
            exit(1)


if __name__ == '__main__':
    os.system('color')
    parser = argparse.ArgumentParser(description="Profil3r OSINT Tool")
    parser.add_argument("keywords", action="append", help="Keywords for the search")
    args = parser.parse_args()

    profiler = Profiler(args.keywords)
    profiler.execute()

