# Define the folder path and the file extension to process
$FolderPath = Read-Host -Prompt "Please input the target/working directory (default: .)"
if (-not $FolderPath) { $FolderPath = "." }
$FileExtension = "*.lrc"

# Loop through all files in the folder and its subfolders
Get-ChildItem -Path $FolderPath -Filter $FileExtension -Recurse | ForEach-Object {
    # Get the content of the file as a byte array
    $Content = [System.IO.File]::ReadAllBytes($_.FullName)
    # Check if the file has LF-only line endings
    if ($Content -notcontains 13) {
        # Convert the byte array to a string with UTF-8 encoding
        $Text = [System.Text.Encoding]::UTF8.GetString($Content)
        # Replace LF with CRLF
        $Text = $Text -replace "`n", "`r`n"
        # Convert the string back to a byte array with UTF-8 encoding
        $Content = [System.Text.Encoding]::UTF8.GetBytes($Text)
        # Write the byte array back to the file
        [System.IO.File]::WriteAllBytes($_.FullName, $Content)
        # Write a message to the console
        Write-Host "Converted file: $($_.FullName)"
    }
}
