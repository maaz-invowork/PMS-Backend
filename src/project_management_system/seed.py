from sqlalchemy import select
from database import SessionLocal, engine, Base
from models import Role, Permission

DEFAULT_PERMISSIONS = [
    # Project management
    {"name": "project:create", "description": "Create new projects"},
    {"name": "project:delete", "description": "Delete projects"},
    {"name": "project:read", "description": "View projects"},
    
    # Board management
    {"name": "board:manage", "description": "Create, update, or delete boards and columns"},
    
    # Task management
    {"name": "task:create", "description": "Create new tasks"},
    {"name": "task:assign", "description": "Assign tasks to team members"},
    {"name": "task:status_update", "description": "Move cards across columns"},
    {"name": "task:delete", "description": "Delete tasks"},
]

# 2. Map Roles to Permissions
ROLE_MAP = {
    "admin": [p["name"] for p in DEFAULT_PERMISSIONS],  # All permissions
    
    "senior_manager": [
        "project:create", "project:delete", "project:read",
        "board:manage", "task:create", "task:assign", "task:status_update", "task:delete"
    ],
    
    "team_lead": [
        "project:read", "board:manage", "task:create",
        "task:assign", "task:status_update", "task:delete"
    ],
    
    "member": [
        "project:read", "task:status_update"
    ],
}


def seed_database():
    # Ensure all tables exist in PostgreSQL
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        print("Seeding Permissions...")
        perm_objects = {}
        for perm_data in DEFAULT_PERMISSIONS:
            existing_perm = db.scalar(
                select(Permission).where(Permission.name == perm_data["name"])
            )
            if not existing_perm:
                existing_perm = Permission(
                    name=perm_data["name"],
                    description=perm_data["description"]
                )
                db.add(existing_perm)
                db.flush()  # Assigns ID
            perm_objects[perm_data["name"]] = existing_perm

        print("Seeding Roles...")
        for role_name, perm_names in ROLE_MAP.items():
            existing_role = db.scalar(
                select(Role).where(Role.name == role_name)
            )
            
            # Map permission string names to Permission ORM models
            required_perms = [perm_objects[p_name] for p_name in perm_names]
            
            if not existing_role:
                new_role = Role(
                    name=role_name,
                    description=f"Default {role_name.replace('_', ' ').title()} role",
                    permissions=required_perms
                )
                db.add(new_role)
            else:
                # Update existing permissions in case new ones were added
                existing_role.permissions = required_perms

        db.commit()
        print("Database successfully seeded with default RBAC configuration!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()