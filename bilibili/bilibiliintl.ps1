Function Get-LatestBiliBiliRelease {
    [CmdletBinding()]
    Param (
        # Enumeration of day of week
        [ValidateSet("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")]
        [string]$Day = (Get-Date).DayOfWeek
    )

    Write-Verbose "Getting latest release of Bilibili International on $Day"
    $url = "https://api.bilibili.tv/intl/gateway/web/v2/anime/timeline?s_locale=en_US&platform=web"
    $resp = Invoke-RestMethod -Uri $url -Method Get -ContentType "application/json"
    $dataarr = $resp.data.items
    Write-Verbose "Filtering releases for $Day"
    $data = $dataarr | Where-Object { $_.full_day_of_week -eq $Day } | Select-Object -First 1
    # select any items that with regex of updated$ on index_show key
    $rel = $data.cards | Where-Object { $_.index_show -match "updated$" }
    $unrel = $data.cards | Where-Object { $_.index_show -notmatch "updated$" }
    Write-Verbose "Returning releases"
    @"
Here is the latest release of Bilibili International, on $Day.

"@
    for ($i = 0; $i -lt $rel.Count; $i++) {
        "$($i+1)) $($rel[$i].title) - $($rel[$i].index_show -replace ' updated', '')"
    }
    @"

q) Quit (or Ctrl+C to quit)
"@

    If ($unrel.Count -gt 0) {
        @"

Here are the unreleased episodes of Bilibili International.
Right now, the current time is $(Get-Date -Format "HH:mm").
"@
        $final = @()
        for ($i = 0; $i -lt $unrel.Count; $i++) {
            $info = $unrel[$i].index_show
            # example of $info = E6 update 23:30
            # grab the episode number
            $episode = [regex]::Match($info, "E([\d\-]+)").Groups[1].Value
            # grab the time
            $time = [regex]::Match($info, "update ([\d:]+)").Groups[1].Value
            $final += "[${time}] $($unrel[$i].title) - E$episode"
        }
        $final = $final | Sort-Object

        for ($i = 0; $i -lt $final.Count; $i++) {
            "$($final[$i])"
        }
    }

    @"

To download, input the number of the release you want to download. We'll ask you again if you want to download more than one release.
"@
    Write-Verbose "Waiting for user input"
    Do {
        $uinput = Read-Host "Which release do you want to download?"
        if ($uinput -eq "q") {
            Write-Verbose "User quit"
            return
        }
        if ($uinput -gt $rel.Count) {
            Write-Verbose "Invalid input"
            Write-Host "Invalid input. Please try again."
        }
    } Until ($uinput -le $rel.Count)
    $uinput = [int]$uinput
    $uinput -= 1
    $item = $rel[$uinput]

    # check if working dir on ~/Videos, else set it to ~/Videos
    If ((Get-Location) -ne "${env:USERPROFILE}\Videos\Bilibili") {
        Set-Location "${env:USERPROFILE}\Videos\Bilibili"
    }

    # set location to title of the release, if it doesn't exist, create it
    If (-not (Test-Path $item.title)) {
        New-Item -ItemType Directory -Path $item.title
        # create dummy file in the directory
        New-Item -ItemType File -Path "$(Get-Location)\$($item.title)\.keep" -Force -Value "" -InformationAction SilentlyContinue -ProgressAction SilentlyContinue
    }

    Set-Location $item.title
    Write-Verbose "Downloading release"
    $durl = "https://www.bilibili.tv/en/play/$($item.season_id)/$($item.episode_id)"

    # download video
    Download-BilibiliVideo -Url $durl
    Set-Location ..
    Write-Verbose "Download complete"
    Write-Host "Download complete. Do you want to download another release?"
    $uinput = Read-Host "y/n"
    if ($uinput -eq "y") {
        Get-LatestBiliBiliRelease -Day $Day
    }
    return
}
