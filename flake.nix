{
  description = "Development shell for rich-card";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    git-hooks = {
      url = "github:cachix/git-hooks.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, git-hooks, ... }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forEachSystem = f:
        nixpkgs.lib.genAttrs systems (system:
          f system (import nixpkgs { inherit system; }));
      updateGeneratedDocs = pkgs:
        pkgs.writeShellApplication {
          name = "update-rich-card-generated-docs";
          runtimeInputs = [
            pkgs.bat
            pkgs.prettier
            pkgs.uv
          ];
          text = ''
            if [ -n "''${NIX_BUILD_TOP:-}" ]; then
              case "$PWD" in
                "$NIX_BUILD_TOP"/*)
                  echo "Skipping generated README update in the Nix build sandbox; uv run requires Python discovery."
                  exit 0
                  ;;
              esac
            fi

            export UV_CACHE_DIR="''${UV_CACHE_DIR:-.uv-cache}"
            uv run python scripts/update_generated_docs.py
            prettier --write --prose-wrap always README.md
          '';
        };
      hookConfig = pkgs:
        let
          docsHook = updateGeneratedDocs pkgs;
          uvxHook = name: command:
            pkgs.writeShellScript name ''
              if [ -n "''${NIX_BUILD_TOP:-}" ]; then
                echo "Skipping ${name} in the Nix build sandbox; uvx hook requires network/cache access."
                exit 0
              fi

              export UV_PYTHON=${pkgs.python313}/bin/python3.13
              export PATH=${pkgs.lib.makeBinPath [ pkgs.coreutils pkgs.python313 pkgs.uv ]}
              exec ${command} "$@"
            '';
        in
        {
          default_stages = [
            "pre-commit"
            "commit-msg"
            "pre-push"
          ];
          excludes = [ "^(\\.cruft\\.json|\\.copier-answers\\.yml)$" ];

          hooks = {
            check-added-large-files.enable = true;
            check-case-conflicts.enable = true;
            check-merge-conflicts.enable = true;
            check-symlinks.enable = true;
            check-toml.enable = true;
            check-yaml = {
              enable = true;
              args = [ "--unsafe" ];
            };
            python-debug-statements.enable = true;
            detect-private-keys.enable = true;
            end-of-file-fixer.enable = true;
            fix-byte-order-marker.enable = true;
            mixed-line-endings = {
              enable = true;
              args = [ "--fix=auto" ];
            };
            trim-trailing-whitespace.enable = true;

            ruff = {
              enable = true;
              args = [ "--exit-non-zero-on-fix" ];
              types_or = [
                "python"
                "pyi"
              ];
              before = [ "ruff-format" ];
            };
            ruff-format = {
              enable = true;
              types_or = [
                "python"
                "pyi"
              ];
            };

            prettier = {
              enable = true;
              types_or = [
                "markdown"
                "html"
                "css"
                "scss"
                "javascript"
                "json"
              ];
              excludes = [ "^docs/.*\\.md$" ];
              settings.prose-wrap = "always";
            };

            codespell = {
              enable = true;
              package = pkgs.codespell;
              entry = "${pkgs.lib.getExe pkgs.codespell} --write-changes";
            };

            yamlfix = {
              enable = true;
              package = pkgs.yamlfix;
              entry = pkgs.lib.getExe pkgs.yamlfix;
              types = [ "yaml" ];
            };

            toml-sort-fix = {
              enable = true;
              name = "toml-sort-fix";
              package = pkgs.toml-sort;
              entry = "${pkgs.lib.getExe pkgs.toml-sort} --in-place";
              files = "\\.toml$";
              types = [ "toml" ];
            };

            betterleaks = {
              enable = true;
              package = pkgs.betterleaks;
              entry = "${pkgs.lib.getExe pkgs.betterleaks} git --pre-commit --staged --baseline-path=betterleaks-report.json";
              pass_filenames = false;
            };

            check-github-workflows = {
              enable = true;
              name = "check-github-workflows";
              package = pkgs.check-jsonschema;
              entry = "${pkgs.lib.getExe pkgs.check-jsonschema} --builtin-schema vendor.github-workflows";
              files = "^\\.github/workflows/.*\\.ya?ml$";
              types = [ "yaml" ];
            };

            check-dependabot = {
              enable = true;
              name = "check-dependabot";
              package = pkgs.check-jsonschema;
              entry = "${pkgs.lib.getExe pkgs.check-jsonschema} --builtin-schema vendor.dependabot";
              files = "^\\.github/dependabot\\.ya?ml$";
              types = [ "yaml" ];
            };

            shellcheck = {
              enable = true;
              excludes = [ "^\\.envrc$" ];
              types = [ "shell" ];
            };

            validate-pyproject = {
              enable = true;
              name = "validate-pyproject";
              package = pkgs.uv;
              entry = "${uvxHook "validate-pyproject-hook" "${pkgs.lib.getExe pkgs.uv}x --from validate-pyproject --with validate-pyproject-schema-store validate-pyproject pyproject.toml"}";
              pass_filenames = false;
              files = "^pyproject\\.toml$";
            };

            complexipy = {
              enable = true;
              name = "complexipy";
              package = pkgs.uv;
              entry = "${uvxHook "complexipy-hook" "${pkgs.lib.getExe pkgs.uv}x complexipy"}";
              types = [ "python" ];
            };

            deadcode = {
              enable = true;
              name = "deadcode";
              package = pkgs.uv;
              entry = "${uvxHook "deadcode-hook" "${pkgs.lib.getExe pkgs.uv}x deadcode"}";
              types = [ "python" ];
            };

            bandit = {
              enable = true;
              package = pkgs.bandit;
              entry = "${pkgs.lib.getExe' pkgs.bandit "bandit"} -c pyproject.toml";
              types = [ "python" ];
            };

            uv-audit = {
              enable = true;
              name = "uv audit";
              description = "Run 'uv audit' to check uv.lock dependencies for known vulnerabilities";
              package = pkgs.symlinkJoin {
                name = "uv-audit-env";
                paths = [
                  pkgs.python314
                  pkgs.uv
                ];
              };
              entry = "${pkgs.writeShellScript "uv-audit-hook" ''
                if [ -n "''${NIX_BUILD_TOP:-}" ]; then
                  echo "Skipping uv audit in the Nix build sandbox; OSV audit requires network."
                  exit 0
                fi

                export PATH=${pkgs.lib.makeBinPath [ pkgs.python314 pkgs.uv ]}
                exec ${pkgs.lib.getExe pkgs.uv} audit --preview-features audit --no-managed-python --python-version 3.14 --frozen
              ''}";
              pass_filenames = false;
              files = "^uv\\.lock$";
            };

            commitizen.enable = true;

            update-generated-docs = {
              enable = true;
              name = "update generated README";
              entry = "${docsHook}/bin/update-rich-card-generated-docs";
              language = "system";
              pass_filenames = false;
              always_run = true;
              after = [
                "ruff"
                "ruff-format"
                "prettier"
                "codespell"
                "toml-sort-fix"
              ];
            };
          };
        };
    in
    {
      formatter = forEachSystem (system: pkgs:
        let
          config = self.checks.${system}.pre-commit-check.config;
        in
        pkgs.writeShellApplication {
          name = "pre-commit-run";
          runtimeInputs = [ config.package ];
          text = ''
            pre-commit run --all-files --config ${config.configFile}
          '';
        });

      checks = forEachSystem (system: pkgs: {
        pre-commit-check = git-hooks.lib.${system}.run (
          {
            src = ./.;
          } // hookConfig pkgs
        );
      });

      devShells = forEachSystem (system: pkgs:
        let
          docsHook = updateGeneratedDocs pkgs;
        in
        {
          default = pkgs.mkShell {
            packages = [
              pkgs.python314
              pkgs.uv
              docsHook
            ] ++ self.checks.${system}.pre-commit-check.enabledPackages;

            shellHook = ''
              export UV_PROJECT_ENVIRONMENT=".venv"
              export UV_LINK_MODE="copy"
            '' + self.checks.${system}.pre-commit-check.shellHook;
          };
        });
    };
}
