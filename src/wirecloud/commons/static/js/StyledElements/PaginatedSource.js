/*
 *     Copyright (c) 2012-2016 CoNWeT Lab., Universidad Politécnica de Madrid
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

/* globals StyledElements */


(function (se, utils) {

    "use strict";

    const privates = new WeakMap();

    const onSuccessCallback = function onSuccessCallback(elements, options) {
        const priv = privates.get(this);

        if (typeof priv.options.processFunc === 'function') {
            priv.options.processFunc(elements, options);
        }
        priv.currentPage = parseInt(options.current_page, 10);
        priv.currentElements = elements;

        if (priv.totalCount !== options.total_count) {
            priv.totalCount = options.total_count;
            calculatePages.call(this);
            this.dispatchEvent('paginationChanged');
        }
        this.dispatchEvent('requestEnd');
    };

    const onErrorCallback = function onErrorCallback(error) {
        const priv = privates.get(this);
        priv.currentElements = [];
        if (error == null) {
            error = {
                'message': 'unknown cause'
            };
        }

        this.dispatchEvent('requestEnd', error);
    };

    const calculatePages = function calculatePages() {
        const priv = privates.get(this);
        if (priv.options.pageSize === 0) {
            priv.totalPages = 1;
        } else {
            priv.totalPages = Math.ceil(priv.totalCount / priv.options.pageSize);
            if (priv.totalPages <= 0) {
                priv.totalPages = 1;
            }
        }
    };

    se.PaginatedSource = class PaginatedSource extends se.ObjectWithEvents {

        /**
         * Creates a new instance of class PaginatedSource.
         *
         * Events supported by this component:
         *      - optionsChanged:
         *      - paginationChanged:
         *      - requestStart:
         *      - requestEnd:
         *
         * @interface
         * @extends {StyledElements.ObjectWithEvents}
         * @name StyledElements.PaginatedSource
         * @since 0.5
         * @param {Object} options
         *      The options to be used
         */
        constructor(options) {
            const defaultOptions = {
                'pageSize': 25,
                'requestFunc': null,
                'processFunc': null
            };

            super(['optionsChanged', 'paginationChanged', 'requestStart', 'requestEnd']);

            // Initialize private variables
            const priv = {};
            privates.set(this, priv);

            if (typeof options.requestFunc !== "function") {
                throw new TypeError("requestFunc must be a function");
            }
            options.requestFunc = options.requestFunc.bind(this);

            Object.defineProperties(this, {
                /** @lends StyledElements.PaginatedSource.prototype */

                /**
                 * The current page.
                 *
                 * @name StyledElements.PaginatedSource#currentPage
                 */
                currentPage: {
                    get: function () {
                        return priv.currentPage;
                    }
                },

                /**
                 * PaginatedSource options.
                 *
                 * @name StyledElements.PaginatedSource#options
                 */
                options: {
                    get: function () {
                        return priv.options;
                    }
                },

                /**
                 * Current estimation of the available items.
                 *
                 * @name StyledElements.PaginatedSource#totalCount
                 */
                totalCount: {
                    get: function () {
                        return priv.totalCount;
                    }
                },

                /**
                 * Current number of pages.
                 *
                 * @name StyledElements.PaginatedSource#totalPages
                 */
                totalPages: {
                    get: function () {
                        return priv.totalPages;
                    }
                },

                /**
                 * The elements being currently displayed
                 *
                 * @name StyledElements.PaginatedSource#currentElements
                 */
                currentElements: {
                    get: function () {
                        return priv.currentElements;
                    }
                }
            });
            priv.options = utils.merge(defaultOptions, options);
            priv.currentPage = 1;
            priv.currentElements = [];
            priv.totalPages = 1;
        }

        /**
         * Gets the elements of the current pageSize
         *
         * @since 0.5
         *
         * @returns {Array.<Object>} currentElements
         *      The current elements.
         */
        getCurrentPage() {
            return this.currentElements;
        }

        /**
         * Updates the options used by this PaginatedSource
         *
         * @since 0.5
         *
         * @param {Object} newOptions
         *      The new options to be used.
         */
        changeOptions(options) {
            let new_page_size, old_offset, key, changed = false;
            const priv = privates.get(this);

            if (typeof options !== 'object') {
                return;
            }

            for (key in options) {
                if (key === 'pageSize') {
                    new_page_size = parseInt(options.pageSize, 10);
                    if (!isNaN(new_page_size) && new_page_size !== priv.options.pageSize) {
                        changed = true;
                        old_offset = (priv.currentPage - 1) * priv.options.pageSize;
                        priv.currentPage = Math.floor(old_offset / new_page_size) + 1;
                        priv.options.pageSize = new_page_size;
                        calculatePages.call(this);
                    }
                } else {
                    changed = true;
                    priv.options[key] = options[key];
                    priv.currentPage = 1;
                }
            }

            if (changed) {
                this.dispatchEvent('optionsChanged', priv.options);
                this.refresh();
            }

            return this;
        }

        /**
         * Changes to the first page
         *
         * @since 0.5
         */
        goToFirst() {
            return this.changePage(0);
        }

        /**
         * Changes to the previous page
         *
         * @since 0.5
         */
        goToPrevious() {
            const priv = privates.get(this);
            return this.changePage(priv.currentPage - 1);
        }

        /**
         * Changes to the next page
         *
         * @since 0.5
         */
        goToNext() {
            const priv = privates.get(this);
            return this.changePage(priv.currentPage + 1);
        }

        /**
         * Changes to the last page
         *
         * @since 0.5
         */
        goToLast() {
            const priv = privates.get(this);
            this.changePage(priv.totalPages);
        }

        /**
         * Refreshes the current page
         *
         * @since 0.5
         */
        refresh() {
            const priv = privates.get(this);
            this.dispatchEvent('requestStart');
            priv.options.requestFunc(priv.currentPage, priv.options, onSuccessCallback.bind(this), onErrorCallback.bind(this));
        }

        /**
         * Changes to the chosen page
         *
         * @since 0.5
         *
         * @param {Integer} index
         *      The number of the target page.
         */
        changePage(idx) {
            const priv = privates.get(this);
            if (idx < 1) {
                idx = 1;
            } else if (idx > priv.totalPages) {
                idx = priv.totalPages;
            }

            this.dispatchEvent('requestStart');
            priv.options.requestFunc(idx, priv.options, onSuccessCallback.bind(this), onErrorCallback.bind(this));
        }

    }

})(StyledElements, StyledElements.Utils);
