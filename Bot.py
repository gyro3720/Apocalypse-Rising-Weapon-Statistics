from requests.exceptions import HTTPError, ReadTimeout
import OAuth2Util
import praw
import sqlite3
import time


def main():
    # Open the log database
    sql = sqlite3.connect("log.db")
    cur = sql.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS log(ID TEXT, Timestamp INTEGER )")
    sql.commit()

    # Open the guns database
    conn = sqlite3.connect("weapons.db")
    c = conn.cursor()

    # Login
    r = praw.Reddit(user_agent="Apocalypse Rising Weapon Statistics")
    o = OAuth2Util.OAuth2Util(r, server_mode=True)

    while True:
        try:
            o.refresh()
            get_comments(cur, sql, c, r)
        except (
            praw.errors.RateLimitExceeded, praw.errors.HTTPException,
            HTTPError, ReadTimeout
        ) as e:
            print(e)
        time.sleep(1)


def get_comments(cur, sql, c, r):
    comments = r.get_comments("apocalypserising", limit=100)

    # Get a list of valid gun and melee weapons
    list_of_guns = []
    list_of_melee = []
    for row in list(c.execute("SELECT NAME FROM Guns")):
        list_of_guns.append(row[0])
    for row in list(c.execute("SELECT NAME FROM Melee")):
        list_of_melee.append(row[0])

    # Cycle through every comment
    for comment in comments:
        # Only check comments that called the bot and gave at least one weapon
        body = comment.body.split(" ")
        if body[0].lower() == "/u/weaponstatisticsbot" and len(body) >= 2:
            # Check if the comment ID hasn't been replied to
            cur.execute("SELECT ID FROM log WHERE ID=?", [comment.id])
            if not cur.fetchone():
                # Check if the gun is valid and if so, add its data to the list
                # and keep a total of valid guns
                comment_body = comment.body.lower().replace("-", "") \
                    .replace(" ", "")
                gun_weapon_data = []
                melee_weapon_data = []
                contains_gun = False
                contains_melee = False

                for weapon in list_of_guns:
                    if weapon.lower().replace("-", "").replace(" ", "") in \
                            comment_body:
                        c.execute("SELECT * FROM Guns WHERE NAME=?", [weapon])
                        gun_weapon_data.append(list(c.fetchall()[0]))
                        contains_gun = True

                for weapon in list_of_melee:
                    if weapon.lower().replace("-", "").replace(" ", "") in \
                            comment_body:
                        c.execute("SELECT * FROM Melee WHERE NAME=?", [weapon])
                        melee_weapon_data.append(list(c.fetchall()[0]))
                        contains_melee = True

                if contains_gun is True and contains_melee is False:
                    print(
                        "(" + comment.id + ") " + comment.author.name + ": " +
                        comment.body.replace("\n", " ")
                    )
                    response = build_gun_comment(gun_weapon_data)
                    comment_reply(comment, cur, sql, response)
                    time.sleep(1)

                if contains_gun is False and contains_melee is True:
                    print(
                        "(" + comment.id + ") " + comment.author.name + ": " +
                        comment.body.replace("\n", " ")
                    )
                    response = build_melee_comment(melee_weapon_data)
                    comment_reply(comment, cur, sql, response)
                    time.sleep(1)


