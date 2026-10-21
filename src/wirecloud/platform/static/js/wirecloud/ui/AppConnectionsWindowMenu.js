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

    ns.AppConnectionsWindowMenu = class AppConnectionsWindowMenu extends ns.WindowMenu {

        constructor() {
            super(utils.gettext('App connections'), 'wc-app-connections');
            this.buttons = [];
            this.content = new se.Container();
            this.content.wrapperElement.setAttribute('aria-live', 'polite');
            this.content.insertInto(this.windowContent);
            this.retry = new se.Button({text: utils.gettext('Retry'), class: 'btn-default'});
            this.retry.addEventListener('click', () => this.load());
            this.retry.insertInto(this.windowBottom);
            const close = new se.Button({text: utils.gettext('Close'), class: 'btn-default'});
            close.addEventListener('click', () => this.hide());
            close.insertInto(this.windowBottom);
            this.load();
        }

        showError(response) {
            let message = utils.gettext('Unable to load app connections. Please try again.');
            if (response && response.status === 401) {
                message = utils.gettext('Your session has expired. Sign in again to manage app connections.');
            } else if (response && response.status === 403) {
                message = utils.gettext('Access denied. Reopen App connections and try again.');
            }
            this.content.clear().appendChild(new se.Alert({state: 'danger', title: message}));
            this.retry.show();
            this.repaint();
        }

        load() {
            this.retry.hide();
            this.buttons = [];
            this.content.clear().appendChild(utils.gettext('Loading app connections…'));
            Wirecloud.io.makeRequest(Wirecloud.URLs.OAUTH2_CONNECTIONS, {
                method: 'GET',
                requestHeaders: {'Accept': 'application/json'},
                onSuccess: (response) => {
                    let data;
                    try {
                        data = JSON.parse(response.responseText);
                        if (!Array.isArray(data.connections) || typeof data.csrf !== 'string') {
                            throw new TypeError('Invalid connections response');
                        }
                    } catch (error) {
                        this.showError();
                        return;
                    }
                    this.csrf = data.csrf;
                    this.render(data.connections);
                },
                onFailure: (response) => this.showError(response)
            });
        }

        render(connections) {
            this.content.clear();
            if (connections.length === 0) {
                const empty = new se.Alert({state: 'info', title: utils.gettext('No connected applications')});
                empty.body.appendChild(utils.gettext('Applications you authorize will appear here. You can revoke their access at any time.'));
                this.content.appendChild(empty);
            }
            connections.forEach((connection) => {
                const revoke = new se.Button({text: utils.gettext('Revoke'), class: 'btn-danger'});
                revoke.wrapperElement.setAttribute('aria-label', utils.gettext('Revoke access for') + ' ' + connection.client_name);
                revoke.addEventListener('click', () => this.revoke(connection.id));
                this.buttons.push(revoke);
                const panel = new se.Panel({title: connection.client_name, subtitle: connection.resource_name});
                const permissions = new se.Container({tagname: 'ul', class: 'app-connection-permissions'});
                connection.permissions.forEach((permission) => {
                    permissions.appendChild(new se.Container({tagname: 'li'}).appendChild(utils.gettext(permission)));
                });
                panel.body.appendChild(permissions);
                const footer = new se.Container({class: 'panel-footer app-connection-footer'});
                const details = new se.Container({tagname: 'details', class: 'app-connection-details'});
                details.appendChild(new se.Container({tagname: 'summary'}).appendChild(utils.gettext('Application ID')));
                details.appendChild(new se.Container({tagname: 'p'}).appendChild(connection.client_id));
                footer.appendChild(details);
                footer.appendChild(revoke);
                footer.insertInto(panel.wrapperElement);
                this.content.appendChild(panel);
            });
            this.repaint();
        }

        revoke(grantId) {
            this.buttons.forEach((button) => button.disable());
            Wirecloud.io.makeRequest(Wirecloud.URLs.OAUTH2_CONNECTIONS, {
                method: 'POST',
                requestHeaders: {'Accept': 'application/json'},
                parameters: {csrf: this.csrf, grant_id: grantId},
                onSuccess: () => this.load(),
                onFailure: (response) => this.showError(response)
            });
        }

    };

})(Wirecloud.ui, StyledElements, Wirecloud.Utils);
