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

    const canRename = function canRename() {
        return this.type === 'widget' && this._component.isAllowed('rename', 'editor');
    };

    const canUpgrade = function canUpgrade() {
        return !this.background && this._component.isAllowed('upgrade', 'editor') && Wirecloud.LocalCatalogue.hasAlternativeVersion(this._component.meta);
    };

    const canCollapseEndpoints = function canCollapseEndpoints() {
        return this.hasEndpoints() && !this.background && !this.orderingEndpoints;
    };

    const canDeleteCascade = function canDeleteCascade() {
        return this.isRemovable();
    };

    const canOrderEndpoints = function canOrderEndpoints() {
        return this.hasOrderableEndpoints() && !this.background && !this.missing && !this.collapsed;
    };

    const canShowSettings = function canShowSettings() {
        return this.hasSettings() && this._component.isAllowed('configure', 'editor');
    };

    const getItemCollapse = function getItemCollapse() {
        if (this.collapsed) {
            return {title: utils.gettext("Expand"), icon: "far fa-caret-square-down"};
        } else {
            return {title: utils.gettext("Collapse"), icon: "far fa-caret-square-up"};
        }
    };

    const getItemOrderEndpoints = function getItemOrderEndpoints() {
        if (this.orderingEndpoints) {
            return {title: utils.gettext("Stop ordering"), icon: "fas fa-sort"};
        } else {
            return {title: utils.gettext("Order endpoints"), icon: "fas fa-sort"};
        }
    };

    const showRenameModal = function showRenameModal() {
        const dialog = new Wirecloud.ui.FormWindowMenu(
            [
                {name: 'title', label: utils.gettext("Title"), type: 'text', placeholder: this.component.title},
            ],
            utils.interpolate(utils.gettext("Rename %(type)s"), this.component),
            "wc-component-rename-modal"
        );

        dialog.executeOperation = function (data) {
            if (data.title) {
                this.component._component.rename(data.title);
            }
        }.bind(this);

        dialog.show();
        dialog.setValue({title: this.component.title});
    };

    /**
     * Create a new instance of class ComponentDraggablePrefs.
     * @extends {DynamicMenuItems}
     *
     * @constructor
     */
    ns.ComponentDraggablePrefs = class ComponentDraggablePrefs extends se.DynamicMenuItems {

        constructor(component) {
            super();
            this.component = component;
        }

        _createMenuItem(title, iconClass, onclick, isEnabled) {
            const item = new se.MenuItem(title, onclick);
            item.addIconClass(iconClass);

            if (isEnabled != null) {
                item.enabled = isEnabled.call(this.component);
            }

            return item;
        }

        /**
         * @override
         */
        build() {
            const item1 = getItemCollapse.call(this.component),
                item2 = getItemOrderEndpoints.call(this.component);

            let list = [
                this._createMenuItem(utils.gettext("Rename"), "fas fa-pencil-alt", function () {
                    showRenameModal.call(this);
                }.bind(this), canRename),
                this._createMenuItem(item1.title, item1.icon, function () {
                    this.collapsed = !this.collapsed;
                }.bind(this.component), canCollapseEndpoints),
                this._createMenuItem(item2.title, item2.icon, function () {
                    if (this.orderingEndpoints) {
                        this.stopOrderingEndpoints();
                    } else {
                        this.startOrderingEndpoints();
                    }
                }.bind(this.component), canOrderEndpoints),
                this._createMenuItem(utils.gettext("Upgrade/Downgrade"), "fas fa-retweet", function () {
                    const dialog = new Wirecloud.ui.UpgradeWindowMenu(this._component);
                    dialog.show();
                }.bind(this.component), canUpgrade),
                this._createMenuItem(utils.gettext("Logs"), "fas fa-tags", function () {
                    this.showLogs();
                }.bind(this.component)),
                this._createMenuItem(utils.gettext("Settings"), "fas fa-cog", function () {
                    this.showSettings();
                }.bind(this.component), canShowSettings)
            ];

            if (this.component.removeCascadeAllowed) {
                list = list.concat(this._createMenuItem(utils.gettext("Delete cascade"), "trash", function () {
                    this.dispatchEvent("optremovecascade");
                }.bind(this.component), canDeleteCascade));
            }

            return list;
        }

    }

})(Wirecloud.ui.WiringEditor, StyledElements, StyledElements.Utils);
