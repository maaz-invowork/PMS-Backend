INSERT INTO permissions (name, description) VALUES
('project:create', 'Create new projects'),
('project:read', 'View projects'),
('project:update', 'Edit project details'),
('project:delete', 'Delete projects'),
('members:manage', 'Add or remove members from a project'),
('board:manage', 'Create, update, or delete boards'),
('column:manage', 'Add, reorder, rename, or delete columns in a board'),
('task:create', 'Create new tasks'),
('task:update', 'Edit task details (title, description, due date, priority)'),
('task:assign', 'Assign tasks to team members'),
('task:status_update', 'Move cards across columns'),
('task:delete', 'Delete tasks');

INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM roles r
CROSS JOIN permissions p
WHERE 
    -- Admin gets all permissions
    (r.name = 'admin')
    
    OR (r.name = 'manager' AND p.name IN (
        'project:read', 'project:update','project:delete',
        'board:manage', 'column:manage', 'members:manage',
        'task:create', 'task:update', 'task:assign', 'task:status_update', 'task:delete'
    ))
    
    OR (r.name = 'member' AND p.name IN (
        'project:read', 'task:status_update'
    ));