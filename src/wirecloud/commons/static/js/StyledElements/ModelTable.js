/*
 *     Copyright (c) 2008-2016 CoNWeT Lab., Universidad Politécnica de Madrid
 *     Copyright (c) 2019-2021 Future Internet Consulting and Development Solutions S.L.
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

/* globals moment, StyledElements */

(function (se, utils) {

    "use strict";

    const privates = new WeakMap();

    const buildHeader = function buildHeader() {
        const priv = privates.get(this);

        priv.header = document.createElement('div');
        priv.header.className = 'se-model-table-headrow';

        priv.headerCells = [];
        priv.columnTemplate = [];
        for (let i = 0; i < this.columns.length; i += 1) {
            const column = this.columns[i];

            const label = column.label != null ? column.label : column.field;

            const cell = document.createElement('div');
            cell.className = 'se-model-table-cell';
            if (typeof column.class === 'string') {
                cell.classList.add(column.class);
            }
            if (column.width != null && column.width !== "css") {
                priv.columnTemplate.push(column.width);
            } else {
                priv.columnTemplate.push("1fr");
            }
            cell.textContent = label;
            if (column.sortable !== false) {
                cell.classList.add('sortable');
                const tooltip = new this.Tooltip({
                    content: utils.interpolate(utils.gettext('Sort by %(column_name)s'), {column_name: label}),
                    placement: ['bottom', 'top', 'right', 'left']
                });
                tooltip.bind(cell);
                cell.callback = sortByColumnCallback.bind({widget: this, column: i});
                cell.addEventListener('click', cell.callback, true);
            }
            priv.header.appendChild(cell);
            priv.headerCells.push(cell);
        }
        priv.tableBody.appendChild(priv.header);
        priv.tableBody.wrapperElement.style.gridTemplateColumns = priv.columnTemplate.join(" ");
    };

    const highlight_selection = function highlight_selection() {
        const priv = privates.get(this);
        this.selection.forEach(function (id) {
            if (id in priv.current_elements) {
                priv.current_elements[id].row.classList.add('highlight');
            }
        }, this);
    };

    const paintTable = function paintTable(items) {
        let i, j, item, row, cell, callback, today, cellContent,
            column, state;

        const priv = privates.get(this);
        clearTable.call(this);
        priv.tableBody.appendChild(priv.header);

        for (i = 0; i < items.length; i += 1) {
            item = items[i];

            callback = rowCallback.bind({table: this, item: item, index: i});

            row = document.createElement('div');
            row.className = 'se-model-table-row';
            if ((i % 2) === 1) {
                row.classList.add('odd');
            }
            state = priv.stateFunc(item);
            if (state != null) {
                row.classList.add('se-model-table-row-' + state);
            }

            for (j = 0; j < this.columns.length; j += 1) {
                column = this.columns[j];

                cell = document.createElement('div');
                cell.className = 'se-model-table-cell';
                priv.columnsCells[j].push(cell);

                if (typeof column.class === 'string') {
                    cell.classList.add(column.class);
                }

                if (column.contentBuilder) {
                    cellContent = column.contentBuilder(item);
                } else if (column.type === 'date') {
                    if (getFieldValue(item, column.field) === '') {
                        cellContent = '';
                    } else {
                        if (!today) {
                            today = new Date();
                        }
                        cellContent = formatDate.call(this, item, column, today);
                    }
                } else if (column.type === 'number') {
                    cellContent = getFieldValue(item, column.field);

                    if (cellContent !== '' && column.unit) {
                        cellContent = cellContent + " " + column.unit;
                    }
                } else {
                    cellContent = getFieldValue(item, column.field);
                }

                if (cellContent == null) {
                    cellContent = '';
                }

                if (typeof cellContent === 'string') {
                    cell.textContent = cellContent;
                } else if (typeof cellContent === 'number' || typeof cellContent === 'boolean') {
                    cell.textContent = "" + cellContent;
                } else if (cellContent instanceof StyledElements.StyledElement) {
                    cellContent.insertInto(cell);
                    priv.components.push(cellContent);
                } else {
                    cell.appendChild(cellContent);
                }

                cell.addEventListener('click', callback, false);
                priv.listeners.push({element: cell, callback: callback});

                row.appendChild(cell);
                if (typeof priv.extractIdFunc === 'function') {
                    priv.current_elements[priv.extractIdFunc(item)] = {
                        row: row,
                        data: item
                    };
                }
            }

            priv.tableBody.appendChild(row);
        }

        if (items.length === 0 && this.source.currentPage) {
            row = document.createElement('div');
            row.className = 'alert alert-info se-model-table-msg';
            row.textContent = this.emptyMessage;

            priv.tableBody.appendChild(row);
        }

        highlight_selection.call(this);
    };

    const onRequestEnd = function onRequestEnd(source, error) {
        if (error == null) {
            this.reload();
        } else {
            const priv = privates.get(this);
            clearTable.call(this);
            const message = document.createElement('div');
            message.className = "alert alert-danger se-model-table-msg";
            message.textContent = error;
            priv.tableBody.appendChild(message);
        }
    };

    const sortByColumn = function sortByColumn(column, descending) {
        let sort_id, order, oldSortHeaderCell, sortHeaderCell;

        const priv = privates.get(this);

        if (priv.sortColumn != null) {
            oldSortHeaderCell = priv.headerCells[priv.sortColumn];
            oldSortHeaderCell.classList.remove('ascending');
            oldSortHeaderCell.classList.remove('descending');
        }
        priv.sortInverseOrder = descending;
        priv.sortColumn = column;

        if (priv.sortColumn != null) {
            sortHeaderCell = priv.headerCells[priv.sortColumn];
            if (priv.sortInverseOrder) {
                sortHeaderCell.classList.remove('ascending');
                sortHeaderCell.classList.add('descending');
            } else {
                sortHeaderCell.classList.remove('descending');
                sortHeaderCell.classList.add('ascending');
            }

            column = this.columns[priv.sortColumn];
            if (column.sort_id != null) {
                sort_id = column.sort_id;
            } else {
                sort_id = column.field;
            }
            if (priv.sortInverseOrder) {
                sort_id = '-' + sort_id;
            }
            order = [sort_id];
        } else {
            order = null;
        }
        this.source.changeOptions({order: order});
    };

    const sortByColumnCallback = function sortByColumnCallback() {
        const priv = privates.get(this.widget);
        const descending = priv.sortColumn === this.column ?
            !priv.sortInverseOrder :
            false;

        sortByColumn.call(this.widget, this.column, descending);
    };

    const getFieldValue = function getFieldValue(item, field) {
        let fieldPath, currentNode, currentField;

        if (typeof field === "string") {
            fieldPath = [field];
        } else {
            fieldPath = field.slice();
        }

        currentNode = item;
        while (currentNode != null && fieldPath.length > 0) {
            currentField = fieldPath.splice(0, 1)[0];
            currentNode = currentNode[currentField];
        }
        if (currentNode == null || fieldPath.length > 0) {
            return "";
        }

        return currentNode;
    };

    const renderDate = function renderDate(format, m) {
        if (format === "relative") {
            return m.fromNow();
        } else if (format === "calendar") {
            const timezone = m.format(" z");
            return (m.calendar() + timezone).trim();
        } else {
            return m.format(format).trim();
        }
    };

    const formatDate = function formatDate(item, column, today) {
        let date, fullVersion, tooltip;

        date = getFieldValue(item, column.field);

        // Convert the input to a Date object
        if (typeof column.dateparser === 'function') {
            date = column.dateparser(date);
        } else if (!(date instanceof Date)) {
            date = new Date(date);
        }

        const m = moment(date);
        if (column.timezone != null) {
            m.tz(column.timezone);
        }
        const format = column.format != null ? column.format : "relative";
        const tooltipFormat = column.tooltip != null ? column.tooltip : "LLLL z";
        const shortVersion = renderDate(format, m);

        const element = document.createElement('span');
        element.textContent = shortVersion;
        if (tooltipFormat !== "none") {
            fullVersion = m.format(tooltipFormat);
            tooltip = new this.Tooltip({
                content: fullVersion,
                placement: ['bottom', 'top', 'right', 'left']
            });
            tooltip.bind(element);
        }

        if (format === "relative" || format === "calendar") {
            // Update rendered date form time to time
            const timer = setInterval(function () {
                // Clear timer if deleted.
                if (!element.ownerDocument.body.contains(element)) {
                    clearInterval(timer);
                }

                const newTime = renderDate(format, m);
                if (element.textContent !== newTime) {
                    element.textContent = newTime;
                }
            }, 1000);
        }

        return element;
    };

    // Row clicked callback
    const rowCallback = function rowCallback(evt) {
        // Stop propagation so wrapperElement's click is not called
        evt.stopPropagation();

        changeSelection.call(this.table, this.item, evt, this.index);

        this.table.events.click.dispatch(this.item, evt);
    };

    const isSelectionEnabled = function isSelectionEnabled(selectionSettings) {
        return selectionSettings === "single" || selectionSettings === "multiple";
    };

    // Row selection
    const changeSelection = function changeSelection(row, event, index) {
        const priv = privates.get(this);

        // Check if selection is ignored
        if (!isSelectionEnabled(priv.selectionType)) {
            return;
        }

        let selected, data, lastSelectedIndex, lower, upper, j;
        const id = priv.extractIdFunc(row);

        if (priv.selectionType === "multiple" && (event.ctrlKey || event.metaKey) && event.shiftKey) {
            // Control + shift behaviour
            data = this.source.getCurrentPage();
            lastSelectedIndex = data.indexOf(priv.lastSelected);
            if (lastSelectedIndex === -1) {
                priv.lastSelected = row;
                selected = [id];
            } else {
                selected = priv.savedSelection.slice();
                selected.splice(selected.indexOf(priv.extractIdFunc(priv.lastSelected)), 1); // Remove pivot row from selection as it will be selected again

                // Get the new selection group and append it
                const aux = [];
                lower = Math.min(index, lastSelectedIndex);
                upper = Math.max(index, lastSelectedIndex);
                for (j = lower; j <= upper; j++) {
                    aux.push(priv.extractIdFunc(data[j]));
                }
                selected = selected.concat(aux);
                event.target.ownerDocument.defaultView.getSelection().removeAllRanges();
            }

        } else if (priv.selectionType === "multiple" && event.shiftKey) {
            // Shift behaviour
            data = this.source.getCurrentPage();
            lastSelectedIndex = data.indexOf(priv.lastSelected);
            // Choose current
            if (lastSelectedIndex === -1) {
                priv.lastSelected = row;
                selected = [id];
            // Choose range
            } else {
                selected = [];

                lower = Math.min(index, lastSelectedIndex);
                upper = Math.max(index, lastSelectedIndex);
                for (j = lower; j <= upper; j++) {
                    selected.push(priv.extractIdFunc(data[j]));
                }
                event.target.ownerDocument.defaultView.getSelection().removeAllRanges();
            }

        } else if (priv.selectionType === "multiple" && (event.ctrlKey || event.metaKey)) {
            // control behaviour
            priv.lastSelected = row;
            selected = this.selection.slice();

            const i = selected.indexOf(id);

            // Remove from selection
            if (i !== -1) {
                priv.lastSelected = null;
                selected.splice(i, 1);
            // Add to selection
            } else {
                selected.push(id);
            }
            priv.savedSelection = selected;

        } else {
            // Normal behaviour
            selected = [id];
            priv.lastSelected = row;
            priv.savedSelection = selected;
        }

        // Update the selection
        this.select(selected);
        // this.trigger("select", selected);
        this.events.select.dispatch(selected);
    };

    const clearTable = function clearTable() {
        let i, entry;
        const priv = privates.get(this);

        for (i = 0; i < priv.listeners.length; i += 1) {
            entry = priv.listeners[i];
            entry.element.removeEventListener('click', entry.callback, false);
        }
        priv.components = [];
        priv.listeners = [];
        priv.columnsCells = [];
        for (i = 0; i < this.columns.length; i += 1) {
            priv.columnsCells[i] = [];
        }
        priv.tableBody.clear();
        priv.current_elements = {};
    };

    /**
     * Each column must provide the following options:
     * * `field` (String): name of the attribute
     *
     * And can provide these other optional options:
     * * `type` (String, default: `"text"`): Type of data stored on the field: text, date, number, string, boolean.
     * * `label` (String, default: `null`): Label to useIf not provided, the value of the `field` option will be used as label for this columns
     * * `sort_id` (String, default: `null`). Id to use when making request sorting by this field. `field` option will be used if not provided.
     * * `sortable` (Boolean, default: `false`)
     */
    se.ModelTable = class ModelTable extends se.StyledElement {

        constructor(columns, options) {
            let className, i, sort_info;

            const defaultOptions = {
                initialSortColumn: -1,
                pageSize: 5,
                emptyMessage: utils.gettext("No data available"),
                selectionType: "none"
            };

            options = utils.merge(defaultOptions, options);

            if (options.class != null) {
                className = utils.appendWord('se-model-table full', options.class);
            } else {
                className = 'se-model-table full';
            }
            super(['click', 'select']);

            // Initialize private variables
            const priv = {};
            privates.set(this, priv);

            priv.selection = [];
            priv.selectionType = options.selectionType;
            let source;
            if (options.source != null) {
                source = options.source;
            } else {
                sort_info = {};
                columns.forEach((column) => {
                    const sort_id = column.sort_id != null ? column.sort_id : column.field;
                    sort_info[sort_id] = column;
                })
                source = new StyledElements.StaticPaginatedSource({pageSize: options.pageSize, sort_info: sort_info, idAttr: options.id});
            }

            priv.layout = new StyledElements.VerticalLayout({'class': className});

            Object.defineProperties(this, {
                columns: {
                    writable: true,
                    value: columns
                },
                emptyMessage: {
                    writable: true,
                    value: options.emptyMessage
                },
                source: {
                    writable: false,
                    value: source
                },
                statusBar: {
                    get: function () {
                        return priv.statusBar;
                    }
                }

            });

            this.wrapperElement = priv.layout.wrapperElement;

            // Deselect rows if clicked no row is clicked
            this.wrapperElement.addEventListener("click", (evt) => {
                const priv = privates.get(this);

                // Only deselect if no modifier key is pressed
                if (!isSelectionEnabled(priv.selectionType) || evt.shiftKey || evt.ctrlKey || evt.metaKey) {
                    return;
                }

                this.select([]);
                this.events.select.dispatch([]);
            });

            /*
             * Table body
             */
            priv.components = [];
            priv.listeners = [];
            priv.tableBody = priv.layout.center;
            priv.tableBody.addClassName('se-model-table-body');
            buildHeader.call(this);

            /*
             * Status bar
             */
            priv.statusBar = priv.layout.south;
            priv.statusBar.addClassName('se-model-table-statusrow');

            priv.sortColumn = null;

            this.source.addEventListener('requestEnd', onRequestEnd.bind(this));

            if (this.source.options.pageSize !== 0) {

                priv.paginationInterface = new StyledElements.PaginationInterface(this.source);
                priv.statusBar.appendChild(priv.paginationInterface);
            }

            if (options.initialSortColumn === -1) {
                for (i = 0; i < this.columns.length; i += 1) {
                    if (this.columns[i].sortable !== false) {
                        options.initialSortColumn = i;
                        break;
                    }
                }
                if (options.initialSortColumn === -1) {
                    options.initialSortColumn = null;
                }
            } else if (typeof options.initialSortColumn === 'string') {
                for (i = 0; i < this.columns.length; i += 1) {
                    if (this.columns[i].field === options.initialSortColumn) {
                        options.initialSortColumn = i;
                        break;
                    }
                }
                if (typeof options.initialSortColumn === 'string') {
                    options.initialSortColumn = null;
                }
            }

            priv.current_elements = {};
            if (typeof options.id === "string") {
                priv.extractIdFunc = (data) => data[options.id];
            } else if (Array.isArray(options.id)) {
                priv.extractIdFunc = (data) => getFieldValue(data, options.id);
            } else if (typeof options.id === "function") {
                priv.extractIdFunc = options.id;
            }
            priv.stateFunc = typeof options.stateFunc === "function" ? options.stateFunc : () => {};

            sortByColumn.call(this, options.initialSortColumn, options.initialDescendingOrder);
        }

        get selection() {
            return privates.get(this).selection;
        }

        set selection(value) {
            const priv = privates.get(this);

            // Check if selection is ignored
            if (!isSelectionEnabled(priv.selectionType)) {
                throw new Error("Selection is disabled");
            }
            if (!Array.isArray(value)) {
                throw new TypeError();
            }
            if (priv.selectionType === "single" && value.length > 1) {
                throw new Error("Selection is set to \"single\" but tried to select more than one rows.");
            }
            // Unhighlihgt previous selection
            priv.selection.forEach((id) => {
                if (id in priv.current_elements) {
                    priv.current_elements[id].row.classList.remove('highlight');
                }
            });

            priv.selection = value;

            // Highlight the new selection
            highlight_selection.call(this);
        }

        /**
         * Changes current selection. Removes the selection when no passing any parameter
         *
         * @since 0.6.3
         *
         * @param {String|String[]} [selection]
         * @returns {StyledElements.ModelTable}
         *     The instance on which the member is called.
         */
        select(selection) {
            if (selection != null) {
                // Update current selection
                this.selection = Array.isArray(selection) ? selection : [selection];
            } else {
                this.selection = [];
            }

            return this;
        }

        reload() {
            paintTable.call(this, this.source.getCurrentPage());
        }

        destroy() {
            let i, cell;
            const priv = privates.get(this);

            for (i = 0; i < priv.headerCells.length; i += 1) {
                cell = priv.headerCells[i];
                if (cell.callback) {
                    cell.removeEventListener('click', cell.callback, true);
                    cell.callback = null;
                }
            }
            clearTable.call(this);

            priv.layout.destroy();
            priv.layout = null;

            if (priv.paginationInterface) {
                priv.paginationInterface.destroy();
                priv.paginationInterface = null;
            }

            this.source.destroy();

            return this;
        }

    }
    se.ModelTable.prototype.Tooltip = StyledElements.Tooltip;

})(StyledElements, StyledElements.Utils);
