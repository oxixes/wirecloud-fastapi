/*
 *     Copyright (c) 2015 CoNWeT Lab., Universidad Politécnica de Madrid
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

    const defaultOptions = {
        state: "warning",
        alignment: "",
        class: "",
        title: "",
        message: ""
    };
    Object.freeze(defaultOptions);

    /**
     * Create a new instance of class Alert.
     *
     * @constructor
     * @extends StyledElements.StyledElement
     * @since 0.6
     * @param {Object.<String, *>} [options] [description]
     */
    se.Alert = class Alert extends se.StyledElement {

        constructor(options) {
            options = utils.merge({}, defaultOptions, options);

            super();

            this.wrapperElement = document.createElement('div');
            this.wrapperElement.className = 'alert';

            if (options.state != null && options.state.trim() !== "") {
                this.addClassName('alert-' + options.state);
            }

            if (options.alignment) {
                this.addClassName('se-alert-' + options.alignment);
            }

            this.addClassName(options.class);

            const heading = new se.Container({
                class: "se-alert-heading"
            });
            heading.appendChild(options.title).insertInto(this.wrapperElement);

            const body = new se.Container({
                class: "se-alert-body"
            });
            body.appendChild(options.message).insertInto(this.wrapperElement);

            Object.defineProperties(this, {
                heading: {value: heading},
                body: {value: body}
            });
        }

        /**
         * [addNote description]
         *
         * @param {StyledElement|String} textContent
         *      [description]
         * @returns {Alert}
         *      The instance on which the member is called.
         */
        addNote(textContent) {
            const blockquote = document.createElement('blockquote');

            if (textContent instanceof StyledElements.StyledElement) {
                textContent.appendTo(blockquote);
            } else {
                blockquote.innerHTML = textContent;
            }
            this.body.appendChild(blockquote);

            return blockquote;
        }

        /**
         * setMessage
         *
         * @param {String} message
         *    The message to be displayed.
         */
        setMessage(message) {
            this.body.clear();
            this.body.appendChild(message);
        }

        /**
         * show
         */
        show() {
            this.wrapperElement.style.display = '';
        }

        /**
         * hide
         */
        hide() {
            this.wrapperElement.style.display = 'none';
        }

    }

})(StyledElements, StyledElements.Utils);
