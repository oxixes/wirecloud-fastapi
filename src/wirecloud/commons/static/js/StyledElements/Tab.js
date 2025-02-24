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

/* globals WeakMap, StyledElements */


(function (se, utils) {

    "use strict";

    const privates = new WeakMap();

    const on_label_get = function on_label_get() {
        return privates.get(this).tabElement.textContent;
    };

    const on_tabelement_get = function on_tabelement_get() {
        return privates.get(this).tabElement;
    };

    const defaultOptions = Object.freeze({
        closable: true,
        containerOptions: {},
        label: ""
    });

    /**
     * Creates a new instance of Tab. This component is meant to be used inside a
     * {@link StyledElements.Notebook} component, use
     * {@link StyledElements.Notebook#createTab} for creating new tabs.
     *
     * Supported events:
     * - close: event raised after removing the tab from its notebook.
     * - hide: event raised after the tab is hidden.
     * - show: event raised after the tab is displayed.
     *
     * @constructor
     * @extends StyledElements.Container
     * @name StyledElements.Tab
     * @since 0.5
     *
     * @param {Object.<String, *>} options
     *    Available options:
     *
     *    - `closable` (Boolean): `true` for allowing users to close this tab by
     *    providing a close button.
     *    - `containerOptions` (Object): options to be used for creating the
     *    associated container.
     *    - `name` (String): label to use for this tab.
     *
     */
    se.Tab = class Tab extends se.Container {

        constructor(id, notebook, options) {

            if (!(notebook instanceof se.Notebook)) {
                throw new TypeError("Invalid notebook argument");
            }

            options = utils.merge({}, defaultOptions, options);
            options.useFullHeight = true;

            /* call to the parent constructor */
            super(options.containerOptions, ['show', 'hide', 'close']);

            Object.defineProperties(this, {
                /**
                 * Name/label associated with this tab
                 *
                 * @memberof StyledElements.Tab#
                 * @since 0.8.0
                 *
                 * @type {String}
                 */
                label: {
                    get: on_label_get
                },
                notebook: {
                    value: notebook
                },
                tabElement: {
                    get: on_tabelement_get
                },
                /**
                 * id used for identify this tab
                 *
                 * @memberof StyledElements.Tab#
                 * @since 0.5.0
                 *
                 * @type {String}
                 */
                tabId: {
                    value: id
                }
            });

            const priv = {
                labelElement: document.createElement('span'),
                tabElement: document.createElement("li")
            };
            privates.set(this, priv);
            priv.tabElement.className = "se-notebook-tab";
            priv.tabElement.appendChild(priv.labelElement);

            this.wrapperElement.classList.add("se-notebook-tab-content");
            this.wrapperElement.classList.add("hidden");

            priv.tabElement.addEventListener(
                "click",
                () => {
                    this.notebook.goToTab(this.tabId);
                },
                false
            );

            /* Process options */
            if (options.closable) {
                const closeButton = new this.Button({
                    iconClass: "fas fa-times",
                    plain: true,
                    class: "close_button"
                });
                closeButton.insertInto(priv.tabElement);

                closeButton.addEventListener("click", this.close.bind(this), false);
            }

            // Support deprecated options.name
            if (options.name != null) {
                options.label = options.name;
            }
            Tab.prototype.setLabel.call(this, options.label);
            this.setTitle(options.title);
        }

        /**
         * Removes this `Tab` from the associated `Notebook`.
         *
         * @since 0.5
         * @name StyledElements.Tab#close
         *
         * @returns {StyledElements.Tab}
         *      The instance on which the member is called.
         */
        close() {
            this.notebook.removeTab(this.tabId);

            return this.dispatchEvent("close");
        }

        /**
         * Sets the label of this `Tab`.
         *
         * @since 0.8
         * @name StyledElements.Tab#setLabel
         *
         * @param {String} newLabel
         *     text to use as label of this `Tab`.
         *
         * @returns {StyledElements.Tab}
         *     The instance on which the member is called.
         */
        setLabel(newLabel) {
            privates.get(this).labelElement.textContent = newLabel;

            return this;
        };

        /**
         * Sets the content to be displayed on the tab's tooltip. Pass `null`,
         * an empty string or directly don't use the `title` parameter for not
         * using a tooltip.
         *
         * @since 0.5
         * @name StyledElements.Tab#setTitle
         *
         * @param {String} [title]
         *      Contents to display in the associated tooltip.
         *
         * @returns {StyledElements.Tab}
         *      The instance on which the member is called.
         */
        setTitle(title) {

            if (title == null || title === '') {
                if (this.tooltip != null) {
                    this.tooltip.destroy();
                    this.tooltip = null;
                }
            } else {
                if (this.tooltip == null) {
                    this.tooltip = new this.Tooltip({content: title, placement: ['bottom', 'top', 'right', 'left']});
                    this.tooltip.bind(privates.get(this).tabElement);
                }
                this.tooltip.options.content = title;
            }

            return this;
        }

        /**
         * @name StyledElements.Tab#setVisible
         * @deprecated since version 0.5
         * @see {@link StyledElements.Tab#show}, {@link StyledElements.Tab#hide} and
         *      {@link StyledElements.Tab#hidden}
         */
        setVisible(newStatus) {
            return newStatus ? this.show() : this.hide();
        }

        /**
         * @override
         * @name StyledElements.Tab#hide
         */
        hide() {
            super.hide();
            privates.get(this).tabElement.classList.remove("selected");
            return this;
        }

        /**
         * @override
         * @name StyledElements.Tab#show
         */
        show() {
            super.show();
            privates.get(this).tabElement.classList.add("selected");
            this.repaint(false);
            return this;
        }

        /**
         * TODO change this.
         *
         * @private
         */
        getTabElement() {
            return privates.get(this).tabElement;
        };

    }

    /**
     * Sets the label of this `Tab`.
     *
     * @name StyledElements.Tab#rename
     * @since 0.5
     * @deprecated since version 0.8
     * @see {@link StyledElements.Tab#setLabel}
     *
     * @param {String} name text to use as name of this `Tab`.
     *
     * @returns {StyledElements.Tab}
     *      The instance on which the member is called.
     */
    se.Tab.prototype.rename = se.Tab.prototype.setLabel;

    se.Tab.prototype.Tooltip = se.Tooltip;
    se.Tab.prototype.Button = se.Button;

})(StyledElements, StyledElements.Utils);
