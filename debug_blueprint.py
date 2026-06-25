from app import create_app
from views.admin_environment import bp as admin_environment_bp

print("Imported admin_environment_bp:", admin_environment_bp)
print("Type:", type(admin_environment_bp))
print("Name:", admin_environment_bp.name)
print("Import name:", admin_environment_bp.import_name)
print("URL prefix:", admin_environment_bp.url_prefix)

app = create_app()
print("\nRegistered blueprints:")
for bp_name, bp in app.blueprints.items():
    print(f"  {bp_name}: {bp.name}")

print("\nChecking if admin_environment_bp is in app.blueprints:")
if admin_environment_bp.name in app.blueprints:
    print("YES - admin_environment blueprint is registered")
    registered_bp = app.blueprints[admin_environment_bp.name]
    print(f"  Registered blueprint name: {registered_bp.name}")
    print(f"  Same object? {registered_bp is admin_environment_bp}")
else:
    print("NO - admin_environment blueprint is NOT registered")

print("\nURL rules for admin_environment endpoints:")
for rule in app.url_map.iter_rules():
    if 'admin_environment' in rule.endpoint:
        print(f"{rule.endpoint} -> {rule.rule}")