import configparser

import psutil

from actions.action import Action
import subprocess

from utils.utils import get_project_root, info, debug, error


class Tor(Action):
    def __init__(self, workspace=None):
        super().__init__(workspace)
        self.commands = ["start", "stop", "install", "change-pwd"]
        self.__rc = r"""
SOCKSPort 9150
RunAsDaemon 1
ControlPort 9151
HashedControlPassword ####PASSWORD####
CookieAuthentication 1
"""
        self.tor = get_project_root().joinpath("tor", "TorBrowser", "Tor", "tor.exe").absolute()
        self.tor_rc = get_project_root().joinpath("tor", "torrc").absolute()
        self.firefox = get_project_root().joinpath("tor").joinpath("firefox.exe")
        self.config = configparser.ConfigParser(allow_no_value=True, interpolation=configparser.ExtendedInterpolation())
        self.config.read(str(get_project_root().joinpath("config", "config.ini").absolute()))

    def hash_password(self, password):
        cmd = f'"{self.tor}" --hash-password {password}'
        output = subprocess.check_output(cmd).decode()
        for line in output.split("\n"):
            line = line.strip()
            if line.startswith("16"):
                return line

    def update_password(self, password):
        self.config.set("TOR", "ctrl_password", password)

    def update_rc(self, password):
        password = self.hash_password(password)
        with open(self.tor_rc, "w") as rc_file:
            rc_file.write(self.__rc.replace("####PASSWORD####", password))

    def install(self):
        if not self.tor_rc.is_file():
            self.update_rc(password=self.config.get("TOR", "ctrl_password"))
        cmd = f"\"{self.tor}\" --service uninstall"
        output = subprocess.check_output(cmd).decode()
        print(output)
        cmd = f"\"{self.tor}\" --service install -options -f \"{self.tor_rc}\""
        output = subprocess.check_output(cmd).decode()
        print(output)

    def stop(self):
        for p in psutil.process_iter():
            try:
                if p.name().lower() == "firefox.exe":
                    if p.cwd() == str(get_project_root()):
                        p.kill()
            except:
                pass

    def execute(self, **kwargs):
        command = kwargs["command"]
        if not command or command not in self.commands:
            command = self.choose_command()

        if command == "start":
            info("Starting TOR Browser, click on connect")
            subprocess.Popen(self.firefox, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, close_fds=True)

        elif command == "stop":
            info("Stopping TOR browser")
            self.stop()

        elif command == "install":
            info("Installing TOR as a Windows Service")
            self.install()

        elif command == "change-pwd":
            password = kwargs["password"]
            while not password or len(password) < 12:
                error("Password should be at least 12 characters")
                info("Please insert a strong password")
                password = self.wait_for_input()

            self.update_password(password=password)
            debug("Remember to launch 'install' again to update the service password")

        else:
            return
