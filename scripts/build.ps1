# git-sentinel build.ps1 - builds the Nuitka binary into
# dist\git-sentinel.exe
# Run from the project root directory.

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
)

# Python 3.14's official Windows build packs the Tcl/Tk script library into
# a zip appended to DLLs\tcl90.dll/tcl9tk90.dll (zipfs), a layout Nuitka's
# tk-inter plugin can't locate on its own (nuitka/nuitka#3993). Resolve the
# real files and hand them to Nuitka directly.
Write-Host "Locating Tcl/Tk libraries..."
$TclTkInfo = uv run python scripts\locate_tcl_tk.py | ConvertFrom-Json

$TclTkArgs = @()

if ((Get-Item $TclTkInfo.tcl).PSIsContainer) {
    $TclTkArgs += "--tcl-library-dir=$($TclTkInfo.tcl)"
} else {
    $TclZip = "$ProjectRoot\build\tcl_library.zip"
    Copy-Item $TclTkInfo.tcl $TclZip -Force
    $TclTkArgs += "--tcl-library-dir=$TclZip"
}

if ((Get-Item $TclTkInfo.tk).PSIsContainer) {
    $TclTkArgs += "--tk-library-dir=$($TclTkInfo.tk)"
} else {
    $TkZip = "$ProjectRoot\build\tk_library.zip"
    Copy-Item $TclTkInfo.tk $TkZip -Force
    $TclTkArgs += "--tk-library-dir=$TkZip"
}

Write-Host "Building console binary (this may take a few minutes)..."
uv run python -m nuitka `
    --onefile `
    --output-filename=git-sentinel.exe `
    --output-dir=build `
    --enable-plugin=tk-inter `
    --include-package=src.config.migrations `
    --assume-yes-for-downloads `
    --windows-icon-from-ico="$ProjectRoot\build\git-sentinel.ico" `
    @TclTkArgs `
    @DataArgs `
    git-sentinel

Copy-Item "$ProjectRoot\build\git-sentinel.exe" "$ProjectRoot\dist\git-sentinel.exe" -Force

if (-not (Test-Path "$ProjectRoot\dist\git-sentinel.exe")) {
    Write-Error "ERROR: build failed - dist\git-sentinel.exe not found"
    exit 1
}

Write-Host "Building windowed binary (this may take a few minutes)..."
uv run python -m nuitka `
    --onefile `
    --output-filename=git-sentinel-gui.exe `
    --output-dir=build `
    --enable-plugin=tk-inter `
    --include-package=src.config.migrations `
    --assume-yes-for-downloads `
    --windows-icon-from-ico="$ProjectRoot\build\git-sentinel.ico" `
    --windows-console-mode=disable `
    @TclTkArgs `
    @DataArgs `
    git-sentinel-gui

Copy-Item "$ProjectRoot\build\git-sentinel-gui.exe" "$ProjectRoot\dist\git-sentinel-gui.exe" -Force

if (-not (Test-Path "$ProjectRoot\dist\git-sentinel-gui.exe")) {
    Write-Error "ERROR: build failed - dist\git-sentinel-gui.exe not found"
    exit 1
}

Write-Host "Build complete -> $ProjectRoot\dist\git-sentinel.exe, $ProjectRoot\dist\git-sentinel-gui.exe"
