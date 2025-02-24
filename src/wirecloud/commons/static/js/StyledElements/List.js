/*
 *     Copyright (c) 2011-2016 CoNWeT Lab., Universidad Politécnica de Madrid
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

/* globals StyledElements */


(function (se, utils) {

    "use strict";

    const itemListener = function itemListener() {
        if (this.listComponent.enabled) {
            this.listComponent.toggleElementSelection(this.value);
        }
    };

    const _cleanSelection = function _cleanSelection() {
        for (let i = 0; i < this.currentSelection.length; i++) {
            const value = this.currentSelection[i];
            this.entriesByValue[value].element.classList.remove("selected");
        }
        this.currentSelection = [];
    };

    /**
     * A list
     */
    se.List = class List extends se.StyledElement {

        constructor(options) {
            options = utils.merge({
                class: '',
                id: null,
                multivalued: false,
                initialEntries: [],
                initialSelection: []
            }, options);

            super(['change']);

            this.wrapperElement = document.createElement("div");
            this.wrapperElement.className = utils.prependWord(options.class, "styled_list");

            if (options.id != null) {
                this.wrapperElement.id = options.id;
            }

            this.content = document.createElement("div");
            this.wrapperElement.appendChild(this.content);

            this.entries = [];
            this.entriesByValue = {};
            this.currentSelection = [];

            this.addEntries(options.initialEntries);
            this.select(options.initialSelection);

            /* Process options */
            if (options.full) {
                this.wrapperElement.classList.add("full");
            }

            this.multivalued = options.multivalued;

            if (options.allowEmpty === undefined) {
                this.allowEmpty = this.multivalued;
            } else {
                this.allowEmpty = options.allowEmpty;
            }
        }

        /**
         * Añade las entradas indicadas en la lista.
         */
        addEntries(entries) {
            let entryValue, entryText;

            if (entries == null || entries.length === 0) {
                return;
            }

            if (!Array.isArray(entries)) {
                throw new TypeError();
            }

            for (let i = 0; i < entries.length; i++) {
                const entry = entries[i];
                if (Array.isArray(entry)) {
                    entryValue = entry[0];
                    entryText = entry[1];
                } else {
                    entryValue = entries[i].value;
                    entryText = entries[i].label;
                }
                entryText = entryText ? entryText : entryValue;

                const row = document.createElement("div");
                row.className = "row";

                const context = {listComponent: this, value: entryValue};
                row.addEventListener("click", itemListener.bind(context), true);
                entry.element = row;

                row.appendChild(document.createTextNode(entryText));
                this.content.appendChild(row);

                this.entriesByValue[entryValue] = entry;
            }
            this.entries = this.entries.concat(entries);
        }

        removeEntryByValue(value) {
            const entry = this.entriesByValue[value];
            delete this.entriesByValue[value];
            this.entries.slice(this.entries.indexOf(entry), 1);
            entry.element.remove();

            const index = this.currentSelection.indexOf(entry);
            if (index !== -1) {
                this.currentSelection.splice(index, 1);
                this.dispatchEvent('change', this.currentSelection, [], [value]);
            }
        }

        /**
         * Removes all entries of this List
         */
        clear() {
            this.cleanSelection();

            this.content.innerHTML = '';
            this.entries = [];
            this.entriesByValue = {};
        }

        /**
         * Devuelve una copia de la selección actual.
         */
        getSelection() {
            return utils.clone(this.currentSelection);
        }

        /**
         * Borra la seleccion actual.
         */
        cleanSelection() {
            if (this.currentSelection.length === 0) {
                return;  // Nothing to do
            }

            const oldSelection = this.currentSelection;

            _cleanSelection.call(this);

            this.dispatchEvent('change', [], [], oldSelection);
        }

        /**
         * Cambia la selección actual a la indicada.
         *
         * @param {Array} selection lista de valores a seleccionar.
         */
        select(selection) {
            _cleanSelection.call(this);

            this.addSelection(selection);
        }

        /**
         * Añade un conjunto de valores a la selección actual.
         */
        addSelection(selection) {
            if (selection.length === 0) {
                return;  // Nothing to do
            }

            const addedValues = [];
            let removedValues = [];

            if (!this.multivalued) {
                if (selection[0] === this.currentSelection[0]) {
                    return; // Nothing to do
                }

                removedValues = this.currentSelection;

                _cleanSelection.call(this);

                if (selection.length > 1) {
                    selection = selection.splice(0, 1);
                }
            }

            selection.forEach((entry) => {
                if (this.currentSelection.indexOf(entry) === -1) {
                    this.entriesByValue[entry].element.classList.add("selected");
                    this.currentSelection.push(entry);
                    addedValues.push(entry);
                }
            })

            this.dispatchEvent('change', this.currentSelection, addedValues, removedValues);
        }

        /**
         * Elimina un conjunto de valores de la selección actual.
         */
        removeSelection(selection) {
            if (selection.length === 0) {
                return;  // Nothing to do
            }

            const removedValues = [];
            selection.forEach((entry) => {
                this.entriesByValue[entry].element.classList.remove("selected");
                const index = this.currentSelection.indexOf(entry);
                if (index !== -1) {
                    this.currentSelection.splice(index, 1);
                    this.entriesByValue[entry].element.classList.remove("selected");
                    removedValues.push(entry);
                }
            })

            if (removedValues.length > 0) {
                this.dispatchEvent('change', this.currentSelection, [], removedValues);
            }
        }

        /**
         * Añade o borra una entrada de la selección dependiendo de si el elemento está
         * ya selecionado o no. En caso de que la entrada estuviese selecionado, el
         * elemento se eliminiaria de la selección y viceversa.
         */
        toggleElementSelection(element) {
            if (!this.entriesByValue[element].element.classList.contains("selected")) {
                this.addSelection([element]);
            } else if (this.allowEmpty) {
                this.removeSelection([element]);
            }
        }

    }

})(StyledElements, StyledElements.Utils);
