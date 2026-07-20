from flask import Flask, redirect, request, session, render_template, url_for
import requests
import json
import os
from datetime import datetime

from database import (
    init_db,
    ensure_guild_exists,
    ensure_all_command_settings,
    get_all_command_settings,
    update_command_settings,
    COMMAND_CATEGORIES,
    ALL_COMMANDS,
    roles_to_text,
)

from premium_manager import (
    init_premium_tables,
    get_guild_premium,
    activate_premium_key,
    cleanup_expired_guild_premium,
    cleanup_expired_keys,
)

from dashboard_boutiques_darknet_v3 import register_boutiques_darknet_routes

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "bloodline_secret_key")

# =========================
# DISCORD OAUTH / BOT CONFIG
# =========================
CLIENT_ID ="1491454272326598796"
CLIENT_SECRET ="QCoFxMtUFFBeLKsT2IsFEdUZ5kaXRX2G"
REDIRECT_URI ="https://bloodline-tau.vercel.app"
BOT_TOKEN ="MTQ5MTQ1NDI3MjMyNjU5ODc5Ng.G2zCvd.c8G3rUrj0SFEzNE4qYbu8AuA6Eo4hmyiIkh1Yk"

DISCORD_API = "https://discord.com/api"
SUPPORT_INVITE =("SUPPORT_INVITE", "https://discord.gg/BWwmaUDCV8")

CUSTOM_FILE = "data/custom_rp.json"

def ensure_custom_file():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(CUSTOM_FILE):
        with open(CUSTOM_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=4, ensure_ascii=False)


