/*
 *     Copyright (c) 2008-2016 CoNWeT Lab., Universidad Politécnica de Madrid
 *     Copyright (c) 2018-2021 Future Internet Consulting and Development Solutions S.L.
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

/* globals CSSPrimitiveValue, StyledElements */


(function (se, utils) {

    "use strict";

    const onNewTab = function onNewTab() {
        this.dispatchEvent('newTab');
    };

    const isTabVisible = function isTabVisible(tabIndex, full) {
        const tabElement = this.tabs[tabIndex].getTabElement();

        const tabAreaStart = this.tabArea.wrapperElement.scrollLeft;
        const tabAreaEnd = tabAreaStart + this.tabArea.wrapperElement.clientWidth;

        if (full) {
            const tabOffsetRight = tabElement.offsetLeft + tabElement.offsetWidth;
            return tabElement.offsetLeft >= tabAreaStart && tabOffsetRight <= tabAreaEnd;
        } else {
            return tabElement.offsetLeft >= tabAreaStart && tabElement.offsetLeft <= tabAreaEnd;
        }
    };

    const isLastTabVisible = function isLastTabVisible() {
        const lastTab = this.tabs.length - 1;

        if (this.tabs.length === 0 || isTabVisible.call(this, lastTab, true)) {
            return true;
        }
        if (!isTabVisible.call(this, lastTab)) {
            return false;
        }
        return this.tabs.length < 2 || !isTabVisible.call(this, lastTab - 1);
    };

    const enableDisableButtons = function enableDisableButtons() {
        if (this.tabs.length === 0) {
            this.moveLeftButton.disable();
            this.moveRightButton.disable();
            if (this.new_tab_button_tabs != null) {
                this.new_tab_button_tabs.enable();
                this.new_tab_button_left.disable();
            }
            return;
        }

        let first_tab_visible = isTabVisible.call(this, 0);
        const last_tab_visible = isLastTabVisible.call(this);

        this.moveLeftButton.setDisabled(first_tab_visible);
        this.moveRightButton.setDisabled(last_tab_visible);

        if (this.new_tab_button_tabs != null) {
            first_tab_visible = isTabVisible.call(this, 0, true);
            if (first_tab_visible && last_tab_visible) {
                this.new_tab_button_tabs.enable();
                this.new_tab_button_left.disable();
            } else {
                this.new_tab_button_tabs.disable();
                this.new_tab_button_left.enable();
            }
            this.tabWrapper.repaint();
        }
    };

    const getFirstVisibleTab = function getFirstVisibleTab() {
        return this.tabs.findIndex((element, index) => {return isTabVisible.call(this, index);});
    };

    const defaultOptions = {
        'class': '',
        'focusOnSetVisible': true,
        'full': true
    };
    Object.freeze(defaultOptions);

    se.Notebook = class Notebook extends se.StyledElement {

        /**
         * Creates a new instance of Notebook. This component is composed of
         * {@link StyledElements.Tab}s.
         *
         * Supported events:
         * - change: this event is dispatched when the notebook changes the visibleTab
         *   tab.
         * - tabDeletion: evento lanzado cuando se elimina algún tab del notebook.
         * - tabInsertion: evento lanzado cuando se crea e inserta un nuevo tab en
         *  el notebook.
         *
         * @constructor
         * @extends StyledElements.StyledElement
         * @name StyledElements.Notebook
         * @since 0.5
         * @param {Object.<String, *>} options
         * - focusOnSetVisible (Boolean): focus the selected tab when they are
         *  displayed (`true` by default).
         *
         */
        constructor(options) {
            super(['change', 'changed', 'tabDeletion', 'tabInsertion', 'newTab']);

            options = utils.merge({}, defaultOptions, options);

            this.wrapperElement = document.createElement("div");
            this.wrapperElement.className = utils.prependWord(options.class, "se-notebook");

            const tabWrapper = new StyledElements.HorizontalLayout({'class': 'se-notebook-tabs-wrapper', 'autoHeight': false});
            this.tabWrapper = tabWrapper;
            tabWrapper.insertInto(this.wrapperElement);

            this.tabArea = new StyledElements.Container();
            tabWrapper.center.appendChild(this.tabArea.addClassName('se-notebook-tab-area'));

            this.moveLeftButton = new this.Button({class: 'move_left', iconClass: 'fas fa-caret-left'});
            tabWrapper.west.appendChild(this.moveLeftButton);

            this.moveRightButton = new this.Button({class: 'move_right', iconClass: 'fas fa-caret-right'});
            tabWrapper.east.appendChild(this.moveRightButton);

            this.contentArea = document.createElement("div");
            this.contentArea.className = "se-notebook-content-wrapper";
            this.wrapperElement.appendChild(this.contentArea);

            this.tabs = [];
            this.tabsById = [];
            this.visibleTab = null;

            /* Process options */
            if (options.id != null) {
                this.wrapperElement.setAttribute('id', options.id);
            }

            if (options.full) {
                this.wrapperElement.classList.add('full');
            }

            this.focusOnSetVisible = options.focusOnSetVisible;

            /* Tab creation support */
            this.events.newTab.addEventListener = function addEventListener(listener) {
                if (this.new_tab_button_tabs == null) {
                    const new_tab_main_listener = onNewTab.bind(this);

                    this.new_tab_button_tabs = new this.Button({iconClass: 'fas fa-plus', 'class': 'se-notebook-new-tab', title: utils.gettext('Add Tab')});
                    this.new_tab_button_tabs.addEventListener('click', new_tab_main_listener);
                    this.tabArea.appendChild(this.new_tab_button_tabs);
                    this.new_tab_button_left = new this.Button({iconClass: 'fas fa-plus', 'class': 'se-notebook-new-tab', title: utils.gettext('Add Tab')});
                    this.new_tab_button_left.addEventListener('click', new_tab_main_listener);
                    this.addToEastSection(this.new_tab_button_left);
                }
                StyledElements.Event.prototype.addEventListener.call(this.events.newTab, listener);
            }.bind(this);

            /* Transitions code */
            const context = {
                control: this,
                initialScrollLeft: null,
                finalScrollLeft: null,
                steps: null,
                step: null,
                inc: null
            };

            const stepFunc = function stepFunc(step, context) {
                const scrollLeft = context.initialScrollLeft + Math.floor((step + 1) * context.inc);

                if ((context.inc < 0) && (scrollLeft > context.finalScrollLeft) ||
                    (context.inc > 0) && (scrollLeft < context.finalScrollLeft)) {
                    context.control.tabArea.wrapperElement.scrollLeft = Math.round(scrollLeft);
                    return true;  // we need to do more iterations
                } else {
                    // Finish current transition
                    context.control.tabArea.wrapperElement.scrollLeft = context.finalScrollLeft;
                    enableDisableButtons.call(context.control);

                    return false;
                }
            };

            const initFunc = function initFunc(context, command) {
                context.initialScrollLeft = context.control.tabArea.wrapperElement.scrollLeft;
                const computedStyle = document.defaultView.getComputedStyle(context.control.tabArea.wrapperElement, null);
                const padding = computedStyle.getPropertyCSSValue('padding-left').getFloatValue(CSSPrimitiveValue.CSS_PX);

                let firstVisibleTab;
                switch (command.type) {
                case 'shiftLeft':

                    if (context.control.tabs.length === 0 || isTabVisible.call(context.control, 0)) {
                        return false;
                    }

                    firstVisibleTab = getFirstVisibleTab.call(context.control);
                    context.tab = context.control.tabs[firstVisibleTab - 1];
                    context.finalScrollLeft = context.tab.getTabElement().offsetLeft - padding;
                    break;

                case 'shiftRight':
                    if (isLastTabVisible.call(context.control)) {
                        return false;
                    }

                    firstVisibleTab = getFirstVisibleTab.call(context.control);
                    context.tab = context.control.tabs[firstVisibleTab + 1];
                    context.finalScrollLeft = context.tab.getTabElement().offsetLeft - padding;
                    break;

                case 'focus':
                    if (command.tab == null || context.control.tabsById[command.tab.tabId] !== command.tab) {
                        // Tab removed
                        return false;
                    }
                    context.tab = command.tab;

                    if (isTabVisible.call(context.control, context.control.getTabIndex(command.tab), true)) {
                        return false;
                    }
                    context.finalScrollLeft = context.tab.getTabElement().offsetLeft - padding;
                    break;
                }

                const maxScrollLeft = context.control.tabArea.wrapperElement.scrollWidth - context.control.tabArea.wrapperElement.clientWidth;
                if (context.finalScrollLeft > maxScrollLeft) {
                    context.finalScrollLeft = maxScrollLeft;
                }

                const baseTime = (new Date()).getTime() + 100;
                const stepTimes = [];
                context.steps = 6;
                for (let i = 0; i <= context.steps; i++) {
                    stepTimes[i] = baseTime + (i * 100);
                }

                context.step = 0;
                context.inc = Math.floor((context.finalScrollLeft - context.initialScrollLeft) / context.steps);
                return new Promise((resolve, reject) => {
                    const doStep = () => {
                        if (context.control.tabsById[context.tab.tabId] !== context.tab) {
                            // Tab removed
                            return resolve();
                        }

                        const cont = stepFunc(context.step, context);

                        if (cont) {
                            let timeDiff = stepTimes[context.step] - (new Date()).getTime();
                            if (timeDiff < 0) {
                                timeDiff = 0;
                            }

                            context.step++;
                            setTimeout(doStep, timeDiff);
                        } else {
                            resolve();
                        }
                    };

                    setTimeout(doStep, 0);
                });
            };

            this.transitionsQueue = new StyledElements.CommandQueue(context, initFunc);

            /* Code for handling internal events */
            this.moveLeftButton.addEventListener("click", this.shiftLeftTabs.bind(this));
            this.moveRightButton.addEventListener("click", this.shiftRightTabs.bind(this));

        }

        get fullscreen() {
            return utils.getFullscreenElement() === this.wrapperElement;
        }

        /**
         * Shifts the tab area to display the previous tab.
         *
         * @name StyledElements.Notebook#shiftLeftTabs
         *
         * @returns {Promise}
         *     A promise tracking the progress of animation
         */
        shiftLeftTabs() {
            return this.transitionsQueue.addCommand({type: "shiftLeft"});
        }

        /**
         * Shifts the tab area to display the next tab.
         *
         * @name StyledElements.Notebook#shiftRightTabs
         *
         * @returns {Promise}
         *     A promise tracking the progress of animation
         */
        shiftRightTabs() {
            return this.transitionsQueue.addCommand({type: "shiftRight"});
        }

        /**
         * Creates a new tab inside this notebook.
         *
         * @name StyledElements.Notebook#createTab
         * @since 0.5
         *
         * @param {Object} options
         *     Options to use for creating the tab. See {@link StyledElements.Tab}
         *     for a list of options related directly with the tab.
         *
         *     In addition, you can use the following options:
         *     - `initiallyVisible` (Boolean): Display this tab just after
         *     creating it. default `false`.
         *     - `tab_constructor` (StyledElements.Tab): Class/constructor to user
         *     for creating the tab instance.
         *
         * @returns {StyledElements.Tab}
         *     The created tab.
         */
        createTab(options) {
            const defaultOptions = {
                initiallyVisible: false,
                tab_constructor: this.Tab
            };
            options = utils.merge(defaultOptions, options);

            // Reserve an id for the new tab
            const tabId = this.tabsById.push(null);

            // Create the tab
            if ((options.tab_constructor !== this.Tab) && !(options.tab_constructor.prototype instanceof StyledElements.Tab)) {
                throw new TypeError();
            }
            // eslint-disable-next-line new-cap
            const tab = new options.tab_constructor(tabId, this, options);

            // Insert it into our hashes
            this.tabs[this.tabs.length] = tab;
            this.tabsById[tabId] = tab;

            const tabElement = tab.getTabElement();

            if (this.new_tab_button_tabs != null) {
                this.tabArea.prependChild(tabElement, this.new_tab_button_tabs);
            } else {
                this.tabArea.appendChild(tabElement);
            }

            tab.insertInto(this.contentArea);

            if (!this.visibleTab) {
                this.visibleTab = tab;
                tab.setVisible(true);
            }

            // Enable/Disable tab moving buttons
            enableDisableButtons.call(this);

            /* Process options */
            if (options.initiallyVisible) {
                this.goToTab(tabId);
            }

            // Event dispatch
            this.dispatchEvent('tabInsertion', tab);

            /* Return the container associated with the newly created tab */
            return tab;
        }

        /**
         * Returns the tab associated with the given ids.
         *
         * @since 0.5
         * @deprecated since version 1.0
         * @name StyledElements.Notebook#getTab
         *
         * @param {Object} id
         *     id of the tab
         *
         * @returns {StyledElements.Tab}
         */
        getTab(id) {
            return this.tabsById[id];
        }

        /**
         * Searches a tab given the label. This method returns the first tab that maches.
         *
         * @since 0.5
         * @name StyledElements.Notebook#getTabByLabel
         *
         * @param {String} label
         *     label to search for
         *
         * @returns {StyledElements.Tab}
         */
        getTabByLabel(label) {
            for (let i = 0; i < this.tabs.length; i++) {
                if (this.tabs[i].label === label) {
                    return this.tabs[i];
                }
            }
            return null;
        }

        /**
         * Returns the tab associated with the given index.
         *
         * @since 0.5
         * @deprecated since version 1.0
         * @name StyledElements.Notebook#getTabByIndex
         * @param {Number} index index of the tab to recover.
         *
         * @returns {StyledElements.Tab}
         */
        getTabByIndex(index) {
            return this.tabs[index];
        }

        /**
         * Devuelve la posición actual de la pestaña indicada mediante su identificador.
         * Esta operación es lenta, por lo que no conviene abusar de ella.
         *
         * @param id identificador de la pestaña de la que se quiere conocer su posición
         * actual.
         */
        getTabIndex(id) {
            if (id instanceof StyledElements.Tab) {
                if (this.tabsById[id.tabId] !== id) {
                    return null;
                }
                id = id.tabId;
            }

            for (let i = 0; i < this.tabs.length; i++) {
                if (this.tabs[i].tabId === id) {
                    return i;
                }
            }
            return null;
        }

        /**
         * Elimina del notebook la pestaña indicada mediante su identificador.
         * @param tab identificador de la pestaña que se quiere eliminar.
         */
        removeTab(tab) {
            if (tab instanceof StyledElements.Tab) {
                if (this.tabsById[tab.tabId] !== tab) {
                    throw new TypeError('tab is not owned by this notebook');
                }
                tab = tab.tabId;
            }

            if (!this.tabsById[tab]) {
                return this;
            }

            delete this.tabsById[tab];
            const index = this.getTabIndex(tab);
            const tabToExtract = this.tabs.splice(index, 1)[0];

            this.tabArea.removeChild(tabToExtract.getTabElement());
            this.contentArea.removeChild(tabToExtract.wrapperElement);

            // Enable/Disable tab scrolling buttons
            enableDisableButtons.call(this);

            if ((this.visibleTab === tabToExtract) && (this.tabs.length > 0)) {
                const nextTab = this.tabs[index] != null ? this.tabs[index] : this.tabs[index - 1];
                this.goToTab(nextTab.tabId);
            } else if (this.visibleTab === tabToExtract) {
                this.visibleTab = null;
            }

            // Send specific tab close event
            tabToExtract.dispatchEvent('close', this);

            // Event dispatch
            this.dispatchEvent('tabDeletion', tabToExtract);

            return this;
        }

        /**
         * Marca la pestaña indicada mediante su identificador como visible, haciendo
         * que el contenido de esta sea visible. En caso de que el notebook fuera
         * creado con la opción "focusOnSetVisible" activada, además se le pasará el
         * foco a la pestaña asociada.
         *
         * @param {Number|Tab} tab intance or tab id of the tab to make visible
         * @param {Object.<String, *>} options
         * - context: context data to be sent on the change and the changed events
         */
        goToTab(tab, options) {
            let newTab;

            if (tab instanceof StyledElements.Tab) {
                if (this.tabsById[tab.tabId] !== tab) {
                    throw new TypeError('tab is not owned by this notebook');
                }
                newTab = tab;
            } else {
                newTab = this.tabsById[tab];
                if (newTab == null) {
                    throw new TypeError('Invalid tab id');
                }
            }
            const oldTab = this.visibleTab;

            if (options == null) {
                options = {};
            }

            if (this.visibleTab && newTab === this.visibleTab) {
                if (this.focusOnSetVisible) {
                    this.focus(newTab.tabId);
                }
                return;
            }

            this.dispatchEvent('change', oldTab, newTab, options.context);

            // At this point there is always a visibleTab
            // if (this.visibleTab) {
            this.visibleTab.setVisible(false);

            this.visibleTab = newTab;
            this.visibleTab.setVisible(true);

            if (this.focusOnSetVisible) {
                this.focus(newTab.tabId);
            }

            this.dispatchEvent('changed', oldTab, newTab, options.context);
        }

        /**
         * Set the focus on the indicated tab. That is, makes the tab visible on
         * the tab area of the notebook.
         *
         * @param {Number|Tab} tab intance or tab id of the tab to focus
         *
         * @returns {Promise}
         *     A promise tracking the progress of animation
         */
        focus(tab) {
            if (tab instanceof StyledElements.Tab) {
                if (this.tabsById[tab.tabId] !== tab) {
                    throw new TypeError('tab is not owned by this notebook');
                }
            } else {
                tab = this.tabsById[tab];
                if (tab == null) {
                    throw new TypeError('Invalid tab id');
                }
            }
            return this.transitionsQueue.addCommand({type: "focus", tab: tab});
        }

        repaint(temporal) {
            temporal = temporal != null ? temporal : false;

            this.tabWrapper.repaint();

            // Enable/Disable tab scrolling buttons
            enableDisableButtons.call(this);

            // Resize contents
            if (temporal) {
                if (this.visibleTab) {
                    this.visibleTab.repaint(true);
                }
            } else {
                this.tabs.forEach((tab) => {
                    tab.repaint(false);
                });
            }

            return this;
        }

        /**
         * @override
         */
        _onenabled(enabled) {
            if (!enabled) {
                this.disabledLayer = document.createElement('div');
                this.disabledLayer.classList.add('se-container-disable-layer');
                this.wrapperElement.appendChild(this.disabledLayer);
            } else {
                this.disabledLayer.remove();
                this.disabledLayer = null;
            }
        }

        /**
         * Clears this notebook by removing all the tabs.
         *
         * @name StyledElements.Notebook#clear
         *
         * @returns {StyledElements.Notebook}
         *      The instance on which the member is called.
         */
        clear() {
            this.tabs = [];
            this.tabsById = [];
            this.visibleTab = null;

            this.tabArea.clear();
            this.contentArea.innerHTML = '';

            // Enable/Disable tab scrolling buttons
            enableDisableButtons.call(this);

            return this;
        }

        /**
         *
         * @name StyledElements.Notebook#addToEastSection
         *
         * @returns {StyledElements.Notebook}
         *      The instance on which the member is called.
         */
        addToEastSection(elem, position) {
            position = position || 'right';

            switch (position) {
            case 'left':
                this.tabWrapper.west.prependChild(elem, this.moveLeftButton);
                break;
            case 'right':
                this.tabWrapper.east.appendChild(elem);
                break;
            }

            // Enable/Disable tab moving buttons
            enableDisableButtons.call(this);

            return this;
        }

        /**
         *
         * @name StyledElements.Notebook#addButton
         *
         * @returns {StyledElements.Notebook}
         *      The instance on which the member is called.
         *
         * @deprecated Old method, use addToEastSection instead
         */
        addButton(button, position) {
            if (!(button instanceof StyledElements.Button) && !(button instanceof StyledElements.Select)) {
                throw new TypeError();
            }

            this.addToEastSection(button, position);

            return this;
        }

        /**
         * Requests fullscreen mode. You must call this method from a user event
         * handler, otherwise the browser will denie this request.
         *
         * @name StyledElements.Notebook#requestFullscreen
         *
         * @returns {StyledElements.Notebook}
         *      The instance on which the member is called.
         */
        requestFullscreen() {
            /* istanbul ignore else */
            if ('requestFullscreen' in this.wrapperElement) {
                this.wrapperElement.requestFullscreen();
            } else if ('msRequestFullscreen' in this.wrapperElement) {
                this.wrapperElement.msRequestFullscreen();
            } else if ('mozRequestFullScreen' in this.wrapperElement) {
                this.wrapperElement.mozRequestFullScreen();
            } else if ('webkitRequestFullscreen' in this.wrapperElement) {
                this.wrapperElement.webkitRequestFullscreen();
            }

            return this;
        }

        /**
         * Exists from fullscreen mode
         *
         * @name StyledElements.Notebook#exitFullscreen
         *
         * @returns {StyledElements.Notebook}
         *      The instance on which the member is called.
         */
        exitFullscreen() {
            if (this.fullscreen !== true) {
                return this;
            }

            /* istanbul ignore else */
            if ('exitFullscreen' in document) {
                document.exitFullscreen();
            } else if ('msExitFullscreen' in document) {
                document.msExitFullscreen();
            } else if ('mozCancelFullScreen' in document) {
                document.mozCancelFullScreen();
            } else if ('webkitExitFullscreen' in document) {
                document.webkitExitFullscreen();
            }

            return this;
        }

        destroy() {
            this.remove();
            this.tabs = null;
            this.tabsById = null;
            this.visibleTab = null;

            StyledElements.StyledElement.prototype.destroy.call(this);
        }

    }

    se.Notebook.prototype.Button = StyledElements.Button;
    se.Notebook.prototype.Tab = StyledElements.Tab;

})(StyledElements, StyledElements.Utils);
