// -*- coding: utf-8 -*-
// Copyright (c) 2026 Future Internet Consulting and Development Solutions S.L.

// This file is part of Wirecloud.

// Wirecloud is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

// Wirecloud is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.

// You should have received a copy of the GNU Affero General Public License
// along with Wirecloud.  If not, see <http://www.gnu.org/licenses/>.

/* globals Wirecloud, StyledElements */


(function (ns, se, utils) {

    "use strict";

    const privates = new WeakMap();

    const fetchElasticsearchData = function fetchElasticsearchData(namespace, maxresults = 1000) {
        return new Promise((resolve, reject) => {
            Wirecloud.io.makeRequest(Wirecloud.URLs.SEARCH_SERVICE, {
                method: 'GET',
                parameters: {
                    namespace: namespace,
                    q: '',
                    maxresults: maxresults
                },
                contentType: 'application/json',
                requestHeaders: {'Accept': 'application/json'},
                onSuccess: function(response) {
                    try {
                        const data = JSON.parse(response.responseText);
                        resolve(data);
                    } catch (e) {
                        reject(e);
                    }
                },
                onFailure: function() {
                    reject(new Error('Failed to fetch ' + namespace));
                }
            });
        });
    };

    const AVAILABLE_PERMISSIONS = [

        {
            key: 'SWITCH_USER',
            label: utils.gettext('Switch User'),
            description: utils.gettext('Allows the user to switch to another user. This will make the user gain all permissions of the switched user (and looses all permissions of the current user, except for this one).'),
            category: 'General'
        },

        {
            key: 'WORKSPACE.CREATE',
            label: utils.gettext('Create Workspaces'),
            description: utils.gettext('Allows the user to create a workspace.'),
            category: 'Workspace'
        },
        {
            key: 'WORKSPACE.VIEW',
            label: utils.gettext('View All Workspaces'),
            description: utils.gettext('Allows the user to view all workspaces.'),
            category: 'Workspace'
        },
        {
            key: 'WORKSPACE.EDIT',
            label: utils.gettext('Edit Workspaces'),
            description: utils.gettext('Allows the user to edit workspaces owned by other users.'),
            category: 'Workspace'
        },
        {
            key: 'WORKSPACE.DELETE',
            label: utils.gettext('Delete Workspaces'),
            description: utils.gettext('Allows the user to delete workspaces owned by other users.'),
            category: 'Workspace'
        },
        {
            key: 'WORKSPACE.CLONE',
            label: utils.gettext('Clone Workspaces'),
            description: utils.gettext('Allows the user to clone workspaces owned by other users.'),
            category: 'Workspace'
        },
        {
            key: 'WORKSPACE.PUBLISH',
            label: utils.gettext('Publish Workspaces'),
            description: utils.gettext('Allows the user to publish your workspaces.'),
            category: 'Workspace'
        },
        {
            key: 'WORKSPACE.PUBLISH.OTHER',
            label: utils.gettext('Publish Other Workspaces'),
            description: utils.gettext('Allows the user to publish workspaces owned by other users.'),
            category: 'Workspace'
        },
        {
            key: 'WORKSPACE.SHARE',
            label: utils.gettext('Share Workspaces'),
            description: utils.gettext('Allows the user to share workspaces owned by other users.'),
            category: 'Workspace'
        },
        {
            key: 'WORKSPACE.MERGE',
            label: utils.gettext('Merge Workspaces'),
            description: utils.gettext('Allows the user to merge workspaces owned by other users.'),
            category: 'Workspace'
        },
        {
            key: 'WORKSPACE.PREFERENCES.EDIT',
            label: utils.gettext('Edit Workspace Preferences'),
            description: utils.gettext('Allows the user to edit preferences of workspaces owned by other users.'),
            category: 'Workspace'
        },
        {
            key: 'WORKSPACE.TAB.CREATE',
            label: utils.gettext('Create Workspace Tabs'),
            description: utils.gettext('Allows the user to create tabs in workspaces owned by other users.'),
            category: 'Workspace Tabs'
        },
        {
            key: 'WORKSPACE.TAB.EDIT',
            label: utils.gettext('Edit Workspace Tabs'),
            description: utils.gettext('Allows the user to edit tabs in workspaces owned by other users.'),
            category: 'Workspace Tabs'
        },
        {
            key: 'WORKSPACE.TAB.DELETE',
            label: utils.gettext('Delete Workspace Tabs'),
            description: utils.gettext('Allows the user to delete tabs in workspaces owned by other users.'),
            category: 'Workspace Tabs'
        },
        {
            key: 'WORKSPACE.TAB.PREFERENCES.EDIT',
            label: utils.gettext('Edit Tab Preferences'),
            description: utils.gettext('Allows the user to edit preferences of tabs in workspaces owned by other users.'),
            category: 'Workspace Tabs'
        },
        {
            key: 'WORKSPACE.WIDGET.CREATE',
            label: utils.gettext('Create Widgets'),
            description: utils.gettext('Allows the user to create widgets in workspaces owned by other users.'),
            category: 'Workspace Widgets'
        },
        {
            key: 'WORKSPACE.WIDGET.VIEW',
            label: utils.gettext('View Widgets'),
            description: utils.gettext('Allows the user to view widgets in workspaces owned by other users.'),
            category: 'Workspace Widgets'
        },
        {
            key: 'WORKSPACE.WIDGET.EDIT',
            label: utils.gettext('Edit Widgets'),
            description: utils.gettext('Allows the user to edit widgets in workspaces owned by other users.'),
            category: 'Workspace Widgets'
        },
        {
            key: 'WORKSPACE.WIDGET.DELETE',
            label: utils.gettext('Delete Widgets'),
            description: utils.gettext('Allows the user to delete widgets in workspaces owned by other users.'),
            category: 'Workspace Widgets'
        },
        {
            key: 'WORKSPACE.WIDGET.PREFERENCES.EDIT',
            label: utils.gettext('Edit Widget Preferences'),
            description: utils.gettext('Allows the user to edit preferences of widgets in workspaces owned by other users.'),
            category: 'Workspace Widgets'
        },
        {
            key: 'WORKSPACE.WIDGET.PROPERTIES.EDIT',
            label: utils.gettext('Edit Widget Properties'),
            description: utils.gettext('Allows the user to edit properties of widgets in workspaces owned by other users.'),
            category: 'Workspace Widgets'
        },
        {
            key: 'WORKSPACE.OPERATOR.CREATE',
            label: utils.gettext('Create Operators'),
            description: utils.gettext('Allows the user to create operators in workspaces owned by other users.'),
            category: 'Workspace Operators'
        },
        {
            key: 'WORKSPACE.OPERATOR.DELETE',
            label: utils.gettext('Delete Operators'),
            description: utils.gettext('Allows the user to delete operators in workspaces owned by other users.'),
            category: 'Workspace Operators'
        },
        {
            key: 'WORKSPACE.OPERATOR.PREFERENCES.EDIT',
            label: utils.gettext('Edit Operator Preferences'),
            description: utils.gettext('Allows the user to edit preferences of operators in workspaces owned by other users.'),
            category: 'Workspace Operators'
        },
        {
            key: 'WORKSPACE.OPERATOR.PROPERTIES.EDIT',
            label: utils.gettext('Edit Operator Properties'),
            description: utils.gettext('Allows the user to edit properties of operators in workspaces owned by other users.'),
            category: 'Workspace Operators'
        },
        {
            key: 'WORKSPACE.WIRING.CREATE',
            label: utils.gettext('Create Wiring'),
            description: utils.gettext('Allows the user to create wiring in workspaces owned by other users.'),
            category: 'Workspace Wiring'
        },
        {
            key: 'WORKSPACE.WIRING.EDIT',
            label: utils.gettext('Edit Wiring'),
            description: utils.gettext('Allows the user to edit wiring in workspaces owned by other users.'),
            category: 'Workspace Wiring'
        },
        {
            key: 'WORKSPACE.WIRING.DELETE',
            label: utils.gettext('Delete Wiring'),
            description: utils.gettext('Allows the user to delete wiring in workspaces owned by other users.'),
            category: 'Workspace Wiring'
        },

        {
            key: 'COMPONENT.INSTALL',
            label: utils.gettext('Install Components'),
            description: utils.gettext('Allows the user to install components.'),
            category: 'Component'
        },
        {
            key: 'COMPONENT.VIEW',
            label: utils.gettext('View Components'),
            description: utils.gettext('Allows the user to view all components.'),
            category: 'Component'
        },
        {
            key: 'COMPONENT.UNINSTALL',
            label: utils.gettext('Uninstall Components'),
            description: utils.gettext('Allows the user to uninstall one version of a component.'),
            category: 'Component'
        },
        {
            key: 'COMPONENT.DELETE',
            label: utils.gettext('Delete Components'),
            description: utils.gettext('Allows the user to delete all versions of a component at once'),
            category: 'Component'
        },

        {
            key: 'MARKETPLACE.CREATE',
            label: utils.gettext('Create Marketplace'),
            description: utils.gettext('Allows the user to create a marketplace.'),
            category: 'Marketplace'
        },
        {
            key: 'MARKETPLACE.VIEW',
            label: utils.gettext('View Marketplaces'),
            description: utils.gettext('Allows the user to view all marketplaces.'),
            category: 'Marketplace'
        },
        {
            key: 'MARKETPLACE.DELETE',
            label: utils.gettext('Delete Marketplaces'),
            description: utils.gettext('Allows the user to delete marketplaces owned by other users.'),
            category: 'Marketplace'
        },
        {
            key: 'MARKETPLACE.PUBLISH',
            label: utils.gettext('Publish Marketplaces'),
            description: utils.gettext('Allows the user to publish marketplaces owned by other users.'),
            category: 'Marketplace'
        },

        {
            key: 'USER.CREATE',
            label: utils.gettext('Create Users'),
            description: utils.gettext('Allows the user to create a user.'),
            category: 'Auth'
        },
        {
            key: 'USER.VIEW',
            label: utils.gettext('View Users'),
            description: utils.gettext('Allows the user to view all users.'),
            category: 'Auth'
        },
        {
            key: 'USER.EDIT',
            label: utils.gettext('Edit Users'),
            description: utils.gettext('Allows the user to edit users.'),
            category: 'Auth'
        },
        {
            key: 'USER.DELETE',
            label: utils.gettext('Delete Users'),
            description: utils.gettext('Allows the user to delete users.'),
            category: 'Auth'
        },
        {
            key: 'GROUP.CREATE',
            label: utils.gettext('Create Groups'),
            description: utils.gettext('Allows the user to create a group.'),
            category: 'Auth'
        },
        {
            key: 'GROUP.VIEW',
            label: utils.gettext('View Groups'),
            description: utils.gettext('Allows the user to view all groups.'),
            category: 'Auth'
        },
        {
            key: 'GROUP.EDIT',
            label: utils.gettext('Edit Groups'),
            description: utils.gettext('Allows the user to edit groups.'),
            category: 'Auth'
        },
        {
            key: 'GROUP.DELETE',
            label: utils.gettext('Delete Groups'),
            description: utils.gettext('Allows the user to delete groups.'),
            category: 'Auth'
        },
        {
            key: 'ORGANIZATION.CREATE',
            label: utils.gettext('Create Organizations'),
            description: utils.gettext('Allows the user to create an organization.'),
            category: 'Auth'
        },
        {
            key: 'ORGANIZATION.VIEW',
            label: utils.gettext('View Organizations'),
            description: utils.gettext('Allows the user to view all organizations.'),
            category: 'Auth'
        },
        {
            key: 'ORGANIZATION.EDIT',
            label: utils.gettext('Edit Organizations'),
            description: utils.gettext('Allows the user to edit organizations.'),
            category: 'Auth'
        },
        {
            key: 'ORGANIZATION.DELETE',
            label: utils.gettext('Delete Organizations'),
            description: utils.gettext('Allows the user to delete organizations.'),
            category: 'Auth'
        }
    ];

    const groupPermissionsByCategory = function groupPermissionsByCategory(permissions) {
        const categories = {};
        permissions.forEach(perm => {
            const categoryKey = perm.category || 'Other';
            if (!categories[categoryKey]) {
                categories[categoryKey] = [];
            }
            categories[categoryKey].push(perm);
        });
        return categories;
    };


    const parseErrorResponse = function parseErrorResponse(response, fallback) {
        try {
            const data = JSON.parse(response.responseText);
            return data.description || fallback;
        } catch (_) {
            return fallback;
        }
    };

    const createFormGroup = function createFormGroup(labelText, inputWidget) {
        const group = new se.Container({class: 'form-group'});
        const label = new se.Container({tagname: 'label'});
        label.wrapperElement.textContent = labelText;
        group.appendChild(label);
        group.appendChild(inputWidget);
        return group;
    };

    const getSelectedPermissions = function getSelectedPermissions(permissionCheckboxes) {
        return Object.keys(permissionCheckboxes).filter(k => permissionCheckboxes[k].getValue());
    };

    const createDialogActions = function createDialogActions(saveFn, cancelFn) {
        const actionsDiv = new se.Container({class: 'um-dialog-actions'});
        const saveBtn = new se.Button({text: utils.gettext('Save Changes'), class: 'btn-primary'});
        saveBtn.addEventListener('click', saveFn);
        const cancelBtn = new se.Button({text: utils.gettext('Cancel'), class: 'btn-default'});
        cancelBtn.addEventListener('click', cancelFn);
        actionsDiv.appendChild(saveBtn);
        actionsDiv.appendChild(cancelBtn);
        return actionsDiv;
    };

    const build_tab = function build_tab(context, options) {
        const container = new se.Container();
        container.addClassName('user-management-tab');

        const toolbar = new se.Container();
        toolbar.addClassName('um-toolbar');

        const backButton = new se.Button({text: utils.gettext('← Admin Panel'), class: 'btn-default'});
        backButton.addEventListener('click', function() {
            context.hide();
            new Wirecloud.ui.AdminPanelWindowMenu().show();
        });
        toolbar.appendChild(backButton);

        const searchBox = new se.TextField({placeholder: options.searchPlaceholder});
        searchBox.addClassName('um-search');
        searchBox.addEventListener('change', function() { options.onSearch(searchBox.getValue()); });
        toolbar.appendChild(searchBox);

        const addButton = new se.Button({text: options.addLabel, class: 'btn-primary'});
        addButton.addEventListener('click', options.onAdd);
        toolbar.appendChild(addButton);

        container.appendChild(toolbar);

        const errorAlert = new se.Alert({state: 'danger', class: 'um-edit-error', title: utils.gettext('Error:')});
        errorAlert.hide();
        container.appendChild(errorAlert);
        context[options.errorAlertKey] = errorAlert;

        const list = new se.Container();
        list.addClassName(options.listClass);
        context[options.listKey] = list.wrapperElement;
        container.appendChild(list);

        options.load();
        return container;
    };


    const parseHierarchyNodes = function parseHierarchyNodes(groups) {
        return groups.map(function(g) {
            const id = String(g.path[g.path.length - 1]);
            const parentId = g.path.length > 1 ? String(g.path[g.path.length - 2]) : null;
            return {id: id, name: g.name, is_organization: parentId === null, parent_id: parentId};
        });
    };

    const buildPermissionsGrid = function buildPermissionsGrid(activePermissions, permissionCheckboxes) {
        const permissionsByCategory = groupPermissionsByCategory(AVAILABLE_PERMISSIONS);
        const permissionsGrid = new se.Container({class: 'um-permissions-grid'});

        Object.keys(permissionsByCategory).forEach(category => {
            const categoryDiv = new se.Container({class: 'um-permission-category'});

            const categoryHeader = new se.Container({class: 'um-permission-category-header'});

            const categoryTitle = new se.Container({tagname: 'span', class: 'um-permission-category-title'});
            categoryTitle.wrapperElement.textContent = category;
            categoryHeader.appendChild(categoryTitle);

            const categoryActions = new se.Container({class: 'um-permission-category-actions'});

            const selectAllCheckbox = new se.CheckBox({initiallyChecked: false});
            const selectAllLabel = new se.Container({tagname: 'label', class: 'um-select-all-label'});
            selectAllLabel.appendChild(selectAllCheckbox);
            selectAllLabel.wrapperElement.insertAdjacentText('beforeend', utils.gettext('Select all'));
            categoryActions.appendChild(selectAllLabel);

            const collapseBtn = new se.Button({iconClass: 'fas fa-chevron-up', title: utils.gettext('Collapse'), plain: true, class: 'um-category-btn'});
            categoryActions.appendChild(collapseBtn);
            categoryHeader.appendChild(categoryActions);
            categoryDiv.appendChild(categoryHeader);

            const itemsWrapper = new se.Container({class: 'um-permission-items'});

            const categoryPerms = permissionsByCategory[category];

            const updateSelectAll = function() {
                const allChecked = categoryPerms.every(perm => permissionCheckboxes[perm.key].getValue());
                selectAllCheckbox.setValue(allChecked);
            };

            selectAllCheckbox.addEventListener('change', function() {
                const allSelected = selectAllCheckbox.getValue();
                categoryPerms.forEach(perm => {
                    permissionCheckboxes[perm.key].setValue(allSelected);
                });
            });

            let collapsed = false;
            collapseBtn.addEventListener('click', function() {
                collapsed = !collapsed;
                if (collapsed) {
                    itemsWrapper.wrapperElement.style.display = 'none';
                    collapseBtn.replaceIconClassName('fa-chevron-up', 'fa-chevron-down');
                    collapseBtn.wrapperElement.title = utils.gettext('Expand');
                } else {
                    itemsWrapper.wrapperElement.style.display = '';
                    collapseBtn.replaceIconClassName('fa-chevron-down', 'fa-chevron-up');
                    collapseBtn.wrapperElement.title = utils.gettext('Collapse');
                }
            });

            categoryPerms.forEach(perm => {
                const permItem = new se.Container({class: 'um-permission-item'});
                const hasPermission = activePermissions.includes(perm.key);
                const checkbox = new se.CheckBox({initiallyChecked: hasPermission});
                const checkboxLabel = new se.Container({tagname: 'label', class: 'checkbox um-permission-checkbox'});
                checkboxLabel.appendChild(checkbox);
                checkboxLabel.wrapperElement.insertAdjacentText('beforeend', perm.label);
                permissionCheckboxes[perm.key] = checkbox;
                checkbox.addEventListener('change', updateSelectAll);
                permItem.appendChild(checkboxLabel);
                if (perm.description) {
                    const desc = new se.Container({class: 'um-permission-description'});
                    desc.wrapperElement.textContent = perm.description;
                    permItem.appendChild(desc);
                }
                itemsWrapper.appendChild(permItem);
            });

            updateSelectAll();

            categoryDiv.appendChild(itemsWrapper);
            permissionsGrid.appendChild(categoryDiv);
        });

        return permissionsGrid;
    };


    const build_users_tab = function build_users_tab(context) {
        return build_tab(context, {
            searchPlaceholder: utils.gettext('Search users...'),
            onSearch: (q) => context.filterUsers(q),
            addLabel: utils.gettext('Create User'),
            onAdd: () => context.showAddUserDialog(),
            errorAlertKey: 'usersErrorAlert',
            listClass: 'um-users-list',
            listKey: 'usersList',
            load: () => context.loadUsers()
        });
    };

    const build_groups_tab = function build_groups_tab(context) {
        return build_tab(context, {
            searchPlaceholder: utils.gettext('Search groups...'),
            onSearch: (q) => context.filterGroups(q),
            addLabel: utils.gettext('Create Group'),
            onAdd: () => context.showAddGroupDialog(),
            errorAlertKey: 'groupsErrorAlert',
            listClass: 'um-groups-list',
            listKey: 'groupsList',
            load: () => context.loadGroups()
        });
    };

    const build_organizations_tab = function build_organizations_tab(context) {
        return build_tab(context, {
            searchPlaceholder: utils.gettext('Search organizations...'),
            onSearch: (q) => context.filterOrganizations(q),
            addLabel: utils.gettext('Create Organization'),
            onAdd: () => context.showAddOrganizationDialog(),
            errorAlertKey: 'orgsErrorAlert',
            listClass: 'um-orgs-list',
            listKey: 'orgsList',
            load: () => context.loadOrganizations()
        });
    };

    const build_user_card = function build_user_card(user, context) {
        const card = new se.Container({class: 'um-card'});

        const header = new se.Container({class: 'um-card-header'});

        const avatar = new se.Container({class: 'um-avatar'});
        avatar.wrapperElement.textContent = user.username.charAt(0).toUpperCase();
        header.appendChild(avatar);

        const info = new se.Container({class: 'um-card-info'});

        const name = new se.Container({class: 'um-card-title'});
        name.wrapperElement.textContent = user.username;
        info.appendChild(name);

        const fullname = new se.Container({class: 'um-card-subtitle'});
        fullname.wrapperElement.textContent = user.fullname || '-';
        info.appendChild(fullname);

        header.appendChild(info);
        card.appendChild(header);

        const actions = new se.Container({class: 'um-card-actions'});

        const editBtn = new se.Button({
            text: utils.gettext('Edit'),
            class: 'btn-sm btn-default'
        });
        editBtn.addEventListener('click', function() {
            context.showEditUserDialog(user);
        });
        actions.appendChild(editBtn);

        const deleteBtn = new se.Button({
            text: utils.gettext('Delete'),
            class: 'btn-sm btn-danger'
        });
        deleteBtn.addEventListener('click', function() {
            context.showDeleteUserDialog(user);
        });
        actions.appendChild(deleteBtn);

        card.appendChild(actions);

        return card.wrapperElement;
    };

    const build_group_card = function build_group_card(group, context) {
        const card = new se.Container({class: 'um-card'});

        const header = new se.Container({class: 'um-card-header'});

        const icon = new se.Container({class: 'um-icon'});
        icon.wrapperElement.innerHTML = '<i class="fas fa-users"></i>';
        header.appendChild(icon);

        const info = new se.Container({class: 'um-card-info'});

        const name = new se.Container({class: 'um-card-title'});
        name.wrapperElement.textContent = group.name;
        info.appendChild(name);

        header.appendChild(info);
        card.appendChild(header);

        const actions = new se.Container({class: 'um-card-actions'});

        const membersBtn = new se.Button({
            text: utils.gettext('Edit'),
            class: 'btn-sm btn-default'
        });
        membersBtn.addEventListener('click', function() {
            context.showEditGroupDialog(group, false);
        });
        actions.appendChild(membersBtn);

        const deleteBtn = new se.Button({
            text: utils.gettext('Delete'),
            class: 'btn-sm btn-danger'
        });
        deleteBtn.addEventListener('click', function() {
            context.showDeleteGroupDialog(group);
        });
        actions.appendChild(deleteBtn);

        card.appendChild(actions);

        return card.wrapperElement;
    };

    const build_organization_card = function build_organization_card(org, context) {
        const card = new se.Container({class: 'um-card'});

        const header = new se.Container({class: 'um-card-header'});

        const icon = new se.Container({class: 'um-icon'});
        icon.wrapperElement.innerHTML = '<i class="fas fa-building"></i>';
        header.appendChild(icon);

        const info = new se.Container({class: 'um-card-info'});

        const name = new se.Container({class: 'um-card-title'});
        name.wrapperElement.textContent = org.name;
        info.appendChild(name);

        header.appendChild(info);
        card.appendChild(header);

        const actions = new se.Container({class: 'um-card-actions'});

        const viewBtn = new se.Button({
            text: utils.gettext('View'),
            class: 'btn-sm btn-primary'
        });
        viewBtn.addEventListener('click', function() {
            context.showOrganizationHierarchy(org);
        });
        actions.appendChild(viewBtn);

        const deleteBtn = new se.Button({
            text: utils.gettext('Delete'),
            class: 'btn-sm btn-danger'
        });
        deleteBtn.addEventListener('click', function() {
            context.showDeleteOrganizationDialog(org);
        });
        actions.appendChild(deleteBtn);

        card.appendChild(actions);

        return card.wrapperElement;
    };

    const ORG_NODE_W = 160;
    const ORG_NODE_H = 56;
    const ORG_H_GAP = 40;   
    const ORG_V_GAP = 80;   

    const build_org_tree = function build_org_tree(nodes, rootId) {
        const byId = {};
        nodes.forEach(n => { byId[n.id] = {data: n, children: []}; });
        nodes.forEach(n => {
            if (n.parent_id && byId[n.parent_id] && n.id !== rootId) {
                byId[n.parent_id].children.push(byId[n.id]);
            }
        });
        return byId[rootId];
    };

    const calc_subtree_width = function calc_subtree_width(node) {
        if (node.children.length === 0) {
            node._subtreeW = ORG_NODE_W;
            return ORG_NODE_W;
        }
        const childrenWidth = node.children.reduce((acc, c) => acc + calc_subtree_width(c), 0)
            + ORG_H_GAP * (node.children.length - 1);
        node._subtreeW = Math.max(ORG_NODE_W, childrenWidth);
        return node._subtreeW;
    };

    const assign_positions = function assign_positions(node, x, y) {
        node.cx = x + (node._subtreeW || ORG_NODE_W) / 2;
        node.cy = y + ORG_NODE_H / 2;

        if (node.children.length > 0) {
            let childX = x;
            node.children.forEach(child => {
                const cw = child._subtreeW || ORG_NODE_W;
                assign_positions(child, childX, y + ORG_NODE_H + ORG_V_GAP);
                childX += cw + ORG_H_GAP;
            });
        }
    };

    const draw_org_graph = function draw_org_graph(svg, node, ns, context, hierarchyDialog, org) {
        node.children.forEach(child => {
            const x1 = node.cx;
            const y1 = node.cy + ORG_NODE_H / 2;
            const x2 = child.cx;
            const y2 = child.cy - ORG_NODE_H / 2;
            const mx = (y1 + y2) / 2;

            const path = document.createElementNS(ns, 'path');
            path.setAttribute('d', `M ${x1} ${y1} C ${x1} ${mx}, ${x2} ${mx}, ${x2} ${y2}`);
            path.setAttribute('fill', 'none');
            path.setAttribute('stroke', '#adb5bd');
            path.setAttribute('stroke-width', '2');
            path.setAttribute('marker-end', 'url(#org-arrow)');
            svg.appendChild(path);

            draw_org_graph(svg, child, ns, context, hierarchyDialog, org);
        });

        const isOrg = node.data.is_organization;
        const nx = node.cx - ORG_NODE_W / 2;
        const ny = node.cy - ORG_NODE_H / 2;

        const g = document.createElementNS(ns, 'g');
        g.setAttribute('class', 'org-node');
        g.setAttribute('cursor', 'default');

        const shadow = document.createElementNS(ns, 'rect');
        shadow.setAttribute('x', nx + 3);
        shadow.setAttribute('y', ny + 3);
        shadow.setAttribute('width', ORG_NODE_W);
        shadow.setAttribute('height', ORG_NODE_H);
        shadow.setAttribute('rx', '8');
        shadow.setAttribute('ry', '8');
        shadow.setAttribute('fill', 'rgba(0,0,0,0.18)');
        g.appendChild(shadow);

        const rect = document.createElementNS(ns, 'rect');
        rect.setAttribute('x', nx);
        rect.setAttribute('y', ny);
        rect.setAttribute('width', ORG_NODE_W);
        rect.setAttribute('height', ORG_NODE_H);
        rect.setAttribute('rx', '8');
        rect.setAttribute('ry', '8');
        rect.setAttribute('fill', isOrg ? '#4a90d9' : '#6c757d');
        rect.setAttribute('stroke', isOrg ? '#2c6fad' : '#495057');
        rect.setAttribute('stroke-width', '1.5');
        g.appendChild(rect);

        const iconText = document.createElementNS(ns, 'text');
        iconText.setAttribute('x', nx + 14);
        iconText.setAttribute('y', node.cy + 5);
        iconText.setAttribute('font-size', '15');
        iconText.setAttribute('fill', 'white');
        iconText.setAttribute('font-family', 'FontAwesome, Arial');
        iconText.textContent = isOrg ? '\uf1ad' : '\uf0c0';
        g.appendChild(iconText);

        const maxChars = 14;
        const displayName = node.data.name.length > maxChars
            ? node.data.name.substring(0, maxChars) + '…'
            : node.data.name;

        const label = document.createElementNS(ns, 'text');
        label.setAttribute('x', nx + 34);
        label.setAttribute('y', node.cy - 5);
        label.setAttribute('font-size', '12');
        label.setAttribute('font-weight', 'bold');
        label.setAttribute('fill', 'white');
        label.setAttribute('font-family', 'Arial, sans-serif');
        label.textContent = displayName;
        g.appendChild(label);

        const badgeLabel = document.createElementNS(ns, 'text');
        badgeLabel.setAttribute('x', nx + 34);
        badgeLabel.setAttribute('y', node.cy + 11);
        badgeLabel.setAttribute('font-size', '10');
        badgeLabel.setAttribute('fill', 'rgba(255,255,255,0.75)');
        badgeLabel.setAttribute('font-family', 'Arial, sans-serif');
        badgeLabel.textContent = isOrg ? utils.gettext('Organization') : utils.gettext('Group');
        g.appendChild(badgeLabel);

        const title = document.createElementNS(ns, 'title');
        title.textContent = node.data.name;
        g.appendChild(title);

        const EDIT_BTN_SIZE = 24;
        const editBtnX = nx + ORG_NODE_W + 6;
        const editBtnY = node.cy - EDIT_BTN_SIZE / 2;

        const editGroup = document.createElementNS(ns, 'g');
        editGroup.setAttribute('cursor', 'pointer');

        const editBtnBg = document.createElementNS(ns, 'rect');
        editBtnBg.setAttribute('x', editBtnX);
        editBtnBg.setAttribute('y', editBtnY);
        editBtnBg.setAttribute('width', EDIT_BTN_SIZE);
        editBtnBg.setAttribute('height', EDIT_BTN_SIZE);
        editBtnBg.setAttribute('rx', '6');
        editBtnBg.setAttribute('ry', '6');
        editBtnBg.setAttribute('fill', '#f0f0f0');
        editBtnBg.setAttribute('stroke', '#adb5bd');
        editBtnBg.setAttribute('stroke-width', '1');
        editGroup.appendChild(editBtnBg);

        const iconOffX = editBtnX + 5;
        const iconOffY = editBtnY + 5;
        const pencilPath = document.createElementNS(ns, 'path');
        pencilPath.setAttribute('d',
            `M ${iconOffX + 9.5} ${iconOffY + 0.5} ` +
            `l ${3} ${3} ` +
            `L ${iconOffX + 4} ${iconOffY + 9} ` +
            `L ${iconOffX + 1} ${iconOffY + 13} ` +
            `L ${iconOffX + 5} ${iconOffY + 10} ` +
            `L ${iconOffX + 12.5} ${iconOffY + 2.5} Z`
        );
        pencilPath.setAttribute('fill', '#555');
        pencilPath.setAttribute('stroke', '#555');
        pencilPath.setAttribute('stroke-width', '0.5');
        pencilPath.setAttribute('stroke-linejoin', 'round');
        editGroup.appendChild(pencilPath);

        const editTitle = document.createElementNS(ns, 'title');
        editTitle.textContent = utils.gettext('Edit');
        editGroup.appendChild(editTitle);

        editGroup.addEventListener('mouseenter', function() {
            editBtnBg.setAttribute('fill', '#d0e8ff');
            editBtnBg.setAttribute('stroke', '#4a90d9');
            pencilPath.setAttribute('fill', '#4a90d9');
            pencilPath.setAttribute('stroke', '#4a90d9');
        });
        editGroup.addEventListener('mouseleave', function() {
            editBtnBg.setAttribute('fill', '#f0f0f0');
            editBtnBg.setAttribute('stroke', '#adb5bd');
            pencilPath.setAttribute('fill', '#555');
            pencilPath.setAttribute('stroke', '#555');
        });

        editGroup.addEventListener('click', function(e) {
            e.stopPropagation();
            hierarchyDialog.hide();
            const groupObj = {
                id: node.data.id,
                name: node.data.name,
                is_organization: node.data.is_organization
            };
            context.showEditGroupDialog(groupObj, org, hierarchyDialog);
        });

        g.appendChild(editGroup);

        const ADD_BTN_SIZE = 24;
        const addBtnX = editBtnX;
        const addBtnY = editBtnY - ADD_BTN_SIZE - 6;

        const addGroup = document.createElementNS(ns, 'g');
        addGroup.setAttribute('cursor', 'pointer');

        const addBtnBg = document.createElementNS(ns, 'rect');
        addBtnBg.setAttribute('x', addBtnX);
        addBtnBg.setAttribute('y', addBtnY);
        addBtnBg.setAttribute('width', ADD_BTN_SIZE);
        addBtnBg.setAttribute('height', ADD_BTN_SIZE);
        addBtnBg.setAttribute('rx', '6');
        addBtnBg.setAttribute('ry', '6');
        addBtnBg.setAttribute('fill', '#f0f0f0');
        addBtnBg.setAttribute('stroke', '#adb5bd');
        addBtnBg.setAttribute('stroke-width', '1');
        addGroup.appendChild(addBtnBg);

        const plusOffX = addBtnX + ADD_BTN_SIZE / 2;
        const plusOffY = addBtnY + ADD_BTN_SIZE / 2;
        const plusSize = 5;

        const plusH = document.createElementNS(ns, 'line');
        plusH.setAttribute('x1', plusOffX - plusSize);
        plusH.setAttribute('y1', plusOffY);
        plusH.setAttribute('x2', plusOffX + plusSize);
        plusH.setAttribute('y2', plusOffY);
        plusH.setAttribute('stroke', '#28a745');
        plusH.setAttribute('stroke-width', '2.5');
        plusH.setAttribute('stroke-linecap', 'round');
        addGroup.appendChild(plusH);

        const plusV = document.createElementNS(ns, 'line');
        plusV.setAttribute('x1', plusOffX);
        plusV.setAttribute('y1', plusOffY - plusSize);
        plusV.setAttribute('x2', plusOffX);
        plusV.setAttribute('y2', plusOffY + plusSize);
        plusV.setAttribute('stroke', '#28a745');
        plusV.setAttribute('stroke-width', '2.5');
        plusV.setAttribute('stroke-linecap', 'round');
        addGroup.appendChild(plusV);

        const addTitle = document.createElementNS(ns, 'title');
        addTitle.textContent = utils.gettext('Add child group');
        addGroup.appendChild(addTitle);

        addGroup.addEventListener('mouseenter', function() {
            addBtnBg.setAttribute('fill', '#d4edda');
            addBtnBg.setAttribute('stroke', '#28a745');
        });
        addGroup.addEventListener('mouseleave', function() {
            addBtnBg.setAttribute('fill', '#f0f0f0');
            addBtnBg.setAttribute('stroke', '#adb5bd');
        });

        addGroup.addEventListener('click', function(e) {
            e.stopPropagation();
            context.showAddGroupToOrgDialog(node.data.name, hierarchyDialog, org);
        });

        g.appendChild(addGroup);

        if (node.data.parent_id !== null) {
            const DEL_BTN_SIZE = 24;
            const delBtnX = editBtnX;
            const delBtnY = addBtnY - DEL_BTN_SIZE - 6;

            const delGroup = document.createElementNS(ns, 'g');
            delGroup.setAttribute('cursor', 'pointer');

            const delBtnBg = document.createElementNS(ns, 'rect');
            delBtnBg.setAttribute('x', delBtnX);
            delBtnBg.setAttribute('y', delBtnY);
            delBtnBg.setAttribute('width', DEL_BTN_SIZE);
            delBtnBg.setAttribute('height', DEL_BTN_SIZE);
            delBtnBg.setAttribute('rx', '6');
            delBtnBg.setAttribute('ry', '6');
            delBtnBg.setAttribute('fill', '#f0f0f0');
            delBtnBg.setAttribute('stroke', '#adb5bd');
            delBtnBg.setAttribute('stroke-width', '1');
            delGroup.appendChild(delBtnBg);

            const xOffX = delBtnX + DEL_BTN_SIZE / 2;
            const xOffY = delBtnY + DEL_BTN_SIZE / 2;
            const xSize = 5;

            const xLine1 = document.createElementNS(ns, 'line');
            xLine1.setAttribute('x1', xOffX - xSize);
            xLine1.setAttribute('y1', xOffY - xSize);
            xLine1.setAttribute('x2', xOffX + xSize);
            xLine1.setAttribute('y2', xOffY + xSize);
            xLine1.setAttribute('stroke', '#dc3545');
            xLine1.setAttribute('stroke-width', '2.5');
            xLine1.setAttribute('stroke-linecap', 'round');
            delGroup.appendChild(xLine1);

            const xLine2 = document.createElementNS(ns, 'line');
            xLine2.setAttribute('x1', xOffX + xSize);
            xLine2.setAttribute('y1', xOffY - xSize);
            xLine2.setAttribute('x2', xOffX - xSize);
            xLine2.setAttribute('y2', xOffY + xSize);
            xLine2.setAttribute('stroke', '#dc3545');
            xLine2.setAttribute('stroke-width', '2.5');
            xLine2.setAttribute('stroke-linecap', 'round');
            delGroup.appendChild(xLine2);

            const delTitle = document.createElementNS(ns, 'title');
            delTitle.textContent = utils.gettext('Remove from parent');
            delGroup.appendChild(delTitle);

            delGroup.addEventListener('mouseenter', function() {
                delBtnBg.setAttribute('fill', '#f8d7da');
                delBtnBg.setAttribute('stroke', '#dc3545');
            });
            delGroup.addEventListener('mouseleave', function() {
                delBtnBg.setAttribute('fill', '#f0f0f0');
                delBtnBg.setAttribute('stroke', '#adb5bd');
            });

            delGroup.addEventListener('click', function(e) {
                e.stopPropagation();
                const confirmDialog = new Wirecloud.ui.AlertWindowMenu({
                    message: utils.interpolate(
                        utils.gettext('Are you sure you want to remove "%(name)s" from its parent group?'),
                        {name: node.data.name}
                    ),
                    acceptLabel: utils.gettext('Remove'),
                    cancelLabel: utils.gettext('Cancel')
                });

                const confirmErrorAlert = new se.Alert({state: 'danger', class: 'um-edit-error', title: utils.gettext('Error:')});
                confirmErrorAlert.hide();
                confirmDialog.windowContent.appendChild(confirmErrorAlert.wrapperElement);

                confirmDialog.setHandler(function() {
                    return new Promise(function(resolve, reject) {
                        Wirecloud.io.makeRequest(
                            Wirecloud.URLs.ADMIN_ORGANIZATION_GROUP_ENTRY.evaluate({group_name: node.data.name}),
                            {
                                method: 'PUT',
                                contentType: 'application/json',
                                postBody: JSON.stringify({parent_name: ''}),
                                onSuccess: function() {
                                    context.reloadHierarchyGraph(org, hierarchyDialog, confirmDialog);
                                    hierarchyDialog.show();
                                    setTimeout(function (){ context.loadGroups() }, 1000);
                                    resolve();
                                },
                                onFailure: function(response) {
                                    const msg = parseErrorResponse(response, utils.gettext('Error removing parent'));
                                    confirmErrorAlert.setMessage(msg);
                                    confirmErrorAlert.show();
                                    reject(msg);
                                }
                            }
                        );
                    });
                }, function() {
                    hierarchyDialog.show();
                });

                confirmDialog.show();
            });

            g.appendChild(delGroup);
        }

        svg.appendChild(g);
    };

    const build_organization_hierarchy_view = function build_organization_hierarchy_view(org, hierarchyData, context, hierarchyDialog) {
        const container = new se.Container({class: 'um-org-hierarchy-view'});
        container.addClassName('um-org-hierarchy-flex');

        const header = new se.Container({class: 'um-org-hierarchy-header'});

        const backBtn = new se.Button({
            text: utils.gettext('← Back'),
            class: 'btn-default btn-sm'
        });
        backBtn.addEventListener('click', function() {
            hierarchyDialog.hide();
            context.show();
            context.notebook.goToTab(context.organizationsTab);
        });
        header.appendChild(backBtn);

        const sitemapIcon = new se.Container({class: 'um-org-sitemap-icon'});
        sitemapIcon.wrapperElement.innerHTML = '<i class="fas fa-sitemap"></i>';
        header.appendChild(sitemapIcon);

        const titleSpan = new se.Container({class: 'um-org-hierarchy-title'});
        titleSpan.wrapperElement.textContent = utils.interpolate(utils.gettext('Organization: %(name)s'), {name: org.name});
        header.appendChild(titleSpan);

        const countBadge = new se.Container({class: 'um-org-hierarchy-badge'});
        countBadge.wrapperElement.textContent = utils.interpolate(utils.gettext('%(count)s nodes'), {count: hierarchyData.length});
        header.appendChild(countBadge);

        container.appendChild(header);

        const svgWrapper = new se.Container({class: 'um-org-svg-wrapper'});

        const ns = 'http://www.w3.org/2000/svg';
        const root = build_org_tree(hierarchyData, hierarchyData[0].id);

        if (!root) {
            svgWrapper.wrapperElement.innerHTML = '<div class="um-org-hierarchy-error">' + utils.gettext('Could not build hierarchy') + '</div>';
            container.appendChild(svgWrapper);
            return container.wrapperElement;
        }

        calc_subtree_width(root);

        const totalTreeW = root._subtreeW || ORG_NODE_W;
        const PADDING = 30;
        const EDIT_BTN_EXTRA = 36; 
        const svgW = Math.max(600, totalTreeW + PADDING * 2 + EDIT_BTN_EXTRA);
        const startX = (svgW - EDIT_BTN_EXTRA - totalTreeW) / 2;
        assign_positions(root, startX, PADDING + 30); 

        const allNodes = [];
        const collect = function collect(n) { allNodes.push(n); n.children.forEach(collect); };
        collect(root);

        const maxY = Math.max(...allNodes.map(n => n.cy + ORG_NODE_H / 2));
        const svgH = maxY + PADDING;

        const svg = document.createElementNS(ns, 'svg');
        svg.setAttribute('width', svgW);
        svg.setAttribute('height', svgH);
        svg.setAttribute('class', 'um-org-svg');

        const defs = document.createElementNS(ns, 'defs');
        const marker = document.createElementNS(ns, 'marker');
        marker.setAttribute('id', 'org-arrow');
        marker.setAttribute('markerWidth', '8');
        marker.setAttribute('markerHeight', '8');
        marker.setAttribute('refX', '6');
        marker.setAttribute('refY', '3');
        marker.setAttribute('orient', 'auto');
        const arrowPath = document.createElementNS(ns, 'path');
        arrowPath.setAttribute('d', 'M0,0 L0,6 L8,3 z');
        arrowPath.setAttribute('fill', '#adb5bd');
        marker.appendChild(arrowPath);
        defs.appendChild(marker);
        svg.appendChild(defs);

        const gMain = document.createElementNS(ns, 'g');
        svg.appendChild(gMain);

        draw_org_graph(gMain, root, ns, context, hierarchyDialog, org);

        svgWrapper.wrapperElement.appendChild(svg);
        container.appendChild(svgWrapper);

        return container.wrapperElement;
    };

    ns.UserManagementWindowMenu = class UserManagementWindowMenu extends Wirecloud.ui.WindowMenu {

        constructor() {
            super(utils.gettext('User Management'), 'wc-user-management');

            const priv = {
                users: [],
                groups: [],
                organizations: [],
                filteredUsers: [],
                filteredGroups: [],
                filteredOrganizations: []
            };
            privates.set(this, priv);

            this.notebook = new se.Notebook();

            this.usersTab = this.notebook.createTab({
                label: utils.gettext('Users'),
                closable: false
            });

            this.groupsTab = this.notebook.createTab({
                label: utils.gettext('Groups'),
                closable: false
            });

            this.organizationsTab = this.notebook.createTab({
                label: utils.gettext('Organizations'),
                closable: false
            });

            this.usersTab.appendChild(build_users_tab(this).wrapperElement);
            this.groupsTab.appendChild(build_groups_tab(this).wrapperElement);
            this.organizationsTab.appendChild(build_organizations_tab(this).wrapperElement);

            this.windowContent.appendChild(this.notebook.wrapperElement);
        }

        loadUsers() {
            const priv = privates.get(this);

            this.usersList.innerHTML = '<div class="um-loading">' + utils.gettext('Loading users...') + '</div>';

            fetchElasticsearchData('user').then(data => {
                priv.users = [];

                if (data.results && data.results.length > 0) {
                    priv.users = data.results.map((user) => {
                        return {
                            id: user.id,
                            username: user.username,
                            fullname: user.fullname || user.username
                        };
                    });
                }

                priv.filteredUsers = priv.users.slice();
                this.renderUsers();
            }).catch(error => {
                console.error('Error loading users:', error);
                this.usersList.innerHTML = '<div class="um-error">' + utils.gettext('Error loading users. Please try again.') + '</div>';
            });
        }

        renderUsers() {
            const priv = privates.get(this);
            this.usersList.innerHTML = '';

            if (priv.filteredUsers.length === 0) {
                this.usersList.innerHTML = '<div class="um-empty">' + utils.gettext('No users found') + '</div>';
                return;
            }

            priv.filteredUsers.forEach(user => {
                const card = build_user_card(user, this);
                this.usersList.appendChild(card);
            });
        }

        filterUsers(query) {
            const priv = privates.get(this);
            query = query.toLowerCase();

            priv.filteredUsers = priv.users.filter(user => {
                return user.username.toLowerCase().includes(query) ||
                       (user.fullname && user.fullname.toLowerCase().includes(query));
            });

            this.renderUsers();
        }

        showAddUserDialog() {
            const context = this;
            const dialog = new Wirecloud.ui.FormWindowMenu(
                [
                    {name: 'username', label: utils.gettext('Username'), type: 'text', required: true},
                    {name: 'email', label: utils.gettext('Email'), type: 'text', required: true},
                    {name: 'first_name', label: utils.gettext('First Name'), type: 'text', required: true},
                    {name: 'last_name', label: utils.gettext('Last Name'), type: 'text', required: true},
                    {name: 'password', label: utils.gettext('Password'), type: 'password', required: true},
                    {name: 'is_active', label: utils.gettext('Active'), type: 'boolean', initialValue: true},
                    {name: 'is_staff', label: utils.gettext('Staff status'), type: 'boolean', initialValue: false},
                    {name: 'is_superuser', label: utils.gettext('Superuser status'), type: 'boolean', initialValue: false}
                ],
                utils.gettext('Create New User'),
                'wc-add-user'
            );

            dialog.form.addEventListener('cancel', function() {
                context.show();
                context.notebook.goToTab(context.usersTab);
            });

            dialog.executeOperation = (data) => {
                const userData = {
                    username: data.username.trim(),
                    email: data.email.trim(),
                    first_name: data.first_name.trim(),
                    last_name: data.last_name.trim(),
                    password: data.password,
                    is_active: data.is_active || false,
                    is_staff: data.is_staff || false,
                    is_superuser: data.is_superuser || false,
                    idm_data: {}
                };

                return new Promise(function(resolve, reject) {
                    Wirecloud.io.makeRequest(Wirecloud.URLs.ADMIN_USER_COLLECTION, {
                        method: 'POST',
                        contentType: 'application/json',
                        postBody: JSON.stringify(userData),
                        onSuccess: function() {
                            const priv = privates.get(context);
                            priv.users.push({
                                id: null,
                                username: userData.username,
                                fullname: userData.first_name + ' ' + userData.last_name,
                            });
                            priv.filteredUsers = priv.users.slice();
                            context.renderUsers();
                            context.show();
                            context.notebook.goToTab(context.usersTab);
                            setTimeout(function() { context.loadUsers(); }, 1500);
                            resolve();
                        },
                        onFailure: function(response) {
                            reject(parseErrorResponse(response, utils.gettext('Error creating user')));
                        }
                    });
                });
            };

            dialog.show();
        }

        showEditUserDialog(user) {
            const context = this;

            const loadingDialog = new Wirecloud.ui.MessageWindowMenu(
                utils.gettext('Loading User Data'),
                {
                    type: 'info',
                    htmlMessage: '<div class="um-loading">' + utils.gettext('Loading user information...') + '</div>'
                }
            );
            loadingDialog.show();

            Wirecloud.io.makeRequest(Wirecloud.URLs.ADMIN_USER_ENTRY.evaluate({user_username: user.username}), {
                method: 'GET',
                onSuccess: function(response) {
                    loadingDialog.hide();
                    context.usersErrorAlert.hide();
                    const userData = JSON.parse(response.responseText);

                    const dialog = new Wirecloud.ui.WindowMenu(
                        utils.gettext('Edit User'),
                        'wc-edit-user'
                    );

                    const contentWrapper = new se.Container({class: 'wc-user-edit-content'});

                    const notebook = new se.Notebook();
                    notebook.addClassName('wc-notebook-dialog');

                    const infoTab = notebook.createTab({label: utils.gettext('User Info'), closable: false});

                    const infoForm = new se.Container({class: 'um-edit-form'});

                    const usernameInput = new se.TextField({initialValue: userData.username});
                    infoForm.appendChild(createFormGroup(utils.gettext('Username'), usernameInput));

                    const emailInput = new se.TextField({initialValue: userData.email});
                    emailInput.inputElement.type = 'email';
                    infoForm.appendChild(createFormGroup(utils.gettext('Email'), emailInput));

                    const firstNameInput = new se.TextField({initialValue: userData.first_name});
                    infoForm.appendChild(createFormGroup(utils.gettext('First Name'), firstNameInput));

                    const lastNameInput = new se.TextField({initialValue: userData.last_name});
                    infoForm.appendChild(createFormGroup(utils.gettext('Last Name'), lastNameInput));

                    const staffCheckbox = new se.CheckBox({initiallyChecked: userData.is_staff});
                    infoForm.appendChild(createFormGroup(utils.gettext('Staff status'), staffCheckbox));

                    const activeCheckbox = new se.CheckBox({initiallyChecked: userData.is_active});
                    infoForm.appendChild(createFormGroup(utils.gettext('Active'), activeCheckbox));

                    const superuserCheckbox = new se.CheckBox({initiallyChecked: userData.is_superuser});
                    infoForm.appendChild(createFormGroup(utils.gettext('Superuser status'), superuserCheckbox));

                    const permissionCheckboxes = {};

                    const errorAlert = new se.Alert({state: 'danger', class: 'um-edit-error', title: utils.gettext('Error:')});
                    errorAlert.hide();
                    infoForm.wrapperElement.insertBefore(errorAlert.wrapperElement, infoForm.wrapperElement.firstChild);

                    const showEditError = function(message) {
                        errorAlert.setMessage(message);
                        errorAlert.show();
                        errorAlert.wrapperElement.scrollIntoView({behavior: 'smooth', block: 'nearest'});
                    };

                    const hideEditError = function() {
                        errorAlert.hide();
                    };

                    const saveChanges = function() {
                        hideEditError();

                        const updateData = {
                            username: usernameInput.getValue().trim(),
                            email: emailInput.getValue().trim(),
                            first_name: firstNameInput.getValue().trim(),
                            last_name: lastNameInput.getValue().trim(),
                            is_staff: staffCheckbox.getValue(),
                            is_active: activeCheckbox.getValue(),
                            is_superuser: superuserCheckbox.getValue(),
                            permissions: getSelectedPermissions(permissionCheckboxes)
                        };


                        Wirecloud.io.makeRequest(Wirecloud.URLs.ADMIN_USER_ENTRY.evaluate({user_username: user.username}), {
                            method: 'PUT',
                            contentType: 'application/json',
                            postBody: JSON.stringify(updateData),
                            onSuccess: function() {
                                dialog.hide();
                                context.show();
                                context.notebook.goToTab(context.usersTab);
                                setTimeout(function() { context.loadUsers(); }, 1000);
                            },
                            onFailure: function(response) {
                                showEditError(parseErrorResponse(response, utils.gettext('Error updating user')));
                            }
                        });
                    };

                    const cancelUser = function() {
                        dialog.hide();
                        context.show();
                        context.notebook.goToTab(context.usersTab);
                    };

                    infoForm.appendChild(createDialogActions(saveChanges, cancelUser));
                    infoTab.appendChild(infoForm);

                    const permissionsTab = notebook.createTab({label: utils.gettext('Permissions'), closable: false});
                    const permissionsContainer = new se.Container({class: 'um-permissions-view'});
                    const permissionsGrid = buildPermissionsGrid(userData.permissions, permissionCheckboxes);
                    permissionsContainer.appendChild(permissionsGrid);
                    permissionsContainer.appendChild(createDialogActions(saveChanges, cancelUser));
                    permissionsTab.appendChild(permissionsContainer);

                    contentWrapper.appendChild(notebook);

                    dialog.windowContent.appendChild(contentWrapper.wrapperElement);

                    dialog.show();
                },
                onFailure: function(response) {
                    loadingDialog.hide();
                    context.show();
                    context.notebook.goToTab(context.usersTab);
                    context.usersErrorAlert.setMessage(parseErrorResponse(response, utils.gettext('Error loading user data')));
                    context.usersErrorAlert.show();
                }
            });
        }

        showDeleteUserDialog(user) {
            const context = this;
            this._showDeleteDialog({
                message: utils.interpolate(utils.gettext('Are you sure you want to delete user %(username)s? This action cannot be undone.'), {username: user.username}),
                url: Wirecloud.URLs.ADMIN_USER_ENTRY.evaluate({user_username: user.username}),
                errorLabel: utils.gettext('Error deleting user'),
                onSuccess: function() {
                    context.renderUsers();
                    context.show();
                    context.notebook.goToTab(context.usersTab);
                    setTimeout(function() { context.loadUsers(); }, 1000);
                },
                onCancel: function() {
                    context.show();
                    context.notebook.goToTab(context.usersTab);
                }
            });
        }


        loadGroups() {
            const priv = privates.get(this);

            this.groupsList.innerHTML = '<div class="um-loading">' + utils.gettext('Loading groups...') + '</div>';

            fetchElasticsearchData('group').then(data => {
                priv.groups = [];

                if (data.results && data.results.length > 0) {

                    const groupsOnly = data.results.filter(item => !item.is_organization);

                    priv.groups = groupsOnly.map((group) => {
                        return {
                            id: group.id,
                            name: group.name
                        };
                    });
                }

                priv.filteredGroups = priv.groups.slice();
                this.renderGroups();
            }).catch(error => {
                console.error('Error loading groups:', error);
                this.groupsList.innerHTML = '<div class="um-error">' + utils.gettext('Error loading groups. Please try again.') + '</div>';
            });
        }

        renderGroups() {
            const priv = privates.get(this);
            this.groupsList.innerHTML = '';

            if (priv.filteredGroups.length === 0) {
                this.groupsList.innerHTML = '<div class="um-empty">' + utils.gettext('No groups found') + '</div>';
                return;
            }

            priv.filteredGroups.forEach(group => {
                const card = build_group_card(group, this);
                this.groupsList.appendChild(card);
            });
        }

        filterGroups(query) {
            const priv = privates.get(this);
            query = query.toLowerCase();

            priv.filteredGroups = priv.groups.filter(group => {
                return group.name.toLowerCase().includes(query);
            });

            this.renderGroups();
        }

        showAddGroupDialog() {
            this._showAddEntityDialog({
                title: utils.gettext('Create Group'),
                cssClass: 'wc-add-group',
                infoTabLabel: utils.gettext('Group Info'),
                namePlaceholder: utils.gettext('Group name'),
                createBtnLabel: utils.gettext('Create Group'),
                emptyMembersLabel: utils.gettext('No members in this group'),
                errorCreatingLabel: utils.gettext('Error creating group'),
                url: Wirecloud.URLs.ADMIN_GROUP_COLLECTION,
                onSuccess: (dialog) => {
                    dialog.hide();
                    this.renderGroups();
                    this.show();
                    this.notebook.goToTab(this.groupsTab);
                    setTimeout(() => this.loadGroups(), 1000);
                },
                onCancel: (dialog) => {
                    dialog.hide();
                    this.show();
                    this.notebook.goToTab(this.groupsTab);
                }
            });
        }

        showDeleteGroupDialog(group) {
            const context = this;
            this._showDeleteDialog({
                message: utils.interpolate(utils.gettext('Are you sure you want to delete group %(name)s? This action cannot be undone.'), {name: group.name}),
                url: Wirecloud.URLs.ADMIN_GROUP_ENTRY.evaluate({group_name: group.name}),
                errorLabel: utils.gettext('Error deleting group'),
                onSuccess: function() {
                    context.renderGroups();
                    context.show();
                    context.notebook.goToTab(context.groupsTab);
                    setTimeout(function() { context.loadGroups(); }, 1000);
                },
                onCancel: function() {
                    context.show();
                    context.notebook.goToTab(context.groupsTab);
                }
            });
        }

        showEditGroupDialog(group, org, hierarchyDialog) {
            const context = this;

            const loadingDialog = new Wirecloud.ui.MessageWindowMenu(
                utils.gettext('Loading group information...'),
                'info'
            );
            loadingDialog.show();

            Wirecloud.io.makeRequest(Wirecloud.URLs.ADMIN_GROUP_ENTRY.evaluate({group_name: group.name}), {
                method: 'GET',
                onSuccess: function(response) {
                    loadingDialog.hide();
                    context.groupsErrorAlert.hide();
                    const groupData = JSON.parse(response.responseText);

                    const dialog = new Wirecloud.ui.WindowMenu(
                        utils.gettext('Edit Group'),
                        'wc-edit-group'
                    );

                    const contentWrapper = new se.Container({class: 'wc-user-edit-content'});

                    const notebook = new se.Notebook();
                    notebook.addClassName('wc-notebook-dialog');

                    const infoTab = notebook.createTab({label: utils.gettext('Group Info'), closable: false});
                    const infoForm = new se.Container({class: 'um-edit-form'});

                    const nameInput = new se.TextField({initialValue: groupData.name});
                    infoForm.appendChild(createFormGroup(utils.gettext('Name'), nameInput));

                    const codenameInput = new se.TextField({initialValue: groupData.codename || ''});
                    infoForm.appendChild(createFormGroup(utils.gettext('Codename'), codenameInput));

                    const permissionCheckboxes = {};

                    const errorAlert = new se.Alert({state: 'danger', class: 'um-edit-error', title: utils.gettext('Error:')});
                    errorAlert.hide();
                    infoForm.wrapperElement.insertBefore(errorAlert.wrapperElement, infoForm.wrapperElement.firstChild);

                    const showEditError = function(message) {
                        errorAlert.setMessage(message);
                        errorAlert.show();
                        errorAlert.wrapperElement.scrollIntoView({behavior: 'smooth', block: 'nearest'});
                    };

                    const hideEditError = function() {
                        errorAlert.hide();
                    };

                    let selectedUserIds = (groupData.users || []).map(String);

                    const saveChanges = function() {
                        hideEditError();
                        const updateData = {
                            name: nameInput.getValue().trim(),
                            codename: codenameInput.getValue().trim(),
                            permissions: getSelectedPermissions(permissionCheckboxes),
                            users: selectedUserIds
                        };

                        Wirecloud.io.makeRequest(Wirecloud.URLs.ADMIN_GROUP_ENTRY.evaluate({group_name: group.name}), {
                            method: 'PUT',
                            contentType: 'application/json',
                            postBody: JSON.stringify(updateData),
                            onSuccess: function() {
                                const editingOrganizationRoot = Boolean(org) && group.name === org.name;
                                group.name = updateData.name;
                                dialog.hide();
                                if (org) {
                                    if (editingOrganizationRoot) {
                                        org.name = updateData.name;
                                    }
                                    context.reloadHierarchyGraph(org, hierarchyDialog, dialog);
                                    hierarchyDialog.show();
                                    setTimeout(function() { context.loadOrganizations(); }, 1000);
                                } else {
                                    context.renderGroups();
                                    context.show();
                                    context.notebook.goToTab(context.groupsTab);
                                    setTimeout(function() { context.loadGroups(); }, 1000);
                                }
                            },
                            onFailure: function(response) {
                                showEditError(parseErrorResponse(response, utils.gettext('Error updating group')));
                            }
                        });
                    };

                    const cancelGroup = function() {
                        dialog.hide();
                        if (org) {
                            hierarchyDialog.show();
                        } else {
                            context.show();
                            context.notebook.goToTab(context.groupsTab);
                        }
                    };

                    infoForm.appendChild(createDialogActions(saveChanges, cancelGroup));
                    infoTab.appendChild(infoForm);

                    const membersTab = notebook.createTab({label: utils.gettext('Members'), closable: false});
                    const membersContainer = new se.Container({class: 'um-edit-form'});

                    let allUsersMap = {};

                    const memberListDiv = new se.Container({class: 'um-member-list'});

                    const membersLoadingRow = new se.Container({class: 'um-loading'});
                    membersLoadingRow.wrapperElement.textContent = utils.gettext('Loading members...');
                    memberListDiv.appendChild(membersLoadingRow);

                    const renderMemberList = function() {
                        memberListDiv.clear();
                        if (selectedUserIds.length === 0) {
                            const empty = new se.Container({class: 'um-empty'});
                            empty.wrapperElement.textContent = utils.gettext('No members in this group');
                            memberListDiv.appendChild(empty);
                            return;
                        }
                        selectedUserIds.forEach(function(uid) {
                            const username = allUsersMap[uid] || allUsersMap[uid.toString()] || uid;
                            const row = new se.Container({class: 'um-member-row'});

                            const nameSpan = new se.Container({tagname: 'span', class: 'um-member-name'});
                            nameSpan.wrapperElement.textContent = username;
                            row.appendChild(nameSpan);

                            const removeBtn = new se.Button({text: '×', class: 'btn-danger um-member-remove-btn'});
                            removeBtn.addEventListener('click', function() {
                                selectedUserIds = selectedUserIds.filter(id => id !== uid);
                                renderMemberList();
                            });
                            row.appendChild(removeBtn);
                            memberListDiv.appendChild(row);
                        });
                    };

                    membersContainer.appendChild(memberListDiv);

                    const addUserField = new se.TextField({placeholder: utils.gettext('Add a user...')});
                    addUserField.addClassName('um-add-user-field');
                    membersContainer.appendChild(addUserField);

                    const typeahead = new Wirecloud.ui.UserTypeahead({autocomplete: false});
                    typeahead.bind(addUserField);
                    typeahead.addEventListener('select', function(th, menuitem) {
                        const userData = menuitem.context;
                        const username = userData.username;

                        let uid = userData.id ? String(userData.id) : null;
                        if (!uid || uid === 'undefined') {
                            uid = Object.keys(allUsersMap).find(k => allUsersMap[k] === username) || null;
                        }

                        if (uid && !selectedUserIds.includes(uid)) {
                            selectedUserIds.push(uid);
                            allUsersMap[uid] = username;
                            renderMemberList();
                        } else if (!uid) {
                            const tempId = '__user__' + username;
                            if (!selectedUserIds.includes(tempId)) {
                                selectedUserIds.push(tempId);
                                allUsersMap[tempId] = username;
                                renderMemberList();
                            }
                        }

                        addUserField.setValue('');
                        addUserField.inputElement.blur();
                    });

                    membersContainer.appendChild(createDialogActions(saveChanges, cancelGroup));
                    membersTab.appendChild(membersContainer);

                    fetchElasticsearchData('user').then(function(userData) {
                        if (userData.results) {
                            userData.results.forEach(function(u) {
                                const uid = String(u.id);
                                allUsersMap[uid] = u.username;
                            });
                        }
                        selectedUserIds = selectedUserIds.map(String);
                        renderMemberList();
                    }).catch(function() {
                        memberListDiv.clear();
                        memberListDiv.wrapperElement.innerHTML = '<div class="um-error">' + utils.gettext('Error loading users') + '</div>';
                    });

                    const permissionsTab = notebook.createTab({label: utils.gettext('Permissions'), closable: false});
                    const permissionsContainer = new se.Container({class: 'um-permissions-view'});
                    const permissionsGrid = buildPermissionsGrid(groupData.permissions || [], permissionCheckboxes);
                    permissionsContainer.appendChild(permissionsGrid);
                    permissionsContainer.appendChild(createDialogActions(saveChanges, cancelGroup));
                    permissionsTab.appendChild(permissionsContainer);

                    contentWrapper.appendChild(notebook);
                    dialog.windowContent.appendChild(contentWrapper.wrapperElement);
                    dialog.show();
                },
                onFailure: function(response) {
                    loadingDialog.hide();
                    context.show();
                    context.notebook.goToTab(context.groupsTab);
                    context.groupsErrorAlert.setMessage(parseErrorResponse(response, utils.gettext('Error loading group data')));
                    context.groupsErrorAlert.show();
                }
            });
        }

        _showDeleteDialog(options) {
            const dialog = new Wirecloud.ui.AlertWindowMenu({
                message: options.message,
                acceptLabel: utils.gettext('Delete'),
                cancelLabel: utils.gettext('Cancel')
            });

            const errorAlert = new se.Alert({state: 'danger', class: 'um-edit-error', title: utils.gettext('Error:')});
            errorAlert.hide();
            dialog.windowContent.appendChild(errorAlert.wrapperElement);

            dialog.setHandler(
                function() {
                    return new Promise(function(resolve, reject) {
                        Wirecloud.io.makeRequest(options.url, {
                            method: 'DELETE',
                            onSuccess: function() {
                                options.onSuccess();
                                resolve();
                            },
                            onFailure: function(response) {
                                const msg = parseErrorResponse(response, options.errorLabel);
                                errorAlert.setMessage(msg);
                                errorAlert.show();
                                reject(msg);
                            }
                        });
                    });
                },
                options.onCancel
            );

            dialog.show();
        }

        loadOrganizations() {
            const priv = privates.get(this);

            this.orgsList.innerHTML = '<div class="um-loading">' + utils.gettext('Loading organizations...') + '</div>';

            fetchElasticsearchData('group').then(data => {
                priv.organizations = [];

                if (data.results && data.results.length > 0) {

                    const rootOrgsOnly = data.results.filter(item =>
                        item.is_organization === true && item.is_root === true
                    );

                    priv.organizations = rootOrgsOnly.map((org) => {
                        return {
                            name: org.name
                        };
                    });
                }

                priv.filteredOrganizations = priv.organizations.slice();
                this.renderOrganizations();
            }).catch(error => {
                console.error('Error loading organizations:', error);
                this.orgsList.innerHTML = '<div class="um-error">' + utils.gettext('Error loading organizations. Please try again.') + '</div>';
            });
        }

        renderOrganizations() {
            const priv = privates.get(this);
            this.orgsList.innerHTML = '';

            if (priv.filteredOrganizations.length === 0) {
                this.orgsList.innerHTML = '<div class="um-empty">' + utils.gettext('No organizations found') + '</div>';
                return;
            }

            priv.filteredOrganizations.forEach(org => {
                const card = build_organization_card(org, this);
                this.orgsList.appendChild(card);
            });
        }

        filterOrganizations(query) {
            const priv = privates.get(this);
            query = query.toLowerCase();

            priv.filteredOrganizations = priv.organizations.filter(org => {
                return org.name.toLowerCase().includes(query);
            });

            this.renderOrganizations();
        }

        showAddOrganizationDialog() {
            this._showAddEntityDialog({
                title: utils.gettext('Create Organization'),
                cssClass: 'wc-add-org',
                infoTabLabel: utils.gettext('Organization Info'),
                namePlaceholder: utils.gettext('Organization name'),
                createBtnLabel: utils.gettext('Create Organization'),
                emptyMembersLabel: utils.gettext('No members in this organization'),
                errorCreatingLabel: utils.gettext('Error creating organization'),
                url: Wirecloud.URLs.ADMIN_ORGANIZATION_COLLECTION,
                onSuccess: (dialog) => {
                    dialog.hide();
                    this.show();
                    this.notebook.goToTab(this.organizationsTab);
                    setTimeout(() => this.loadOrganizations(), 1000);
                },
                onCancel: (dialog) => {
                    dialog.hide();
                    this.show();
                    this.notebook.goToTab(this.organizationsTab);
                }
            });
        }

        _showAddEntityDialog(options) {
            const dialog = new Wirecloud.ui.WindowMenu(options.title, options.cssClass);
            const contentWrapper = new se.Container({class: 'wc-user-edit-content'});
            const notebook = new se.Notebook();
            notebook.addClassName('wc-notebook-dialog');

            let selectedUserIds = [];
            let allUsersMap = {};

            const errorAlert = new se.Alert({state: 'danger', class: 'um-edit-error', title: utils.gettext('Error:')});
            errorAlert.hide();

            const showEditError = function(message) {
                errorAlert.setMessage(message);
                errorAlert.show();
                errorAlert.wrapperElement.scrollIntoView({behavior: 'smooth', block: 'nearest'});
            };

            const hideEditError = function() {
                errorAlert.hide();
            };

            const create = function() {
                hideEditError();
                Wirecloud.io.makeRequest(options.url, {
                    method: 'POST',
                    contentType: 'application/json',
                    postBody: JSON.stringify({
                        name: nameInput.getValue().trim(),
                        codename: codenameInput.getValue().trim(),
                        users: selectedUserIds
                    }),
                    onSuccess: function() {
                        options.onSuccess(dialog);
                    },
                    onFailure: function(response) {
                        let errorMessage = options.errorCreatingLabel;
                        errorMessage = parseErrorResponse(response, errorMessage);
                        showEditError(errorMessage);
                    }
                });
            };

            const infoTab = notebook.createTab({label: options.infoTabLabel, closable: false});
            const infoForm = new se.Container({class: 'um-edit-form'});

            const nameInput = new se.TextField({placeholder: options.namePlaceholder});
            infoForm.appendChild(createFormGroup(utils.gettext('Name'), nameInput));

            const codenameInput = new se.TextField({placeholder: utils.gettext('Codename')});
            infoForm.appendChild(createFormGroup(utils.gettext('Codename'), codenameInput));

            infoForm.appendChild(errorAlert);

            const createEntityActions = function() {
                const div = new se.Container({class: 'um-dialog-actions'});
                const createBtn = new se.Button({text: options.createBtnLabel, class: 'btn-primary'});
                createBtn.addEventListener('click', create);
                const cancelBtn = new se.Button({text: utils.gettext('Cancel'), class: 'btn-default'});
                cancelBtn.addEventListener('click', () => options.onCancel(dialog));
                div.appendChild(createBtn);
                div.appendChild(cancelBtn);
                return div;
            };

            infoForm.appendChild(createEntityActions());
            infoTab.appendChild(infoForm);

            const membersTab = notebook.createTab({label: utils.gettext('Members'), closable: false});
            const membersContainer = new se.Container({class: 'um-edit-form'});
            const memberListDiv = new se.Container({class: 'um-member-list'});

            const renderMemberList = function() {
                memberListDiv.clear();
                if (selectedUserIds.length === 0) {
                    const empty = new se.Container({class: 'um-empty'});
                    empty.wrapperElement.textContent = options.emptyMembersLabel;
                    memberListDiv.appendChild(empty);
                    return;
                }
                selectedUserIds.forEach(function(uid) {
                    const username = allUsersMap[uid] || uid;
                    const row = new se.Container({class: 'um-member-row'});
                    const nameSpan = new se.Container({tagname: 'span', class: 'um-member-name'});
                    nameSpan.wrapperElement.textContent = username;
                    row.appendChild(nameSpan);
                    const removeBtn = new se.Button({text: '×', class: 'btn-danger um-member-remove-btn'});
                    removeBtn.addEventListener('click', function() {
                        selectedUserIds = selectedUserIds.filter(id => id !== uid);
                        renderMemberList();
                    });
                    row.appendChild(removeBtn);
                    memberListDiv.appendChild(row);
                });
            };

            renderMemberList();
            membersContainer.appendChild(memberListDiv);

            const addUserField = new se.TextField({placeholder: utils.gettext('Add a user...')});
            addUserField.addClassName('um-add-user-field');
            membersContainer.appendChild(addUserField);

            const typeahead = new Wirecloud.ui.UserTypeahead({autocomplete: false});
            typeahead.bind(addUserField);
            typeahead.addEventListener('select', function(th, menuitem) {
                const userData = menuitem.context;
                const username = userData.username;
                let uid = userData.id ? String(userData.id) : null;
                if (!uid || uid === 'undefined') {
                    uid = Object.keys(allUsersMap).find(k => allUsersMap[k] === username) || null;
                }
                if (uid && !selectedUserIds.includes(uid)) {
                    selectedUserIds.push(uid);
                    allUsersMap[uid] = username;
                    renderMemberList();
                } else if (!uid) {
                    const tempId = '__user__' + username;
                    if (!selectedUserIds.includes(tempId)) {
                        selectedUserIds.push(tempId);
                        allUsersMap[tempId] = username;
                        renderMemberList();
                    }
                }
                addUserField.setValue('');
                addUserField.inputElement.blur();
            });

            const membersActionsDiv = createEntityActions();
            membersContainer.appendChild(membersActionsDiv);
            membersTab.appendChild(membersContainer);

            fetchElasticsearchData('user').then(function(data) {
                if (data.results) {
                    data.results.forEach(function(u) {
                        allUsersMap[String(u.id)] = u.username;
                    });
                }
            }).catch(function() {});

            contentWrapper.appendChild(notebook);
            dialog.windowContent.appendChild(contentWrapper.wrapperElement);
            dialog.show();
        }


        showDeleteOrganizationDialog(org) {
            const context = this;
            this._showDeleteDialog({
                message: utils.interpolate(utils.gettext('Are you sure you want to delete organization %(name)s? This action cannot be undone.'), {name: org.name}),
                url: Wirecloud.URLs.ADMIN_ORGANIZATION_ENTRY.evaluate({org_name: org.name}),
                errorLabel: utils.gettext('Error deleting organization'),
                onSuccess: function() {
                    context.show();
                    context.notebook.goToTab(context.organizationsTab);
                    setTimeout(function() { context.loadOrganizations(); }, 1000);
                },
                onCancel: function() {
                    context.show();
                    context.notebook.goToTab(context.organizationsTab);
                }
            });
        }

        showOrganizationHierarchy(org) {
            const context = this;

            const loadingDialog = new Wirecloud.ui.MessageWindowMenu(
                utils.gettext('Loading Organization Hierarchy'),
                {
                    type: 'info',
                    htmlMessage: '<div class="um-loading">' + utils.gettext('Loading organization structure...') + '</div>'
                }
            );
            loadingDialog.show();

            Wirecloud.io.makeRequest(Wirecloud.URLs.ADMIN_ORGANIZATION_ENTRY.evaluate({org_name: org.name}), {
                method: 'GET',
                requestHeaders: {'Accept': 'application/json'},
                onSuccess: function(response) {
                    loadingDialog.hide();
                    context.orgsErrorAlert.hide();

                    let groups;
                    try {
                        groups = JSON.parse(response.responseText);
                    } catch (_) {
                        context.show();
                        context.notebook.goToTab(context.organizationsTab);
                        context.orgsErrorAlert.setMessage(utils.gettext('Error parsing organization data'));
                        context.orgsErrorAlert.show();
                        return;
                    }

                    if (!groups || groups.length === 0) {
                        context.show();
                        context.notebook.goToTab(context.organizationsTab);
                        context.orgsErrorAlert.setMessage(utils.gettext('No groups found for this organization'));
                        context.orgsErrorAlert.show();
                        return;
                    }

                    const hierarchyNodes = parseHierarchyNodes(groups);

                    const rootNode = hierarchyNodes.find(n => n.parent_id === null);
                    if (!rootNode) {
                        context.show();
                        context.notebook.goToTab(context.organizationsTab);
                        context.orgsErrorAlert.setMessage(utils.gettext('Could not find root organization node'));
                        context.orgsErrorAlert.show();
                        return;
                    }

                    const sortedHierarchy = [rootNode, ...hierarchyNodes.filter(n => n.id !== rootNode.id)];

                    const dialog = new Wirecloud.ui.WindowMenu(
                        utils.gettext('Organization Hierarchy'),
                        'wc-org-hierarchy'
                    );

                    const hierarchyView = build_organization_hierarchy_view(org, sortedHierarchy, context, dialog);
                    dialog.windowContent.appendChild(hierarchyView);
                    dialog.show();
                },
                onFailure: function(response) {
                    loadingDialog.hide();
                    context.show();
                    context.notebook.goToTab(context.organizationsTab);
                    context.orgsErrorAlert.setMessage(parseErrorResponse(response, utils.gettext('Error loading organization hierarchy')));
                    context.orgsErrorAlert.show();
                }
            });
        }

        reloadHierarchyGraph(org, hierarchyDialog, dialogToClose) {
            const context = this;
            Wirecloud.io.makeRequest(Wirecloud.URLs.ADMIN_ORGANIZATION_ENTRY.evaluate({org_name: org.name}), {
                method: 'GET',
                requestHeaders: {'Accept': 'application/json'},
                onSuccess: function(response) {
                    let groups;
                    try { groups = JSON.parse(response.responseText); } catch (_) { return; }

                    const hierarchyNodes = parseHierarchyNodes(groups);

                    const rootNode = hierarchyNodes.find(n => n.parent_id === null);
                    if (!rootNode) { return; }

                    const sortedHierarchy = [rootNode, ...hierarchyNodes.filter(n => n.id !== rootNode.id)];
                    if (dialogToClose) { dialogToClose.hide(); }
                    hierarchyDialog.windowContent.innerHTML = '';
                    const newView = build_organization_hierarchy_view(org, sortedHierarchy, context, hierarchyDialog);
                    hierarchyDialog.windowContent.appendChild(newView);
                },
                onFailure: function(response) {
                    const errorMessage = parseErrorResponse(response, utils.gettext('Error reloading organization hierarchy'));
                    context.show();
                    context.notebook.goToTab(context.organizationsTab);
                    setTimeout(function() {
                        new Wirecloud.ui.MessageWindowMenu(errorMessage, 'error').show();
                    }, 200);
                }
            });
        }

        showAddGroupToOrgDialog(parentGroupName, hierarchyDialog, org) {
            const context = this;

            const dialog = new Wirecloud.ui.WindowMenu(
                utils.interpolate(utils.gettext('Add group to "%(parent)s"'), {parent: parentGroupName}),
                'wc-add-group-to-org'
            );

            const wrapper = new se.Container({class: 'um-edit-form'});

            const errorAlert = new se.Alert({state: 'danger', class: 'um-edit-error', title: utils.gettext('Error:')});
            errorAlert.hide();
            wrapper.appendChild(errorAlert);

            const desc = new se.Container({tagname: 'p', class: 'um-add-group-desc'});
            desc.wrapperElement.textContent = utils.interpolate(
                utils.gettext('Search and select a group to add as child of "%(parent)s"'),
                {parent: parentGroupName}
            );
            wrapper.appendChild(desc);

            const label = new se.Container({tagname: 'label', class: 'um-add-group-label'});
            label.wrapperElement.textContent = utils.gettext('Group');
            wrapper.appendChild(label);

            const groupField = new se.TextField({placeholder: utils.gettext('Search group...')});
            groupField.addClassName('um-add-user-field');
            wrapper.appendChild(groupField);

            let selectedGroupName = null;

            const groupTypeahead = new se.Typeahead({
                autocomplete: true,
                lookup: function(querytext) {
                    return Wirecloud.io.makeRequest(Wirecloud.URLs.SEARCH_SERVICE, {
                        parameters: {namespace: 'group', q: querytext},
                        method: 'GET',
                        contentType: 'application/json',
                        requestHeaders: {'Accept': 'application/json'}
                    }).then(function(response) {
                        const data = JSON.parse(response.responseText);
                        return data.results.filter(function(g) { return !g.is_organization || g.is_root !== true; });
                    });
                },
                build: function(typeahead, data) {
                    return {
                        value: data.name,
                        title: data.name,
                        description: data.is_organization ? utils.gettext('Organization') : utils.gettext('Group'),
                        iconClass: data.is_organization ? 'fas fa-building' : 'fas fa-users',
                        context: data
                    };
                }
            });
            groupTypeahead.bind(groupField);

            groupTypeahead.addEventListener('select', function(th, menuitem) {
                selectedGroupName = menuitem.context.name;
            });

            const actionsDiv = new se.Container({class: 'um-dialog-actions'});

            const addBtn = new se.Button({text: utils.gettext('Add Group'), class: 'btn-primary'});
            addBtn.addEventListener('click', function() {

                const groupName = selectedGroupName || groupField.getValue().trim();
                if (!groupName) { return; }

                errorAlert.hide();

                Wirecloud.io.makeRequest(
                    Wirecloud.URLs.ADMIN_ORGANIZATION_GROUP_ENTRY.evaluate({group_name: groupName}),
                    {
                        method: 'PUT',
                        contentType: 'application/json',
                        postBody: JSON.stringify({parent_name: parentGroupName}),
                        onSuccess: function() {
                            context.reloadHierarchyGraph(org, hierarchyDialog, dialog);
                            hierarchyDialog.show();
                            setTimeout(function() { context.loadGroups(); }, 1000);
                        },
                        onFailure: function(response) {
                            errorAlert.setMessage(parseErrorResponse(response, utils.gettext('Error adding group to organization')));
                            errorAlert.show();
                        }
                    }
                );
            });
            actionsDiv.appendChild(addBtn);

            const cancelBtn = new se.Button({text: utils.gettext('Cancel'), class: 'btn-default'});
            cancelBtn.addEventListener('click', function() {
                dialog.hide();
                hierarchyDialog.show();
            });
            actionsDiv.appendChild(cancelBtn);

            wrapper.appendChild(actionsDiv);
            dialog.windowContent.appendChild(wrapper.wrapperElement);
            dialog.show();
        }
    };

})(Wirecloud.ui, StyledElements, Wirecloud.Utils);
