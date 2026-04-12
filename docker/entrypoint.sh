#!/usr/bin/env sh
set -eu

export PYTHONPATH="/app/docker:${PYTHONPATH:-}"

: "${WIRECLOUD_BASEDIR:=/var/lib/wirecloud}"
: "${WIRECLOUD_CACHE_DIR:=${WIRECLOUD_BASEDIR}/cache}"
: "${WIRECLOUD_CATALOGUE_MEDIA_ROOT:=${WIRECLOUD_BASEDIR}/catalogue/media}"
: "${WIRECLOUD_WIDGET_DEPLOYMENT_DIR:=${WIRECLOUD_BASEDIR}/deployment/widgets}"

mkdir -p "${WIRECLOUD_BASEDIR}" \
         "${WIRECLOUD_CACHE_DIR}" \
         "${WIRECLOUD_CATALOGUE_MEDIA_ROOT}" \
         "${WIRECLOUD_WIDGET_DEPLOYMENT_DIR}"

exec "$@"
