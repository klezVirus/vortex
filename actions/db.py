import os.path
import re
import sqlite3

import pandas
import pandas as pd
from tabulate import tabulate

from actions.action import Action
from utils.utils import error, info, warning, success, get_project_root, fatal, highlight


class Db(Action):
    def __init__(self, workspace):
        super().__init__(workspace=workspace)
        self.commands = {
            "init": [],
            "sql": [],
            "add-endpoint": [],
            "add-user": [],
            "drop-user": [],
            "truncate-table": [],
            "found-logins": [],
            "show-info": ["domain"],
            "export": [],
            "check": [],
        }
        self.no_child_process = True

    def execute(self, **kwargs):
        self.dbh.connect()
        command = kwargs["command"]
        domain = kwargs.get("domain")
        if command == "init":
            if os.path.exists(self.dbh.db) and self.dbh.db_initialised():
                error("The DB file exists and it was initialised, overwrite?")
                if not self.wait_for_choice():
                    exit(1)
                self.dbh.tear_down()
                os.unlink(self.dbh.db)
            info("Initialising the DB")
            with self.dbh.create_cursor() as cursor:
                cursor.execute(r'''
    CREATE TABLE IF NOT EXISTS users(
    uid integer primary key AUTOINCREMENT,
    name text,
    email text not null unique,
    job text,
    valid integer default 0);''')
                cursor.connection.commit()
                cursor.execute(r'''
    CREATE TABLE IF NOT EXISTS profiles(
    pid integer primary key AUTOINCREMENT,
    uid integer not null,
    username text,
    email text,
    phone text,
    url text not null,
    ptype text not null);''')
                cursor.connection.commit()
                cursor.execute(r'''
    CREATE TABLE IF NOT EXISTS domains(
    did integer primary key AUTOINCREMENT,
    name text not null,
    level integer not null,
    email_format text default null,
    dns text default null,
    frontable text default null,
    takeover text default null,
    additional_info text default null);''')
                cursor.connection.commit()
                cursor.execute(r'''
    CREATE TABLE IF NOT EXISTS host(
    hid integer primary key AUTOINCREMENT,
    hostname text not null,
    ip text not null,
    geo_ref integer default null
    );''')
                cursor.connection.commit()
                cursor.execute(r'''
    CREATE TABLE IF NOT EXISTS origins(
    oid integer primary key AUTOINCREMENT,
    host text not null,
    port text not null,
    ssl integer default 0,
    up integer default 1);''')
                cursor.connection.commit()
                cursor.execute(r'''
    CREATE TABLE IF NOT EXISTS endpoints(
    eid integer primary key AUTOINCREMENT,
    target text not null,
    email_format text default null,
    etype_ref integer not null,
    additional_info text default null);''')
                cursor.connection.commit()
                cursor.execute(r'''
    CREATE TABLE IF NOT EXISTS etypes(
    etid integer primary key AUTOINCREMENT,
    name text not null,
    is_vpn integer not null default 0,
    is_office integer not null default 0,
    is_o365 integer not null default 0);''')
                cursor.connection.commit()
                r"""
                # ----------- F**k off this sh*t -------------
                etypes = get_project_root().joinpath("config", "etypes.csv").absolute()
                if not etypes.is_file():
                    error("Supported Endpoint Types config file was not found. Aborting.")
                    exit(1)
                df = pandas.read_csv(str(etypes))
                df.to_sql("etypes", cursor.connection, if_exists='append', index=False)
                # --------------------------------------------
                """
                counter = 0
                etypes = [{"etid": counter, "name": "UNKNOWN", "is_vpn": 0, "is_office": 0, "is_o365": 0}]
                counter += 1
                for enumerator in self.enumerators():
                    _d, _f = enumerator.split(".")
                    etypes.append({"etid": counter, "name": _f.upper(), "is_vpn": _d == "vpn", "is_office": _d == "office", "is_o365": _f.find("365") > -1})
                    counter += 1
                df = pandas.DataFrame(etypes)
                df.to_sql("etypes", cursor.connection, if_exists='append', index=False)

                cursor.execute(r'''
    CREATE TABLE IF NOT EXISTS leaks(
    lid integer primary key AUTOINCREMENT,
    uid integer not null,
    password text not null,
    hash text default null,
    address text default null,
    phone text default null,
    database text default null);''')
                cursor.connection.commit()
                cursor.execute(r'''
    CREATE TABLE IF NOT EXISTS found_logins(
    login_id integer primary key AUTOINCREMENT,
    realm text default "",
    vgroup text default "",
    email text not null,
    password text not null,
    eid integer not null);''')
                cursor.connection.commit()
                cursor.execute(r'''
    CREATE TABLE IF NOT EXISTS attempts(
    attempt_id integer primary key AUTOINCREMENT,
    user_id integer not null,
    etype_ref integer not null,
    realm text default "",
    vgroup text default "",
    username text not null,
    password text not null,
    url text not null,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);''')
                cursor.connection.commit()
                cursor.execute(r'''
    CREATE TABLE IF NOT EXISTS aws_api(
    aid integer primary key AUTOINCREMENT,
    api_id text not null,
    region text not null,
    url text not null,
    proxy_url text not null,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);''')
                cursor.connection.commit()
                cursor.execute(r'''
    CREATE TABLE IF NOT EXISTS config(
    cid integer primary key,
    email_format text not null,
    aws_prefix text not null);''')
        elif command == "sql":
            sql = kwargs["sql"]
            if not sql:
                warning("Be sure you know what you're doing")
                info("Write down a SQL command to execute")
                sql = self.wait_for_input()
            info(f"Executing SQL statement: {sql}")
            with self.dbh.create_cursor() as cursor:
                cursor.execute(sql)
                for row in cursor:
                    print(*row)
        elif command == "add-endpoint":
            target = kwargs["url"]
            if not target:
                warning("DEPRECATED: Please consider using action `vpn -c add` to add an endpoint manually")
                info("Please provide an endpoint to add to the DB (IP:PORT)")
                target = self.wait_for_input()
                # TODO: Perform target validation
            vpn = kwargs["endpoint_type"]
            if not vpn:
                warning("DEPRECATED: Please consider using action `vpn -c add` to add an endpoint manually")
                fatal("Please specify a VPN type")
            endpoint_type = self.dbms.get_etype_id(vpn)
            if endpoint_type is None:
                error(f"{vpn} is not a valid VPN type")
                exit(1)

            info(f"Adding user Endpoint(target='{target}', endpoint_type='{vpn}')")
            with self.dbh.create_cursor() as cursor:
                cursor.execute("INSERT INTO endpoints (target, endpoint_type) values (?, ?)", (target, endpoint_type))

        elif command == "add-user":
            email = kwargs["email"]
            username = kwargs["user"]
            domain = kwargs["domain"]
            if not all([email, username, domain]):
                print("[-] To add a user, specify a valid mail or the pair <username, domain>")
                email = ""
                while not re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email):
                    info("Enter a valid email address")
                    email = self.wait_for_input()
            if email == "":
                email = f"{username}@{domain}"
            name = kwargs["name"]
            if not name:
                info("OPTIONAL: Provide the person full name, or press ENTER")
                name = input()
            role = kwargs["role"]
            if not role:
                info("OPTIONAL: Provide the person job role, or press ENTER")
                role = input()

            info(f"Adding user User(email='{email}', username='{username}', name='{name}', role='{role[0:10]}...')")
            with self.dbh.create_cursor() as cursor:
                cursor.execute("INSERT INTO users (name, username, email, job) values (?, ?, ?, ?)", (name, username, email, role))

        elif command == "drop-user":
            email = kwargs["email"]
            if email in [None, ""]:
                info("To drop a user, specify a valid mail regex")
                email = self.wait_for_input()
            info(f"Deleting {email} from DB")
            with self.dbh.create_cursor() as cursor:
                cursor.execute("DELETE FROM users WHERE email LIKE ?", ("%" + email + "%", ))

        elif command == "found-logins":
            success("Valid Logins Collected:")
            sql = "SELECT * FROM found_logins"
            table = []
            with self.dbh.create_cursor() as cursor:
                cursor.execute(sql)
                for row in cursor:
                    table.append(list(row))
            print(tabulate(table, headers=["ID", "Target", "E-Mail", "Password"]))

        elif command == "show-info":
            cmd = f"python vortex.py -w {self.dbh.workspace} office -c show -D {domain}"
            info(f"To show MS related information, execute "
                 f"`{highlight(cmd)}`"
                 f"")
            cmd = f"python vortex.py -w {self.dbh.workspace} vpn -c show -D {domain}"
            info(f"To show VPN related information, execute "
                 f"`{highlight(cmd)}`"
                 f"")
            cmd = f"python vortex.py -w {self.dbh.workspace} subdomain -c show -D {domain}"
            info(f"To show DNS related information, execute "
                 f"`{highlight(cmd)}`"
                 f"")
            success(f"Showing Info for domain {domain}:")
            domain = f'%{domain}%'
            sql = "SELECT name, email_format, frontable, takeover FROM domains where name LIKE ?"
            args = (domain, )
            tables = []
            with self.dbh.create_cursor() as cursor:
                cursor.execute(sql, args)
                for table in cursor:
                    tables.append(table)
            print(tabulate(tables, headers=["Domain", "Email Format", "Fronting Possible", "Takeover Possible"], tablefmt="fancy_grid"))

        elif command == "drop-table":
            tables = []
            with self.dbh.create_cursor() as cursor:
                try:
                    cursor.execute("SELECT name FROM sqlite_schema WHERE type ='table' AND name NOT LIKE 'sqlite_%';")
                except sqlite3.OperationalError as e:
                    print(str(e))
                    if str(e).find("no such table") > -1:
                        cursor.execute(
                            "SELECT name FROM sqlite_master WHERE type ='table' AND name NOT LIKE 'sqlite_%';")
                    else:
                        raise e
                for table in cursor:
                    tables.append(table[0])

            print("[*] Select a table to truncate:")
            choice = -1

            for n, g in enumerate(tables, start=0):
                print(f"{n} : {g}")
            while choice < 0 or choice > len(tables) - 1:
                try:
                    choice = int(input("  $> "))
                except KeyboardInterrupt:
                    exit(1)
                except ValueError:
                    pass
            table = tables[choice]

            info(f"Deleting all data from {table}")
            with self.dbh.create_cursor() as cursor:
                cursor.execute(f"DELETE FROM `{table}`")
                cursor.execute("UPDATE `sqlite_sequence` SET `seq` = 0 WHERE `name` = ?;", (table, ))

        elif command == "export":
            export = kwargs["export_file"]
            quotes = kwargs["quotes"]
            no_headers = kwargs["no_headers"]
            if not export:
                error("Please provide a file to export the result to (-O <path-to-file>)")
                exit(1)
            tables = []
            with self.dbh.create_cursor() as cursor:
                try:
                    cursor.execute("SELECT name FROM sqlite_schema WHERE type ='table' AND name NOT LIKE 'sqlite_%';")
                except sqlite3.OperationalError as e:
                    if str(e).find("no such table") > -1:
                        cursor.execute(
                            "SELECT name FROM sqlite_master WHERE type ='table' AND name NOT LIKE 'sqlite_%';")
                    else:
                        raise e
                for table in cursor:
                    tables.append(table[0])

            info("Select a table to export:")
            choice = -1

            for n, g in enumerate(tables, start=0):
                print(f"{n} : {g}")
            while choice < 0 or choice > len(tables) - 1:
                try:
                    choice = int(input("  $> "))
                except KeyboardInterrupt:
                    exit(1)
                except ValueError:
                    pass
            table = tables[choice]
            columns = []
            with self.dbh.create_cursor() as cursor:
                cursor.execute(f"SELECT name FROM PRAGMA_TABLE_INFO('{table}')")
                for c in cursor:
                    columns.append(c[0])

            info("Select a column to export or -1 to export all:")
            choice = -2

            for n, g in enumerate(columns, start=0):
                print(f"{n} : {g}")
            while choice < -1 or choice > len(columns) - 1:
                try:
                    choice = int(input("  $> "))
                except KeyboardInterrupt:
                    exit(1)
                except ValueError:
                    pass

            if choice != -1:
                column = columns[choice]
            else:
                column = "`" + "`,`".join(columns) + "`"

            info(f"Exporting to {export}")

            with self.dbh.create_cursor() as cursor:
                cursor.execute(f"SELECT {column} FROM `{table}`")
                with open(export, "w", encoding="latin-1", errors="replace") as csvfile:
                    if not no_headers:
                        csvfile.write(column.replace("`", "") + "\n")
                    for record in cursor:
                        if quotes:
                            csvfile.write('"' + '","'.join([f"{record[column_index]}" for column_index in range(len(record))]) + '"\n')
                        else:
                            csvfile.write(','.join([f"{record[column_index]}" for column_index in range(len(record))]) + '\n')

        else:
            NotImplementedError(f"Action {command} not implemented")

        success("Done")
