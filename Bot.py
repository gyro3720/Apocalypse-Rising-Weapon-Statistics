import json
import praw
import re
import sqlite3
import time


def main(username, password, user_agent):

    # Open the log database
    sql = sqlite3.connect("log.db")
    cur = sql.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS log(ID TEXT, Timestamp INTEGER )")
    sql.commit()

    # Open the guns database
    conn = sqlite3.connect("weapons.db")
    c = conn.cursor()

    r = praw.Reddit(user_agent=user_agent)
    r.login(username, password)

    while True:
        get_comments(cur, sql, c, r, username)
        time.sleep(3)

def get_comments(cur, sql, c, r, username):
    comments = r.get_comments("test", limit=500)

    # Cycle through every comment
    for comment in comments:
        # Check if the comment ID hasn't been replied to
        cur.execute("SELECT ID FROM log WHERE ID=?", [comment.id])
        if not cur.fetchone():
            body = comment.body.split(" ")
            call = "/u/" + username.lower()
            # Only check comments that called the bot
            if body[0].lower() == call and len(body) >= 2:
                # Get a list of valid weapons
                list_of_rifles = []
                list_of_melee = []
                for row in list(c.execute("SELECT NAME FROM Guns")):
                    list_of_rifles.append(row[0])
                for row in list(c.execute("SELECT NAME FROM Melee")):
                    list_of_melee.append(row[0])

                # Check if the gun is valid and if so, add its data to the list and keep a total of valid guns
                weapon_data = []
                number_of_weapons = 0
                contains_rifle = False

                for weapon in list_of_rifles:
                    if re.search(r'(\s|^|$)' + weapon + r'(\s|^|$)', comment.body, flags=re.IGNORECASE):
                        c.execute("SELECT * FROM Guns WHERE NAME=?", [weapon])
                        weapon_data.append(list(c.fetchall()[0]))
                        number_of_weapons += 1
                        contains_rifle = True

                contains_melee = False
                # if number_of_weapons == 0:
                if contains_rifle is True:
                    while contains_melee is False:
                        for weapon in list_of_melee:
                            if re.search(r'(\s|^|$)' + weapon + r'(\s|^|$)', comment.body, flags=re.IGNORECASE):
                                c.execute("SELECT * FROM Melee WHERE NAME=?", [weapon])
                                weapon_data.append(list(c.fetchall()[0]))
                                number_of_weapons += 1
                                contains_melee = True

def valid_comment(cur, sql, comment, number_of_weapons, weapon_data):
    print("(" + comment.id + ") " + comment.author.name + ": " + comment.body)

    response = (
        "Name | Class | Damage | DPS | Fire Rate | ADS Spread | Hip Fire Spread | Recoil | Attachment Capabilities | "
        "Magazine Capabilities\n"
        ":-------|:-------|:----------|:-----|:----------|:---------------|:-----------------|:--------|"
        ":-----------------------------|:-------------------------\n"
    )

    if number_of_weapons > 1:
        damage = 0
        dps = 0
        firerate = 0
        ads_spread = 10
        hipfire_spread = 50
        recoil = 50

        # Find the highest/lowest stats
        for weapon in weapon_data:
            if weapon[2] > damage:
                damage = weapon[2]
            try:
                if weapon[3] > dps:
                    dps = weapon[3]
            except TypeError:
                pumpaction = ["M870", "Maverick 88"]
                boltaction = ["Lee Einfeld", "Mosin Nagant"]
                if weapon[0] in pumpaction:
                    weapon[3] = "***Pump Action***"
                if weapon[0] in boltaction:
                    weapon[3] = "***Bolt Action***"
            if weapon[4] > firerate:
                firerate = weapon[4]
            if weapon[5] < ads_spread:
                ads_spread = weapon[5]
            if weapon[6] < hipfire_spread:
                hipfire_spread = weapon[6]
            if weapon[7] < recoil:
                recoil = weapon[7]

        # Bold the highest/lowest stats
        for weapon in weapon_data:
            if weapon[2] == damage:
                weapon[2] = "**" + str(weapon[2]) + "**"
            if weapon[3] == dps:
                weapon[3] = "**" + str(weapon[3]) + "**"
            if weapon[4] == firerate:
                weapon[4] = "**" + str(weapon[4]) + "**"
            if weapon[5] == ads_spread:
                weapon[5] = "**" + str(weapon[5]) + "**"
            if weapon[6] == hipfire_spread:
                weapon[6] = "**" + str(weapon[6]) + "**"
            if weapon[7] == recoil:
                weapon[7] = "**" + str(weapon[7]) + "**"

    for weapon in weapon_data:
        for i in range(10):
            response += str(weapon[i]) + " | "
        response += "\n"

    response += ("\n* For ADS spread, hip fire spread, and recoil: **lower = better**\n\n"
                 "---\n\n"
                 "*I'm a bot. Was there an issue with this comparison? "
                 "[Message the mods](http://www.reddit.com/message/compose?to=%2Fr%2FApocalypseRising).*")

    print(response)

    timestamp = int(time.time())
    cur.execute("INSERT INTO log VALUES(?,?)", (comment.id, timestamp))
    sql.commit()

if __name__ == "__main__":
    with open("info.json") as info:
        info = json.load(info)
        username = info["Reddit"]["username"]
        password = info["Reddit"]["password"]
        user_agent = info["Reddit"]["user_agent"]

    main(username, password, user_agent)