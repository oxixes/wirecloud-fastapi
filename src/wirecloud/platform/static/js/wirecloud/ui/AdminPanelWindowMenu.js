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

    const addInfoRow = function addInfoRow(list, label, value) {
        const dt = new se.Container({tagname: 'dt'});
        dt.appendChild(label);
        list.appendChild(dt);

        const dd = new se.Container({tagname: 'dd'});
        dd.appendChild(value);
        list.appendChild(dd);
    };

    const build_info_section = function build_info_section() {
        const panel = new se.Panel({title: utils.gettext('System Information'), state: 'default'});

        const infoList = new se.Container({tagname: 'dl', class: 'info-list'});

        addInfoRow(infoList, utils.gettext('Current User:'), Wirecloud.contextManager.get('username') || '-');
        addInfoRow(infoList, utils.gettext('Superuser:'), Wirecloud.contextManager.get('issuperuser') ? utils.gettext('Yes') : utils.gettext('No'));
        addInfoRow(infoList, utils.gettext('Staff:'), Wirecloud.contextManager.get('isstaff') ? utils.gettext('Yes') : utils.gettext('No'));

        panel.body.appendChild(infoList);
        return panel;
    };

    const build_actions_section = function build_actions_section() {
        const panel = new se.Panel({title: utils.gettext('Actions'), state: 'default'});

        const btn1 = new se.Button({
            text: utils.gettext('User Management'),
            class: 'btn-primary'
        });
        btn1.addEventListener('click', function() {
            const userMgmt = new Wirecloud.ui.UserManagementWindowMenu();
            userMgmt.show();
        });
        panel.body.appendChild(btn1);

        return panel;
    };

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
                onFailure: function(response) {
                    reject(new Error('Failed to fetch ' + namespace));
                }
            });
        });
    };

    const build_statistics_section = function build_statistics_section() {
        const panel = new se.Panel({title: utils.gettext('Statistics'), state: 'default'});

        const grid = new se.Container({class: 'stats-grid'});

        const createStatCard = function(label, initialValue = '...', variant = 'default') {
            const card = new se.Panel({state: variant, class: 'stat-card'});

            const valueEl = new se.Container({class: 'stat-value'});
            valueEl.appendChild(initialValue);
            card.body.appendChild(valueEl);

            const labelEl = new se.Container({class: 'stat-label'});
            labelEl.appendChild(label);
            card.body.appendChild(labelEl);

            return {card, valueEl};
        };

        const usersCard = createStatCard(utils.gettext('Total Users'), '...', 'primary');
        grid.appendChild(usersCard.card);

        const groupsCard = createStatCard(utils.gettext('Total Groups'), '...', 'info');
        grid.appendChild(groupsCard.card);

        const orgsCard = createStatCard(utils.gettext('Total Organizations'), '...', 'success');
        grid.appendChild(orgsCard.card);

        const workspacesCard = createStatCard(utils.gettext('Total Workspaces'), '...', 'warning');
        grid.appendChild(workspacesCard.card);

        panel.body.appendChild(grid);

        fetchElasticsearchData('user').then(data => {
            usersCard.valueEl.clear().appendChild(data.total.toString());
        }).catch(() => {
            usersCard.valueEl.clear().appendChild('0');
        });

        fetchElasticsearchData('group').then(data => {
            const groups = data.results ? data.results.filter(item => !item.is_organization) : [];
            groupsCard.valueEl.clear().appendChild(groups.length.toString());

            const organizations = data.results ? data.results.filter(item => item.is_organization && item.is_root) : [];
            orgsCard.valueEl.clear().appendChild(organizations.length.toString());
        }).catch(() => {
            groupsCard.valueEl.clear().appendChild('0');
            orgsCard.valueEl.clear().appendChild('0');
        });

        let totalWorkspaces = 0;
        if (Wirecloud.workspacesByUserAndName) {
            for (let username in Wirecloud.workspacesByUserAndName) {
                totalWorkspaces += Object.keys(Wirecloud.workspacesByUserAndName[username]).length;
            }
        }
        workspacesCard.valueEl.clear().appendChild(totalWorkspaces.toString());

        return panel;
    };

    ns.AdminPanelWindowMenu = class AdminPanelWindowMenu extends Wirecloud.ui.WindowMenu {

        constructor() {
            super(utils.gettext('Administration Panel'), 'wc-admin-panel');

            build_info_section().insertInto(this.windowContent);
            build_statistics_section().insertInto(this.windowContent);
            build_actions_section().insertInto(this.windowContent);
        }

    };

})(Wirecloud.ui, StyledElements, Wirecloud.Utils);