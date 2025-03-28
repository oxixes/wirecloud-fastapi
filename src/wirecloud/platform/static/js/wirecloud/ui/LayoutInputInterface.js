/*
 *     Copyright (c) 2014-2016 CoNWeT Lab., Universidad Politécnica de Madrid
 *     Copyright (c) 2020 Future Internet Consulting and Development Solutions S.L.
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

    const LAYOUT_FIELDS_MAPPING = {
        'columnlayout': [
            {
                "name": "smart",
                "defaultValue": true,
                "label": utils.gettext("Smart"),
                "type": "boolean",
                "description": utils.gettext("Widgets will tend to be placed on the topmost position available if this option is enabled. (default: enabled)")
            },
            {
                "name": "columns",
                "min": 1,
                "max": 200,
                "defaultValue": 20,
                "label": utils.gettext("Columns"),
                "type": "number",
                "description": utils.gettext("Grid columns. (default: 20 columns)")
            },
            {
                "name": "cellheight",
                "min": 7,
                "max": 1024,
                "defaultValue": 13,
                "label": utils.gettext("Row Height (in pixels)"),
                "type": "number",
                "description": utils.gettext("Row/cell height. Must be specified in pixel units. (default: 13px)")
            },
            {
                "name": "horizontalmargin",
                "min": 0,
                "defaultValue": 4,
                "label": utils.gettext("Horizontal Margin between widgets (in pixels)"),
                "type": "number",
                "description": utils.gettext("Horizontal Margin between widgets. Must be specified in pixel units. (default: 4px)")
            },
            {
                "name": "verticalmargin",
                "min": 0,
                "defaultValue": 3,
                "label": utils.gettext("Vertical Margin between widgets (in pixels)"),
                "type": "number",
                "description": utils.gettext("Vertical Margin between widgets. Must be specified in pixel units. (default: 3px)")
            }
        ],
        'gridlayout': [
            {
                "name": "columns",
                "min": 1,
                "max": 200,
                "defaultValue": 20,
                "label": utils.gettext("Columns"),
                "type": "number",
                "description": utils.gettext("Grid columns. (default: 20 columns)")
            },
            {
                "name": "rows",
                "min": 1,
                "max": 200,
                "defaultValue": 12,
                "label": utils.gettext("Rows"),
                "type": "number",
                "description": utils.gettext("Grid rows. (default: 12 rows)")
            },
            {
                "name": "horizontalmargin",
                "min": 0,
                "defaultValue": 4,
                "label": utils.gettext("Horizontal Margin between widgets (in pixels)"),
                "type": "number",
                "description": utils.gettext("Horizontal Margin between widgets. Must be specified in pixel units. (default: 4px)")
            },
            {
                "name": "verticalmargin",
                "min": 0,
                "defaultValue": 3,
                "label": utils.gettext("Vertical Margin between widgets (in pixels)"),
                "type": "number",
                "description": utils.gettext("Vertical Margin between widgets. Must be specified in pixel units. (default: 3px)")
            }
        ]
    };

    const updateLayoutSummary = function updateLayoutSummary() {
        const context = utils.clone(this.layout);
        let summary = '';

        switch (this.layout.type) {
        case 'columnlayout':
            if (context.smart) {
                context.smart = utils.gettext(' smart');
            } else {
                context.smart = '';
            }
            summary = utils.gettext('%(columns)s%(smart)s columns');
            break;
        case 'gridlayout':
            summary = utils.gettext('%(columns)s columns x %(rows)s rows');
            break;
        }
        summary = utils.interpolate(summary, context);
        this.summary_addon.setLabel(summary).setTitle(summary);
    };

    /**
     *
     */
    ns.LayoutInputInterface = class LayoutInputInterface extends se.InputInterface {

        constructor(fieldId, options) {
            super(fieldId, options);

            this.wrapperElement = new StyledElements.Container({class: 'se-layout-field se-input-group'});

            // Layout type select
            this.selectElement = new StyledElements.Select({
                name: options.name + '-type',
                initialEntries: [
                    {"value": "columnlayout", "label": utils.gettext("Columns")},
                    {"value": "gridlayout", "label": utils.gettext("Grid")}
                ]
            });
            this.selectElement.addEventListener('change', function (select) {
                this.layout = utils.clone(this.layout);
                this.layout.type = select.getValue();

                const fields = LAYOUT_FIELDS_MAPPING[this.layout.type];
                for (let i = 0; i < fields.length; i++) {
                    if (!(fields[i].name in this.layout)) {
                        this.layout[fields[i].name] = fields[i].defaultValue;
                    }
                }
                updateLayoutSummary.call(this);
            }.bind(this));
            this.wrapperElement.appendChild(this.selectElement);

            // Summary-addon
            this.summary_addon = new StyledElements.Addon();
            this.wrapperElement.appendChild(this.summary_addon);

            // Settings button
            this.buttonElement = new StyledElements.Button({iconClass: 'fas fa-cogs'});
            this.buttonElement.addEventListener('click', function () {
                const fields = LAYOUT_FIELDS_MAPPING[this.layout.type];
                const dialog = new Wirecloud.ui.FormWindowMenu(fields, utils.gettext('Layout configuration'), 'wc-layout-settings-modal');

                // Form data is sent to server
                dialog.executeOperation = function (data) {
                    this.layout = utils.clone(this.layout);
                    utils.merge(this.layout, data);
                    updateLayoutSummary.call(this);
                }.bind(this);

                dialog.show(Wirecloud.UserInterfaceManager.currentWindowMenu);
                dialog.setValue(this.layout);
            }.bind(this));
            this.wrapperElement.appendChild(this.buttonElement);
        }

        static parse(value) {
            return JSON.parse(value);
        }

        static stringify(value) {
            return JSON.stringify(value);
        }

        _checkValue(newValue) {
            return StyledElements.InputValidationError.NO_ERROR;
        }

        getValue() {
            return this.layout;
        }

        setDisabled(disabled) {
            this.selectElement.setDisabled(disabled);
            this.summary_addon.setDisabled(disabled);
            this.buttonElement.setDisabled(disabled);
        }

        repaint() {
            this.wrapperElement.repaint();
        }

        _setValue(newValue) {
            this.layout = newValue;
            this.selectElement.setValue(this.layout.type);
            updateLayoutSummary.call(this);
        }

        _setError(error) {
        }

        insertInto(element) {
            this.wrapperElement.insertInto(element);
        }

    }

})(Wirecloud.ui, StyledElements, Wirecloud.Utils);
