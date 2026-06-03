from premium_manager import create_premium_key, init_premium_tables


if __name__ == "__main__":
    init_premium_tables()

    print("Type de clé ? (1M / 3M / LIFE)")
    key_type = input(">>> ").strip().upper()

    if key_type == "1M":
        key = create_premium_key(
            plan_name="Premium 1 Mois",
            duration_days=30,
            max_uses=1,
            created_by="console"
        )
    elif key_type == "3M":
        key = create_premium_key(
            plan_name="Premium 3 Mois",
            duration_days=90,
            max_uses=1,
            created_by="console"
        )
    elif key_type == "LIFE":
        key = create_premium_key(
            plan_name="Premium Lifetime",
            duration_days=0,
            max_uses=1,
            created_by="console"
        )
    else:
        print("❌ Type invalide. Choisis 1M, 3M ou LIFE.")
        raise SystemExit

    print(f"✅ Clé générée : {key}")
