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
    'DRIVER': 'postgresql+asyncpg',
    'NAME': 'wirecloud_fastapi',
    'HOST': 'localhost',
    'PORT': '',  # Set to empty string for default. Not used with sqlite3.
    'USER': 'postgres',  # Not used with sqlite3.
    'PASSWORD': 'pass123',  # Not used with sqlite3.
    'ECHO': True,
}

LANGUAGES = (
    ('es', 'Spanish'),
    ('en', 'English'),
    ('pt', 'Portuguese'),
)

# Make this unique, and don't share it with anybody.
JWT_KEY = '15=7f)g=)&spodi3bg8%&4fqt%f3rpg%b$-aer5*#a*(rqm79e'

SESSION_AGE = 60 * 60 * 24 * 14  # 2 weeks

CATALOGUE_MEDIA_ROOT = path.join(BASEDIR, 'catalogue', 'media')

WIRECLOUD_HTTPS_VERIFY = True

# TODO Allow to define a list of known proxies to trust the X-Forwarded-For header