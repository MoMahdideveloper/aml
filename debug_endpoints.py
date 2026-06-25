from app import create_app
app = create_app()
print("Registered blueprints:")
for bp_name, bp in app.blueprints.items():
    print(f"  {bp_name}: {bp.name}")
print("\nURL rules containing 'admin_environment':")
for rule in app.url_map.iter_rules():
    if 'admin_environment' in rule.endpoint:
        print(f"{rule.endpoint} -> {rule.rule}")
print("\nAll endpoints:")
for rule in app.url_map.iter_rules():
    print(f"{rule.endpoint} -> {rule.rule}")