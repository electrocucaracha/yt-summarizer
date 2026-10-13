#!/bin/bash
# SPDX-license-identifier: Apache-2.0
##############################################################################
# Copyright (c) 2026
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

set -o errexit
set -o pipefail
if [[ ${DEBUG:-false} == "true" ]]; then
    set -o xtrace
fi

trap "make fmt" EXIT

if ! command -v go >/dev/null; then
    curl -fsSL http://bit.ly/install_pkg | PKG=go-lang bash
    # shellcheck disable=SC1091
    source /etc/profile.d/path.sh
fi

go_version="$(curl -sL https://golang.org/VERSION?m=text | sed -n 's/go//;s/\..$//;1p')"
find .github/workflows -type f \( -name '*.yml' -o -name '*.yaml' \) \
    -exec grep -l 'go-version:' {} + \
    -exec env go_version="${go_version}" bash -s {} + <<'EOF'
    for file; do
        sed -i \
            "s|^\([[:space:]]*go-version:[[:space:]]*\).*|\
\1\"^${go_version}\"|" \
            "${file}"
    done
EOF

if ! command -v uvx >/dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi
uv sync --upgrade
uvx pre-commit autoupdate
uv run --no-project --with git+https://github.com/electrocucaracha/gh-updater.git gh-updater .
