packages=(
    opam
    m4
    libffi-dev
)

apt-get install -y --no-install-recommends "${packages[@]}"
