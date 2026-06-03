
from flask import render_template_string, request, redirect, url_for, session
from database import get_connection

STYLE = """
<style>
body{margin:0;background:#050505;color:white;font-family:Arial,sans-serif}
body:before{content:"";position:fixed;inset:0;background:radial-gradient(circle at 20% 15%,rgba(255,0,0,.22),transparent 30%),linear-gradient(180deg,#090000,#020202);z-index:-1}
.wrap{max-width:1250px;margin:0 auto;padding:34px}.top{display:flex;justify-content:space-between;align-items:center;gap:18px;margin-bottom:26px}
h1{color:#ff2020;margin:0;font-size:34px}h2{margin:0 0 12px}.muted{color:rgba(255,255,255,.62)}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px}
.card{background:linear-gradient(145deg,rgba(255,255,255,.06),rgba(255,255,255,.02)),rgba(8,9,10,.86);border:1px solid rgba(255,35,35,.36);border-radius:18px;padding:22px;box-shadow:0 25px 70px rgba(0,0,0,.55)}
.btn{display:inline-flex;align-items:center;justify-content:center;padding:12px 18px;border-radius:10px;text-decoration:none;border:1px solid rgba(255,35,35,.55);background:rgba(255,0,0,.10);color:#ff3030;font-weight:900;cursor:pointer}
.btn-fill{color:white;border:0;background:linear-gradient(135deg,#ff3434,#a80000);box-shadow:0 0 24px rgba(255,0,0,.22)}
form{display:grid;gap:14px}label{color:rgba(255,255,255,.72);font-weight:800;font-size:14px}
input,textarea{width:100%;box-sizing:border-box;padding:13px 14px;border-radius:12px;border:1px solid rgba(255,255,255,.14);background:rgba(0,0,0,.45);color:white;outline:none;margin-top:7px}
table{width:100%;border-collapse:collapse;background:rgba(10,10,10,.75);border-radius:14px;overflow:hidden}
th,td{padding:14px;border-bottom:1px solid rgba(255,255,255,.08);text-align:left;vertical-align:middle}th{color:#ff3030;background:rgba(255,0,0,.08)}
.actions{display:flex;gap:10px;flex-wrap:wrap}
</style>
"""

BOUTIQUES_HTML = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><title>Boutiques</title>""" + STYLE + """</head><body><div class="wrap">
<div class="top"><div><h1>🏪 Boutiques</h1><p class="muted">Serveur : {{ guild.name }}</p></div><a class="btn" href="{{ url_for('guild_config', guild_id=guild.id) }}">← Retour configuration</a></div>
<div class="card" style="margin-bottom:22px"><h2>Créer une boutique</h2><p class="muted">Elle sera visible par le bot comme si elle avait été créée avec /boutique creer.</p><form method="POST" action="{{ url_for('dashboard_boutique_create', guild_id=guild.id) }}"><div><label>Nom de la boutique</label><input name="name" placeholder="Exemple : Ammu-Nation" required></div><button class="btn btn-fill" type="submit">Créer la boutique</button></form></div>
{% if shops %}<div class="grid">{% for shop in shops %}<div class="card"><h2>{{ shop["name"] }}</h2><p class="muted">Créée le {{ shop["created_at"] }}</p><div class="actions"><a class="btn btn-fill" href="{{ url_for('dashboard_boutique_items', guild_id=guild.id, shop_name=shop['name']) }}">Gérer les articles</a><a class="btn" href="{{ url_for('dashboard_boutique_delete', guild_id=guild.id, shop_id=shop['id']) }}">Supprimer</a></div></div>{% endfor %}</div>{% else %}<div class="card"><p class="muted">Aucune boutique. Crée-en une avec /boutique creer ou depuis le formulaire.</p></div>{% endif %}
</div></body></html>"""

ITEMS_HTML = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><title>Articles</title>""" + STYLE + """</head><body><div class="wrap">
<div class="top"><div><h1>📦 Articles — {{ shop_name }}</h1><p class="muted">Serveur : {{ guild.name }}</p></div><a class="btn" href="{{ url_for('dashboard_boutiques', guild_id=guild.id) }}">← Retour boutiques</a></div>
<div class="card" style="margin-bottom:22px"><h2>Ajouter un article</h2><form method="POST" action="{{ url_for('dashboard_boutique_item_add', guild_id=guild.id, shop_name=shop_name) }}"><div><label>Nom</label><input name="item_name" required></div><div><label>Stock</label><input name="stock" type="number" min="0" value="1" required></div><div><label>Prix</label><input name="price" type="number" min="0" value="100" required></div><button class="btn btn-fill" type="submit">Ajouter</button></form></div>
<div class="card"><h2>Articles existants</h2>{% if items %}<table><tr><th>Nom</th><th>Stock</th><th>Prix</th><th>Actions</th></tr>{% for item in items %}<tr><form method="POST" action="{{ url_for('dashboard_boutique_item_update', guild_id=guild.id, shop_name=shop_name, item_id=item['id']) }}"><td><input name="item_name" value="{{ item['item_name'] }}" required></td><td><input name="stock" type="number" min="0" value="{{ item['stock'] }}" required></td><td><input name="price" type="number" min="0" value="{{ item['price'] }}" required></td><td><div class="actions"><button class="btn btn-fill" type="submit">Modifier</button><a class="btn" href="{{ url_for('dashboard_boutique_item_delete', guild_id=guild.id, shop_name=shop_name, item_id=item['id']) }}">Supprimer</a></div></td></form></tr>{% endfor %}</table>{% else %}<p class="muted">Aucun article dans cette boutique.</p>{% endif %}</div>
</div></body></html>"""

