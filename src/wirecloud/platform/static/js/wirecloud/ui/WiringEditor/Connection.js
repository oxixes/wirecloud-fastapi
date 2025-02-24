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

    const events = ['change', 'click', 'customizestart', 'customizeend', 'optremove', 'optshare', 'remove'];

    const prop_active_get = function prop_active_get(active) {
        return !!active;
    };

    const prop_active_set = function prop_active_set(active, isActive) {

        if (this.enabled) {
            active = isActive;
            this.toggleClassName('active', active);
        }

        if (active) {
            showButtonGroup.call(this);
        } else {
            hideButtonGroup.call(this);
        }

        toggleActiveEndpoints.call(this, active);

        return active;
    };

    const prop_highlighted_get = function prop_highlighted_get(highlightedCount) {
        return !!highlightedCount;
    };

    const prop_highlighted_set = function prop_highlighted_set(highlightedCount, isHighlighted) {

        if (highlightedCount == null) {
            highlightedCount = 0;
        }

        highlightedCount = highlightedCount + (isHighlighted ? 1 : -1);

        if (highlightedCount < 0) {
            highlightedCount = 0;
        }

        this.toggleClassName('highlighted', !!highlightedCount);

        return highlightedCount;
    };

    const refreshInternally = function refreshInternally() {
        const newDepth = this.active || this.highlighted || !this.background ? 1 : 0;

        this.btnLogs.depth = newDepth;
        this.btnPrefs.depth = newDepth;
        this.btnRemove.depth = newDepth;
    };

    const updateFlagRemoveAllowed = function updateFlagRemoveAllowed() {
        return this.removeAllowed ? this._showButtonRemove() : this._showButtonDelete();
    };

    const showButtonGroup = function showButtonGroup() {
        this.btnPrefs.show();
        this.btnLogs.show();
    };

    const hideButtonGroup = function hideButtonGroup() {
        this.btnPrefs.hide();

        if (!this.hasClassName('has-error') && !this.missing) {
            this.btnLogs.hide();
        }
    };

    const appendEndpoint = function appendEndpoint(endpoint, options) {

        this[endpoint.type] = {
            endpoint: endpoint,
            handle: new ns.ConnectionHandle(endpoint, options)
        };

        return this;
    };

    const bindWiringConnection = function bindWiringConnection(wiringConnection) {

        Object.defineProperties(this, {

            logManager: {value: wiringConnection.logManager},

            readonly: {value: wiringConnection.readonly}

        });

        this._connection = wiringConnection;
        this._connection.logManager.addEventListener('newentry', notifyErrors.bind(this));

        this.options.show();
        notifyErrors.call(this);

        if (this.readonly) {
            this.addClassName("readonly");
            this.btnRemove.disable();
        }

        return this;
    };

    const notifyErrors = function notifyErrors() {
        const count = this._connection.logManager.errorCount;

        this.toggleClassName('has-error', !!count);
        this.btnLogs.setBadge(count ? count : null, 'danger', true);

        if (count) {
            this.btnLogs.show();
        } else {
            this.btnLogs.hide();
        }
    };

    const btnerrors_onclick = function btnerrors_onclick() {
        this.showLogs();
    };

    const btnremove_onclick = function btnremove_onclick(event) {

        if (this.background) {
            this.dispatchEvent('optshare', event);
        } else {
            if (!this.readonly) {
                this.dispatchEvent('optremove', event);
            }
        }
    };

    const b1 = function b1(t) { return t * t * t; };
    const b2 = function b2(t) { return 3 * t * t * (1 - t); };
    const b3 = function b3(t) { return 3 * t * (1 - t) * (1 - t); };
    const b4 = function b4(t) { return (1 - t) * (1 - t) * (1 - t); };

    const bezier = function bezier(percent, c1, c2, c3, c4) {
        const x = c1.x * b1(percent) + c2.x * b2(percent) + c3.x * b3(percent) + c4.x * b4(percent);
        const y = c1.y * b1(percent) + c2.y * b2(percent) + c3.y * b3(percent) + c4.y * b4(percent);
        return {x: Math.round(x), y: Math.round(y)};
    };

    const calculateMiddle = function calculateMiddle(source, sourceHandle, target, targetHandle) {
        return bezier(0.5, source, sourceHandle, targetHandle, target);
    };

    const connection_onclick = function connection_onclick(event) {

        event.preventDefault();
        event.stopPropagation();

        if (event.button === 0) {
            this.click();
        }
    };

    const establishConnection = function establishConnection(wiringConnection) {

        if (wiringConnection == null) {
            return this;
        }

        this.source.handle.addEventListener('drag', handle_ondrag.bind(this));
        this.source.handle.addEventListener('dragend', handle_ondragend.bind(this));

        this.target.handle.addEventListener('drag', handle_ondrag.bind(this));
        this.target.handle.addEventListener('dragend', handle_ondragend.bind(this));

        bindWiringConnection.call(this, wiringConnection);

        this.source.endpoint.appendConnection(this);
        this.target.endpoint.appendConnection(this);

        this.get().setAttribute('data-sourceid', this.sourceId);
        this.get().setAttribute('data-targetid', this.targetId);

        this.options.get().setAttribute('data-sourceid', this.sourceId);
        this.options.get().setAttribute('data-targetid', this.targetId);

        return this;
    };

    const handle_ondrag = function handle_ondrag(position, handle) {
        return this.refresh();
    };

    const handle_ondragend = function handle_ondragend() {
        return this.dispatchEvent('change', this.toJSON());
    };

    const formatDistance = function formatDistance(s, sHandle, t, tHandle) {
        return "M " + s.x + "," + s.y + " C " + sHandle.x + "," + sHandle.y + " " + tHandle.x + "," + tHandle.y + " " + t.x + "," + t.y;
    };

    const getHandlePosition = function getHandlePosition(start, end, invert) {
        const position = ns.ConnectionHandle.getRelativePosition(start, end, invert);

        return {x: start.x + position.x, y: start.y + position.y};
    };

    const removeEndpoint = function removeEndpoint(endpoint) {

        this[endpoint.type] = {};

        return this;
    };

    const isCreated = function isCreated() {
        this.toggleClassName('incomplete', !this.created);
    };

    const toggleActiveEndpoints = function toggleActiveEndpoints(active) {
        if (this.source.endpoint != null) {
            this.source.endpoint.toggleActive(active);
        }

        if (this.target.endpoint != null) {
            this.target.endpoint.toggleActive(active);
        }

        return this;
    };

    const updateDistance = function updateDistance(source, sourceHandle, target, targetHandle) {
        this.pathElement.setAttribute('d', formatDistance(source, sourceHandle, target, targetHandle));

        if (this.established) {
            const middlePosition = calculateMiddle(source, sourceHandle, target, targetHandle);

            this.options.style({
                top: middlePosition.y + 'px',
                left: middlePosition.x + 'px'
            });
        }

        return this;
    };

    const connection_onmouseenter = function connection_onmouseenter() {
        if (this.established && !this.editable) {
            this.highlighted = true;
            toggleActiveEndpoints.call(this, true);
        }
    };

    const connection_onmouseleave = function connection_onmouseleave() {
        if (this.established && !this.editable) {
            this.highlighted = false;
            toggleActiveEndpoints.call(this, false);
        }
    };

    ns.Connection = class Connection extends se.StyledElement {

        /**
         * Create a new instance of class Connection.
         * @extends {StyledElements.StyledElement}
         *
         * @constructor
         */
        constructor() {
            super(events);

            this.wrapperElement = document.createElementNS(ns.Connection.SVG_NS, 'g');
            this.wrapperElement.setAttribute('class', "connection");
            this.wrapperElement.addEventListener('click', connection_onclick.bind(this));
            this.wrapperElement.addEventListener('dblclick', utils.stopPropagationListener, true);

            this.wrapperElement.addEventListener('mouseenter', connection_onmouseenter.bind(this));
            this.wrapperElement.addEventListener('mouseleave', connection_onmouseleave.bind(this));

            this.pathElement = document.createElementNS(ns.Connection.SVG_NS, 'path');
            this.pathElement.setAttribute('class', "connection-path");
            this.wrapperElement.appendChild(this.pathElement);

            this.options = new se.Container({class: "connection-options btn-group btn-group-circle btn-group-xs"});
            this.options.hide();

            this.btnLogs = new se.Button({
                title: utils.gettext("Logs"),
                state: 'default',
                depth: 1,
                class: "btn-show-logs",
                iconClass: "fas fa-bell"
            });
            this.btnLogs.addEventListener('click', btnerrors_onclick.bind(this));
            this.btnLogs.appendTo(this.options);

            this.btnRemove = new se.Button({
                title: utils.gettext("Remove"),
                state: 'danger',
                depth: 1,
                class: "btn-remove",
                iconClass: "fas fa-times"
            });
            this.btnRemove.addEventListener('click', btnremove_onclick.bind(this));
            this.btnRemove.appendTo(this.options);

            this.btnPrefs = new se.PopupButton({
                title: utils.gettext("Preferences"),
                state: 'default',
                depth: 1,
                class: "we-prefs-btn",
                iconClass: "fas fa-bars"
            });
            this.btnPrefs.popup_menu.append(new ns.ConnectionPrefs(this));
            this.btnPrefs.appendTo(this.options);

            this.activeCount = 0;

            this.source = {};
            this.target = {};

            let removeAllowed = true;

            let active;
            let highlightedCount;

            Object.defineProperties(this, {

                /**
                 * @memberof WiringEditor.Connection#
                 * @type {!Boolean}
                 */
                active: {
                    get: function get() {
                        return prop_active_get.call(this, active);
                    },
                    set: function set(isActive) {
                        active = prop_active_set.call(this, active, !!isActive);
                        refreshInternally.call(this);
                    }
                },

                background: {
                    get: function get() {return this.hasClassName('background');},
                    set: function set(value) {this._onbackground(value);}
                },

                created: {
                    get: function get() {return this.source.endpoint != null && this.target.endpoint != null;}
                },

                established: {
                    get: function get() {return this.created && this._connection != null;}
                },

                editable: {
                    get: function get() {return this.hasClassName('editable');},
                    set: function set(value) {this._oneditable(value);}
                },

                /**
                 * @memberof WiringEditor.Connection#
                 * @type {!Boolean}
                 */
                highlighted: {
                    get: function get() {
                        return prop_highlighted_get.call(this, highlightedCount);
                    },
                    set: function set(isHighlighted) {
                        highlightedCount = prop_highlighted_set.call(this, highlightedCount, !!isHighlighted);
                    }
                },

                missing: {
                    get: function get() {
                        return this.created && (this.source.endpoint.missing || this.target.endpoint.missing);
                    }
                },

                removeAllowed: {
                    get: function get() {return removeAllowed;},
                    set: function set(value) {
                        removeAllowed = !!value;
                        if (!this.background) {
                            updateFlagRemoveAllowed.call(this);
                        }
                    }
                },

                sourceComponent: {
                    get: function get() {return this.source.endpoint.component;}
                },

                sourceId: {
                    get: function get() {return this.source.endpoint.id;}
                },

                targetComponent: {
                    get: function get() {return this.target.endpoint.component;}
                },

                targetId: {
                    get: function get() {return this.target.endpoint.id;}
                }

            });

            // Initial configuration

            this.highlighted = false;
            this.active = false;
            isCreated.call(this);
        }

        /**
         * [TODO: _onbackground description]
         * @protected
         *
         * @param {Boolean} background
         *      [TODO: description]
         * @returns {Connection}
         *      The instance on which the member is called.
         */
        _onbackground(background) {
            const newDepth = this.active || !background ? 1 : 0;

            this.toggleClassName('background', background);

            this.btnLogs.depth = newDepth;
            this.btnPrefs.depth = newDepth;
            this.btnRemove.depth = newDepth;

            return background ? this._showButtonAdd() : updateFlagRemoveAllowed.call(this);
        }

        /**
         * [TODO: _oneditable description]
         * @protected
         *
         * @param {Boolean} editable
         *      [TODO: description]
         * @returns {Connection}
         *      The instance on which the member is called.
         */
        _oneditable(editable) {

            if (this.editable === editable) {
                return this;
            }

            this.toggleClassName('editable', editable);
            toggleActiveEndpoints.call(this, editable);

            if (editable) {
                this.source.handle.appendTo(this.wrapperElement);
                this.target.handle.appendTo(this.wrapperElement);
                this.dispatchEvent('customizestart');
            } else {
                this.source.handle.remove();
                this.target.handle.remove();
                this.dispatchEvent('customizeend');
            }

            return this;
        }

        _showButtonAdd() {

            this.btnRemove
                .replaceClassName("btn-remove", "btn-add")
                .removeIconClassName(['fa-trash', 'fa-times'])
                .addIconClassName('fa-plus')
                .setTitle(utils.gettext("Add"));
            this.btnRemove.state = 'info';

            return this;
        }

        _showButtonDelete() {

            this.btnRemove
                .replaceClassName('btn-add', 'btn-remove')
                .removeIconClassName(['fa-plus', 'fa-trash'])
                .addIconClassName('fa-times')
                .setTitle(utils.gettext("Remove"));
            this.btnRemove.state = 'danger';

            return this;
        }

        _showButtonRemove() {

            this.btnRemove
                .replaceClassName('btn-add', 'btn-remove')
                .removeIconClassName(['fa-plus', 'fa-times'])
                .addIconClassName('fa-trash')
                .setTitle(utils.gettext("Remove"));
            this.btnRemove.state = 'danger';

            return this;
        }

        click() {

            if (this.enabled && !this.editable) {
                this.active = !this.active;
                this.dispatchEvent('click');
            }

            return this;
        }

        /**
         * [TODO: createAndBind description]
         *
         * @param {Boolean} readonly
         *      [TODO: description]
         * @param {Wiring} wiringEngine
         *      [TODO: description]
         * @returns {Connection}
         *      The instance on which the member is called.
         */
        createAndBind(readonly, wiringEngine) {
            const source = this.source.endpoint._endpoint,
                target = this.target.endpoint._endpoint;

            if (this.established) {
                return this;
            }
            wiringEngine.createConnection(source, target, {
                readonly: readonly
            }).then((connection) => {
                establishConnection.call(this, connection);
                this.refresh();
            });

            return this;
        }

        /**
         * [TODO: equals description]
         *
         * @param {Connection} connection
         *      [TODO: description]
         * @returns {Boolean}
         *      [TODO: description]
         */
        equals(connection) {

            if (!(connection instanceof ns.Connection)) {
                return false;
            }

            return this.sourceId === connection.sourceId && this.targetId === connection.targetId;
        }

        /**
         * [TODO: hasEndpoint description]
         *
         * @param {Endpoint} endpoint
         *      [TODO: description]
         * @returns {Boolean}
         *      [TODO: description]
         */
        hasEndpoint(endpoint) {
            return this[endpoint.type].endpoint.equals(endpoint);
        }

        /**
         * [TODO: refresh description]
         *
         * @returns {Connection}
         *      The instance on which the member is called.
         */
        refresh() {
            if (!this.created) {
                return this;
            }

            this.toggleClassName('missing', this.missing);

            const sourcePosition = this.source.endpoint.anchorPosition;
            const targetPosition = this.target.endpoint.anchorPosition;

            const sourceHandle = this.source.handle.updateDistance(targetPosition).position();
            const targetHandle = this.target.handle.updateDistance(sourcePosition, true).position();

            updateDistance.call(this, sourcePosition, sourceHandle, targetPosition, targetHandle);

            return this;
        }

        refreshEndpoint(endpoint) {

            if (this.established) {
                this[endpoint.type].endpoint = endpoint;
                this[endpoint.type].handle.endpoint = endpoint;
            }

            return this;
        }

        /**
         * @override
         */
        remove(childElement) {

            if (childElement == null) {

                if (this.established) {
                    this.source.endpoint.removeConnection(this);
                    this.target.endpoint.removeConnection(this);
                }

                this.dispatchEvent('remove');
            }


            return super.remove(childElement);
        }

        /**
         * [TODO: restoreDefaults description]
         *
         * @returns {Connection}
         *      The instance on which the member is called.
         */
        restoreDefaults() {

            if (this.readonly || this.background) {
                return this;
            }

            if (this.established) {
                this.source.handle.auto = true;
                this.target.handle.auto = true;

                this.refresh().dispatchEvent('change', this.toJSON());
            }

            return this;
        }

        /**
         * [TODO: stickEndpoint description]
         *
         * @param {Endpoint} endpoint
         *      [TODO: description]
         * @param {PlainObject} [options]
         *      [TODO: description]
         * @returns {Connection}
         *      The instance on which the member is called.
         */
        stickEndpoint(endpoint, options) {

            if (this.established) {
                return this;
            }

            options = utils.merge({
                establish: true,
                wiringConnection: null
            }, options);

            appendEndpoint.call(this, endpoint, options);

            if (this.created) {

                if (options.establish) {
                    establishConnection.call(this, options.wiringConnection);
                }

                this.refresh();
            }

            isCreated.call(this);

            return this;
        }

        /**
         * [TODO: showLogs description]
         *
         * @returns {Connection}
         *      The instance on which the member is called.
         */
        showLogs() {
            const count = this._connection.logManager.errorCount;

            this.btnLogs.setBadge(count ? count : null, 'danger');
            this._connection.showLogs();

            return this;
        }

        /**
         * [TODO: toFirst description]
         *
         * @returns {Connection}
         *      The instance on which the member is called.
         */
        toFirst() {
            let parentElement;

            if (this.parentElement != null) {
                this.parentElement.removeChild(this).appendChild(this);
            } else {
                parentElement = this.get().parentElement;

                if (parentElement != null) {
                    parentElement.removeChild(this.get());
                    parentElement.appendChild(this.get());
                }
            }

            return this;
        }

        /**
         * [TODO: toggleActive description]
         *
         * @param {Boolean} active
         *      [TODO: description]
         * @returns {Connection}
         *      The instance on which the member is called.
         */
        toggleActive(active) {
            return active ? this.activate() : this.deactivate();
        }

        /**
         * [TODO: toJSON description]
         *
         * @returns {PlainObject}
         *      [TODO: description]
         */
        toJSON() {
            return {
                sourcename: this.sourceId,
                sourcehandle: this.source.handle.toJSON(),
                targetname: this.targetId,
                targethandle: this.target.handle.toJSON()
            };
        }

        /**
         * [TODO: unstickEndpoint description]
         *
         * @param {Endpoint} endpoint
         *      [TODO: description]
         * @returns {Connection}
         *      The instance on which the member is called.
         */
        unstickEndpoint(endpoint) {

            if (this.established) {
                return this;
            }

            removeEndpoint.call(this, endpoint);
            isCreated.call(this);

            return this;
        }

        /**
         * [TODO: updateCursorPosition description]
         *
         * @param {PlainObject} position
         *      [TODO: description]
         * @returns {Connection}
         *      The instance on which the member is called.
         */
        updateCursorPosition(position) {
            let source, sourceHandle, target, targetHandle;

            if (this.created) {
                return this;
            }

            if (this.source.endpoint != null) {
                source = this.source.endpoint.anchorPosition;
                target = position;
                sourceHandle = this.source.handle.updateDistance(target).position();
                targetHandle = getHandlePosition(target, source, true);
            } else {
                source = position;
                target = this.target.endpoint.anchorPosition;
                sourceHandle = getHandlePosition(source, target);
                targetHandle = this.target.handle.updateDistance(source, true).position();
            }

            updateDistance.call(this, source, sourceHandle, target, targetHandle);

            return this;
        }

    }
    ns.Connection.SVG_NS = "http://www.w3.org/2000/svg";

})(Wirecloud.ui.WiringEditor, StyledElements, StyledElements.Utils);
