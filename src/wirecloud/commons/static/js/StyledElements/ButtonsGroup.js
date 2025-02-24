/*
 *     Copyright (c) 2008-2016 CoNWeT Lab., Universidad Politécnica de Madrid
 *     Copyright (c) 2020-2021 Future Internet Consulting and Development Solutions S.L.
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

    /**
     * Virtual input field grouping a set of radio buttons or checkboses
     */
    se.ButtonsGroup = class ButtonsGroup extends se.InputElement {

        constructor(name) {
            super("", ['change']);

            Object.defineProperty(this, 'name', {value: name});
            this.buttons = [];
        }

        /**
         * @private
         */
        insertButton(button) {
            this.buttons[this.buttons.length] = button;
            button.addEventListener(
                'change',
                () => {
                    this.dispatchEvent('change');
                }
            );

            return this;
        }

        getValue() {
            if (this.buttons[0] instanceof StyledElements.CheckBox) {
                const result = [];
                this.buttons.forEach((button) => {
                    if (button.inputElement.checked) {
                        result.push(button.getValue());
                    }
                });
                return result;
            } else {
                for (let i = 0; i < this.buttons.length; i++) {
                    if (this.buttons[i].inputElement.checked) {
                        return this.buttons[i].getValue();
                    }
                }
            }
        }

        setValue(newValue) {
            if (newValue == null) {
                newValue = [];
            } else if (typeof newValue === 'string') {
                newValue = [newValue];
            }

            this.buttons.forEach((button) => {
                button.setValue(newValue.indexOf(button.inputElement.value) !== -1);
            });

            return this;
        }

        reset() {
            this.buttons.forEach((button) => {
                button.reset();
            });

            return this;
        }

        /**
         * Devuelve una lista de los elementos CheckBox o RadioButton
         * seleccionados. En caso de que la selección este vacía, este método devolverá
         * una lista vacía y en caso de que este ButtonGroup este formado por
         * RadioButtons, la selección será como mucho de un elemento.
         */
        getSelectedButtons() {
            if (this.buttons.length === 0) {
                return [];
            }

            if (this.buttons[0] instanceof StyledElements.CheckBox) {
                const result = [];

                for (let i = 0; i < this.buttons.length; i++) {
                    if (this.buttons[i].inputElement.checked) {
                        result[result.length] = this.buttons[i];
                    }
                }

                return result;
            } else {
                for (let i = 0; i < this.buttons.length; i++) {
                    if (this.buttons[i].inputElement.checked) {
                        return [this.buttons[i]];
                    }
                }
                return [];
            }
        }

    }

})(StyledElements, StyledElements.Utils);
