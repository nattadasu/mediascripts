$code = Get-Content "./refresh_shell.cs" -Raw

Add-Type -MemberDefinition $code -Namespace WinAPI -Name Explorer

Function Set-FolderIcon {
    <#
    .DESCRIPTION
        This function sets the folder icon to folder.ico if it exists, otherwise it sets it to poster.ico.
        It also sets the folder to be a system folder so that the desktop.ini file is hidden.
    .PARAMETER Path
        The path to the folder to set the icon for. Defaults to the current directory.
    .EXAMPLE
        Set-FolderIcon
        Sets the folder icon for the current directory.
    .EXAMPLE
        Set-FolderIcon -Path 'C:\Users\John Doe\Downloads'
        Sets the folder icon for the Downloads folder.
    .NOTES
        THIS FUNCTION IS DESTRUCTIVE AND WILL MODIFY THE CONTENTS OF THE FOLDER'S DESKTOP.INI FILE.
    #>
    Param ($Path = '.')

    # Get all the subfolders in the given path
    $Folders = Get-ChildItem -Path $Path -Directory -Recurse

    # Loop through each folder
    ForEach ($Folder in $Folders) {
        # Check if the folder has a desktop.ini file
        $DesktopIni = Join-Path -Path $Folder.FullName -ChildPath 'desktop.ini'
        
        If (Test-Path -Path $DesktopIni) {
            Write-Host "Setting icon for $Folder" -ForegroundColor Yellow
            # Make the folder a system folder
            attrib +s $Folder.FullName
            
            # Read the content of the desktop.ini file
            $Content = Get-Content -Path $DesktopIni

            # Check if there's already a folder.ico in the directory
            $HasFolderIcon = Test-Path (Join-Path -Path $Folder.FullName -ChildPath 'folder.ico')
            $HasPosterIcon = Test-Path (Join-Path -Path $Folder.FullName -ChildPath 'poster.ico')
            If ($HasFolderIcon) {
                # Replace with folder.ico if it exists
                $Content = $Content -replace 'IconResource=poster.ico', 'IconResource=folder.ico'
                Write-Host "poster.ico -> folder.ico"
            } elseif ($HasPosterIcon) {
                $Content = $Content -replace 'IconResource=folder.ico', 'IconResource=poster.ico'
                Write-Host "folder.ico -> poster.ico"
            }
            Set-Content -Path $DesktopIni -Value $Content
            Write-Host "[SUCCESS] $Folder" -ForegroundColor Green
        } else {
            Write-Host "[ERROR] desktop.ini not found in $Folder" -ForegroundColor Red
        }
        # print - for 80 characters
        Write-Host ('=' * 80)
    }

    # Refresh the folder icons
    [WinAPI.Explorer]::Refresh()
}

Export-ModuleMember -Function Set-FolderIcon
