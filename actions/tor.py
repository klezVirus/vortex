import configparser
import os
from pathlib import Path

import psutil

from actions.action import Action
import subprocess

from utils.utils import get_project_root, info, debug, error


class Tor(Action):
    def __init__(self, workspace=None):
        super().__init__(workspace)
        self.win = os.name == "nt"
        self.commands = ["start", "stop", "install", "change-pwd"]
        if self.win:
            self.tor = get_project_root().joinpath("tor", "TorBrowser", "Tor", "tor.exe").absolute()
            self.tor_rc = get_project_root().joinpath("tor", "torrc").absolute()
            self.firefox = get_project_root().joinpath("tor").joinpath("firefox.exe")
        else:
            self.tor_rc = Path("/etc/tor/torrc")
            try:
                output = subprocess.check_output(
                    "which tor",
                    shell=True
                )
                self.tor = output.decode().strip()
                self.firefox = ""
            except subprocess.CalledProcessError:
                error("Tor not found. Please install it or add it to PATH")
                exit(1)

        self.socks_port = self.config.get("TOR", "socks_port")
        self.ctrl_port = self.config.get("TOR", "ctrl_port")
        self.__rc = r"""
SOCKSPort ####SOCKS_PORT####
RunAsDaemon 1
ControlPort ####CTRL_PORT####
HashedControlPassword ####PASSWORD####
CookieAuthentication 1
    """

    @property
    def rc(self):
        return self.__rc.replace(
            "####SOCKS_PORT####", self.socks_port
        ).replace(
            "####CTRL_PORT####",
            self.ctrl_port
        )

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
        if not self.win:
            error("Install: Not supported on non-Windows platforms")
            return
        if not self.tor_rc.is_file():
            self.update_rc(password=self.config.get("TOR", "ctrl_password"))
        cmd = f"\"{self.tor}\" --service uninstall"
        output = subprocess.check_output(cmd).decode()
        print(output)
        cmd = f"\"{self.tor}\" --service install -options -f \"{self.tor_rc}\""
        output = subprocess.check_output(cmd).decode()
        print(output)

    def stop(self):
        if self.win:
            for p in psutil.process_iter():
                try:
                    if p.name().lower() == "firefox.exe":
                        if p.cwd() == str(get_project_root()):
                            p.kill()
                except:
                    pass
        else:
            try:
                subprocess.check_call("sudo killall tor", shell=True)
            except subprocess.CalledProcessError:
                pass

    def execute(self, **kwargs):
        command = kwargs["command"]
        if not command or command not in self.commands:
            command = self.choose_command()

        if command == "start":
            if self.win:
                info("Starting TOR Browser, click on connect")
                subprocess.Popen(self.firefox, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, close_fds=True)
            else:
                info("Starting TOR, give it a few seconds to connect")
                subprocess.Popen(self.tor, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, close_fds=True)

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
