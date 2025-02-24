/*
 *     Copyright (c) 2015-2016 CoNWeT Lab., Universidad Politécnica de Madrid
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

    const events = ['btncreate.click'];

    const version_onchange = function version_onchange(element) {
        const version = element.getValue();

        this.meta = Wirecloud.LocalCatalogue.getResourceId(this.id + "/" + version.text);

        this.titleElement.textContent = this.meta.title;
        this.tooltip.options.content = this.meta.title;
        this.descriptionElement.textContent = this.meta.description ? this.meta.description : utils.gettext("No description provided");
        setImage.call(this, this.meta.image);
    };

    const setImage = function setImage(imageURL) {
        const thumbnailElement = this.imageElement.parentElement;

        thumbnailElement.classList.remove('se-thumbnail-missing');
        thumbnailElement.innerHTML = "";
        thumbnailElement.appendChild(this.imageElement);

        this.imageElement.removeAttribute('src');

        if (imageURL) {
            this.imageElement.src = imageURL;
        } else {
            image_onerror.call(this);
        }
    };

    const image_onerror = function image_onerror() {
        this.imageElement.parentElement.classList.add('se-thumbnail-missing');
        this.imageElement.parentElement.appendChild(document.createTextNode(utils.gettext("No image available")));
    };

    const orderVersions = function orderVersions(versions) {
        versions = versions.sort(function (version1, version2) {
            return -version1.compareTo(version2);
        });

        versions[0] = {
            label: utils.interpolate(utils.gettext("%(version)s (latest)"), {
                version: versions[0]
            }),
            value: versions[0]
        };

        return versions;
    };

    ns.ComponentGroup = class ComponentGroup extends se.StyledElement {

        constructor(resource, title) {
            super(events);

            title = title || utils.gettext("Create");

            this.titleElement = document.createElement('span');
            this.tooltip = new se.Tooltip();
            this.tooltip.bind(this.titleElement);

            this.imageElement = document.createElement('img');
            this.imageElement.onerror = image_onerror.bind(this);

            const version = new se.Select({
                initialValue: resource.version,
                initialEntries: orderVersions([resource.version].concat(resource.others))
            });
            version.addEventListener('change', version_onchange.bind(this));

            const button = new se.Button({
                class: 'btn-create wc-create-resource-component',
                title: title,
                iconClass: 'fas fa-plus'
            });
            button.addEventListener('click', function () {
                this.dispatchEvent('btncreate.click', button);
            }.bind(this));

            this.descriptionElement = document.createElement('div');
            this.descriptionElement.className = "text-muted";

            this.wrapperElement = (new se.GUIBuilder()).parse(Wirecloud.currentTheme.templates['wirecloud/wiring/component_group'], {
                title: this.titleElement,
                image: this.imageElement,
                versionselect: version,
                createbutton: button,
                vendor: resource.vendor,
                description: this.descriptionElement
            }).children[1];

            this.components = {};

            Object.defineProperties(this, {
                id: {value: resource.vendor + "/" + resource.name}
            });

            this.wrapperElement.setAttribute('data-id', this.id);
            version_onchange.call(this, version);
        }

        addComponent(component) {
            if (!(component.id in this.components)) {
                this.components[component.id] = component.appendTo(this.wrapperElement);
            }
            return this;
        }

    }

})(Wirecloud.ui.WiringEditor, StyledElements, StyledElements.Utils);
