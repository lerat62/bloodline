import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Any


COMMAND_CATEGORIES: dict[str, list[str]] = {
    "Économie": [
        "balance",
        "payer",
        "deposer",
        "retirer",
        "virement",
        "historique",
        "salaire",
        "blanchir"
    ],
    "Banque": [
        "pret_bancaire"
    ],
    "Inventaire & Armes": [
        "inventaire",
        "giveitem",
        "removeitem",
        "armes",
        "giveweapon",
        "removeweapon"
    ],
    "Boutique": [
        "boutique_creer",
        "boutique_supprimer",
        "boutique_liste",
        "boutique_voir",
        "item_boutique_ajouter",
        "item_boutique_retirer",
        "item_boutique_modifier",
        "acheter"
    ],
    "Métiers & Service": [
        "metier",
        "service",
        "service_finir",
        "enservice"
    ],
    "Profil": [
        "profil",
        "profil_joueur"
    ],
    "Police": [
        "set_police_role",
        "menotter",
        "escorter",
        "liberer",
        "recherche",
        "enlever_recherche",
        "mandat",
        "fouiller",
        "perquisition",
        "amende",
        "payer_amende",
        "voir_amendes",
        "clear_amendes",
        "casier",
        "clear_casier",
        "convocation"
    ],
    "Braquage": [
        "braquage_superette",
        "braquage_banque",
        "braquage_bijouterie",
        "porte",
        "percage",
        "coffre",
        "accepter_intervention",
        "braquage_status",
        "interrompre_braquage",
        "capturer_braqueur"
    ],
    "Logs & RP": [
        "logs_definir",
        "logs_voir",
        "logs_categories",
        "mortrp"
    ],
    "Drogue": [
        "drogue_recolter_weed",
        "drogue_recolter_cocaine",
        "drogue_recolter_meth",
        "drogue_traiter_weed",
        "drogue_traiter_cocaine",
        "drogue_traiter_meth",
        "drogue_vente_weed",
        "drogue_vente_cocaine",
        "drogue_vente_meth",
        "planque",
        "coffre_voiture"
    ],
    "Entreprise": [
        "entreprise_creer",
        "embauche",
        "licencier",
        "coffre_entreprise",
        "gestion_pdg",
        "paiement_interne"
    ],
    "Documents": [
        "identiter_creer",
        "identiter_afficher",
        "permis_creer",
        "permis_afficher",
        "cartegrise_creer",
        "cartegrise_afficher",
        "assurance_creer",
        "assurance_afficher",
        "portefeuille"
    ],
    "Immobilier": [
        "agence_immobiliere"
    ],
    "Organisation": [
        "session"
    ]
}


ALL_COMMANDS = []

for _, commands in COMMAND_CATEGORIES.items():
    for cmd in commands:
        if cmd not in ALL_COMMANDS:
            ALL_COMMANDS.append(cmd)


def get_connection():
    return psycopg2.connect(
        os.getenv("DATABASE_URL"),
        cursor_factory=RealDictCursor
    )


