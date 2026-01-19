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

/* globals StyledElements, Wirecloud */


(function (ns, se, utils) {

    "use strict";

    const titles = ['', utils.gettext('Error'), utils.gettext('Warning'), utils.gettext('Info')];

    /**
     * Specific class representing alert dialogs.
     */
    ns.MessageWindowMenu = class MessageWindowMenu extends ns.WindowMenu {

        constructor(message, type) {
            super('', 'message');

            this.msgElement = document.createElement('div');
            this.msgElement.className = "msg";
            this.windowContent.appendChild(this.msgElement);

            // Accept button
            this.button = new se.Button({
                text: utils.gettext('Accept'),
                state: 'primary',
                class: 'btn-accept btn-cancel'
            });
            this.button.insertInto(this.windowBottom);
            this.button.addEventListener("click", this._closeListener);

            this.setMsg(message);
            this.setType(type);
        }

        /**
         * Updates the message displayed by this <code>WindowMenu</code>
         */
        setMsg(msg) {

            if (msg instanceof se.StyledElement) {
                this.msgElement.innerHTML = '';
                msg.insertInto(this.msgElement);
            } else {
                this.msgElement.textContent = msg;
            }

            this.repaint();
        }

        setFocus() {
            this.button.focus();
        }

        setType(type) {
            // Update title
            this.setTitle(typeof type === "number" ? titles[type] : type);
        }

    }

})(Wirecloud.ui, StyledElements, Wirecloud.Utils);
