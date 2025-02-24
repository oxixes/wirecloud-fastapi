/*
 *     Copyright (c) 2008-2016 CoNWeT Lab., Universidad Politécnica de Madrid
 *     Copyright (c) 2020-2021 Future Internet Consulting and Development Solutions S.L.
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

    const on_alternatives_get = function on_alternatives_get() {
        return utils.clone(privates.get(this).alternatives);
    };

    const on_alternative_list_get = function on_alternative_list_get() {
        return privates.get(this).alternativeList.slice(0);
    };

    const build_transit_promise = function build_transit_promise(effect, outAlternative, inAlternative, context) {
        let p = new Promise((fulfill) => {
            // Throw an event notifying we are going to change the visible alternative
            context.dispatchEvent('preTransition', outAlternative, inAlternative);
            context.wrapperElement.classList.add('se-on-transition');
            fulfill();
        });

        switch (effect) {
        case StyledElements.Alternatives.HORIZONTAL_SLIDE:
            outAlternative.addClassName('slide');
            inAlternative.addClassName([
                'slide',
                inAlternative.altId < outAlternative.altId ? 'left' : 'right'
            ]).show();
            p = p.then(function () {
                return utils.timeoutPromise(Promise.all([
                    utils.waitTransition(inAlternative.get()),
                    utils.waitTransition(outAlternative.get())
                ]), 3000, 'timeout');
            }).then(function () {
                inAlternative.removeClassName('slide');
                outAlternative.removeClassName('slide left right').hide();
            });
            // Trigger slide effects
            setTimeout(function () {
                outAlternative.addClassName(inAlternative.altId < outAlternative.altId ? 'right' : 'left');
                inAlternative.removeClassName('left right');
            }, 10);
            break;
        case StyledElements.Alternatives.CROSS_DISSOLVE:
            inAlternative.addClassName('fade').show();
            outAlternative.addClassName('fade in');
            p = p.then(function () {
                return utils.timeoutPromise(Promise.all([
                    utils.waitTransition(inAlternative.get()),
                    utils.waitTransition(outAlternative.get())
                ]), 3000, 'timeout');
            }).then(function () {
                inAlternative.removeClassName('fade in');
                outAlternative.removeClassName('fade').hide();
            });
            // Trigger fade effects
            setTimeout(() => {
                inAlternative.addClassName('in');
                outAlternative.removeClassName('in');
            }, 10);
            break;
        default:
        case StyledElements.Alternatives.NONE:
            p = p.then(() => {
                inAlternative.show();
                outAlternative.hide();
            });
        }

        return p.then(() => {
            privates.get(context).visibleAlt = inAlternative;
            context.wrapperElement.classList.remove('se-on-transition');
            // Throw an event notifying we have changed the visible alternative
            context.dispatchEvent('postTransition', outAlternative, inAlternative);
            return {in: inAlternative, out: outAlternative};
        });
    };

    se.Alternatives = class Alternatives extends se.StyledElement {

        /**
         * Creates an Alternatives component. An Alternative container allows
         * contents to share the same placement, being only one of the configured
         * {@link StyledElements.Alternative} able to be displayed at one time.
         *
         * @constructor
         * @extends StyledElements.StyledElement
         * @name StyledElements.Alternatives
         * @since 0.5
         *
         * @param {Object.<String, *>} options
         *    Available options:
         */
        constructor(options) {
            const defaultOptions = {
                'class': '',
                'full': true,
                'defaultEffect': StyledElements.Alternatives.NONE
            };

            options = utils.merge(defaultOptions, options);
            super(['preTransition', 'postTransition']);

            this.wrapperElement = document.createElement("div");
            this.wrapperElement.className = utils.prependWord(options.class, "se-alternatives");

            /* Process options */
            if (options.id) {
                this.wrapperElement.setAttribute("id", options.id);
            }

            if (options.full) {
                this.wrapperElement.classList.add("full");
            }

            Object.defineProperties(this, {
                alternatives: {
                    get: on_alternatives_get
                },
                alternativeList: {
                    get: on_alternative_list_get
                },
                defaultEffect: {
                    value: options.defaultEffect,
                    writable: true
                }
            });

            /* Transitions code */
            const initFunc = function initFunc(context, command) {
                let inAlternative, outAlternative;

                const priv = privates.get(context);
                let p = Promise.resolve();

                switch (command.type) {
                case "transit":
                    inAlternative = command.inAlternative;
                    outAlternative = context.visibleAlt;

                    if (inAlternative === outAlternative) {
                        utils.callCallback(command.onComplete, context, outAlternative, inAlternative);
                        return {in: inAlternative, out: outAlternative}; // we are not going to process this command
                    }

                    p = build_transit_promise(command.effect, outAlternative, inAlternative, context);
                    break;
                case "remove":
                    outAlternative = command.outAlternative;
                    if (priv.visibleAlt === outAlternative) {
                        if (priv.alternativeList.length > 0) {
                            inAlternative = priv.alternativeList[command.index];
                            if (!inAlternative) {
                                inAlternative = priv.alternativeList[command.index - 1];
                            }
                            p = build_transit_promise(command.effect, outAlternative, inAlternative, context);
                        } else {
                            priv.visibleAlt = null;
                        }
                    }
                    p = p.then(function () {
                        context.wrapperElement.removeChild(outAlternative.wrapperElement);
                    }.bind(this));
                }

                return p.then((result) => {
                    // Call the onComplete callback
                    utils.callCallback(command.onComplete, context, outAlternative, inAlternative);
                    return result;
                });
            };

            privates.set(this, {
                nextAltId: 0,
                transitionsQueue: new StyledElements.CommandQueue(this, initFunc),
                visibleAlt: null,
                alternatives: {},
                alternativeList: []
            });
        }

        repaint(temporal) {
            const priv = privates.get(this);

            // Resize content
            if (priv.visibleAlt != null) {
                priv.visibleAlt.repaint(!!temporal);  // Convert temporal to boolean
            }

            return this;
        }

        createAlternative(options) {
            const priv = privates.get(this);

            const defaultOptions = {
                alternative_constructor: StyledElements.Alternative,
                containerOptions: {},
                initiallyVisible: false
            };
            options = utils.update(defaultOptions, options);
            options.containerOptions.parentElement = this;

            const altId = privates.get(this).nextAltId++;

            if ((options.alternative_constructor !== StyledElements.Alternative) && !(options.alternative_constructor.prototype instanceof StyledElements.Alternative)) {
                throw new TypeError();
            }
            // eslint-disable-next-line new-cap
            const alt = new options.alternative_constructor(altId, options.containerOptions);
            alt.parentElement = this;

            alt.insertInto(this.wrapperElement);

            priv.alternatives[altId] = alt;
            priv.alternativeList.push(alt);

            if (!priv.visibleAlt) {
                priv.visibleAlt = alt;
                alt.setVisible(true);
            } else if (options.initiallyVisible) {
                this.showAlternative(alt);
            }

            /* Return the alternative container */
            return alt;
        }

        /**
         * Removes an alternative from this Alternatives instance
         *
         * @param {Number|StyledElements.Alternative} Alternative to remove. Must
         * belong to this instance of Alternatives.
         *
         * @param {Object} [options]
         *
         * Optional object with extra options:
         * - `effect`: effect to use in case of requiring switching to another
         *   alternative
         * - `onComplete`: callback to call on completion (deprecated, use the
         *   returned promise)
         *
         * @returns {Promise}
         *     A promise tracking the progress of visually removing the alternative.
         *     The alternative itself is removed immediatelly from the list of
         *     available alternatives.
         */
        removeAlternative(alternative, options) {
            const priv = privates.get(this);

            options = utils.update({
                effect: this.defaultEffect,
                onComplete: null
            }, options);

            let id;
            if (alternative instanceof StyledElements.Alternative) {
                id = alternative.altId;
                if (priv.alternatives[id] !== alternative) {
                    throw new TypeError('alternative is not owner by this alternatives element');
                }
            } else {
                id = alternative;
                alternative = priv.alternatives[alternative];
                if (!alternative) {
                    // Do nothing
                    utils.callCallback(options.onComplete);
                    return Promise.resolve();
                }
            }

            delete priv.alternatives[id];
            const index = priv.alternativeList.indexOf(alternative);
            priv.alternativeList.splice(index, 1);

            return priv.transitionsQueue.addCommand({
                effect: options.effect,
                index: index,
                type: "remove",
                onComplete: options.onComplete,
                outAlternative: alternative
            });
        }

        clear() {
            const priv = privates.get(this);
            priv.alternatives = {};
            priv.alternativeList = [];
            priv.nextAltId = 0;
            priv.visibleAlt = null;
            this.wrapperElement.innerHTML = '';

            return this;
        }

        getCurrentAlternative() {
            return privates.get(this).visibleAlt;
        }

        get visibleAlt() {
            return this.getCurrentAlternative();
        }

        /**
         * Changes current visible alternative.
         *
         * @since 0.5
         * @name StyledElements.Alternative#showAlternative
         *
         * @param {Number|StyledElements.Alternative} Alternative to show. Must belong
         * to this instance of Alternatives.
         *
         * @param {Object} [options]
         *
         * Optional object with extra options:
         * - `effect`: effect to use in the transition
         * - `onComplete`: callback to call on completion (deprecated, use the
         *   returned promise)
         *
         * @returns {Promise}
         *     A promise tracking the progress of the alternative switch.
         */
        showAlternative(alternative, options) {
            const command = {};

            options = utils.update({
                effect: this.defaultEffect,
                onComplete: null
            }, options);

            const priv = privates.get(this);

            if (alternative instanceof StyledElements.Alternative) {
                if (priv.alternatives[alternative.altId] !== alternative) {
                    throw new TypeError('Invalid alternative');
                }
                command.inAlternative = alternative;
            } else {
                if (priv.alternatives[alternative] == null) {
                    throw new TypeError('Invalid alternative');
                }
                command.inAlternative = priv.alternatives[alternative];
            }

            command.type = "transit";
            command.onComplete = options.onComplete;
            command.effect = options.effect;

            return priv.transitionsQueue.addCommand(command);
        }

    }

    se.Alternatives.HORIZONTAL_FLIP = "horizontalflip";
    se.Alternatives.HORIZONTAL_SLIDE = "horizontalslide";
    se.Alternatives.CROSS_DISSOLVE = "dissolve";
    se.Alternatives.NONE = "none";

})(StyledElements, StyledElements.Utils);
