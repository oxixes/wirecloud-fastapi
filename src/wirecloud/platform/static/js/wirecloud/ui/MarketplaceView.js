/*
 *     Copyright (c) 2012-2017 CoNWeT Lab., Universidad Politécnica de Madrid
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

    const ERROR_TEMPLATE = '<s:styledgui xmlns:s="http://wirecloud.conwet.fi.upm.es/StyledElements" xmlns:t="http://wirecloud.conwet.fi.upm.es/Template" xmlns="http://www.w3.org/1999/xhtml"><div class="alert alert-error"><t:message/></div></s:styledgui>';

    const builder = new StyledElements.GUIBuilder();

    const notifyError = function notifyError(message, context) {
        message = builder.parse(builder.DEFAULT_OPENING + message + builder.DEFAULT_CLOSING, context);
        const error_alert = builder.parse(ERROR_TEMPLATE, {
            'message': message
        });

        this.errorsAlternative.clear();
        this.errorsAlternative.appendChild(error_alert);
        this.alternatives.showAlternative(this.errorsAlternative);
    };

    const auto_select_initial_market = function auto_select_initial_market() {
        const currentState = Wirecloud.HistoryManager.getCurrentState();
        if (currentState.market && currentState.market in this.viewsByName) {
            this.changeCurrentMarket(currentState.market, {history: "ignore"});
        } else if (this.viewList.length > 0) {
            this.changeCurrentMarket(this.viewList[0].market_id, {history: "replace"});
        } else {
            const msg = utils.gettext("<p>WireCloud is not connected with any marketplace.</p><p>Suggestions:</p><ul><li>Connect WireCloud with a new marketplace.</li><li>Go to the my resources view instead</li></ul>");
            notifyError.call(this, msg);
        }
    };

    const onGetMarketsSuccess = function onGetMarketsSuccess(response) {
        this.loading = false;
        this.loadtask = null;

        const old_views = this.viewsByName;
        this.viewsByName = {};
        this.viewList = [];

        for (let i = 0; i < response.length; i++) {
            const view_element = response[i];
            const market_key = view_element.user + '/' + view_element.name;

            if (market_key in old_views) {
                this.viewsByName[market_key] = old_views[market_key];
                delete old_views[market_key];
            } else {
                const view_constructor = Wirecloud.MarketManager.getMarketViewClass(view_element.type);
                if (view_constructor == null) {
                    continue;
                }
                this.viewsByName[market_key] = this.alternatives.createAlternative({alternative_constructor: view_constructor, containerOptions: {catalogue: this, marketplace_desc: view_element}});
                Wirecloud.UserInterfaceManager.workspaceviews[market_key] = this.viewsByName[market_key];
            }
            this.viewList.push(this.viewsByName[market_key]);

            this.number_of_alternatives += 1;
        }

        let p = Promise.resolve();
        for (const market_key in old_views) {
            p = p.then(remove_market.bind(this, old_views[market_key]));
        }

        return p.then(() => {
            return new Promise((resolve, reject) => {
                for (const market_key in old_views) {
                    old_views[market_key].destroy();
                }

                if (this.isVisible()) {
                    if (this.temporalAlternatives.indexOf(this.alternatives.getCurrentAlternative()) !== -1) {
                        auto_select_initial_market.call(this);
                    } else {
                        // Refresh wirecloud header as current marketplace may have been changed
                        Wirecloud.dispatchEvent('viewcontextchanged');
                    }
                }
                resolve();
            });
        });
    };

    const refresh_view_info = function refresh_view_info() {
        this.loading = true;
        this.number_of_alternatives = 0;
        Wirecloud.dispatchEvent('viewcontextchanged');

        this.loadtask = Wirecloud.MarketManager.getMarkets().then(
            onGetMarketsSuccess.bind(this),
            (error) => {
                this.loading = false;

                this.errorsAlternative.clear();
                notifyError.call(this, error);
                return Promise.reject(error);
            }
        );
    };

    const remove_market = function remove_market(market_view) {
        return new Promise(function (alt, resolve) {
            delete Wirecloud.UserInterfaceManager.workspaceviews[market_view.market_id];
            this.alternatives.removeAlternative(alt, {onComplete: resolve});
        }.bind(this, market_view));
    };

    ns.MarketplaceView = class MarketplaceView extends se.Alternative {

        constructor(id, options) {
            options.id = 'marketplace';
            super(id, options);

            this.viewsByName = {};
            this.alternatives = new StyledElements.Alternatives();
            this.emptyAlternative = this.alternatives.createAlternative();
            this.errorsAlternative = this.alternatives.createAlternative({containerOptions: {'class': 'marketplace-error-view'}});
            this.temporalAlternatives = [this.emptyAlternative, this.errorsAlternative];

            this.alternatives.addEventListener('postTransition', function (alternatives, out_alternative, in_alternative) {
                Wirecloud.dispatchEvent('viewcontextchanged', this);
            }.bind(this));
            this.appendChild(this.alternatives);

            this.marketMenu = new StyledElements.PopupMenu();
            this.marketMenu.append(new Wirecloud.ui.MarketplaceViewMenuItems(this));

            options.parentElement.addEventListener("postTransition", function (alts, outalt, inalt) {
                if (inalt === this && this.loading === null) {
                    this.refreshViewInfo();
                }
            }.bind(this));

            this.addEventListener('show', function (view) {

                if (view.loading === false && !view.error) {
                    if (view.alternatives.getCurrentAlternative() === view.emptyAlternative) {
                        auto_select_initial_market.call(view);
                    } else {
                        view.alternatives.getCurrentAlternative().refresh_if_needed();
                    }
                }
            });

            Object.defineProperty(this, 'error', {
                get: function () {
                    return this.alternatives.getCurrentAlternative() === this.errorsAlternative;
                }
            });

            this.myresourcesButton = new StyledElements.Button({
                iconClass: 'fas fa-archive',
                class: "wc-show-myresources-button",
                title: utils.gettext('My Resources')
            });
            this.myresourcesButton.addEventListener('click', function () {
                Wirecloud.UserInterfaceManager.changeCurrentView('myresources', {history: "push"});
            });

            this.number_of_alternatives = 0;
            this.loading = null;
            this.callbacks = [];
        }

        buildStateData() {
            const currentState = Wirecloud.HistoryManager.getCurrentState();
            const data = {
                workspace_owner: currentState.workspace_owner,
                workspace_name: currentState.workspace_name,
                view: 'marketplace',
                params: currentState.params
            };

            if (this.loading === false && this.error === false && this.alternatives.getCurrentAlternative() !== this.emptyAlternative) {
                // TODO
                if (this.alternatives.getCurrentAlternative().alternatives != null) {
                    const subview = this.alternatives.getCurrentAlternative().alternatives.getCurrentAlternative();
                    if (subview.view_name != null) {
                        data.subview = subview.view_name;
                        if ('buildStateData' in subview) {
                            subview.buildStateData(data);
                        }
                    }
                }
                data.market = this.alternatives.getCurrentAlternative().market_id;
            }

            return data;
        }

        onHistoryChange(state) {
            if (this.loading === false && state.market in this.viewsByName) {
                this.changeCurrentMarket(state.market, {history: "ignore"});
                if ('onHistoryChange' in this.viewsByName[state.market]) {
                    this.viewsByName[state.market].onHistoryChange(state);
                }
            }
        }

        goUp() {
            let change = false;

            const current_alternative = this.alternatives.getCurrentAlternative();
            if (this.temporalAlternatives.indexOf(current_alternative) === -1) {
                change = this.alternatives.getCurrentAlternative().goUp();
            }

            if (!change) {
                Wirecloud.UserInterfaceManager.changeCurrentView('workspace');
            }
        }

        getBreadcrumb() {
            const current_alternative = this.alternatives.getCurrentAlternative();
            if (current_alternative === this.emptyAlternative) {
                return [utils.gettext('loading marketplace view...')];
            } else if (current_alternative === this.errorsAlternative) {
                return [utils.gettext('marketplace list not available')];
            } else {
                const breadcrum = ['marketplace'];
                breadcrum.push(current_alternative.getLabel());
                // TODO
                if (current_alternative.alternatives != null) {
                    const subalternative = current_alternative.alternatives.getCurrentAlternative();

                    if (subalternative.view_name === 'details' && subalternative.currentEntry != null) {
                        breadcrum.push({
                            label: subalternative.currentEntry.title,
                            'class': 'resource_title'
                        });
                    }
                }
                return breadcrum;
            }
        }

        getTitle() {
            const current_alternative = this.alternatives.getCurrentAlternative();
            if (current_alternative === this.emptyAlternative || current_alternative === this.errorsAlternative) {
                return utils.gettext('Marketplace');
            } else {
                const marketname = current_alternative.getLabel();
                let title = utils.interpolate(utils.gettext('Marketplace - %(marketname)s'), {marketname: marketname});
                // Deprecated code, currently used for WireCloud and for the deprecated FIWARE Marketplace (now replaced by the BAE)
                if (current_alternative.alternatives) {
                    const subalternative = current_alternative.alternatives.getCurrentAlternative();
                    if (subalternative.view_name === "details" && subalternative.currentEntry != null) {
                        title += ' - ' + subalternative.currentEntry.title;
                    }
                }

                return title;
            }
        }

        getToolbarMenu() {
            return this.marketMenu;
        }

        getToolbarButtons() {
            return [this.myresourcesButton];
        }

        waitMarketListReady(options) {
            if (options == null || typeof options.onComplete !== 'function') {
                throw new TypeError('missing onComplete callback');
            }

            if (options.include_markets === true) {
                options.onComplete = function (onComplete) {
                    let count = Object.keys(this.viewsByName).length;

                    if (count === 0) {
                        try {
                            onComplete();
                        } catch (e) {}
                        return;
                    }

                    const listener = function () {
                        if (--count === 0) {
                            onComplete();
                        }
                    };
                    for (const key in this.viewsByName) {
                        this.viewsByName[key].wait_ready(listener);
                    }
                }.bind(this, options.onComplete);
            }

            if (this.loading === false) {
                utils.callCallback(options.onComplete);
                return;
            }

            if (this.loading === null) {
                refresh_view_info.call(this);
            }
            this.loadtask.then(options.onComplete);
        }

        refreshViewInfo() {
            return new Wirecloud.Task("Refreshing marketplace view", function (resolve, reject) {
                if (this.loading === true) {
                    return resolve();
                }

                refresh_view_info.call(this);
                this.loadtask.then(resolve, reject);
            }.bind(this));
        }

        addMarket(market_info) {
            const market_key = market_info.user + '/' + market_info.name;
            const view_constructor = Wirecloud.MarketManager.getMarketViewClass(market_info.type);
            market_info.permissions = {'delete': true};
            this.viewsByName[market_key] = this.alternatives.createAlternative({alternative_constructor: view_constructor, containerOptions: {catalogue: this, marketplace_desc: market_info}});
            Wirecloud.UserInterfaceManager.workspaceviews[market_key] = this.viewsByName[market_key];
            this.viewList.push(this.viewsByName[market_key]);

            this.number_of_alternatives += 1;
            this.changeCurrentMarket(market_key);
        }

        changeCurrentMarket(market, options) {
            options = utils.merge({
                history: "push",
            }, options);

            this.alternatives.showAlternative(this.viewsByName[market], {
                onComplete: function () {
                    const new_status = this.buildStateData();
                    if (options.history === "push") {
                        Wirecloud.HistoryManager.pushState(new_status);
                    } else if (options.history === "replace") {
                        Wirecloud.HistoryManager.replaceState(new_status);
                    }
                }.bind(this)
            });
        }

    }

    ns.MarketplaceView.prototype.view_name = 'marketplace';

})(Wirecloud.ui, StyledElements, Wirecloud.Utils);
