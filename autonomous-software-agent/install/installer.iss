#define MyAppName "Autonomous Software Agent"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Real Media Pro"
#define MyAppExeName "AutonomousSoftwareAgent.exe"

[Setup]
AppId={{C2B22B5C-11B4-4E3F-B423-3C9A33D94AF0}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\AutonomousSoftwareAgent
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
OutputDir=..\output
OutputBaseFilename=AutonomousSoftwareAgent-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\config.default.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--watch"
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--watch"; WorkingDir: "{app}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--watch"

[Run]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--notify-ready"; Flags: nowait postinstall skipifsilent
Filename: "{app}\{#MyAppExeName}"; Parameters: "--watch"; Flags: nowait postinstall skipifsilent