DARKNET_HTML = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><title>Marché noir</title>""" + STYLE + """</head><body><div class="wrap">
<div class="top"><div><h1>🕶️ Marché noir</h1><p class="muted">Serveur : {{ guild.name }}</p></div><a class="btn" href="{{ url_for('guild_config', guild_id=guild.id) }}">← Retour configuration</a></div>
<div class="card" style="margin-bottom:22px"><h2>Créer un marché noir</h2><p class="muted">Crée une catégorie de marché noir, puis ajoute des articles dedans comme pour les boutiques.</p><form method="POST" action="{{ url_for('dashboard_darknet_create', guild_id=guild.id) }}"><div><label>Nom du marché noir</label><input name="name" placeholder="Exemple : Armes illégales" required></div><button class="btn btn-fill" type="submit">Créer le marché noir</button></form></div>
{% if shops %}<div class="grid">{% for shop in shops %}<div class="card"><h2>{{ shop["name"] }}</h2><p class="muted">Créé le {{ shop["created_at"] }}</p><div class="actions"><a class="btn btn-fill" href="{{ url_for('dashboard_darknet_items', guild_id=guild.id, shop_name=shop['name']) }}">Gérer les articles</a><a class="btn" href="{{ url_for('dashboard_darknet_delete', guild_id=guild.id, shop_id=shop['id']) }}">Supprimer</a></div></div>{% endfor %}</div>{% else %}<div class="card"><p class="muted">Aucun marché noir. Crée-en un depuis le formulaire.</p></div>{% endif %}
</div></body></html>"""

DARKNET_ITEMS_HTML = """<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><title>Articles marché noir</title>""" + STYLE + """</head><body><div class="wrap">
<div class="top"><div><h1>📦 Marché noir — {{ shop_name }}</h1><p class="muted">Serveur : {{ guild.name }}</p></div><a class="btn" href="{{ url_for('dashboard_darknet', guild_id=guild.id) }}">← Retour marché noir</a></div>
<div class="card" style="margin-bottom:22px"><h2>Ajouter un article</h2><p class="muted">Ces articles pourront ensuite être récupérés par le bot dans le market noir du téléphone.</p><form method="POST" action="{{ url_for('dashboard_darknet_item_add', guild_id=guild.id, shop_name=shop_name) }}"><div><label>Nom</label><input name="item_name" placeholder="Exemple : Glock 17" required></div><div><label>Stock</label><input name="stock" type="number" min="0" value="1" required></div><div><label>Prix</label><input name="price" type="number" min="0" value="1000" required></div><button class="btn btn-fill" type="submit">Ajouter</button></form></div>
<div class="card"><h2>Articles existants</h2>{% if items %}<table><tr><th>Nom</th><th>Stock</th><th>Prix</th><th>Actions</th></tr>{% for item in items %}<tr><form method="POST" action="{{ url_for('dashboard_darknet_item_update', guild_id=guild.id, shop_name=shop_name, item_id=item['id']) }}"><td><input name="item_name" value="{{ item['item_name'] }}" required></td><td><input name="stock" type="number" min="0" value="{{ item['stock'] }}" required></td><td><input name="price" type="number" min="0" value="{{ item['price'] }}" required></td><td><div class="actions"><button class="btn btn-fill" type="submit">Modifier</button><a class="btn" href="{{ url_for('dashboard_darknet_item_delete', guild_id=guild.id, shop_name=shop_name, item_id=item['id']) }}">Supprimer</a></div></td></form></tr>{% endfor %}</table>{% else %}<p class="muted">Aucun article dans ce marché noir.</p>{% endif %}</div>
</div></body></html>"""

def _ensure_dashboard_tables():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS shops (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT NOT NULL, name TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(guild_id, name))""")
    cur.execute("""CREATE TABLE IF NOT EXISTS shop_items (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT NOT NULL, shop_name TEXT NOT NULL, item_name TEXT NOT NULL, stock INTEGER NOT NULL DEFAULT 0, price INTEGER NOT NULL DEFAULT 0, UNIQUE(guild_id, shop_name, item_name))""")
    cur.execute("""CREATE TABLE IF NOT EXISTS darknet_market_posts (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT NOT NULL, seller_id INTEGER NOT NULL DEFAULT 0, title TEXT NOT NULL, description TEXT NOT NULL, price INTEGER NOT NULL, contact_info TEXT NOT NULL, is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS darknet_shops (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT NOT NULL, name TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(guild_id, name))""")
    cur.execute("""CREATE TABLE IF NOT EXISTS darknet_items (id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id TEXT NOT NULL, shop_name TEXT NOT NULL, item_name TEXT NOT NULL, stock INTEGER NOT NULL DEFAULT 0, price INTEGER NOT NULL DEFAULT 0, UNIQUE(guild_id, shop_name, item_name))""")
    conn.commit()
    conn.close()

