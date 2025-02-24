(function () {
    "use strict";

    let catalog = {};

    {{ js_catalogue|safe }}

    window.gettext = function (msgid) {
        return catalog[msgid] || msgid;
    }

    window.ngettext = function (msgid, msgid_plural, n) {
        const value = catalog[msgid];
        if (value) {
            return n === 1 ? value[0] : value[1];
        } else {
            return n === 1 ? msgid : msgid_plural;
        }
    }

    window.gettext_noop = function (msgid) {
        return msgid;
    }

    window.interpolate = function (fmt, obj, named) {
        if (named) {
            return fmt.replace(/%\(\w+\)s/g, function (match) {
                return String(obj[match.slice(2, -2)]);
            });
        } else {
            return fmt.replace(/%s/g, function (match) {
                return String(obj.shift());
            });
        }
    }
})();