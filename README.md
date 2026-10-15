# AutoShutdowner

A small Windows desktop app for scheduling a daily shutdown at a chosen local time.

## Features
- Daily shutdown time in 24-hour `HH:MM` format.
- Save settings in `%APPDATA%\AutoShutdowner\settings.json`.
- Optional launch at Windows sign-in (current user).
- 60-second warning before scheduled shutdown.
- Test shutdown and cancel-pending-shutdown controls.
- GitHub Actions workflow builds separate 32-bit (`x86`) and 64-bit (`x64`) Windows EXEs.

## Important behavior
- This is a **daily clock-time schedule**, not a one-time date/time appointment.
- The computer must be powered on and awake at the scheduled time.
- If the app starts after today's scheduled time, it waits until the next day instead of immediately shutting down.
- Windows shutdown closes apps and may cause unsaved work to be lost. Save work first.
- Startup is registered for the current Windows user, not all users.
- Do not use the test button unless you are ready for Windows to shut down in 60 seconds.

## Build locally on Windows
Open Command Prompt in this folder:
```bat
py -m pip install --upgrade pip pyinstaller
py -m PyInstaller --noconfirm --clean --onefile --windowed --name AutoShutdowner app.py
```
The EXE will be in `dist\AutoShutdowner.exe`. Build on the desired architecture for the most reliable result.

## Build both architectures using GitHub
1. Create a GitHub repository and upload these files.
2. Commit the default branch as `main`.
3. Open **Actions** → **Build Windows EXE** → **Run workflow**.
4. After the workflow finishes, open its run and download the `AutoShutdowner-x86` and `AutoShutdowner-x64` artifacts.
5. Extract each artifact ZIP to get the matching `.exe`.

The workflow uses GitHub-hosted Windows runners and `actions/setup-python` to select x86 and x64 Python. If GitHub's runner image no longer provides one architecture, update the Python/architecture combination in the workflow.

## Security note
The app uses the standard Windows `shutdown` command and a per-user startup registry entry. Review the source code before running it.
