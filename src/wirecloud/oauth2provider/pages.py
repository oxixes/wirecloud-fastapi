"""Theme-owned OAuth pages using StyledElements and scoped form destinations."""

from urllib.parse import quote, urlencode, urlsplit

from fastapi.responses import HTMLResponse
from jinja2 import select_autoescape

from wirecloud import settings


def page_headers(form_redirect_uri=None):
    form_actions = "'self'"
    if form_redirect_uri is not None:
        callback = urlsplit(form_redirect_uri)
        form_actions += " " + quote(f"{callback.scheme}://{callback.netloc}", safe=":/[]")
    return {
        "Cache-Control": "no-store",
        "Referrer-Policy": "no-referrer",
        "X-Frame-Options": "DENY",
        "Content-Security-Policy": "default-src 'none'; script-src 'self'; script-src-attr 'none'; "
        "style-src 'self'; img-src 'self'; font-src 'self'; "
        f"form-action {form_actions}; frame-ancestors 'none'; base-uri 'none'",
    }


def render_page(request, template, context, *, form_redirect_uri=None):
    from wirecloud.commons.templates.tags import get_translation
    from wirecloud.commons.utils.theme import get_jinja2_templates
    from wirecloud.platform.plugins import get_template_context
    from wirecloud.platform.utils import get_current_theme

    theme = get_current_theme(request)
    lang = getattr(request.state, "lang", settings.DEFAULT_LANGUAGE)
    root = request.scope.get("root_path", "").rstrip("/")
    values = get_template_context(request)
    values.update(
        {
            "request": request,
            "LANGUAGE_CODE": lang,
            "THEME": theme,
            "home_url": root + "/",
            "trans": lambda text: get_translation(theme, lang, text),
            "static": lambda asset, view="classic": root
            + "/static/"
            + asset
            + "?"
            + urlencode({"themeactive": theme, "view": view}),
        }
    )
    values.update(context)
    # Limit autoescaping changes to OAuth pages; existing widget/theme rendering is unaffected.
    environment = get_jinja2_templates(theme).env.overlay(autoescape=select_autoescape(["html", "xml"]))
    content = environment.get_template(f"wirecloud/oauth2provider/{template}.html").render(values)
    return HTMLResponse(content, headers=page_headers(form_redirect_uri))
