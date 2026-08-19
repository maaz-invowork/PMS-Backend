from sqlalchemy import select
from sqlalchemy.orm import Session

from project_management_system.database import engine
from project_management_system.models import Permission, Role

DEFAULT_ROLES = [
    {"name": "admin", "description": "System Administrator with full permissions"},
    {"name": "manager", "description": "Project manager with elevated permissions"},
    {"name": "member", "description": "Standard user with standard permissions"},
]

DEFAULT_PERMISSIONS = [
    {"name": "project:create", "description": "Create new projects"},
    {"name": "project:read", "description": "View projects"},
    {"name": "project:update", "description": "Edit project details"},
    {"name": "project:delete", "description": "Delete projects"},
    {"name": "members:manage", "description": "Add or remove members from a project"},
    {"name": "board:manage", "description": "Create, update, or delete boards"},
    {"name": "column:manage", "description": "Add, reorder, rename, or delete columns in a board"},
    {"name": "task:create", "description": "Create new tasks"},
    {"name": "task:update", "description": "Edit task details (title, description, due date, priority)"},
    {"name": "task:assign", "description": "Assign tasks to team members"},
    {"name": "task:status_update", "description": "Move cards across columns"},
    {"name": "task:delete", "description": "Delete tasks"},
]

# Map role names to their corresponding permission strings
ROLE_PERMISSIONS_MAPPING = {
    "admin": [p["name"] for p in DEFAULT_PERMISSIONS],  # Admin gets all
    "manager": [
        "project:read",
        "project:update",
        "project:delete",
        "board:manage",
        "column:manage",
        "members:manage",
        "task:create",
        "task:update",
        "task:assign",
        "task:status_update",
        "task:delete",
    ],
    "member": [
        "project:read",
        "task:status_update",
    ],
}


def seed_database():
    """Seed roles, permissions, and role-permission mappings."""
    with Session(engine) as db:
        # 1. Seed Roles
        roles_dict = {}
        for role_data in DEFAULT_ROLES:
            role = db.scalar(select(Role).where(Role.name == role_data["name"]))
            if not role:
                role = Role(
                    name=role_data["name"],
                    description=role_data["description"],
                )
                db.add(role)
                db.flush()  # Ensures role.id is available
                print(f"Seeded default role: {role_data['name']}")
            roles_dict[role.name] = role

        # 2. Seed Permissions
        permissions_dict = {}
        for perm_data in DEFAULT_PERMISSIONS:
            permission = db.scalar(
                select(Permission).where(Permission.name == perm_data["name"])
            )
            if not permission:
                permission = Permission(
                    name=perm_data["name"],
                    description=perm_data["description"],
                )
                db.add(permission)
                db.flush()  # Ensures permission.id is available
                print(f"Seeded default permission: {perm_data['name']}")
            permissions_dict[permission.name] = permission

        # 3. Seed Role-Permissions Relationships
        for role_name, perm_names in ROLE_PERMISSIONS_MAPPING.items():
            role_obj = roles_dict.get(role_name)
            if not role_obj:
                continue

            for perm_name in perm_names:
                perm_obj = permissions_dict.get(perm_name)
                if perm_obj and perm_obj not in role_obj.permissions:
                    role_obj.permissions.append(perm_obj)
                    print(f"Assigned '{perm_name}' to role '{role_name}'")

        db.commit()


if __name__ == "__main__":
    seed_database()