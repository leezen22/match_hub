Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
batchPath = files.BuildPath(files.GetParentFolderName(WScript.ScriptFullName), "daily_maintenance.bat")
exitCode = shell.Run(Chr(34) & batchPath & Chr(34), 7, True)
WScript.Quit exitCode
