# git-sentinel build.ps1 - builds the Nuitka binary into
# dist\git-sentinel.exe
# Run from the project root directory.

param(
    # Which binary/binaries to build: console, gui, or all (default - used by
    # local/CONTRIBUTING.md runs). CI passes "console" or "gui" explicitly so
    # the two can build as separate, parallel jobs.
    [ValidateSet("console", "gui", "all")]
    [string]$Target = "all"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "ERROR: uv is not installed."
    Write-Error "       Install it from: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
}

if (-not (Test-Path "$ProjectRoot\pyproject.toml")) {
    Write-Error "ERROR: pyproject.toml not found in $ProjectRoot"
    exit 1
}

Write-Host "Syncing build dependencies..."
Set-Location $ProjectRoot
uv sync --group dev

Write-Host "Generating icon..."
uv run python scripts\gen-ico.py

New-Item -ItemType Directory -Force -Path "$ProjectRoot\dist" | Out-Null

$DataArgs = @(
    "--include-data-files=$ProjectRoot\README.md=data/README.md"
    "--include-data-files=$ProjectRoot\CHANGELOG.md=data/CHANGELOG.md"
    "--include-data-dir=$ProjectRoot\src\ui\webview\web=web"
)

if ($Target -eq "console" -or $Target -eq "all") {
    Write-Host "Building console binary (this may take a few minutes)..."
    uv run python -m nuitka `
        --onefile `
        --output-filename=git-sentinel.exe `
        --output-dir=build `
        --enable-plugin=pyside6 `
        --include-package=src.config.migrations `
        --assume-yes-for-downloads `
        --windows-icon-from-ico="$ProjectRoot\build\git-sentinel.ico" `
        @DataArgs `
        git-sentinel

    Copy-Item "$ProjectRoot\build\git-sentinel.exe" "$ProjectRoot\dist\git-sentinel.exe" -Force

    if (-not (Test-Path "$ProjectRoot\dist\git-sentinel.exe")) {
        Write-Error "ERROR: build failed - dist\git-sentinel.exe not found"
        exit 1
    }
}

if ($Target -eq "gui" -or $Target -eq "all") {
    Write-Host "Building windowed binary (this may take a few minutes)..."
    uv run python -m nuitka `
        --onefile `
        --output-filename=git-sentinel-gui.exe `
        --output-dir=build `
        --enable-plugin=pyside6 `
        --include-package=src.config.migrations `
        --assume-yes-for-downloads `
        --windows-icon-from-ico="$ProjectRoot\build\git-sentinel.ico" `
        --windows-console-mode=disable `
        @DataArgs `
        git-sentinel-gui

    Copy-Item "$ProjectRoot\build\git-sentinel-gui.exe" "$ProjectRoot\dist\git-sentinel-gui.exe" -Force

    if (-not (Test-Path "$ProjectRoot\dist\git-sentinel-gui.exe")) {
        Write-Error "ERROR: build failed - dist\git-sentinel-gui.exe not found"
        exit 1
    }
}

Write-Host "Build complete -> $ProjectRoot\dist"
