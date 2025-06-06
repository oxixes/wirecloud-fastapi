/*
 *     Copyright 2012-2017 (c) CoNWeT Lab., Universidad Politécnica de Madrid
 *     Copyright (c) 2018-2020 Future Internet Consulting and Development Solutions S.L.
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

    const get_widgets = function get_widgets() {
        return Array.prototype.concat.apply([], this.notebook.tabs.map(function (tab) {
            return tab.widgets;
        }));
    };

    // =========================================================================
    // EVENT HANDLERS
    // =========================================================================

    const showHideTabBar = function showHideTabBar(editing) {
        this.layout.content.toggleClassName("wc-workspace-editing", editing);

        this.walletButton.enabled = editing && this.model.isAllowed('edit');
        this.wiringButton.enabled = editing && this.model.isAllowed('edit');
        this.notebook.tabWrapper.toggleClassName("hidden", !(editing || this.tabs.length > 1));
        if (this.addTabButton) {
            this.addTabButton.toggleClassName("hidden", !editing);
        }

        if (this.editingIntervalAddon) {
            this.editingIntervalAddon.toggleClassName("hidden", !editing);
        }
    };

    const on_workspace_createoperator = function on_workspace_createoperator(workspace_model, operator) {
        if (operator.wrapperElement) {
            this.layout.content.appendChild(operator.wrapperElement);
        }
    };

    const on_workspace_removeoperator = function on_workspace_removeoperator(workspace_model, operator) {
        if (operator.wrapperElement) {
            this.layout.content.removeChild(operator.wrapperElement);
        }
    };

    const on_workspace_change = function on_workspace_change(workspace) {
        const state = {
            workspace_owner: this.model.owner,
            workspace_name: this.model.name,
            workspace_title: this.model.title,
            view: "workspace",
            tab: Wirecloud.HistoryManager.getCurrentState().tab
        };
        Wirecloud.HistoryManager.replaceState(state);

        Wirecloud.UserInterfaceManager.header.refresh();
    };

    const on_workspace_remove = function on_workspace_remove(workspace) {
        // Go to the wirecloud/home dashboard
        Wirecloud.UserInterfaceManager.monitorTask(
            Wirecloud.changeActiveWorkspace({owner: 'wirecloud', name: 'home'})
        );
    };

    const on_workspace_unload = function on_workspace_unload(workspace) {
        // This must be always the case
        // if (this.model === workspace) {
        this.model.operators.forEach((operator) => {
            operator.unload(true);
        });

        this.model = null;
        this.editButton.enabled = false;
        this.editButton.active = false;
        this.walletButton.enabled = false;
        this.wiringButton.enabled = false;
        this.layout.content.clear();
        workspace.removeEventListener('remove', this.on_workspace_remove_bound);
        workspace.removeEventListener('change', this.on_workspace_change_bound);
        workspace.removeEventListener('unload', this.on_workspace_unload_bound);
        workspace.removeEventListener('createoperator', this.on_workspace_createoperator_bound);
        workspace.removeEventListener('removeoperator', this.on_workspace_removeoperator_bound);
        this.model = null;
        showHideTabBar.call(this, false);
    };

    const on_click_createtab = function on_click_createtab(button) {
        button.disable();
        this.model.createTab().then(
            (tab) => {
                this.notebook.createTab({
                    tab_constructor: Wirecloud.ui.WorkspaceTabView,
                    model: tab,
                    workspace: this
                });
                button.enable();
            },
            () => {
                button.enable();
            }
        );
    };

    ns.WorkspaceView = class WorkspaceView extends se.Alternative {

        constructor(id, options) {
            super(id, options);
            this.events.editmode = new StyledElements.Event(this);

            this.wrapperElement.classList.add("wc-workspace");

            this.wsMenu = new StyledElements.PopupMenu();
            this.wsMenu.append(new Wirecloud.ui.WorkspaceListItems(function (context, workspace) {
                Wirecloud.UserInterfaceManager.monitorTask(Wirecloud.changeActiveWorkspace(workspace));
            }));
            this.wsMenu.appendSeparator();
            this.wsMenu.append(new Wirecloud.ui.WorkspaceViewMenuItems(this));

            this.editButton = new se.ToggleButton({
                class: "wc-edit-mode-button",
                iconClass: "fas fa-pencil-alt"
            });
            this.editButton.addEventListener("click", (button) => {
                showHideTabBar.call(this, button.active);
                if (!button.active) {
                    this.walletButton.active = false;
                    this.layout.slideOut();
                    this.tabs.forEach((tab) => {
                        if (tab.quitEditingInterval) {
                            tab.quitEditingInterval();
                        }
                    });
                }
                this.activeTab.dragboard._updateIWidgetSizes(true, true);
            });
            this.editButton.addEventListener("active", (button) => {
                if (this.editing) {
                    this.activeTab.dragboard.topLayout.active = true;
                    this.activeTab.dragboard.rightLayout.active = true;
                    this.activeTab.dragboard.bottomLayout.active = true;
                    this.activeTab.dragboard.leftLayout.active = true;
                }
                if (this.model != null) {
                    this.model.contextManager.modify({editing: this.editing});
                }
                this.dispatchEvent("editmode", this.editing);
            });

            this.walletButton = this.buildAddWidgetButton();

            this.wiringButton = new StyledElements.Button({
                class: "wc-show-wiring-button",
                iconClass: 'fas fa-puzzle-piece',
                title: utils.gettext('Wiring')
            });
            this.wiringButton.addEventListener('click', function () {
                Wirecloud.UserInterfaceManager.changeCurrentView('wiring');
            });

            this.myresourcesButton = new StyledElements.Button({
                iconClass: 'fas fa-archive',
                class: "wc-show-myresources-button",
                title: utils.gettext('My Resources')
            });
            this.myresourcesButton.addEventListener('click', function () {
                Wirecloud.UserInterfaceManager.changeCurrentView('myresources');
            });

            this.marketButton = new StyledElements.Button({
                iconClass: 'fas fa-shopping-cart',
                class: "wc-show-marketplace-button",
                title: utils.gettext('Get more components')
            });
            this.marketButton.addEventListener('click', function () {
                Wirecloud.UserInterfaceManager.changeCurrentView('marketplace');
            });

            this.layout = new StyledElements.OffCanvasLayout();
            this.appendChild(this.layout);

            Object.defineProperties(this, {
                editing: {
                    get: () => {
                        return this.editButton.active;
                    }
                },
                activeTab: {
                    get: function () {
                        return this.notebook.visibleTab;
                    }
                },
                tabs: {
                    get: function () {
                        return this.notebook.tabs;
                    }
                },
                name: {
                    get: function () {
                        return this.model.name;
                    }
                },
                title: {
                    get: function () {
                        return this.model.title;
                    }
                },
                widgets: {
                    get: function () {
                        return get_widgets.call(this);
                    }
                }
            });

            this.on_workspace_change_bound = on_workspace_change.bind(this);
            this.on_workspace_remove_bound = on_workspace_remove.bind(this);
            this.on_workspace_unload_bound = on_workspace_unload.bind(this);
            this.on_workspace_createoperator_bound = on_workspace_createoperator.bind(this);
            this.on_workspace_removeoperator_bound = on_workspace_removeoperator.bind(this);

            Wirecloud.addEventListener('loaded', () => {
                this.showcase =  new Wirecloud.ui.ComponentSidebar();
                this.layout.appendChild(this.showcase);

                this.showcase.addEventListener('create', (showcase, group, button) => {
                    button.disable();

                    if (group.meta.type === 'widget') {
                        this.activeTab.createWidget(group.meta).then(
                            () => {
                                button.enable();
                            },
                            () => {
                                button.enable();
                            }
                        );
                    } else {
                        Wirecloud.UserInterfaceManager.monitorTask(
                            Wirecloud.mergeWorkspace(
                                this.model,
                                {
                                    mashup: group.meta.uri
                                }
                            ).then(
                                (workspace) => {
                                    return Wirecloud.changeActiveWorkspace(workspace, {history: "replace"});
                                },
                                (error) => {
                                    button.enable();
                                    let dialog;
                                    if (error.details != null && 'missingDependencies' in error.details) {
                                        // Show missing dependencies
                                        dialog = new Wirecloud.ui.MissingDependenciesWindowMenu(null, error.details);
                                    } else {
                                        dialog = new Wirecloud.ui.MessageWindowMenu(error, Wirecloud.constants.LOGGING.ERROR_MSG);
                                    }
                                    dialog.show();
                                }
                            )
                        );
                    }
                });
            });
        }

        findTab(id) {
            let i;

            for (i = 0; i < this.notebook.tabs.length; i++) {
                if (this.notebook.tabs[i].id === id) {
                    return this.notebook.tabs[i];
                }
            }

            return null;
        }

        findWidget(id) {
            let i, widget;

            for (i = 0; i < this.notebook.tabs.length; i++) {
                if (!(this.notebook.tabs[i] instanceof ns.WorkspaceTabView)) {
                    continue;
                }
                widget = this.notebook.tabs[i].findWidget(id);
                if (widget != null) {
                    return widget;
                }
            }

            return null;
        }

        showSettings() {
            (new Wirecloud.ui.PreferencesWindowMenu('workspace', this.model.preferences)).show();
            return this;
        }

        loadWorkspace(workspace, options) {
            options = utils.merge({
                initialtab: null
            }, options);

            this.walletButton.active = false;

            this.notebook = new StyledElements.Notebook({
                'class': 'se-notebook-bottom'
            });
            this.layout.slideOut().content.clear();
            this.notebook.appendTo(this.layout.content);

            const loadingTab = this.notebook.createTab();
            loadingTab.disable();
            loadingTab.addClassName('loading');

            this.model = workspace;
            this.model.view = this;
            this.model.addEventListener('unload', this.on_workspace_unload_bound);
            this.model.addEventListener('change', this.on_workspace_change_bound);
            this.model.addEventListener('remove', this.on_workspace_remove_bound);
            this.model.addEventListener('createoperator', this.on_workspace_createoperator_bound);
            this.model.addEventListener('removeoperator', this.on_workspace_removeoperator_bound);

            this.model.operators.forEach((operator) => {
                if (operator.wrapperElement) {
                    this.layout.content.appendChild(operator.wrapperElement);
                }
            });

            let initialTab = null;
            let requestedTab = null;

            this.model.tabs.forEach(function (model) {
                const tab = this.notebook.createTab({
                    tab_constructor: Wirecloud.ui.WorkspaceTabView,
                    model: model,
                    workspace: this
                });

                if (options.initialtab === model.name) {
                    requestedTab = tab;
                }

                if (model.initial) {
                    initialTab = tab;
                }
            }, this);

            if (requestedTab != null) {
                this.notebook.goToTab(requestedTab);
            } else {
                this.notebook.goToTab(initialTab);
            }

            this.notebook.removeTab(loadingTab);

            if (this.model.isAllowed('edit')) {
                this.editingIntervalAddon = new StyledElements.Addon({
                    class: 'wc-editing-interval',
                    listeners: false
                });
                this.notebook.addToEastSection(this.editingIntervalAddon);
                this.updateEditingInterval(this.activeTab.getEditingIntervalElement());

                this.notebook.addEventListener('changed', (nt, oldTab, newTab) => {
                    newTab.updateEditingIntervalName();
                    this.updateEditingInterval(newTab.getEditingIntervalElement());
                });

                this.addTabButton = new StyledElements.Button({
                    title: utils.gettext("New tab"),
                    iconClass: "fas fa-plus",
                    class: "wc-create-workspace-tab"
                });
                this.notebook.addToEastSection(this.addTabButton);
                this.addTabButton.addEventListener('click', on_click_createtab.bind(this));
            } else {
                this.addTabButton = null;
            }
            this.editButton.enabled = this.model.isAllowed('edit');
            this.editButton.active = false;

            if (Wirecloud.Utils.isFullscreenSupported()) {
                this.fullscreenButton = new StyledElements.Button({
                    iconClass: 'fas fa-expand',
                    title: utils.gettext('Full screen')
                });
                this.notebook.addToEastSection(this.fullscreenButton);
                Wirecloud.Utils.onFullscreenChange(this.notebook, () => {
                    this.fullscreenButton.removeIconClassName(['fa-expand', 'fa-compress']);
                    if (this.notebook.fullscreen) {
                        this.fullscreenButton.addIconClassName('fa-compress');
                        this.fullscreenButton.setTitle(utils.gettext('Exit full screen'));
                        this.notebook.addClassName('fullscreen');
                    } else {
                        this.fullscreenButton.addIconClassName('fa-expand');
                        this.fullscreenButton.setTitle(utils.gettext('Full screen'));
                        this.notebook.removeClassName('fullscreen');
                    }
                });
                this.fullscreenButton.addEventListener('click', () => {
                    if (this.notebook.fullscreen) {
                        this.notebook.exitFullscreen();
                    } else {
                        this.notebook.requestFullscreen();
                    }
                });
            }

            if (Wirecloud.contextManager.get('mode') === 'embedded') {
                this.seeOnWirecloudButton = new StyledElements.Button({
                    'class': 'powered-by-wirecloud'
                });
                this.notebook.addToEastSection(this.seeOnWirecloudButton);
                this.seeOnWirecloudButton.addEventListener('click', () => {
                    const url = Wirecloud.URLs.WORKSPACE_VIEW.evaluate({owner: encodeURIComponent(this.model.owner), name: encodeURIComponent(this.model.name)});
                    window.open(url, '_blank');
                });
            } else {
                this.poweredByWirecloudButton = new StyledElements.Button({
                    'class': 'powered-by-wirecloud'
                });
                this.notebook.addToEastSection(this.poweredByWirecloudButton);
                this.poweredByWirecloudButton.addEventListener('click', () => {
                    window.open('https://github.com/Wirecloud/wirecloud', '_blank');
                });
            }
            showHideTabBar.call(this, false);
        }

        buildAddWidgetButton() {
            const button = new se.ToggleButton({
                title: utils.gettext("Add components"),
                class: "btn-primary wc-show-component-sidebar-button",
                iconClass: "fas fa-archive",
                stackedIconClass: "fas fa-plus-circle"
            });
            button.addEventListener('click', (button) => {
                if (button.active) {
                    this.showcase.searchComponents.refresh();
                    this.layout.slideIn();
                } else {
                    this.layout.slideOut();
                }
            });

            return button;
        }

        buildStateData() {
            const currentState = Wirecloud.HistoryManager.getCurrentState();
            return {
                workspace_owner: currentState.workspace_owner,
                workspace_name: currentState.workspace_name,
                workspace_title: currentState.workspace_title,
                view: 'workspace',
                params: currentState.params
            };
        }

        canGoUp() {
            return Wirecloud.activeWorkspace != null && (Wirecloud.activeWorkspace.owner !== "wirecloud" || Wirecloud.activeWorkspace.name !== "home");
        }

        goUp() {
            Wirecloud.changeActiveWorkspace({owner: 'wirecloud', name: 'home'});
            return this;
        }

        getBreadcrumb() {
            const current_state = Wirecloud.HistoryManager.getCurrentState();

            let entries;
            if (this.model != null) {
                entries = [
                    {
                        'label': this.model.owner
                    }, {
                        'label': this.model.title,
                    }
                ];
            } else if ('workspace_owner' in current_state) {
                entries = [
                    {
                        'label': current_state.workspace_owner
                    }, {
                        'label': current_state.workspace_title,
                    }
                ];
            } else {
                entries = [{
                    'label': utils.gettext('loading...')
                }];
            }

            return entries;
        }

        getTitle() {
            const current_state = Wirecloud.HistoryManager.getCurrentState();
            if (this.model != null) {
                return this.model.owner + '/' + this.model.title;
            } else if ('workspace_owner' in current_state) {
                return current_state.workspace_owner + '/' + current_state.workspace_title;
            } else {
                return utils.gettext('loading...');
            }
        }

        getToolbarMenu() {
            const current_state = Wirecloud.HistoryManager.getCurrentState();
            if ('workspace_owner' in current_state) {
                const context = Wirecloud.contextManager;
                if (context && context.get('username') !== 'anonymous') {
                    return this.wsMenu;
                }
            }
            return null;
        }

        getToolbarButtons() {
            if (Wirecloud.contextManager && Wirecloud.contextManager.get('username') !== 'anonymous') {

                return [this.editButton, this.walletButton, this.wiringButton, this.myresourcesButton, this.marketButton];
            } else {
                return [];
            }
        }

        onHistoryChange(newState) {
            let target_tab, nextWorkspace, alert_msg;

            if (newState.workspace_owner in Wirecloud.workspacesByUserAndName) {
                nextWorkspace = Wirecloud.workspacesByUserAndName[newState.workspace_owner][newState.workspace_name];
            }

            if (nextWorkspace == null) {
                if (Wirecloud.activeWorkspace != null) {
                    Wirecloud.activeWorkspace.unload();
                    Wirecloud.activeWorkspace = null;
                }
                alert_msg = document.createElement('div');
                alert_msg.className = 'alert alert-info';
                alert_msg.textContent = utils.gettext('The requested workspace is no longer available (it was deleted).');
                this.layout.slideOut().content.clear().appendChild(alert_msg);
                Wirecloud.dispatchEvent('viewcontextchanged');
            } else if (Wirecloud.activeWorkspace == null || (nextWorkspace.id !== Wirecloud.activeWorkspace.id)) {
                Wirecloud.changeActiveWorkspace(nextWorkspace, {initialtab: newState.tab, history: 'ignore', params: newState.params});
            } else if (newState.tab != null) {
                target_tab = this.findTab(newState.tab_id);
                this.notebook.goToTab(target_tab);
                document.title = newState.workspace_owner + '/' + newState.workspace_name;
            } else {
                document.title = newState.workspace_owner + '/' + newState.workspace_name;
            }
        }

        /**
         * Draw attention from the user to the indicated widget. This method should
         * be used when a widget requires intervention from the user.
         *
         * @returns {Wirecloud.ui.WorkspaceView}
         **/
        drawAttention(id) {
            const widget = this.findWidget(id);

            if (widget !== null) {
                widget.tab.dragboard.raiseToTop(widget);
                widget.highlight().tab.highlight();
                if (widget.layout instanceof Wirecloud.ui.SidebarLayout) {
                    widget.layout.active = true;
                }
            }

            return this;
        }

        /**
         * Update the editing interval addon's content with the given element.
         */
        updateEditingInterval(element) {
            if (this.editingIntervalAddon) {
                this.editingIntervalAddon.wrapperElement.innerHTML = "";
                this.editingIntervalAddon.wrapperElement.appendChild(element);
            }
        }

    }
    ns.WorkspaceView.prototype.view_name = 'workspace';

})(Wirecloud.ui, StyledElements, StyledElements.Utils);