def _get_authorized_guild(access_token, guild_id, get_discord_user, get_admin_guilds_with_icons, get_sidebar_guilds):
    user = get_discord_user(access_token)
    admin_guilds = get_admin_guilds_with_icons(access_token)
    sidebar_guilds = get_sidebar_guilds(access_token)
    selected = None
    for g in admin_guilds:
        if str(g["id"]) == str(guild_id):
            selected = g
            break
    return user, selected, sidebar_guilds

def register_boutiques_darknet_routes(app, get_discord_user, get_admin_guilds_with_icons, get_sidebar_guilds, support_invite):
    _ensure_dashboard_tables()

    @app.route("/guild/<guild_id>/boutiques")
    def dashboard_boutiques(guild_id):
        access_token = session.get("access_token")
        if not access_token:
            return redirect(url_for("home"))
        user, guild, sidebar = _get_authorized_guild(access_token, guild_id, get_discord_user, get_admin_guilds_with_icons, get_sidebar_guilds)
        if not guild:
            return "❌ Serveur introuvable ou accès refusé."
        conn = get_connection()
        shops = conn.execute("SELECT * FROM shops WHERE guild_id = ? ORDER BY name ASC", (str(guild_id),)).fetchall()
        conn.close()
        return render_template_string(BOUTIQUES_HTML, user=user, guild=guild, sidebar_guilds=sidebar, support_invite=support_invite, shops=shops)

    @app.route("/guild/<guild_id>/boutiques/create", methods=["POST"])
    def dashboard_boutique_create(guild_id):
        if "access_token" not in session:
            return redirect(url_for("home"))
        name = request.form.get("name", "").strip()
        if name:
            conn = get_connection()
            conn.execute("INSERT OR IGNORE INTO shops (guild_id, name) VALUES (?, ?)", (str(guild_id), name))
            conn.commit()
            conn.close()
        return redirect(url_for("dashboard_boutiques", guild_id=guild_id))

    @app.route("/guild/<guild_id>/boutiques/delete/<int:shop_id>")
    def dashboard_boutique_delete(guild_id, shop_id):
        if "access_token" not in session:
            return redirect(url_for("home"))
        conn = get_connection()
        shop = conn.execute("SELECT * FROM shops WHERE id = ? AND guild_id = ?", (shop_id, str(guild_id))).fetchone()
        if shop:
            conn.execute("DELETE FROM shop_items WHERE guild_id = ? AND shop_name = ?", (str(guild_id), shop["name"]))
            conn.execute("DELETE FROM shops WHERE id = ? AND guild_id = ?", (shop_id, str(guild_id)))
            conn.commit()
        conn.close()
        return redirect(url_for("dashboard_boutiques", guild_id=guild_id))

    @app.route("/guild/<guild_id>/boutiques/<shop_name>")
    def dashboard_boutique_items(guild_id, shop_name):
        access_token = session.get("access_token")
        if not access_token:
            return redirect(url_for("home"))
        user, guild, sidebar = _get_authorized_guild(access_token, guild_id, get_discord_user, get_admin_guilds_with_icons, get_sidebar_guilds)
        if not guild:
            return "❌ Serveur introuvable ou accès refusé."
        conn = get_connection()
        items = conn.execute("SELECT * FROM shop_items WHERE guild_id = ? AND shop_name = ? ORDER BY item_name ASC", (str(guild_id), shop_name)).fetchall()
        conn.close()
        return render_template_string(ITEMS_HTML, user=user, guild=guild, sidebar_guilds=sidebar, support_invite=support_invite, shop_name=shop_name, items=items)

    @app.route("/guild/<guild_id>/boutiques/<shop_name>/add", methods=["POST"])
    def dashboard_boutique_item_add(guild_id, shop_name):
        if "access_token" not in session:
            return redirect(url_for("home"))
        item_name = request.form.get("item_name", "").strip()
        stock = int(request.form.get("stock", 0))
        price = int(request.form.get("price", 0))
        if item_name:
            conn = get_connection()
            conn.execute("""INSERT INTO shop_items (guild_id, shop_name, item_name, stock, price) VALUES (?, ?, ?, ?, ?) ON CONFLICT(guild_id, shop_name, item_name) DO UPDATE SET stock = excluded.stock, price = excluded.price""", (str(guild_id), shop_name, item_name, stock, price))
            conn.commit()
            conn.close()
        return redirect(url_for("dashboard_boutique_items", guild_id=guild_id, shop_name=shop_name))

    @app.route("/guild/<guild_id>/boutiques/<shop_name>/update/<int:item_id>", methods=["POST"])
    def dashboard_boutique_item_update(guild_id, shop_name, item_id):
        if "access_token" not in session:
            return redirect(url_for("home"))
        item_name = request.form.get("item_name", "").strip()
        stock = int(request.form.get("stock", 0))
        price = int(request.form.get("price", 0))
        conn = get_connection()
        conn.execute("UPDATE shop_items SET item_name = ?, stock = ?, price = ? WHERE id = ? AND guild_id = ? AND shop_name = ?", (item_name, stock, price, item_id, str(guild_id), shop_name))
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard_boutique_items", guild_id=guild_id, shop_name=shop_name))

    @app.route("/guild/<guild_id>/boutiques/<shop_name>/delete/<int:item_id>")
    def dashboard_boutique_item_delete(guild_id, shop_name, item_id):
        if "access_token" not in session:
            return redirect(url_for("home"))
        conn = get_connection()
        conn.execute("DELETE FROM shop_items WHERE id = ? AND guild_id = ? AND shop_name = ?", (item_id, str(guild_id), shop_name))
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard_boutique_items", guild_id=guild_id, shop_name=shop_name))

    @app.route("/guild/<guild_id>/darknet")
    def dashboard_darknet(guild_id):
        access_token = session.get("access_token")
        if not access_token:
            return redirect(url_for("home"))
        user, guild, sidebar = _get_authorized_guild(access_token, guild_id, get_discord_user, get_admin_guilds_with_icons, get_sidebar_guilds)
        if not guild:
            return "❌ Serveur introuvable ou accès refusé."
        conn = get_connection()
        shops = conn.execute("SELECT * FROM darknet_shops WHERE guild_id = ? ORDER BY name ASC", (str(guild_id),)).fetchall()
        conn.close()
        return render_template_string(DARKNET_HTML, user=user, guild=guild, sidebar_guilds=sidebar, support_invite=support_invite, shops=shops)

    @app.route("/guild/<guild_id>/darknet/create", methods=["POST"])
    def dashboard_darknet_create(guild_id):
        if "access_token" not in session:
            return redirect(url_for("home"))
        name = request.form.get("name", "").strip()
        if name:
            conn = get_connection()
            conn.execute("INSERT OR IGNORE INTO darknet_shops (guild_id, name) VALUES (?, ?)", (str(guild_id), name))
            conn.commit()
            conn.close()
        return redirect(url_for("dashboard_darknet", guild_id=guild_id))

    @app.route("/guild/<guild_id>/darknet/delete/<int:shop_id>")
    def dashboard_darknet_delete(guild_id, shop_id):
        if "access_token" not in session:
            return redirect(url_for("home"))
        conn = get_connection()
        shop = conn.execute("SELECT * FROM darknet_shops WHERE id = ? AND guild_id = ?", (shop_id, str(guild_id))).fetchone()
        if shop:
            conn.execute("DELETE FROM darknet_items WHERE guild_id = ? AND shop_name = ?", (str(guild_id), shop["name"]))
            conn.execute("DELETE FROM darknet_shops WHERE id = ? AND guild_id = ?", (shop_id, str(guild_id)))
            conn.commit()
        conn.close()
        return redirect(url_for("dashboard_darknet", guild_id=guild_id))

    @app.route("/guild/<guild_id>/darknet/<shop_name>")
    def dashboard_darknet_items(guild_id, shop_name):
        access_token = session.get("access_token")
        if not access_token:
            return redirect(url_for("home"))
        user, guild, sidebar = _get_authorized_guild(access_token, guild_id, get_discord_user, get_admin_guilds_with_icons, get_sidebar_guilds)
        if not guild:
            return "❌ Serveur introuvable ou accès refusé."
        conn = get_connection()
        items = conn.execute("SELECT * FROM darknet_items WHERE guild_id = ? AND shop_name = ? ORDER BY item_name ASC", (str(guild_id), shop_name)).fetchall()
        conn.close()
        return render_template_string(DARKNET_ITEMS_HTML, user=user, guild=guild, sidebar_guilds=sidebar, support_invite=support_invite, shop_name=shop_name, items=items)

    @app.route("/guild/<guild_id>/darknet/<shop_name>/add", methods=["POST"])
    def dashboard_darknet_item_add(guild_id, shop_name):
        if "access_token" not in session:
            return redirect(url_for("home"))
        item_name = request.form.get("item_name", "").strip()
        stock = int(request.form.get("stock", 0))
        price = int(request.form.get("price", 0))
        if item_name:
            conn = get_connection()
            conn.execute("""INSERT INTO darknet_items (guild_id, shop_name, item_name, stock, price) VALUES (?, ?, ?, ?, ?) ON CONFLICT(guild_id, shop_name, item_name) DO UPDATE SET stock = excluded.stock, price = excluded.price""", (str(guild_id), shop_name, item_name, stock, price))
            conn.commit()
            conn.close()
        return redirect(url_for("dashboard_darknet_items", guild_id=guild_id, shop_name=shop_name))

    @app.route("/guild/<guild_id>/darknet/<shop_name>/update/<int:item_id>", methods=["POST"])
    def dashboard_darknet_item_update(guild_id, shop_name, item_id):
        if "access_token" not in session:
            return redirect(url_for("home"))
        item_name = request.form.get("item_name", "").strip()
        stock = int(request.form.get("stock", 0))
        price = int(request.form.get("price", 0))
        conn = get_connection()
        conn.execute("UPDATE darknet_items SET item_name = ?, stock = ?, price = ? WHERE id = ? AND guild_id = ? AND shop_name = ?", (item_name, stock, price, item_id, str(guild_id), shop_name))
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard_darknet_items", guild_id=guild_id, shop_name=shop_name))

    @app.route("/guild/<guild_id>/darknet/<shop_name>/delete/<int:item_id>")
    def dashboard_darknet_item_delete(guild_id, shop_name, item_id):
        if "access_token" not in session:
            return redirect(url_for("home"))
        conn = get_connection()
        conn.execute("DELETE FROM darknet_items WHERE id = ? AND guild_id = ? AND shop_name = ?", (item_id, str(guild_id), shop_name))
        conn.commit()
        conn.close()
        return redirect(url_for("dashboard_darknet_items", guild_id=guild_id, shop_name=shop_name))
