## Git Sentinel {{TAG}}

**Channel:** {{CHANNEL}}

### Install

Installation and uninstallation both use the same self-contained binary. Below
you will find instructions for each platform:

#### Linux

> [!NOTE]
> Make sure you are running under a desktop environment! TUI support will come
> in later releases.

> [!NOTE]
> Two Linux executables are provided - pick whichever suits how you plan to
> launch it, both install/uninstall/run the exact same way otherwise:
> - **`git-sentinel`** - install/uninstall/first-run print to whichever
>   terminal launched it; expects to be run from a terminal.
> - **`git-sentinel-gui`** - install/uninstall/first-run use a small window
>   instead of the terminal. Choose this one if you'll be launching it from a
>   file manager or app launcher rather than a terminal.

**Installation:**
1. Download the pre-compiled self-contained binary below from packages -
choose "Linux x86_64" for the terminal-driven build, or "Linux x86_64,
windowed" for the windowed build;
    ```bash
    curl -fL -o git-sentinel "https://gitlab.com/api/v4/projects/83160866/packages/generic/git-sentinel/{{TAG}}/git-sentinel"
    # or, for the windowed build:
    curl -fL -o git-sentinel-gui "https://gitlab.com/api/v4/projects/83160866/packages/generic/git-sentinel/{{TAG}}/git-sentinel-gui"
    ```
2. Mark it as executable;
    ```bash
    chmod +x git-sentinel
    # or
    chmod +x git-sentinel-gui
    ```
3. Run it directly - from a terminal (even a TTY) for `git-sentinel`, or by
launching `git-sentinel-gui` from a file manager or terminal. This will
install the application on your system.
    ```bash
    ./git-sentinel
    # or
    ./git-sentinel-gui
    ```

**Uninstallation:**
1. Run the installed binary with the `--uninstall` flag. If you don't remember
the install path, re-download the binary and run it with `--uninstall` instead -
it uninstalls the software either way.
    ```bash
    ~/.local/bin/git-sentinel --uninstall # could be different!
    # or
    chmod +x git-sentinel
    ./git-sentinel --uninstall
    ```

#### Windows

> [!NOTE]
> Two Windows executables are provided - pick whichever you prefer, both
> install/uninstall/run the exact same way otherwise:
> - **`git-sentinel.exe`** - shows a console window during
>   install/uninstall/first-run only; the daily scan itself always opens the
>   same GUI either way.
> - **`git-sentinel-gui.exe`** - never shows a console window at all;
>   install/uninstall/first-run use a small window instead. Choose this one
>   if you'd rather not see a terminal flash by.

> [!WARNING]
> The Windows binaries register themselves in the registry as uninstallable
> software and create a scheduled task on install. Simply deleting the
> binary will **not** remove either of these - you must uninstall it through
> the Windows apps manager or by running the binary with `--uninstall` flag,
> otherwise the registry keys and scheduled task will be left behind.

**Installation:**
1. Download the pre-compiled self-contained executable below from packages -
choose "Windows x86_64" for the console build, or "Windows x86_64, windowed"
for the GUI build;
    ```powershell
    curl.exe -fL -o git-sentinel.exe "https://gitlab.com/api/v4/projects/83160866/packages/generic/git-sentinel/{{TAG}}/git-sentinel.exe"
    # or, for the windowed build:
    curl.exe -fL -o git-sentinel-gui.exe "https://gitlab.com/api/v4/projects/83160866/packages/generic/git-sentinel/{{TAG}}/git-sentinel-gui.exe"
    ```
2. Execute the binary like any other program - it installs itself
automatically the first time you run it. You can also run it from
PowerShell or Command Prompt, though it isn't necessary.
    ```powershell
    .\git-sentinel.exe
    # or
    .\git-sentinel-gui.exe
    ```

**Uninstallation:**
1. Run the installed binary with the `--uninstall` flag. By default it lives
here (same folder for either variant):
    ```powershell
    & "$env:LOCALAPPDATA\Programs\git-sentinel\git-sentinel.exe" --uninstall
    # or
    & "$env:LOCALAPPDATA\Programs\git-sentinel\git-sentinel-gui.exe" --uninstall
    ```
2. If you don't remember the install path, re-download the executable and run
it with `--uninstall` instead:
    ```powershell
    curl.exe -fL -o git-sentinel.exe "https://gitlab.com/api/v4/projects/83160866/packages/generic/git-sentinel/{{TAG}}/git-sentinel.exe"
    .\git-sentinel.exe --uninstall
    ```
3. Or uninstall it the usual Windows way: via **Settings → Apps → Installed Apps** or
**Control Panel → Programs and Features**.

On first run the binary detects it is not installed and sets itself up
automatically. To force a reinstall or update, run whichever variant you
downloaded with `--install` (e.g. `git-sentinel --install` or
`git-sentinel-gui.exe --install`). Uninstall the same way, with `--uninstall`
instead.
