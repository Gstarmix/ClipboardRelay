Option Explicit
Dim sh, fso, scriptDir, relayPath, logPath, cmd
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
relayPath = fso.BuildPath(scriptDir, "relay.py")
logPath = fso.BuildPath(sh.ExpandEnvironmentStrings("%TEMP%"), "Clipboard_Relay.log")
If Not fso.FileExists(relayPath) Then
    MsgBox "relay.py introuvable dans " & scriptDir, vbCritical, "Clipboard Relay"
    WScript.Quit 1
End If
cmd = "cmd /c """"pythonw.exe"" """ & relayPath & """ > """ & logPath & """ 2>&1"""
sh.Run cmd, 0, False
WScript.Sleep 3000
Dim wmi, processes, alive, proc
Set wmi = GetObject("winmgmts:\\.\root\cimv2")
Set processes = wmi.ExecQuery("SELECT * FROM Win32_Process WHERE Name = 'pythonw.exe'")
alive = False
For Each proc In processes
    If Not IsNull(proc.CommandLine) Then
        If InStr(LCase(proc.CommandLine), "relay.py") > 0 Then
            alive = True
            Exit For
        End If
    End If
Next
If Not alive Then
    Dim logExists
    logExists = fso.FileExists(logPath)
    If logExists Then
        sh.Run "notepad.exe """ & logPath & """", 1, False
    End If
    MsgBox "Clipboard Relay a planté au boot." & vbCrLf & vbCrLf & _
           "Cause probable : pywin32 pas installé, ou port 5681 occupé." & vbCrLf & vbCrLf & _
           "Voir le log :" & vbCrLf & logPath & vbCrLf & vbCrLf & _
           "Pour debug interactif : lance start_relay_debug.bat", _
           vbExclamation, "Clipboard Relay - Crash"
End If