def ensure_extra_columns():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name='command_settings'
    """)

    cols = [row["column_name"] for row in cursor.fetchall()]

    if "custom_value_4" not in cols:
        cursor.execute("""
            ALTER TABLE command_settings
            ADD COLUMN custom_value_4 TEXT DEFAULT ''
        """)

    conn.commit()
    conn.close()



    
def init_db():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS guilds (
        guild_id TEXT PRIMARY KEY,
        guild_name TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS command_settings (
        id SERIAL PRIMARY KEY,
        guild_id TEXT NOT NULL,
        command_name TEXT NOT NULL,
        enabled INTEGER NOT NULL DEFAULT 1,
        allowed_roles TEXT NOT NULL DEFAULT '[]',
        blocked_roles TEXT NOT NULL DEFAULT '[]',
        channel_id TEXT DEFAULT '',
        log_channel_id TEXT DEFAULT '',
        custom_value_1 TEXT DEFAULT '',
        custom_value_2 TEXT DEFAULT '',
        custom_value_3 TEXT DEFAULT '',
        custom_value_4 TEXT DEFAULT '',
        UNIQUE(guild_id, command_name)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shops (
        id SERIAL PRIMARY KEY,
        guild_id TEXT NOT NULL,
        name TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(guild_id, name)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shop_items (
        id SERIAL PRIMARY KEY,
        guild_id TEXT NOT NULL,
        shop_name TEXT NOT NULL,
        item_name TEXT NOT NULL,
        stock INTEGER NOT NULL DEFAULT 0,
        price INTEGER NOT NULL DEFAULT 0,
        UNIQUE(guild_id, shop_name, item_name)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS darknet_market_posts (
        id SERIAL PRIMARY KEY,
        guild_id TEXT NOT NULL,
        seller_id TEXT NOT NULL DEFAULT '0',
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        price INTEGER NOT NULL,
        contact_info TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

    ensure_extra_columns()



def ensure_guild_exists(guild_id: str, guild_name: str):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO guilds (guild_id, guild_name)
    VALUES (%s, %s)
    ON CONFLICT(guild_id)
    DO UPDATE SET guild_name = EXCLUDED.guild_name
    """, (
        str(guild_id),
        guild_name
    ))

    conn.commit()
    conn.close()



def ensure_command_exists(guild_id: str, command_name: str):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO command_settings (
        guild_id,
        command_name,
        enabled,
        allowed_roles,
        blocked_roles,
        channel_id,
        log_channel_id,
        custom_value_1,
        custom_value_2,
        custom_value_3,
        custom_value_4
    )
    VALUES (%s,%s,1,'[]','[]','','','','','','')
    ON CONFLICT(guild_id, command_name)
    DO NOTHING
    """, (
        str(guild_id),
        command_name
    ))

    conn.commit()
    conn.close()



def ensure_all_command_settings(guild_id: str):

    for command_name in ALL_COMMANDS:
        ensure_command_exists(
            guild_id,
            command_name
        )



def get_all_command_settings(guild_id: str):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM command_settings
    WHERE guild_id = %s
    ORDER BY command_name ASC
    """, (
        str(guild_id),
    ))

    rows = cursor.fetchall()

    conn.close()

    return rows



def get_command_setting(guild_id: str, command_name: str):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM command_settings
    WHERE guild_id = %s
    AND command_name = %s
    """, (
        str(guild_id),
        command_name
    ))

    row = cursor.fetchone()

    conn.close()

    return row



def update_command_settings(
    guild_id,
    command_name,
    enabled,
    allowed_roles,
    blocked_roles,
    channel_id,
    log_channel_id,
    custom_value_1=None,
    custom_value_2=None,
    custom_value_3=None,
    custom_value_4=None
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO command_settings (
        guild_id,
        command_name,
        enabled,
        allowed_roles,
        blocked_roles,
        channel_id,
        log_channel_id,
        custom_value_1,
        custom_value_2,
        custom_value_3,
        custom_value_4
    )
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)

    ON CONFLICT(guild_id, command_name)

    DO UPDATE SET

        enabled = EXCLUDED.enabled,
        allowed_roles = EXCLUDED.allowed_roles,
        blocked_roles = EXCLUDED.blocked_roles,
        channel_id = EXCLUDED.channel_id,
        log_channel_id = EXCLUDED.log_channel_id,
        custom_value_1 = EXCLUDED.custom_value_1,
        custom_value_2 = EXCLUDED.custom_value_2,
        custom_value_3 = EXCLUDED.custom_value_3,
        custom_value_4 = EXCLUDED.custom_value_4

    """, (
        str(guild_id),
        command_name,
        int(enabled),
        allowed_roles or "[]",
        blocked_roles or "[]",
        channel_id or "",
        log_channel_id or "",
        custom_value_1 or "",
        custom_value_2 or "",
        custom_value_3 or "",
        custom_value_4 or ""
    ))

    conn.commit()
    conn.close()
