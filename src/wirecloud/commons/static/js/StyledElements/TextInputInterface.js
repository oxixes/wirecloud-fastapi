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

    /**
     *
     */
    se.TextInputInterface = class TextInputInterface extends se.InputInterface {

        constructor(fieldId, options) {
            super(fieldId, options);

            this.inputElement = new StyledElements.TextField(options);
            this.inputElement.addEventListener('change', () => {
                if (this.timeout != null) {
                    clearTimeout(this.timeout);
                }

                this.timeout = setTimeout(this.validate.bind(this), 700);
            });
            this.inputElement.addEventListener('blur', this.validate.bind(this));
        }

        static parse(value) {
            return value;
        }

        static stringify(value) {
            return value;
        }

        assignDefaultButton(button) {
            this.inputElement.addEventListener('submit', function () {
                button.click();
            });
        }

    }

})(StyledElements, StyledElements.Utils);
