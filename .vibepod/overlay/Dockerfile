# .vibepod/overlay/Dockerfile — no FROM line
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# --- aqua-managed CLIs (gh, uv) ----------------------------------------------
#
# gh and uv come from aqua rather than apt or a curl|sh one-liner: their
# versions are pinned in aqua.yaml and every download is checked against
# aqua-checksums.json
# (checksum.require_checksum). Both files sit next to this Dockerfile, which is
# the overlay build context, so editing them rebuilds the image on the next run.
#
# Two flags this environment needs:
#   * -v pins the aqua version. Without it aqua-installer calls
#     `aqua update-aqua` with no argument and installs whatever is latest.
#   * AQUA_DISABLE_SLSA=true — aqua's SLSA step fetches
#     tuf-repo-cdn.sigstore.dev, which the vibepod proxy answers with 403.
#     The installer's built-in sha256 list plus aqua-checksums.json still cover
#     every downloaded artifact. Drop it if sigstore gets allowlisted.
ARG AQUA_INSTALLER_VERSION=v4.0.5
ARG AQUA_INSTALLER_SHA256=451028d56959cc738564885b1dbebc2691ea038ffde04e2472e4d486a3591146
ARG AQUA_VERSION=v2.62.3
# ARG, not ENV: the build steps below need it, but if it persisted into the
# image every bare `aqua` call by the non-root runtime user would try to write
# root-owned /opt/aqua instead of ~/.local/share/aquaproj-aqua.
ARG AQUA_ROOT_DIR=/opt/aqua

COPY aqua.yaml aqua-checksums.json /opt/aqua/

# The last three lines are the smoke test. The gh version is asserted rather
# than just executed because aqua carries its own older gh for attestation
# checks and `aqua cp gh` falls back to that one when the pinned package fails.
RUN set -eux; \
    cd /tmp; \
    curl -sSfL -O "https://raw.githubusercontent.com/aquaproj/aqua-installer/${AQUA_INSTALLER_VERSION}/aqua-installer"; \
    echo "${AQUA_INSTALLER_SHA256}  aqua-installer" | sha256sum -c -; \
    chmod +x aqua-installer; \
    AQUA_DISABLE_SLSA=true ./aqua-installer -v "${AQUA_VERSION}"; \
    rm aqua-installer; \
    ln -s "${AQUA_ROOT_DIR}/bin/aqua" /usr/local/bin/aqua; \
    AQUA_DISABLE_SLSA=true aqua -c /opt/aqua/aqua.yaml cp -o /usr/local/bin gh uv; \
    rm -rf "${AQUA_ROOT_DIR}/pkgs"; \
    want="$(sed -n 's|.*- name: cli/cli@v\([0-9.]*\).*|\1|p' /opt/aqua/aqua.yaml)"; \
    test -n "${want}"; \
    gh --version | grep -qF "gh version ${want}"; \
    uv --version