def roles_to_text(raw_roles):

    if not raw_roles:
        return ""

    try:
        parsed = json.loads(raw_roles)

        if isinstance(parsed, list):
            return ", ".join(
                str(r)
                for r in parsed
                if str(r).strip()
            )

        return ""

    except Exception:
        return ""



def text_to_roles(raw_text):

    roles = [
        r.strip()
        for r in raw_text.split(",")
        if r.strip()
    ]

    return json.dumps(
        roles,
        ensure_ascii=False
    )



def safe_int(value: Any, default: int):

    try:
        return int(value)

    except Exception:
        return default



# =========================
# BOUTIQUES
# =========================


async def create_shop(guild_id, name):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO shops (
            guild_id,
            name
        )
        VALUES (%s,%s)
        ON CONFLICT(guild_id,name)
        DO NOTHING
    """, (
        str(guild_id),
        name
    ))

    conn.commit()
    conn.close()



async def get_shop(guild_id, name):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM shops
        WHERE guild_id=%s
        AND name=%s
    """, (
        str(guild_id),
        name
    ))

    result = cursor.fetchone()

    conn.close()

    return result



async def list_shops(guild_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name, created_at
        FROM shops
        WHERE guild_id=%s
    """, (
        str(guild_id),
    ))

    result = cursor.fetchall()

    conn.close()

    return result



async def delete_shop(guild_id, name):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM shops
        WHERE guild_id=%s
        AND name=%s
    """, (
        str(guild_id),
        name
    ))

    conn.commit()
    conn.close()



# =========================
# ITEMS BOUTIQUE
# =========================


async def add_shop_item(
    guild_id,
    shop_name,
    item_name,
    stock,
    price
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO shop_items (
            guild_id,
            shop_name,
            item_name,
            stock,
            price
        )
        VALUES (%s,%s,%s,%s,%s)

        ON CONFLICT(
            guild_id,
            shop_name,
            item_name
        )

        DO UPDATE SET

            stock = EXCLUDED.stock,
            price = EXCLUDED.price

    """, (
        str(guild_id),
        shop_name,
        item_name,
        stock,
        price
    ))

    conn.commit()
    conn.close()



async def get_shop_items(guild_id, shop_name):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT item_name, stock, price
        FROM shop_items
        WHERE guild_id=%s
        AND shop_name=%s
    """, (
        str(guild_id),
        shop_name
    ))

    result = cursor.fetchall()

    conn.close()

    return result



async def get_shop_item(
    guild_id,
    shop_name,
    item_name
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT item_name, stock, price
        FROM shop_items
        WHERE guild_id=%s
        AND shop_name=%s
        AND item_name=%s
    """, (
        str(guild_id),
        shop_name,
        item_name
    ))

    result = cursor.fetchone()

    conn.close()

    return result



async def remove_shop_item(
    guild_id,
    shop_name,
    item_name
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM shop_items

        WHERE guild_id=%s
        AND shop_name=%s
        AND item_name=%s

    """, (
        str(guild_id),
        shop_name,
        item_name
    ))

    conn.commit()
    conn.close()



async def update_shop_item(
    guild_id,
    shop_name,
    item_name,
    stock,
    price
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE shop_items

        SET stock=%s,
            price=%s

        WHERE guild_id=%s
        AND shop_name=%s
        AND item_name=%s

    """, (
        stock,
        price,
        str(guild_id),
        shop_name,
        item_name
    ))

    conn.commit()
    conn.close()



async def update_shop_item_stock(
    guild_id,
    shop_name,
    item_name,
    stock
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE shop_items

        SET stock=%s

        WHERE guild_id=%s
        AND shop_name=%s
        AND item_name=%s

    """, (
        stock,
        str(guild_id),
        shop_name,
        item_name
    ))

    conn.commit()
    conn.close()

init_db()