def build_gun_comment(gun_weapon_data):
    response = (
        "Name | Class | Damage | DPS | Fire Rate | ADS Spread | Hip Fire Spread"
        " | Recoil | Attachment Capabilities | Magazine Capabilities\n"
        ":-------|:-------|:----------|:-----|:----------|:---------------|"
        ":-----------------|:--------|:-----------------------------|"
        ":-------------------------\n"
    )

    # Comparison loop
    # Check the length of the array rather than keep a variable
    contains_shotgun = False

    if len(gun_weapon_data) > 1:
        damage = 0
        dps = 0
        firerate = 0
        ads_spread = 10
        hipfire_spread = 50
        recoil = 50

        # Find the highest/lowest stats
        for weapon in gun_weapon_data:
            # Highest damage
            if weapon[2] > damage:
                damage = weapon[2]
            # Highest DPS
            if weapon[3] > dps:
                dps = weapon[3]
            # Highest fireratae
            if weapon[4] > firerate:
                firerate = weapon[4]
            # Lowest ADS spread
            if weapon[5] < ads_spread:
                ads_spread = weapon[5]
            # Lowest hipfire spread
            if weapon[6] < hipfire_spread:
                hipfire_spread = weapon[6]
            # Lowest recoil
            if weapon[7] < recoil:
                recoil = weapon[7]

        # Bold the highest/lowest stats
        for weapon in gun_weapon_data:
            # Divide shotgun damage by number of pellets
            if weapon[1] == "Shotgun":
                contains_shotgun = True
                if weapon[2] == damage:
                    weapon[2] = "**" + str(weapon[2]) + " (" + \
                                str(weapon[2] / 8) + "/pellet)" + "**"
                else:
                    weapon[2] = "**"
            else:
                if weapon[2] == damage:
                    weapon[2] = "**" + str(weapon[2]) + "**"
            # Check if the weapon's a pump action or bolt action
            if weapon[3] == 0:
                pumpaction = ["M870", "Maverick 88"]
                boltaction = ["Lee Enfield", "Mosin Nagant"]
                if weapon[0] in pumpaction:
                    weapon[3] = "**Pump Action**"
                if weapon[0] in boltaction:
                    weapon[3] = "**Bolt Action**"
            else:
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

        # Create the response payload
        for weapon in gun_weapon_data:
            for i in range(10):
                response += str(weapon[i]) + " | "
            response += "\n"
    else:
        # Create the response payload
        for weapon in gun_weapon_data:
            if weapon[1] == "Shotgun":
                contains_shotgun = True
                for i in range(2):
                    response += str(weapon[i]) + " | "
                # Damage
                response += str(weapon[2]) + " (" + str(weapon[2] / 8) + \
                    "/pellet) | "
                # DPS
                if weapon[3] == 0:
                    response += "Pump Action | "
                else:
                    response += str(weapon[3]) + " | "
                for i in range(4, 10):
                    response += str(weapon[i]) + " | "
            # Bolt action stuff
            elif weapon[0] in ["Lee Enfield", "Mosin Nagant"]:
                for i in range(3):
                    response += str(weapon[i]) + " | "
                # DPS
                response += "Bolt Action | "
                for i in range(4, 10):
                    response += str(weapon[i]) + " | "
            else:
                for i in range(10):
                    response += str(weapon[i]) + " | "
            response += "\n"

    if contains_shotgun:
        response += "\n* For shotguns each shot contains **8** pellets"

    response += (
        "\n* For ADS spread, hip fire spread, and recoil: **lower = better**"
        "\n\n---\n\n*I'm a bot. Was there an issue with this comparison? "
        "[Message the mods](http://www.reddit.com/message/"
        "compose?to=%2Fr%2FApocalypseRising).*"
    )

    return response


def build_melee_comment(melee_weapon_data):
    response = (
        "Name | Damage | Speed\n"
        ":-------|:-----------|:-------\n"
    )

    if len(melee_weapon_data) > 1:
        damage = 0
        speed = "slow"

        # Find the best stats
        for weapon in melee_weapon_data:
            # Highest damage
            if weapon[1] > damage:
                damage = weapon[1]
            if weapon[2] != "Slow":
                speed = "Fast"
                break

        # Bold the best stats
        for weapon in melee_weapon_data:
            if weapon[1] == damage:
                weapon[1] = "**" + str(weapon[1]) + "**"
            if weapon[2] == speed:
                weapon[2] = "**" + weapon[2] + "**"

    for weapon in melee_weapon_data:
        for i in range(3):
            response += str(weapon[i]) + " | "
        response += "\n"

    response += (
        "\n*I'm a bot. Was there an issue with this comparison? "
        "[Message the mods](http://www.reddit.com/message/"
        "compose?to=%2Fr%2FApocalypseRising).*"
    )

    return response


# Reply with the response payload
def comment_reply(comment, cur, sql, response):
    comment.reply(response)
    timestamp = int(time.time())
    cur.execute("INSERT INTO log VALUES(?,?)", (comment.id, timestamp))
    sql.commit()


if __name__ == "__main__":
    main()
