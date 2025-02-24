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

    const onclick = function onclick(e) {

        if ('target' in e && e.target === this.wrapperElement) {
            e.stopPropagation();
            e.preventDefault();
        }

        const dialog = new Wirecloud.ui.MACSelectionWindowMenu(this.dialog_title, {
            scope: this.scope,
        });
        dialog.show(Wirecloud.UserInterfaceManager.currentWindowMenu);
        dialog.addEventListener('select', function (menu, selected_mashup) {
            this.setValue(selected_mashup);
        }.bind(this));

    };

    const onfocus = function onfocus() {
        this.wrapperElement.classList.add('focus');
        this.dispatchEvent('focus');
    };

    const onblur = function onblur() {
        this.wrapperElement.classList.remove('focus');
        this.dispatchEvent('blur');
    };

    /**
     * Field for selecting a mashable application component
     */
    ns.MACField = class MACField extends se.InputElement {

        constructor(options) {
            const defaultOptions = {
                'class': '',
                'scope': '',
                'dialog': null
            };
            options = Wirecloud.Utils.merge({}, defaultOptions, options);

            super(options.initialValue, ['change', 'focus', 'blur']);

            this.wrapperElement = document.createElement('div');
            this.wrapperElement.className = 'se-mac-field se-input-group';
            if (options.class !== "") {
                this.wrapperElement.className += " " + options.class;
            }

            this.inputElement = document.createElement("input");
            this.inputElement.setAttribute("type", "hidden");

            if (options.name) {
                this.inputElement.setAttribute("name", options.name);
            }

            if (options.id != null) {
                this.wrapperElement.setAttribute("id", options.id);
            }

            const close_button = new StyledElements.Button({iconClass: 'fas fa-times', title: utils.gettext('Clear current selection')});
            close_button.appendTo(this.wrapperElement);
            close_button.disable().addEventListener('click', function () {
                this.setValue('');
            }.bind(this));

            this.name_preview = document.createElement('div');
            this.name_preview.className = 'se-add-on';
            this.wrapperElement.appendChild(this.name_preview);
            this.wrapperElement.appendChild(this.inputElement);

            const button = new StyledElements.Button({iconClass: 'fas fa-search', title: utils.gettext('Search')});
            button.appendTo(this.wrapperElement);

            /* Public fields */
            Object.defineProperties(this, {
                'close_button': {value: close_button},
                'scope': {value: options.scope},
                'dialog_title': {value: options.dialog_title}
            });

            /* Internal events */
            this.wrapperElement.addEventListener('click', onclick.bind(this), false);
            button.addEventListener('click', onclick.bind(this), true);
            close_button.addEventListener('focus', onfocus.bind(this));
            close_button.addEventListener('blur', onblur.bind(this));
            button.addEventListener('focus', onfocus.bind(this));
            button.addEventListener('blur', onblur.bind(this));
        }

        insertInto(element, refElement) {
            StyledElements.InputElement.prototype.insertInto.call(this, element, refElement);
            this.repaint();
        }

        setValue(new_value) {
            let mac_id, mac_title;

            if (typeof new_value !== 'string') {
                mac_id = new_value.uri;
                mac_title = new_value.title;
            } else {
                mac_id = new_value;
                mac_title = new_value;
            }

            this.inputElement.value = mac_id;

            this.name_preview.textContent = mac_title;
            this.close_button.setDisabled(new_value === '');
            this.dispatchEvent('change');
        }

        getValue() {
            return this.inputElement.value;
        }

    }

    ns.MACInputInterface = class MACInputInterface extends se.InputInterface {

        constructor(fieldId, options) {
            super(fieldId, options);

            this.inputElement = new Wirecloud.ui.MACField(options);
        }

    }

})(Wirecloud.ui, StyledElements, Wirecloud.Utils);
