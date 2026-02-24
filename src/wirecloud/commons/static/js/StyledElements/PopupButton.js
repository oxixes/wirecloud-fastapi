// -*- coding: utf-8 -*-
// Copyright (c) 2026 Future Internet Consulting and Development Solutions S.L.

// This file is part of Wirecloud.

// Wirecloud is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.

// Wirecloud is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.

// You should have received a copy of the GNU Affero General Public License
// along with Wirecloud.  If not, see <http://www.gnu.org/licenses/>.

/* globals StyledElements */


(function (se, utils) {

    "use strict";

    const visibilityChangeListener = function visibilityChangeListener() {
        if (this.popup_menu.isVisible()) {
            this.wrapperElement.classList.add('open');
            this.wrapperElement.setAttribute('aria-expanded', 'true');
        } else {
            this.wrapperElement.classList.remove('open');
            this.wrapperElement.setAttribute('aria-expanded', 'false');
        }
    };

    const defaultOptions = {
        menuOptions: null,
        menu: null
    };

    se.PopupButton = class PopupButton extends se.Button {

        constructor(options) {
            options = utils.merge({}, defaultOptions, options);

            super(options);

            this.wrapperElement.setAttribute('aria-haspopup', 'true');
            this.wrapperElement.setAttribute('aria-expanded', 'false');

            if (options.menu != null) {
                this.popup_menu = options.menu;
                this._owned_popup_menu = false;
            } else {
                this.popup_menu = new this.PopupMenu(options.menuOptions);
                this._owned_popup_menu = true;
            }

            // Set aria-controls to reference the popup menu
            if (this.popup_menu && this.popup_menu.wrapperElement) {
                // Ensure the menu has an ID
                let menuId = this.popup_menu.wrapperElement.getAttribute('id');
                if (!menuId) {
                    menuId = 'se-popup-menu-' + Math.random().toString(36).substr(2, 9);
                    this.popup_menu.wrapperElement.setAttribute('id', menuId);
                }
                this.wrapperElement.setAttribute('aria-controls', menuId);
            }

            this.addEventListener('click', () => {
                if (this.popup_menu.isVisible()) {
                    this.popup_menu.hide();
                } else {
                    this.popup_menu.show(this);
                }
            });

            this._visibilityChangeListener = visibilityChangeListener.bind(this);
            this.popup_menu.addEventListener('visibilityChange', this._visibilityChangeListener);
        }

        /**
         * @override
         */
        _onkeydown(event, key) {

            switch (key) {
            case 'ArrowDown':
                event.preventDefault();
                this.popup_menu.show(this.getBoundingClientRect()).moveFocusDown();
                break;
            case 'ArrowUp':
                event.preventDefault();
                this.popup_menu.show(this.getBoundingClientRect()).moveFocusUp();
                break;
            case ' ':
            case 'Enter':
                this._clickCallback(event);
                break;
            case 'Tab':
                if (this.popup_menu.hasEnabledItem()) {
                    event.preventDefault();
                    this.popup_menu.moveFocusDown();
                }
                break;
            default:
                // Quit when this doesn't handle the key event.
                break;
            }
        }

        getPopupMenu() {
            return this.popup_menu;
        }

        replacePopupMenu(new_popup_menu) {
            if (this._owned_popup_menu) {
                this.popup_menu.destroy();
                this._owned_popup_menu = false;
            } else {
                if (this.popup_menu) {
                    this.popup_menu.clearEventListeners('visibilityChange');
                }
            }
            this.popup_menu = new_popup_menu;

            if (this.popup_menu) {
                this.wrapperElement.setAttribute('aria-expanded', this.popup_menu.isVisible() ? 'true' : 'false');
                this.popup_menu.addEventListener('visibilityChange', this._visibilityChangeListener);
            }

            // Update aria-controls to reference the new popup menu
            if (this.popup_menu && this.popup_menu.wrapperElement) {
                let menuId = this.popup_menu.wrapperElement.getAttribute('id');
                if (!menuId) {
                    menuId = 'se-popup-menu-' + Math.random().toString(36).substr(2, 9);
                    this.popup_menu.wrapperElement.setAttribute('id', menuId);
                }
                this.wrapperElement.setAttribute('aria-controls', menuId);
            } else {
                this.wrapperElement.removeAttribute('aria-controls');
            }
        }

        destroy() {
            StyledElements.Button.prototype.destroy.call(this);

            if (this._owned_popup_menu) {
                this.popup_menu.destroy();
            } else {
                this.popup_menu.clearEventListeners('visibilityChange');
            }
            this.popup_menu = null;
        }

    }

    se.PopupButton.prototype.PopupMenu = StyledElements.PopupMenu;

})(StyledElements, StyledElements.Utils);
