/*
 *     Copyright (c) 2015-2016 CoNWeT Lab., Universidad Politécnica de Madrid
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

/* globals gettext, ngettext, StyledElements, Wirecloud */


Wirecloud.Utils = StyledElements.Utils;

Wirecloud.Utils.gettext = gettext;
Wirecloud.Utils.ngettext = ngettext;
Wirecloud.Utils.getLayoutMatrix = function getLayoutMatrix(layout, widgets, screenSize) {
    const matrix = [];
    for (let x = 0; x < layout.columns; x++) {
        matrix[x] = [];
    }

    widgets.forEach((widget) => {
        if (!(widget.layout instanceof Wirecloud.ui.FullDragboardLayout) && !(widget.layout instanceof Wirecloud.ui.FreeLayout)) {
            const layoutConfig = widget.model.getLayoutConfigBySize(screenSize);
            layout._reserveSpace2(matrix, "NOTAWIDGET", layoutConfig.left, layoutConfig.top, layoutConfig.width, layoutConfig.height);
        }
    });

    return matrix;
};
Wirecloud.Utils.getCookie = function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
        return parts.pop().split(';').shift();
    }
    return null;
}