/*
 *     Copyright (c) 2015-2016 CoNWeT Lab., Universidad Politécnica de Madrid
 *     Copyright (c) 2021 Future Internet Consulting and Development Solutions S.L.
 *
 *     This file is part of Wirecloud Platform.
 *
 *     Wirecloud Platform is free software: you can redistribute it and/or
 *     modify it under the terms of the GNU Affero General Public License as
 *     published by the Free Software Foundation, either version 3 of the
 *     License, or (at your option) any later version.
 *
 *     Wirecloud is distributed in the hope that it will be useful, but WITHOUT
 *     ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 *     FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public
 *     License for more details.
 *
 *     You should have received a copy of the GNU Affero General Public License
 *     along with Wirecloud Platform.  If not, see
 *     <http://www.gnu.org/licenses/>.
 *
 */

/* globals StyledElements, Wirecloud */


(function (ns, se, utils) {

    "use strict";

    /**
     * Create a new instance of class BehaviourPrefs.
     * @extends {DynamicMenuItems}
     *
     * @constructor
     */
    ns.BehaviourPrefs = class BehaviourPrefs extends se.DynamicMenuItems {

        constructor(behaviour) {
            super();
            this.behaviour = behaviour;
        }

        _createMenuItem(title, iconClass, onclick, isEnabled) {
            const item = new se.MenuItem(utils.gettext(title), onclick);
            item.addIconClass(iconClass);

            if (isEnabled != null) {
                item.enabled = isEnabled.call(this.behaviour);
            }

            return item;
        }

        /**
         * @override
         */
        build() {
            return [
                this._createMenuItem("Logs", "fas fa-tags", () => {
                    this.behaviour.showLogs();
                }),
                this._createMenuItem("Settings", "fas fa-cog", () => {
                    this.behaviour.showSettings();
                })
            ];
        }

    }

})(Wirecloud.ui.WiringEditor, StyledElements, StyledElements.Utils);
