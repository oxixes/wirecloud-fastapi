from os import path, pardir

BASEDIR = path.abspath(path.join(path.dirname(path.abspath(__file__)), pardir))

# TODO If platform is installed, the proxy has to be installed too
INSTALLED_APPS = (
    'wirecloud.commons',
    'wirecloud.platform',
    'wirecloud.catalogue',
    'wirecloud.proxy'
)

DATABASE = {
    'DRIVER': 'mongodb',
    'NAME': 'wirecloud-fastapi',
    'HOST': 'localhost',
    'PORT': '',
    'USER': '',
    'PASSWORD': ''
}

LANGUAGES = (
    ('es', 'Spanish'),
    ('en', 'English'),
    ('pt', 'Portuguese'),
)

DEFAULT_LANGUAGE = 'en'

# Make this unique, and don't share it with anybody.
JWT_KEY = '15=7f)g=)&spodi3bg8%&4fqt%f3rpg%b$-aer5*#a*(rqm79e'

SESSION_AGE = 60 * 60 * 24 * 14  # 2 weeks

CATALOGUE_MEDIA_ROOT = path.join(BASEDIR, 'catalogue', 'media')
CACHE_DIR = path.join(BASEDIR, 'cache')

WIRECLOUD_HTTPS_VERIFY = True

AVAILABLE_THEMES = [
    "defaulttheme"
]
THEME_ACTIVE = "defaulttheme"

# TODO Allow to define a list of known proxies to trust the X-Forwarded-For header