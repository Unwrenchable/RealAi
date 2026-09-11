# Path to your exported CSV file
csvPath = "C:\Users\tsmit\copilot-activity-history.csv"

# Output folder for Markdown files
outputFolder = "C:\CopilotChats_MD"
New-Item -ItemType Directory -Force -Path $outputFolder | Out-Null

# Import CSV
$rows = Import-Csv $csvPath

# Group by conversation ID
$groups = $rows | Group-Object ConversationId

foreach ($group in $groups) {
    $conversationId = $group.Name
    $mdPath = Join-Path $outputFolder "$conversationId.md"

    # Start Markdown file
    $content = "# Copilot Chat — $conversationId`n"
    $content += "Generated from Windows Copilot Activity History`n`n"

    foreach ($row in $group.Group) {
        $timestamp = $row.Timestamp
        $speaker = if ($row.Role -eq "User") { "### You" } else { "### Copilot" }
        $message = $row.Message

        # Append each message
        $content += "$speaker — *$timestamp*`n"
        $content += "$message`n`n"
    }

    # Write the file
    Set-Content -Path $mdPath -Value $content -Encoding UTF8
}

Write-Host "Done! Markdown files saved to $outputFolder"
