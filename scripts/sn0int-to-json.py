import json

leaks = []
leak = {}
with open("../zzz_doosan/leaked.txt") as infile:
    uid = None
    mail = None
    creds = []
    for line in infile:
        if line.startswith("#"):
            leak["credentials"] = creds
            leaks.append(leak)
            creds = []
            leak = {"uid": line.split(",")[0].replace("#", ""),
                    "mail": line.split(",")[1].replace("\"", "").strip().split(" ")[0]}
        else:
            db = line.split(" ")[0].replace("\"", "")
            cred = line.split(" ")[1].replace("\"", "").replace("\n", "").strip(" ()")
            creds.append(cred)

with open("../zzz_doosan/leaked.json", "w") as outfile:
    json.dump(leaks, outfile)
