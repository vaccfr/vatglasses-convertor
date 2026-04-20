{
  description = "Euroscope ESE to VATGlasses convertor";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      forAllSystems = nixpkgs.lib.genAttrs [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          python = pkgs.python3.withPackages (ps: with ps; [
            geojson
            requests
            pyyaml
            pip
          ]);
        in
        {
          default = pkgs.mkShell {
            packages = [ python ];
            shellHook = ''
              export PIP_PREFIX="$PWD/.pip"
              export PYTHONPATH="$PIP_PREFIX/${python.sitePackages}:$PYTHONPATH"
              export PATH="$PIP_PREFIX/bin:$PATH"
              mkdir -p "$PIP_PREFIX"
              if [ ! -d "$PIP_PREFIX/${python.sitePackages}/geojsonio" ]; then
                pip install --quiet geojsonio
              fi
            '';
          };
        }
      );
    };
}