def load_custom():
    ensure_custom_file()

    with open(CUSTOM_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_custom(data):
    ensure_custom_file()

    with open(CUSTOM_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_discord_user(access_token):
    response = requests.get(
        f"{DISCORD_API}/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return response.json()


def get_discord_guilds(access_token):
    response = requests.get(
        f"{DISCORD_API}/users/@me/guilds",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return response.json()


def parse_roles_ids(form, key):
    values = form.getlist(key)
    return json.dumps([v for v in values if v.strip()], ensure_ascii=False)


def parse_service_legal_jobs(form):
    role_ids = form.getlist("service_job_role_id")
    names = form.getlist("service_job_name")
    jobs = []

    for index, role_id in enumerate(role_ids):
        role_id = str(role_id).strip()
        if not role_id:
            continue

        name = ""
        if index < len(names):
            name = str(names[index]).strip()

        jobs.append({
            "role_id": role_id,
            "name": name
        })

    return json.dumps(jobs, ensure_ascii=False)


def load_service_legal_jobs(command_settings):
    row = command_settings.get("service")
    if not row:
        return []

    try:
        value = row["custom_value_1"] or "[]"
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def build_guild_icon_url(guild: dict):
    if guild.get("icon"):
        return f"https://cdn.discordapp.com/icons/{guild['id']}/{guild['icon']}.png?size=128"
    return None


def get_admin_guilds_with_icons(access_token):
    guilds = get_discord_guilds(access_token)

    if not isinstance(guilds, list):
        return []

    admin_guilds = [
        g for g in guilds
        if (int(g["permissions"]) & 0x8) == 0x8
    ]

    for guild in admin_guilds:
        guild["icon_url"] = build_guild_icon_url(guild)

    return admin_guilds


def get_sidebar_guilds(access_token, limit=12):
    guilds = get_admin_guilds_with_icons(access_token)
    return guilds[:limit]


# On enregistre les routes boutiques/darknet APRES avoir défini les fonctions utiles.
# Flask ne permet pas de remplacer facilement le premier enregistrement, donc on fait le vrai ici
# avec un nom de fonction différent côté module impossible. Le module v3 sera chargé correctement
# dans la version propre ci-dessous en évitant le register trop tôt.

def format_premium_row(row):
    if not row:
        return None

    expires_at = row["expires_at"]
    is_lifetime = expires_at is None
    expired = False
    expires_text = "À vie"

    if expires_at:
        try:
            expiry_dt = datetime.fromisoformat(expires_at)
            expired = expiry_dt < datetime.utcnow()
            expires_text = expiry_dt.strftime("%d/%m/%Y %H:%M")
        except Exception:
            expires_text = str(expires_at)

    return {
        "guild_id": row["guild_id"],
        "plan_name": row["plan_name"],
        "activated_by_user_id": row["activated_by_user_id"],
        "license_key": row["license_key"],
        "activated_at": row["activated_at"],
        "expires_at": expires_at,
        "expires_text": expires_text,
        "is_active": bool(row["is_active"]) and not expired,
        "is_lifetime": is_lifetime,
        "expired": expired,
    }


def get_guild_roles_from_bot(guild_id: str):
    guild_roles = []

    if not BOT_TOKEN:
        return guild_roles

    try:
        headers = {
            "Authorization": f"Bot {BOT_TOKEN}"
        }

        res = requests.get(
            f"{DISCORD_API}/guilds/{guild_id}/roles",
            headers=headers,
            timeout=10
        )

        if res.status_code == 200:
            roles_data = res.json()

            guild_roles = sorted(
                [
                    {
                        "id": str(role["id"]),
                        "name": role["name"]
                    }
                    for role in roles_data
                    if role["name"] != "@everyone"
                ],
                key=lambda r: r["name"].lower()
            )
        else:
            print(f"Erreur récupération rôles [{res.status_code}] : {res.text}")

    except Exception as e:
        print("Erreur récupération rôles:", e)

    return guild_roles


def get_guild_channels_from_bot(guild_id: str):
    guild_channels = []

    if not BOT_TOKEN:
        return guild_channels

    try:
        headers = {
            "Authorization": f"Bot {BOT_TOKEN}"
        }

        res = requests.get(
            f"{DISCORD_API}/guilds/{guild_id}/channels",
            headers=headers,
            timeout=10
        )

        if res.status_code == 200:
            channels_data = res.json()

            guild_channels = sorted(
                [
                    {
                        "id": str(channel["id"]),
                        "name": channel["name"],
                        "type": channel["type"]
                    }
                    for channel in channels_data
                    if channel.get("type") in [0, 5]
                ],
                key=lambda c: c["name"].lower()
            )
        else:
            print(f"Erreur récupération salons [{res.status_code}] : {res.text}")

    except Exception as e:
        print("Erreur récupération salons:", e)

    return guild_channels


# Routes boutiques/darknet ajoutées au dashboard
register_boutiques_darknet_routes(
    app,
    get_discord_user,
    get_admin_guilds_with_icons,
    get_sidebar_guilds,
    SUPPORT_INVITE
)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login")
def login():
    discord_login_url = (
        f"{DISCORD_API}/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify%20guilds"
    )
    return redirect(discord_login_url)


@app.route("/callback")
def callback():
    code = request.args.get("code")

    if not code:
        return "❌ Aucun code OAuth reçu."

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": "identify guilds",
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    token_response = requests.post(
        f"{DISCORD_API}/oauth2/token",
        data=data,
        headers=headers
    )

    token_data = token_response.json()
    access_token = token_data.get("access_token")

    if not access_token:
        return f"❌ Erreur OAuth2 : {token_data}"

    session["access_token"] = access_token
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    access_token = session.get("access_token")
    if not access_token:
        return redirect(url_for("home"))

    user = get_discord_user(access_token)
    admin_guilds = get_admin_guilds_with_icons(access_token)
    sidebar_guilds = get_sidebar_guilds(access_token)

    return render_template(
        "dashboard.html",
        user=user,
        guilds=admin_guilds,
        sidebar_guilds=sidebar_guilds,
        support_invite=SUPPORT_INVITE,
        active_page="dashboard"
    )


@app.route("/servers")
def servers():
    access_token = session.get("access_token")
    if not access_token:
        return redirect(url_for("home"))

    user = get_discord_user(access_token)
    admin_guilds = get_admin_guilds_with_icons(access_token)
    sidebar_guilds = get_sidebar_guilds(access_token)

    return render_template(
        "servers.html",
        user=user,
        guilds=admin_guilds,
        sidebar_guilds=sidebar_guilds,
        support_invite=SUPPORT_INVITE,
        active_page="servers"
    )


@app.route("/modules")
def modules():
    access_token = session.get("access_token")
    if not access_token:
        return redirect(url_for("home"))

    user = get_discord_user(access_token)
    sidebar_guilds = get_sidebar_guilds(access_token)

    modules_list = [
        {"name": "Convocation", "desc": "Système de convocation configurable."},
        {"name": "Police", "desc": "Amendes, fouille, perquisition, mandats."},
        {"name": "Braquage", "desc": "Braquages séparés avec étapes et argent sale."},
        {"name": "Drogue", "desc": "Récolte, vente, configuration par type."},
        {"name": "Blanchiment", "desc": "Transformation de l'argent sale en argent propre."},
        {"name": "Documents RP", "desc": "Cartes d'identité, permis, cartes grises, assurance."},
        {"name": "Entreprises", "desc": "Création, gestion, membres et finances d'entreprise."},
        {"name": "Prêt bancaire", "desc": "Demandes de prêts avec validation bancaire."},
        {"name": "Custom RP", "desc": "Création de braquages et drogues personnalisés."},
        {"name": "Boutiques", "desc": "Gère les boutiques créées avec /boutique creer depuis le dashboard."},
        {"name": "Marché Noir", "desc": "Gère les annonces Darknet visibles dans /telephone."}
    ]

    return render_template(
        "modules.html",
        user=user,
        sidebar_guilds=sidebar_guilds,
        support_invite=SUPPORT_INVITE,
        active_page="modules",
        modules_list=modules_list
    )


@app.route("/profile")
def profile():
    access_token = session.get("access_token")
    if not access_token:
        return redirect(url_for("home"))

    user = get_discord_user(access_token)
    sidebar_guilds = get_sidebar_guilds(access_token)

    avatar_url = None
    if user.get("avatar"):
        avatar_url = f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png?size=256"

    return render_template(
        "profile.html",
        user=user,
        sidebar_guilds=sidebar_guilds,
        support_invite=SUPPORT_INVITE,
        active_page="profile",
        avatar_url=avatar_url
    )


@app.route("/security")
def security():
    access_token = session.get("access_token")
    if not access_token:
        return redirect(url_for("home"))

    user = get_discord_user(access_token)
    sidebar_guilds = get_sidebar_guilds(access_token)

    return render_template(
        "security.html",
        user=user,
        sidebar_guilds=sidebar_guilds,
        support_invite=SUPPORT_INVITE,
        active_page="security"
    )


@app.route("/premium", methods=["GET", "POST"])
def premium():
    access_token = session.get("access_token")
    if not access_token:
        return redirect(url_for("home"))

    cleanup_expired_guild_premium()
    cleanup_expired_keys()

    user = get_discord_user(access_token)
    admin_guilds = get_admin_guilds_with_icons(access_token)
    sidebar_guilds = get_sidebar_guilds(access_token)

    message = None
    message_type = "info"

    if request.method == "POST":
        selected_guild_id = request.form.get("guild_id", "").strip()
        license_key = request.form.get("license_key", "").strip()

        selected_guild = None
        for guild in admin_guilds:
            if str(guild["id"]) == selected_guild_id:
                selected_guild = guild
                break

        if not selected_guild:
            message = "Serveur invalide ou accès refusé."
            message_type = "error"
        elif not license_key:
            message = "Tu dois entrer une clé premium."
            message_type = "error"
        else:
            success, result_message = activate_premium_key(
                license_key=license_key,
                guild_id=int(selected_guild_id),
                activated_by_user_id=int(user["id"])
            )
            message = result_message
            message_type = "success" if success else "error"

    premium_statuses = []
    for guild in admin_guilds:
        row = get_guild_premium(int(guild["id"]))
        status = format_premium_row(row)
        premium_statuses.append({
            "guild": guild,
            "premium": status
        })

    return render_template(
        "premium.html",
        user=user,
        sidebar_guilds=sidebar_guilds,
        support_invite=SUPPORT_INVITE,
        active_page="premium",
        guilds=admin_guilds,
        premium_statuses=premium_statuses,
        message=message,
        message_type=message_type
    )


@app.route("/guild/<guild_id>", methods=["GET", "POST"])
def guild_config(guild_id):
    access_token = session.get("access_token")

    if not access_token:
        return redirect(url_for("home"))

    user = get_discord_user(access_token)
    admin_guilds = get_admin_guilds_with_icons(access_token)
    sidebar_guilds = get_sidebar_guilds(access_token)

    selected_guild = None
    for guild in admin_guilds:
        if str(guild["id"]) == str(guild_id):
            selected_guild = guild
            break

    if not selected_guild:
        return "❌ Serveur introuvable ou accès refusé."

    guild_id_str = str(selected_guild["id"])

    ensure_guild_exists(guild_id_str, selected_guild["name"])
    ensure_all_command_settings(guild_id_str)

    if request.method == "POST":
        for command_name in ALL_COMMANDS:
            enabled = 1 if request.form.get(f"{command_name}_enabled") == "on" else 0

            allowed_roles = parse_roles_ids(request.form, f"{command_name}_allowed_roles")
            blocked_roles = parse_roles_ids(request.form, f"{command_name}_blocked_roles")

            channel_id = ",".join(request.form.getlist(f"{command_name}_channel_id"))
            log_channel_id = ",".join(request.form.getlist(f"{command_name}_log_channel_id"))

            custom_value_1 = request.form.get(f"{command_name}_custom_1", "").strip() or None
            custom_value_2 = request.form.get(f"{command_name}_custom_2", "").strip() or None
            custom_value_3 = request.form.get(f"{command_name}_custom_3", "").strip() or None

            if command_name == "service":
                custom_value_1 = parse_service_legal_jobs(request.form)

            if command_name == "pret_bancaire":
                custom_value_4 = parse_roles_ids(request.form, f"{command_name}_custom_4")
            else:
                custom_value_4 = request.form.get(f"{command_name}_custom_4", "").strip() or None

            update_command_settings(
                guild_id=guild_id_str,
                command_name=command_name,
                enabled=enabled,
                allowed_roles=allowed_roles,
                blocked_roles=blocked_roles,
                channel_id=channel_id,
                log_channel_id=log_channel_id,
                custom_value_1=custom_value_1,
                custom_value_2=custom_value_2,
                custom_value_3=custom_value_3,
                custom_value_4=custom_value_4
            )

    command_rows = get_all_command_settings(guild_id_str)
    command_settings = {row["command_name"]: row for row in command_rows}

    categorized_commands = {}
    for category, commands in COMMAND_CATEGORIES.items():
        categorized_commands[category] = []
        for cmd in commands:
            if cmd in command_settings:
                categorized_commands[category].append((cmd, command_settings[cmd]))

    guild_roles = get_guild_roles_from_bot(guild_id_str)
    guild_channels = get_guild_channels_from_bot(guild_id_str)
    service_legal_jobs = load_service_legal_jobs(command_settings)

    command_allowed_role_ids = {}
    command_blocked_role_ids = {}
    command_custom_role_ids = {}

    for cmd in command_settings:
        try:
            command_allowed_role_ids[cmd] = json.loads(command_settings[cmd]["allowed_roles"] or "[]")
        except Exception:
            command_allowed_role_ids[cmd] = []

        try:
            command_blocked_role_ids[cmd] = json.loads(command_settings[cmd]["blocked_roles"] or "[]")
        except Exception:
            command_blocked_role_ids[cmd] = []

        try:
            command_custom_role_ids[cmd] = json.loads(command_settings[cmd]["custom_value_4"] or "[]")
        except Exception:
            command_custom_role_ids[cmd] = []

    return render_template(
        "guild.html",
        user=user,
        guild=selected_guild,
        categorized_commands=categorized_commands,
        roles_to_text=roles_to_text,
        sidebar_guilds=sidebar_guilds,
        support_invite=SUPPORT_INVITE,
        active_page="servers",
        guild_roles=guild_roles,
        guild_channels=guild_channels,
        command_allowed_role_ids=command_allowed_role_ids,
        command_blocked_role_ids=command_blocked_role_ids,
        command_custom_role_ids=command_custom_role_ids,
        service_legal_jobs=service_legal_jobs
    )


@app.route("/guild/<guild_id>/custom", methods=["GET", "POST"])
def custom_config(guild_id):
    access_token = session.get("access_token")

    if not access_token:
        return redirect(url_for("home"))

    cleanup_expired_guild_premium()

    user = get_discord_user(access_token)
    admin_guilds = get_admin_guilds_with_icons(access_token)
    sidebar_guilds = get_sidebar_guilds(access_token)

    selected_guild = None
    for guild in admin_guilds:
        if str(guild["id"]) == str(guild_id):
            selected_guild = guild
            break

    if not selected_guild:
        return "❌ Serveur introuvable ou accès refusé."

    premium_row = get_guild_premium(int(guild_id))
    premium = format_premium_row(premium_row)

    if not premium or not premium["is_active"]:
        return "❌ Ce serveur n'a pas le premium BloodLine."

    data = load_custom()
    guild_id_str = str(guild_id)

    data.setdefault(guild_id_str, {})
    data[guild_id_str].setdefault("braquages", {})
    data[guild_id_str].setdefault("drogues", {})

    if request.method == "POST":
        action = request.form.get("action", "").strip()

        if action == "create_braquage":
            nom = request.form.get("nom", "").strip()
            recompense_min = request.form.get("recompense_min", "").strip()
            recompense_max = request.form.get("recompense_max", "").strip()
            cooldown = request.form.get("cooldown", "").strip()
            risque = request.form.get("risque", "").strip()

            if not nom:
                return "❌ Nom du braquage obligatoire."

            try:
                recompense_min = int(recompense_min)
                recompense_max = int(recompense_max)
                cooldown = int(cooldown)
                risque = int(risque)
            except ValueError:
                return "❌ Les valeurs du braquage doivent être des nombres."

            if recompense_min > recompense_max:
                return "❌ La récompense minimum ne peut pas être plus grande que la maximum."

            if risque < 0 or risque > 100:
                return "❌ Le risque police doit être entre 0 et 100."

            data[guild_id_str]["braquages"][nom.lower()] = {
                "nom": nom,
                "recompense_min": recompense_min,
                "recompense_max": recompense_max,
                "cooldown_minutes": cooldown,
                "risque_police": risque
            }

            save_custom(data)
            return redirect(url_for("custom_config", guild_id=guild_id_str))

        if action == "create_drogue":
            nom = request.form.get("nom", "").strip()
            prix = request.form.get("prix", "").strip()
            recolte_min = request.form.get("min", "").strip()
            recolte_max = request.form.get("max", "").strip()
            cooldown = request.form.get("cooldown", "").strip()

            if not nom:
                return "❌ Nom de la drogue obligatoire."

            try:
                prix = int(prix)
                recolte_min = int(recolte_min)
                recolte_max = int(recolte_max)
                cooldown = int(cooldown)
            except ValueError:
                return "❌ Les valeurs de la drogue doivent être des nombres."

            if recolte_min > recolte_max:
                return "❌ La récolte minimum ne peut pas être plus grande que la maximum."

            data[guild_id_str]["drogues"][nom.lower()] = {
                "nom": nom,
                "prix_unite": prix,
                "recolte_min": recolte_min,
                "recolte_max": recolte_max,
                "cooldown_minutes": cooldown
            }

            save_custom(data)
            return redirect(url_for("custom_config", guild_id=guild_id_str))

    return render_template(
        "custom.html",
        user=user,
        guild=selected_guild,
        sidebar_guilds=sidebar_guilds,
        support_invite=SUPPORT_INVITE,
        active_page="servers",
        braquages=data[guild_id_str].get("braquages", {}),
        drogues=data[guild_id_str].get("drogues", {})
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__ == "__main__":
    init_db()
    init_premium_tables()
    ensure_custom_file()
    print("✅ DASHBOARD BLOODLINE LANCÉ")
    app.run(debug=True)
