const vscode = require('vscode')
const path = require('path')
const fs = require('fs')
const fsPromises = require('fs').promises
const polka = require('polka')
const { json } = require('body-parser')
const nodeFetch = require('node-fetch')
const { v4: uuidv4 } = require('uuid')
const DiffManager = require('../DiffManager')
const ChatSidebarProvider = require('../ChatSidebarProvider')
const language = require('../utils/language.js')
const isUUID = require('../utils/isUUID')
const { openExternalView } = require('../utils/nextjs_webview.js')
const { getSession } = require('../utils/distinctId')
const state = require('../state')
const { notify } = require('../utils/notify')
const { log, chatLog } = require('../loggers')
const { getIdeDiagnostics: _getIdeDiagnostics } = require('../utils/diagnostics')
const { getOrCreatePtyController: _getOrCreatePtyController } = require('../utils/terminal/pty')

const fetch = async (url, options) => {
  try {
    return await nodeFetch(url, options)
  } catch (error) {
    console.error('Error al realizar la solicitud:', error)
    throw error
  }
}

/**
 * Create the polka-based extension driver.
 * @param {Object} deps
 * @param {() => string|undefined} deps.getWorkspaceRoot
 * @param {boolean} deps.hasWorkspace
 * @returns {(context: import('vscode').ExtensionContext) => Promise<void>}
 */
function createDriver(deps) {
  const { getWorkspaceRoot, hasWorkspace } = deps

  const getIdeDiagnostics = (filePath) => _getIdeDiagnostics(filePath, getWorkspaceRoot)
  const getOrCreatePtyController = (name, shellHint) =>
    _getOrCreatePtyController(name, shellHint, getWorkspaceRoot)

  const {
    getProjectStructure,
    openFile,
    readFileContent,
    formatClosedDocument,
    writeFileContent,
    createFolder,
    deleteFile,
    getAllPathsFromProject,
    resolveWorkspacePath
  } = require('../utils/fs')(getWorkspaceRoot)

  const vscodeDriver = async (context) => {
    const app = polka()

    app.use((req, res, next) => {
      res.setHeader('Access-Control-Allow-Origin', '*')
      res.setHeader('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept')
      next()
    })

    app.use(json({ limit: '10mb' }))

    app.post('/showErrorMessage', async (req, res) => {
      const { message } = req.body
      // vscode.window.showErrorMessage(message);
      notify(message, 'error')
      res.end()
    })

    app.post('/showWarningMessage', async (req, res) => {
      const { message } = req.body
      vscode.window.showWarningMessage(message)
      res.end()
    })

    app.post('/showInformationMessage', async (req, res) => {
      const { message } = req.body
      vscode.window.showInformationMessage(message)
      res.end()
    })

    app.post('/executeCommand', async (req, res) => {
      const { command } = req.body

      if (!getWorkspaceRoot()) {
        res.end(
          JSON.stringify({
            ok: false,
            error:
            'No workspace is currently open. Please open a folder or workspace to use CodeGPT features.'
          })
        )
        return
      }

      vscode.commands.executeCommand(command)
      res.end()
    })

    app.get('/language', async (req, res) => {
      const { activeTextEditor } = vscode.window
      if (activeTextEditor) {
        const { document } = activeTextEditor
        const { languageId } = document
        res.end(languageId)
      } else {
        res.end('')
      }
    })

    app.get('/filename', async (req, res) => {
    // Fall back to the most recent visible editor when the webview steals
    // focus and activeTextEditor goes undefined.
      const editor =
      vscode.window.activeTextEditor ||
      vscode.window.visibleTextEditors.find((e) => e.document.uri.scheme === 'file')
      if (editor) {
        res.end(path.basename(editor.document.fileName))
      } else {
        res.end('')
      }
    })

    app.get('/isAnonymous', async (req, res) => {
      let isAnonymous = true
      try {
        const session = await getSession()
        const accessToken = JSON.parse(session)?.accessToken
        if (accessToken) {
          isAnonymous = false
        }
      } catch (e) {
        isAnonymous = true
      }
      res.end(isAnonymous.toString())
    })

    app.get('/ideLanguage', async (req, res) => {
      const language = vscode.env.language
      const localesMap = {
        en: 'English',
        'zh-cn': 'Simplified_Chinese',
        'zh-tw': 'Traditional_Chinese',
        fr: 'French',
        de: 'German',
        it: 'Italian',
        es: 'Spanish',
        ja: 'Japanese',
        ko: 'Korean',
        ru: 'Russian',
        'pt-br': 'Portuguese',
        tr: 'Turkish',
        pl: 'Polish',
        cs: 'Czech',
        hu: 'Hungarian'
      }
      res.end(localesMap[language] ?? 'English')
    })

    app.post('/insertCode', async (req, res) => {
      const { code } = req.body
      const { activeTextEditor } = vscode.window
      // console.log({ activeTextEditor })
      if (activeTextEditor) {
        const { selection } = activeTextEditor
        activeTextEditor.edit((editBuilder) => {
          editBuilder.replace(selection, code)
        })
      }
      vscode.commands.executeCommand('editor.action.format')
      res.end()
    })

    app.post('/insertCodeInTerminal', async (req, res) => {
      const { code } = req.body
      let terminal = vscode.window.activeTerminal
      if (!terminal) {
        terminal = vscode.window.createTerminal()
      }
      terminal.show()
      terminal.sendText(code.trimEnd(), false)
      res.end()
    })

    app.post('/newFileWithCode', async (req, res) => {
      const { code } = req.body
      const newDocument = await vscode.workspace.openTextDocument({
        content: '',
        language: ''
      })
      await vscode.window.showTextDocument(newDocument)
      const { activeTextEditor } = vscode.window
      if (activeTextEditor) {
        const { selection } = activeTextEditor
        activeTextEditor.edit((editBuilder) => {
          editBuilder.replace(selection, code)
        })
      }
      res.end()
    })

    app.get('/getSelectedText', async (req, res) => {
      let selectedText = ''
      const { activeTextEditor } = vscode.window
      if (activeTextEditor) {
        const { document } = activeTextEditor

        const { selection } = activeTextEditor
        selectedText = document.getText(selection)
      } else {
        console.log('No active text editor found.')
      }
      res.end(selectedText)
    })

    app.get('/getSelectedText/full', async (req, res) => {
      console.log('getSelectedText/full')
      if (!vscode.window.activeTextEditor) {
        res.end(JSON.stringify({ ok: false, error: 'No active text editor.' }))
        console.log('No active text editor found.')
        return
      }
      const selection = vscode.window.activeTextEditor.selection
      const selectedText = vscode.window.activeTextEditor.document.getText(selection)
      const fullFileText = vscode.window.activeTextEditor.document.getText()
      const sendFullText = Boolean(selectedText)
      res.end(
        JSON.stringify({
          ok: true,
          selectedText: selectedText || fullFileText,
          fileName: path.basename(vscode.window.activeTextEditor.document.fileName),
          language: vscode.window.activeTextEditor.document.languageId,
          ...(sendFullText
            ? {
                from: vscode.window.activeTextEditor.selection.start,
                to: vscode.window.activeTextEditor.selection.end,
                lines: vscode.window.activeTextEditor.document.lineCount,
                lineAt: vscode.window.activeTextEditor.document.lineAt(selection.active)
              }
            : {})
        })
      )
    })

    app.post('/secrets', async (req, res) => {
      const { key, value } = req.body
      await context.secrets.store(key, value)
      res.end()
    })

    app.delete('/secret/:id', async (req, res) => {
      const { id } = req.params
      await context.secrets.delete(id)
      res.end()
    })

    app.post('/globalState', async (req, res) => {
      const { key, value } = req.body
      await context.globalState.update(key, value)
      res.end()
    })

    app.delete('/globalState/:id', async (req, res) => {
      const { id } = req.params
      await context.globalState.update(id, '')
      res.end()
    })

    app.post('/config', async (req, res) => {
      const { key, value } = req.body
      console.log({
        key,
        value
      })
      if (hasWorkspace) {
        await vscode.workspace
          .getConfiguration()
          .update(key, value, vscode.ConfigurationTarget.Workspace)
      } else {
        if (key === 'CodeGPT.apiKey') {
          state.provider = value
        }
      }
      res.end()
    })

    app.post('/copy', async (req, res) => {
      const { code } = req.body
      vscode.env.clipboard.writeText(code)
      console.log('copied', code)
      res.end()
    })

    app.get('/paste', async (req, res) => {
      const code = await vscode.env.clipboard.readText()
      console.log('pasted', code)
      res.end(code)
    })

    app.get('/pasteImage', async (req, res) => {
      try {
        const { execFile } = require('child_process')
        const os = require('os')
        const fs = require('fs')
        const path = require('path')

        const tmpFile = path.join(os.tmpdir(), `codegpt-clip-${Date.now()}.png`)

        const runCmd = (cmd, args) =>
          new Promise((resolve) => {
            execFile(cmd, args, { timeout: 5000 }, (error) => resolve(!error))
          })

        let ok = false
        if (process.platform === 'darwin') {
        // osascript: si el clipboard tiene una imagen la guarda en un PNG; si no, error.
          const script = `try
  set png_data to the clipboard as «class PNGf»
  set fp to open for access POSIX file ${JSON.stringify(tmpFile)} with write permission
  write png_data to fp
  close access fp
on error errMsg
  try
    close access POSIX file ${JSON.stringify(tmpFile)}
  end try
  return "no_image"
end try`
          ok = await runCmd('osascript', ['-e', script])
        } else if (process.platform === 'win32') {
          const ps = `Add-Type -AssemblyName System.Windows.Forms; $img = [System.Windows.Forms.Clipboard]::GetImage(); if ($img -ne $null) { $img.Save(${JSON.stringify(tmpFile)}, [System.Drawing.Imaging.ImageFormat]::Png) } else { exit 1 }`
          ok = await runCmd('powershell.exe', ['-NoProfile', '-Command', ps])
        } else {
        // Linux: requiere xclip o wl-paste. Probamos xclip primero.
          ok = await runCmd('xclip', ['-selection', 'clipboard', '-t', 'image/png', '-o', '-o', tmpFile])
          if (!ok) {
            ok = await runCmd('wl-paste', ['--type', 'image/png', '-o', tmpFile])
          }
        }

        if (!ok || !fs.existsSync(tmpFile) || fs.statSync(tmpFile).size === 0) {
          try { fs.unlinkSync(tmpFile) } catch (_) {}
          res.statusCode = 204
          res.end()
          return
        }

        const buf = fs.readFileSync(tmpFile)
        try { fs.unlinkSync(tmpFile) } catch (_) {}
        const dataUrl = `data:image/png;base64,${buf.toString('base64')}`
        res.setHeader('Content-Type', 'application/json')
        res.end(JSON.stringify({ dataUrl }))
      } catch (e) {
        console.error('pasteImage error', e)
        res.statusCode = 500
        res.end(JSON.stringify({ error: e.message }))
      }
    })

    app.post('/openUrl', async (req, res) => {
      const { url } = req.body
      vscode.env.openExternal(vscode.Uri.parse(url))
      res.end()
    })

    app.get('/version', async (req, res) => {
      const codeGPTVersion = context.extension.packageJSON.version
      res.end(codeGPTVersion)
    })

    app.post('/autocompleteEnabled', async (req, res) => {
      const { value } = req.body
      await context.globalState.update('autocompleteEnabled', value)
      res.end()
    })

    app.post('/model', async (req, res) => {
      const { model, fromMarketplace, provider } = req.body
      await context.globalState.update(`${provider}_model`, { model, fromMarketplace })
      console.log({ model, fromMarketplace, provider })
      res.end()
    })

    app.post('/openWebviewUrl', async (req, res) => {
      const { url } = req.body
      openExternalView(url)
      res.end()
    })

    app.post('/changeIframeUrl', async (req, res) => {
      const { url } = req.body
      console.log({ body: req.body })
      const chatSidebarProvider = ChatSidebarProvider.getChatInstance(context)
      chatSidebarProvider.changeUrl(url)
      res.end()
    })

    app.get('/getProjectStructure', async (req, res) => {
      if (!getWorkspaceRoot()) {
        res.end(
          JSON.stringify({
            ok: false,
            error:
            'No workspace is currently open. Please open a folder or workspace to use CodeGPT features.'
          })
        )
        return
      }

      const projectStructure = await getProjectStructure()

      if (!projectStructure || projectStructure.length === 0) {
        res.end(JSON.stringify({ ok: false, error: 'No project found.' }))
        return
      }

      res.end(JSON.stringify(projectStructure))
    })

    app.get('/openFolder', async (req, res) => {
      await vscode.commands.executeCommand('vscode.openFolder')
      res.end(JSON.stringify({ ok: true }))
    })

    app.get('/workspaceFolder', async (req, res) => {
      const workspaceFolder = vscode?.workspace?.workspaceFolders?.[0]?.uri?.fsPath
      if (!workspaceFolder) {
        res.end(
          JSON.stringify({
            ok: false,
            error:
            'No workspace is currently open. Please open a folder or workspace to use CodeGPT features.'
          })
        )
        return
      }
      res.end(workspaceFolder)
    })

    app.get('/getFileContent', async (req, res) => {
      if (!getWorkspaceRoot() && !vscode.window.activeTextEditor) {
        res.statusCode = 400
        res.end(
          JSON.stringify({
            ok: false,
            error:
            'No workspace is currently open. Please open a folder or workspace to use CodeGPT features.'
          })
        )
        return
      }

      const { filePath, from, to } = req.query

      // Decode URL-encoded paths (URLSearchParams encodes spaces/accents) and
      // normalize to NFC so macOS NFD filenames compare correctly downstream.
      const decodedFilePath = filePath
        ? decodeURIComponent(filePath).normalize('NFC')
        : filePath

      // No path → fall back to the active editor's content (legacy behaviour).
      if (!decodedFilePath) {
        if (!vscode.window.activeTextEditor) {
          res.statusCode = 400
          res.end(
            JSON.stringify({
              ok: false,
              error: 'No active editor and no filePath provided'
            })
          )
          return
        }
        res.end(vscode.window.activeTextEditor.document.getText())
        return
      }

      const resolved = await resolveWorkspacePath(decodedFilePath)
      if (!resolved.ok) {
        res.statusCode = resolved.status
        res.end(
          JSON.stringify({
            ok: false,
            error: resolved.error,
            ...(resolved.suggestions ? { suggestions: resolved.suggestions } : {})
          })
        )
        return
      }

      const fileContent = await readFileContent(resolved.absolutePath, from, to)
      res.end(fileContent)
    })

    app.post('/grepSearch', async (req, res) => {
      if (!getWorkspaceRoot()) {
        res.end(JSON.stringify({ ok: false, error: 'No workspace is currently open.' }))
        return
      }

      const { pattern, include, maxResults } = req.body
      if (!pattern) {
        res.end(JSON.stringify({ ok: false, error: 'Missing required parameter: pattern' }))
        return
      }

      const workspaceRoot = getWorkspaceRoot()
      const limit = Math.min(maxResults || 50, 300)

      try {
        const { spawn } = require('child_process')

        // Try VS Code's bundled ripgrep first
        let rgPath
        const rgBinName = process.platform === 'win32' ? 'rg.exe' : 'rg'
        try {
          const rgModule = path.join(vscode.env.appRoot, 'node_modules', '@vscode', 'ripgrep', 'bin', rgBinName)
          require('fs').accessSync(rgModule)
          rgPath = rgModule
        } catch {
          rgPath = rgBinName // Fallback to system ripgrep
        }

        const args = [
          '-i',
          '--json',
          '-e', pattern,
          '-C', '1',
          '-m', String(limit),
          '--max-filesize', '256K',
          ...(include ? ['--glob', include] : []),
          '--glob', '!node_modules',
          '--glob', '!.git',
          '--glob', '!dist',
          '--glob', '!build',
          '--glob', '!.next',
          '--glob', '!coverage',
          workspaceRoot
        ]

        const rg = spawn(rgPath, args, { timeout: 30000 })

        let output = ''
        let lineCount = 0
        const maxLines = limit * 5
        const MAX_BYTES = 256 * 1024

        rg.stdout.on('data', (data) => {
          if (output.length < MAX_BYTES) {
            const text = data.toString()
            const lines = text.split('\n')
            for (const line of lines) {
              if (lineCount >= maxLines || output.length >= MAX_BYTES) {
                rg.kill()
                break
              }
              output += line + '\n'
              lineCount++
            }
          } else {
            rg.kill()
          }
        })

        let stderr = ''
        rg.stderr.on('data', (data) => {
          stderr += data.toString()
        })

        rg.on('close', (code) => {
          try {
          // Parse ripgrep JSON output into grouped results
            const results = []
            let currentFile = null
            const jsonLines = output.split('\n').filter(Boolean)

            for (const line of jsonLines) {
              try {
                const parsed = JSON.parse(line)
                if (parsed.type === 'match') {
                  const filePath = path.relative(workspaceRoot, parsed.data.path.text)
                  const lineNum = parsed.data.line_number
                  const lineText = parsed.data.lines.text.replace(/\n$/, '')
                  if (currentFile !== filePath) {
                    currentFile = filePath
                    results.push({ file: filePath, matches: [] })
                  }
                  const last = results[results.length - 1]
                  if (last) last.matches.push({ line: lineNum, text: lineText })
                } else if (parsed.type === 'context' && results.length > 0) {
                  const lineNum = parsed.data.line_number
                  const lineText = parsed.data.lines.text.replace(/\n$/, '')
                  const last = results[results.length - 1]
                  if (last) last.matches.push({ line: lineNum, text: lineText, isContext: true })
                }
              } catch {
              // Skip malformed JSON lines
              }
            }

            // Format for LLM consumption
            const totalMatches = results.reduce((sum, r) => sum + r.matches.filter(m => !m.isContext).length, 0)
            let formatted = `Found ${totalMatches} results for "${pattern}"\n`

            for (const result of results) {
              formatted += `\n${result.file}\n`
              for (const match of result.matches) {
                formatted += `  ${String(match.line).padStart(5)}: ${match.text}\n`
              }
            }

            if (output.length >= MAX_BYTES) {
              formatted += '\n[... results truncated due to size limit]'
            }

            res.end(JSON.stringify({ ok: true, results: formatted, count: totalMatches }))
          } catch (parseError) {
            res.end(JSON.stringify({ ok: false, error: `Failed to parse results: ${parseError}` }))
          }
        })

        rg.on('error', (err) => {
        // ripgrep not found — fallback to grep
          const grepArgs = ['-rn', '-i', '--include=' + (include || '*'), pattern, workspaceRoot]
          const grepProcess = spawn('grep', grepArgs, { timeout: 30000 })
          let grepOutput = ''

          grepProcess.stdout.on('data', (data) => {
            if (grepOutput.length < MAX_BYTES) grepOutput += data.toString()
          })

          grepProcess.on('close', () => {
            const lines = grepOutput.split('\n').filter(Boolean).slice(0, limit)
            const formatted = `Found ${lines.length} results for "${pattern}" (via grep fallback)\n\n` +
            lines.map(l => {
              const rel = l.replace(workspaceRoot + '/', '')
              return `  ${rel}`
            }).join('\n')
            res.end(JSON.stringify({ ok: true, results: formatted, count: lines.length }))
          })

          grepProcess.on('error', () => {
            res.end(JSON.stringify({ ok: false, error: 'Neither ripgrep nor grep available on this system' }))
          })
        })
      } catch (error) {
        res.end(JSON.stringify({ ok: false, error: `Search failed: ${error}` }))
      }
    })

    app.get('/listCodeDefinitions', async (req, res) => {
      if (!getWorkspaceRoot()) {
        console.log('[listCodeDefinitions]  No workspace is currently open.')

        res.end(JSON.stringify({ ok: false, error: 'No workspace is currently open.' }))
        return
      }

      const { filePath } = req.query
      if (!filePath) {
        console.log('[listCodeDefinitions] Missing required parameter: filePath')
        res.end(JSON.stringify({ ok: false, error: 'Missing required parameter: filePath' }))
        return
      }

      try {
        const absolutePath = path.isAbsolute(filePath)
          ? filePath
          : path.join(getWorkspaceRoot(), filePath)
        const uri = vscode.Uri.file(absolutePath)

        // Ensure the file is recognized by VS Code
        let doc
        try {
          doc = await vscode.workspace.openTextDocument(uri)
        } catch (openErr) {
          console.error('[listCodeDefinitions] Could not open file:', filePath, openErr)
          res.end(JSON.stringify({ ok: false, error: `Could not open file: ${filePath}` }))
          return
        }

        // Try to get symbols with retries (language server may need time to activate)
        let symbols = null
        for (let attempt = 0; attempt < 3; attempt++) {
          symbols = await vscode.commands.executeCommand(
            'vscode.executeDocumentSymbolProvider',
            uri
          )
          if (symbols && symbols.length > 0) break
          // Wait progressively longer between retries
          await new Promise((resolve) => setTimeout(resolve, 300 * (attempt + 1)))
        }

        if (!symbols || !Array.isArray(symbols) || symbols.length === 0) {
        // Fallback: extract basic definitions by reading the document text
          const text = doc.getText()
          const lines = text.split('\n')
          let fallbackResult = `Definitions in ${filePath} (basic scan):\n\n`
          let defCount = 0
          const defPatterns = [
            /^(?:export\s+)?(?:async\s+)?function\s+(\w+)/,
            /^(?:export\s+)?class\s+(\w+)/,
            /^(?:export\s+)?interface\s+(\w+)/,
            /^(?:export\s+)?(?:type)\s+(\w+)\s*=/,
            /^(?:export\s+)?enum\s+(\w+)/,
            /^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(/,
            /^\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*[:{]/
          ]

          for (let i = 0; i < lines.length && defCount < 50; i++) {
            const trimmed = lines[i].trimStart()
            for (const pattern of defPatterns) {
              const match = trimmed.match(pattern)
              if (match) {
                fallbackResult += `  [${i + 1}] ${lines[i].trim()}\n`
                defCount++
                break
              }
            }
          }

          if (defCount === 0) {
            fallbackResult = `No definitions found in ${filePath}`
          }

          res.end(JSON.stringify({ ok: true, result: fallbackResult }))
          return
        }

        const RELEVANT_KINDS = new Set([
          vscode.SymbolKind.Class,
          vscode.SymbolKind.Function,
          vscode.SymbolKind.Method,
          vscode.SymbolKind.Interface,
          vscode.SymbolKind.Enum,
          vscode.SymbolKind.Struct,
          vscode.SymbolKind.Constructor,
          vscode.SymbolKind.Property,
          vscode.SymbolKind.Variable,
          vscode.SymbolKind.Constant,
          vscode.SymbolKind.TypeParameter
        ])

        const SYMBOL_KIND_NAMES = {
          [vscode.SymbolKind.Class]: 'class',
          [vscode.SymbolKind.Function]: 'function',
          [vscode.SymbolKind.Method]: 'method',
          [vscode.SymbolKind.Interface]: 'interface',
          [vscode.SymbolKind.Enum]: 'enum',
          [vscode.SymbolKind.Struct]: 'struct',
          [vscode.SymbolKind.Constructor]: 'constructor',
          [vscode.SymbolKind.Property]: 'property',
          [vscode.SymbolKind.Variable]: 'variable',
          [vscode.SymbolKind.Constant]: 'constant',
          [vscode.SymbolKind.TypeParameter]: 'type'
        }

        const MAX_DEFINITIONS = 50
        const MAX_DEPTH = 3
        let count = 0

        function formatSymbols(symbolList, depth) {
          let output = ''
          const indent = '  '.repeat(depth)

          for (const symbol of symbolList) {
            if (count >= MAX_DEFINITIONS) break
            if (!RELEVANT_KINDS.has(symbol.kind)) continue

            const kindName = SYMBOL_KIND_NAMES[symbol.kind] || 'symbol'
            const startLine = (symbol.range?.start?.line ?? 0) + 1
            const endLine = (symbol.range?.end?.line ?? 0) + 1

            let signatureLine = ''
            try {
              signatureLine = doc.lineAt(symbol.range.start.line).text.trim()
            } catch {
              signatureLine = symbol.name
            }

            output += `${indent}${kindName} ${symbol.name} [${startLine}-${endLine}]\n`
            output += `${indent}  ${signatureLine}\n`
            count++

            if (symbol.children && symbol.children.length > 0 && depth < MAX_DEPTH) {
              output += formatSymbols(symbol.children, depth + 1)
            }
          }

          return output
        }

        const result = `Definitions in ${filePath}:\n\n` + formatSymbols(symbols, 0)
        res.end(JSON.stringify({ ok: true, result }))
      } catch (error) {
        console.error('[listCodeDefinitions] Error:', error)
        res.end(JSON.stringify({ ok: false, error: `Failed to list definitions: ${error?.message || error}` }))
      }
    })

    app.get('/cleanCache', async (req, res) => {
      console.log('reset cache')
      await context.globalState.update('resetCache', true)
      res.end()
    })

    app.get('/getAllPathsFromProject', async (req, res) => {
      const paths = await getAllPathsFromProject()
      res.end(JSON.stringify(paths))
    })

    app.post('/writeFileContent', async (req, res) => {
      const { filePath, content } = req.body

      const response = {
        success: false,
        message: [],
        details: {
          path: filePath,
          existed: false,
          error: null
        }
      }

      try {
        if (!getWorkspaceRoot()) {
          response.message.push(
            'No workspace is currently open. Please open a folder or workspace to use CodeGPT features.'
          )
          response.details.error = 'NO_WORKSPACE'
          res.end(JSON.stringify(response))
          return
        }

        if (!filePath || content === undefined) {
          response.message.push('Invalid parameters. Expected { filePath: string, content: string }')
          res.end(JSON.stringify(response))
          return
        }

        const fullPath = path.join(getWorkspaceRoot() || '', filePath)

        // Verificar si el archivo ya existe
        try {
          await fsPromises.access(fullPath, fs.constants.F_OK)
          response.details.existed = true
          response.message.push(`File '${filePath}' already exists and was not overwritten`)
          res.end(JSON.stringify(response))
          return
        } catch (error) {
        // El archivo no existe, podemos continuar
        }

        const success = await writeFileContent(filePath, content)

        if (success) {
          response.success = true
          response.message.push(`File '${filePath}' created successfully`)

          // Obtener diagnósticos de IDE después de crear el archivo
          try {
            const diagnostics = await getIdeDiagnostics(fullPath)
            response.diagnostics = diagnostics
          } catch (diagError) {
            response.diagnostics = {
              success: false,
              error: `Could not get diagnostics: ${diagError.message}`
            }
          }
        } else {
          response.message.push(`Failed to create file '${filePath}'`)
          response.details.error = 'WRITE_ERROR'
        }

        res.end(JSON.stringify(response))
      } catch (error) {
        response.message.push(`Error: ${error.message}`)
        response.details.error = 'UNEXPECTED_ERROR'
        res.end(JSON.stringify(response))
      }
    })

    app.post('/appendFileContent', async (req, res) => {
      try {
        const { filePath, content } = req.body
        if (!filePath || content === undefined) {
          return res.end(
            JSON.stringify({ success: false, error: 'filePath and content are required' })
          )
        }
        const fullPath = path.join(getWorkspaceRoot(), filePath)

        // Ensure file exists before appending
        try {
          await fsPromises.access(fullPath)
        } catch (_e) {
        // File doesn't exist — create it with the content
          const dir = path.dirname(fullPath)
          await fsPromises.mkdir(dir, { recursive: true })
          await fsPromises.writeFile(fullPath, content)
          await formatClosedDocument(fullPath)
          return res.end(JSON.stringify({ success: true, created: true }))
        }

        // Append content to existing file
        await fsPromises.appendFile(fullPath, content)

        // Refresh the editor buffer if the file is open
        const openDoc = vscode.workspace.textDocuments.find(
          (doc) => doc.uri.fsPath === fullPath || doc.uri.fsPath === path.resolve(fullPath)
        )
        if (openDoc) {
        // Revert the editor buffer to pick up the disk change
          await vscode.commands.executeCommand('workbench.action.files.revert')
        }

        res.end(JSON.stringify({ success: true }))
      } catch (error) {
        console.error('Error appending to file:', error)
        res.end(JSON.stringify({ success: false, error: error.message }))
      }
    })

    app.post('/createFolder', async (req, res) => {
      const { folderPath } = req.body

      const response = {
        success: false,
        message: [],
        details: {
          path: folderPath,
          existed: false,
          error: null
        }
      }

      try {
        if (!getWorkspaceRoot()) {
          response.message.push(
            'No workspace is currently open. Please open a folder or workspace to use CodeGPT features.'
          )
          response.details.error = 'NO_WORKSPACE'
          res.end(JSON.stringify(response))
          return
        }

        if (!folderPath) {
          response.message.push('Invalid parameters. Expected { folderPath: string }')
          res.end(JSON.stringify(response))
          return
        }

        const fullPath = path.join(getWorkspaceRoot() || '', folderPath)

        // Verificar si la carpeta ya existe
        try {
          const stats = await fsPromises.stat(fullPath)
          if (stats.isDirectory()) {
            response.details.existed = true
            response.message.push(`Folder '${folderPath}' already exists`)
            res.end(JSON.stringify(response))
            return
          } else {
            response.message.push(`Path '${folderPath}' exists but is not a folder`)
            response.details.error = 'PATH_IS_FILE'
            res.end(JSON.stringify(response))
            return
          }
        } catch (error) {
        // La carpeta no existe, podemos continuar
        }

        const success = await createFolder(folderPath)

        if (success) {
          response.success = true
          response.message.push(`Folder '${folderPath}' created successfully`)
        } else {
          response.message.push(`Failed to create folder '${folderPath}'`)
          response.details.error = 'CREATE_ERROR'
        }

        res.end(JSON.stringify(response))
      } catch (error) {
        response.message.push(`Error: ${error.message}`)
        response.details.error = 'UNEXPECTED_ERROR'
        res.end(JSON.stringify(response))
      }
    })

    app.post('/deleteFile', async (req, res) => {
      const { filePath } = req.body

      const response = {
        success: false,
        message: [],
        details: {
          type: null,
          path: filePath,
          error: null
        }
      }

      try {
        if (!getWorkspaceRoot()) {
          response.message.push(
            'No workspace is currently open. Please open a folder or workspace to use CodeGPT features.'
          )
          response.details.error = 'NO_WORKSPACE'
          res.end(JSON.stringify(response))
          return
        }

        if (!filePath) {
          response.message.push('Invalid parameters. Expected { filePath: string }')
          res.end(JSON.stringify(response))
          return
        }

        const result = await deleteFile(filePath)

        // Copiar los valores del resultado a la respuesta estructurada
        response.success = result.success
        response.message.push(result.message)
        response.details.type = result.type || null
        response.details.error = result.error || null

        // Obtener diagnósticos de IDE después de eliminar el archivo (si es exitoso)
        if (result.success) {
          try {
          // Para archivos eliminados, no podemos obtener diagnósticos del archivo en sí,
          // pero podríamos obtener diagnósticos de archivos que lo referencian
            response.diagnostics = {
              success: true,
              message: 'File deleted successfully, diagnostics not applicable for deleted files'
            }
          } catch (diagError) {
            response.diagnostics = {
              success: false,
              error: `Could not get diagnostics: ${diagError.message}`
            }
          }
        }

        res.end(JSON.stringify(response))
      } catch (error) {
        response.message.push(`Error: ${error.message}`)
        response.details.error = 'UNEXPECTED_ERROR'

        res.end(JSON.stringify(response))
      }
    })

    app.post('/openFile', async (req, res) => {
      const { filePath, startLine, endLine, absolutePath } = req.body
      await openFile(filePath, startLine, endLine, absolutePath)
      res.end()
    })

    app.get('/rootPath', async (req, res) => {
      const workspaceFolders = vscode.workspace.workspaceFolders
      if (!workspaceFolders || workspaceFolders.length === 0) {
        res.end(
          JSON.stringify({
            ok: false,
            error:
            'No workspace is currently open. Please open a folder or workspace to use CodeGPT features.'
          })
        )
        return
      }
      res.end(workspaceFolders[0].uri.fsPath)
    })

    app.post('/autoSelect', async (req, res) => {
      const { enabled } = req.body
      await context.globalState.update('autoSelect', enabled)
      if (enabled) {
        state.autoSelectSend()
      }
      res.end(Boolean(enabled).toString())
    })

    app.get('/autoSelect', async (req, res) => {
      const enabled = await context.globalState.get('autoSelect')
      res.end(Boolean(enabled).toString())
    })

    app.get('/extensionVersion', async (req, res) => {
      const codeGPTVersion = context.extension.packageJSON.version
      res.end(codeGPTVersion)
    })

    app.get('/shellInfo', async (req, res) => {
    // Read the user's default terminal profile from VS Code settings
      const isWindows = process.platform === 'win32'
      const isMac = process.platform === 'darwin'
      const platformKey = isWindows ? 'windows' : isMac ? 'osx' : 'linux'
      const defaultProfileSetting = vscode.workspace.getConfiguration('terminal.integrated').get(`defaultProfile.${platformKey}`) || ''
      const shellEnv = process.env.SHELL || ''

      let shell = 'unknown'
      const hint = String(defaultProfileSetting || shellEnv).toLowerCase()
      if (hint.includes('powershell') || hint.includes('pwsh')) {
        shell = 'powershell'
      } else if (hint.includes('cmd')) {
        shell = 'cmd'
      } else if (hint.includes('bash')) {
        shell = 'bash'
      } else if (hint.includes('zsh')) {
        shell = 'zsh'
      } else if (hint.includes('fish')) {
        shell = 'fish'
      } else if (isWindows) {
        shell = 'powershell'
      } else {
        shell = 'bash'
      }

      res.setHeader('Content-Type', 'application/json')
      res.end(JSON.stringify({
        shell,
        os: process.platform,
        arch: process.arch,
        defaultProfile: defaultProfileSetting || null
      }))
    })

    app.get('/ghCopilot', async (req, res) => {
      const models = await vscode.lm.selectChatModels()
      res.setHeader('Content-Type', 'application/json')
      res.end(JSON.stringify(models))
    })

    app.post('/ghCopilot', async (req, res) => {
      const { messages, model, temperature } = req.body
      console.log({ messages, model })
      const models = await vscode.lm.selectChatModels({ family: model })
      const msg = await models[0].sendRequest(
        messages.map((message) => {
          if (message.role !== 'user') {
            return vscode.LanguageModelChatMessage.Assistant(message.content)
          } else {
            return vscode.LanguageModelChatMessage.User(message.content)
          }
        }),
        {
          modelOptions: {
            ...(temperature ? { temperature } : {})
          }
        }
      )
      res.setHeader('Content-Type', 'text/event-stream')
      res.setHeader('Cache-Control', 'no-cache')

      for await (const chunk of msg.text) {
        const structured = {
          choices: [
            {
              delta: {
                content: chunk
              }
            }
          ],
          created: Date.now(),
          model: model.id
        }

        res.write(`data: ${JSON.stringify(structured)}\n\n`)
      }
      res.write('[DONE]')
      res.end()
    })

    app.get('/distinctId', async (req, res) => {
      const codeGPTUserId = await context.globalState.get('codeGPTUserId') // uuid = logged in | codeGPTUserId = anonymous or logged in
      const validId = isUUID(codeGPTUserId)
      res.end(validId ? codeGPTUserId : '')
    })

    app.post('/applyCode', async (req, res) => {
      const { filePath, edits, allowCreate } = req.body

      const response = {
        success: false,
        message: [],
        details: {
          successful: [],
          notFound: [],
          skipped: [],
          errors: []
        }
      }

      try {
        if (!filePath || !edits || !Array.isArray(edits)) {
          response.message.push(
            'Invalid parameters. Expected { filePath: string, edits: Array<{old_string, new_string, replace_all?}> }'
          )
          res.statusCode = 400
          res.end(JSON.stringify(response))
          return
        }

        const isAbsolutePath =
        path.isAbsolute(filePath) ||
        filePath.startsWith('/') ||
        filePath.startsWith('\\') ||
        (filePath.length >= 2 && filePath[1] === ':')

        const absolutePath = isAbsolutePath ? filePath : path.join(getWorkspaceRoot() || '', filePath)

        // Normaliza línea por línea: CRLF→LF, lone \r→LF, strip trailing whitespace.
        // El modelo recibe el archivo normalizado en el context, así que matcheamos
        // contra la misma forma para que old_string coincida en el primer intento.
        const normalize = (s) =>
          s.replace(/\r\n/g, '\n').replace(/\r/g, '\n').replace(/[ \t]+$/gm, '')

        // Cuando un edit falla, devolvemos las ~7 líneas alrededor del mejor match
        // parcial para que el modelo vea el contenido real sin tener que re-leer.
        const findBestLineWindow = (haystack, needle) => {
          const hayLines = haystack.split('\n')
          const needleLines = needle.split('\n').filter((l) => l.trim().length > 0)
          if (needleLines.length === 0) return 0
          const firstNeedle = needleLines[0].trim()
          let bestLine = 0
          let bestScore = -1
          for (let i = 0; i < hayLines.length; i++) {
            if (hayLines[i].trim() !== firstNeedle) continue
            let score = 0
            for (let k = 0; k < needleLines.length && i + k < hayLines.length; k++) {
              if (hayLines[i + k].trim() === needleLines[k].trim()) score++
            }
            if (score > bestScore) {
              bestScore = score
              bestLine = i
            }
          }
          return bestLine
        }

        const excerptAround = (haystack, lineIdx, around = 3) => {
          const lines = haystack.split('\n')
          const start = Math.max(0, lineIdx - around)
          const end = Math.min(lines.length, lineIdx + around + 1)
          return lines
            .slice(start, end)
            .map((l, k) => `${start + k + 1}: ${l}`)
            .join('\n')
        }

        const rawContent = await fsPromises.readFile(absolutePath, 'utf8')
        let content = normalize(rawContent)

        for (let i = 0; i < edits.length; i++) {
          const edit = edits[i]

          if (!edit.old_string || edit.new_string === undefined) {
            response.details.errors.push({
              index: i,
              reason: 'Invalid edit: missing old_string or new_string',
              edit
            })
            response.message.push(`Edit ${i}: Error - missing old_string or new_string`)
            continue
          }

          const oldNorm = normalize(edit.old_string)
          const newNorm = normalize(edit.new_string)

          if (oldNorm === newNorm) {
            response.details.skipped.push({
              index: i,
              reason: 'old_string and new_string are identical',
              string: oldNorm.substring(0, 50) + (oldNorm.length > 50 ? '...' : '')
            })
            response.message.push(`Edit ${i}: Skipped - old_string and new_string are identical`)
            continue
          }

          // Fallback whitespace-tolerante: si el modelo armó un old_string con
          // diferencias menores de espacios/newlines (típico cuando el archivo
          // tiene una línea larga que el modelo "rompe" en varias), buscamos
          // colapsando todo run de \s a un solo espacio, y mapeamos el match
          // colapsado de vuelta al rango real del archivo. La unicidad se
          // chequea sobre el texto colapsado para no reemplazar zonas ambiguas.
          const findWhitespaceTolerant = (hay, needle) => {
            if (!needle) return null
            // Colapsa runs de \s a un solo espacio, manteniendo un map de
            // cada char colapsado → índice en el original. Trim de bordes
            // se hace con punteros sobre el needle colapsado, así el rango
            // real preserva la indentación original al reemplazar.
            const collapse = (s) => {
              const map = []
              let out = ''
              let prevWasSpace = false
              for (let k = 0; k < s.length; k++) {
                const ch = s[k]
                const isSpace = /\s/.test(ch)
                if (isSpace) {
                  if (prevWasSpace) continue
                  out += ' '
                  map.push(k)
                  prevWasSpace = true
                } else {
                  out += ch
                  map.push(k)
                  prevWasSpace = false
                }
              }
              return { collapsed: out, map }
            }
            const { collapsed: hayC, map: hayMap } = collapse(hay)
            const { collapsed: needleC } = collapse(needle)
            // Match contra el contenido trimeado: preservamos el whitespace
            // de borde del archivo (newlines, indent) y solo reemplazamos el
            // contenido. El caller debe usar new_string también trimeado para
            // no duplicar indentación.
            const needleTrimmed = needleC.trim()
            if (!needleTrimmed) return null
            const first = hayC.indexOf(needleTrimmed)
            if (first === -1) return null
            const second = hayC.indexOf(needleTrimmed, first + 1)
            if (second !== -1) return { ambiguous: true }
            const startReal = hayMap[first]
            const endReal = hayMap[first + needleTrimmed.length - 1] + 1
            return { start: startReal, end: endReal, trimmed: true }
          }

          if (content.includes(oldNorm)) {
            let replacedCount = 1
            if (edit.replace_all) {
              const parts = content.split(oldNorm)
              replacedCount = parts.length - 1
              content = parts.join(newNorm)
            } else {
              content = content.replace(oldNorm, newNorm)
            }
            response.details.successful.push({
              index: i,
              old_string: oldNorm.substring(0, 50) + (oldNorm.length > 50 ? '...' : ''),
              new_string: newNorm.substring(0, 50) + (newNorm.length > 50 ? '...' : ''),
              replacedCount
            })
            response.message.push(
            `Edit ${i}: Success - replaced ${replacedCount} occurrence(s) of "${oldNorm.substring(0, 30)}${
              oldNorm.length > 30 ? '...' : ''
            }" with "${newNorm.substring(0, 30)}${newNorm.length > 30 ? '...' : ''}"`
            )
            continue
          }

          const tolerant = findWhitespaceTolerant(content, oldNorm)
          if (tolerant && !tolerant.ambiguous) {
          // Si match fue trimeado, reemplazamos con new trimeado para que el
          // whitespace de borde del archivo (indent, newlines) se preserve.
            const replacement = tolerant.trimmed ? newNorm.trim() : newNorm
            content = content.slice(0, tolerant.start) + replacement + content.slice(tolerant.end)
            response.details.successful.push({
              index: i,
              old_string: oldNorm.substring(0, 50) + (oldNorm.length > 50 ? '...' : ''),
              new_string: newNorm.substring(0, 50) + (newNorm.length > 50 ? '...' : ''),
              matchedVia: 'whitespace-tolerant'
            })
            response.message.push(
            `Edit ${i}: Success (whitespace-tolerant) - replaced "${oldNorm.substring(0, 30)}${
              oldNorm.length > 30 ? '...' : ''
            }" with "${newNorm.substring(0, 30)}${newNorm.length > 30 ? '...' : ''}"`
            )
            continue
          }

          const bestLine = findBestLineWindow(content, oldNorm)
          const excerpt = excerptAround(content, bestLine)
          const ambiguousNote = tolerant && tolerant.ambiguous
            ? ' (Whitespace-tolerant match was ambiguous — multiple matches found. Make old_string longer/more unique.)'
            : ''
          response.details.notFound.push({
            index: i,
            old_string: oldNorm.substring(0, 50) + (oldNorm.length > 50 ? '...' : ''),
            actualContextNearBestMatch: excerpt,
            ambiguous: !!(tolerant && tolerant.ambiguous)
          })
          response.message.push(
          `Edit ${i}: Not found - "${oldNorm.substring(0, 30)}${
            oldNorm.length > 30 ? '...' : ''
          }" was not found in the file.${ambiguousNote} Nearest content (line ${bestLine + 1}):\n${excerpt}\nUse this exact text as old_string and retry.`
          )
        }

        // Si el archivo está abierto en VSCode, aplicar via WorkspaceEdit para
        // que el editor sincronice con disco y no sobrescriba con la versión
        // vieja en memoria. Si no está abierto, escribir directo a disco.
        const fileUri = vscode.Uri.file(absolutePath)
        const openDoc = vscode.workspace.textDocuments.find(
          (d) => d.uri.fsPath === absolutePath
        )

        if (openDoc) {
          const workspaceEdit = new vscode.WorkspaceEdit()
          const fullRange = new vscode.Range(
            openDoc.positionAt(0),
            openDoc.positionAt(openDoc.getText().length)
          )
          workspaceEdit.replace(fileUri, fullRange, content)
          const applied = await vscode.workspace.applyEdit(workspaceEdit)
          if (!applied) {
          // Fallback: escribir directo si applyEdit falla.
            await fsPromises.writeFile(absolutePath, content, 'utf8')
          } else {
          // Persistir los cambios del editor a disco.
            await openDoc.save()
          }
        } else {
          await fsPromises.writeFile(absolutePath, content, 'utf8')
        }

        // Formatear solo si el documento editado coincide con el editor activo.
        const activeEditor = vscode.window.activeTextEditor
        if (activeEditor && activeEditor.document.uri.fsPath === absolutePath) {
          try {
            await vscode.commands.executeCommand('editor.action.formatDocument')
            await new Promise((resolve) => setTimeout(resolve, 200))
          } catch (_) {}
        }

        const totalEdits = edits.length
        const successCount = response.details.successful.length
        const notFoundCount = response.details.notFound.length
        const skippedCount = response.details.skipped.length
        const errorCount = response.details.errors.length

        response.success = successCount > 0

        response.message.push(
        `Summary: Applied ${successCount}/${totalEdits} edits. ${notFoundCount} not found, ${skippedCount} skipped, ${errorCount} errors.`
        )

        // Obtener diagnósticos de IDE después de aplicar los cambios
        const diagnostics = await getIdeDiagnostics(absolutePath)
        response.diagnostics = diagnostics

        res.end(JSON.stringify(response))
      } catch (error) {
        response.message.push(`Error: ${error.message}`)

        // Intentar obtener diagnósticos incluso en caso de error
        try {
          const isAbsolutePath =
          path.isAbsolute(filePath) ||
          filePath.startsWith('/') ||
          filePath.startsWith('\\') ||
          (filePath.length >= 2 && filePath[1] === ':')

          const absolutePath = isAbsolutePath
            ? filePath
            : path.join(getWorkspaceRoot() || '', filePath)

          const diagnostics = await getIdeDiagnostics(absolutePath)
          response.diagnostics = diagnostics
        } catch (diagError) {
          response.diagnostics = {
            success: false,
            error: `Could not get diagnostics: ${diagError.message}`
          }
        }

        res.end(JSON.stringify(response))
      }
    })

    app.get('/getIdeDiagnostic', async (req, res) => {
      const { filePath } = req.query

      const diagnostics = await getIdeDiagnostics(filePath)
      res.end(JSON.stringify(diagnostics))
    })

    app.post('/executeCommandInTerminal', async (req, res) => {
      const { command, name } = req.body
      res.setHeader('Content-Type', 'text/event-stream')
      res.setHeader('Cache-Control', 'no-cache')
      res.setHeader('Connection', 'keep-alive')

      if (!getWorkspaceRoot()) {
        res.write(
        `data: ${JSON.stringify({ error: 'No workspace is currently open. Please open a folder or workspace to use CodeGPT features.' })}\n\n`
        )
        res.write(`data: ${JSON.stringify({ done: true })}\n\n`)
        res.end()
        return
      }

      let clientClosed = false
      const safeWrite = (chunk) => {
        if (clientClosed) return
        try { res.write(chunk) } catch {}
      }
      const safeEnd = () => {
        if (clientClosed) return
        try { res.end() } catch {}
      }
      // Use res.on('close') — req.on('close') fires when body-parser finishes
      // reading the POST body, which is not the same as the client disconnecting.
      res.on('close', () => {
        if (!res.writableEnded) clientClosed = true
      })

      try {
        const terminalName = name || `CodeGPT Terminal ${uuidv4().substring(0, 8)}`
        // `name` often carries a shell hint from the backend (e.g.
        // "powershell - call_function_...", "bash - ..."). Parse it so the pty
        // spawns the requested shell instead of the platform default.
        const ctrl = getOrCreatePtyController(terminalName, name)
        ctrl.terminal.show(true)

        safeWrite(`data: ${JSON.stringify({ shell: ctrl.shellName, os: process.platform })}\n\n`)

        // No command — we already created/reused the terminal. Done.
        if (!command) {
          safeWrite(`data: ${JSON.stringify({ done: true })}\n\n`)
          safeEnd()
          return
        }

        // Per-command line buffer so the model receives tidy line-oriented events
        // regardless of how stdout chunks arrive.
        let lineBuffer = ''
        const stripAnsi = (s) => s
          .replace(/\x1b\[[0-9;?]*[A-Za-z]/g, '')
          .replace(/\x1b\]\d+;[^\x07\x1b]*(\x07|\x1b\\)/g, '')
        const flushLine = (line) => {
          const cleaned = stripAnsi(line).replace(/\r$/, '')
          if (cleaned) safeWrite(`data: ${JSON.stringify({ message: cleaned })}\n\n`)
        }
        const onChunk = (text) => {
          lineBuffer += text
          let idx
          while ((idx = lineBuffer.indexOf('\n')) !== -1) {
            flushLine(lineBuffer.slice(0, idx))
            lineBuffer = lineBuffer.slice(idx + 1)
          }
        }

        const result = await ctrl.runCommand(command, onChunk, () => clientClosed)

        if (lineBuffer) {
          flushLine(lineBuffer)
          lineBuffer = ''
        }

        if (!clientClosed) {
          safeWrite(`data: ${JSON.stringify({ done: true, exitCode: result.exitCode })}\n\n`)
          safeEnd()
        }
      } catch (error) {
        const errorData = `data: ${JSON.stringify({ error: error.message })}\n\n`
        const doneData = `data: ${JSON.stringify({ done: true })}\n\n`
        try {
          res.write(errorData)
          res.write(doneData)
          res.end()
        } catch {}
      }
    })

    app.post('/chatLog', async (req, res) => {
      const { message } = req.body
      console.log({ message, body: req.body })
      chatLog(message)
      res.end('ok')
    })

    // Diff Preview Endpoints
    app.post('/diffPreview/start', async (req, res) => {
      const { sessionId, filePath, initialContent } = req.body

      if (!sessionId || !filePath) {
        res.end(
          JSON.stringify({
            success: false,
            error: 'sessionId and filePath are required'
          })
        )
        return
      }

      if (!state.diffManager) {
        state.diffManager = new DiffManager()
      }

      const result = await state.diffManager.startSession(sessionId, filePath, initialContent)
      res.end(JSON.stringify(result))
    })

    app.post('/diffPreview/stream', async (req, res) => {
      const { sessionId, content, isPartial } = req.body

      if (!sessionId || content === undefined) {
        res.end(
          JSON.stringify({
            success: false,
            error: 'sessionId and content are required'
          })
        )
        return
      }

      if (!state.diffManager) {
        res.end(
          JSON.stringify({
            success: false,
            error: 'No diff manager initialized'
          })
        )
        return
      }

      const result = await state.diffManager.streamUpdate(sessionId, content, isPartial)
      res.end(JSON.stringify(result))
    })

    app.post('/diffPreview/complete', async (req, res) => {
      const { sessionId, finalContent } = req.body

      if (!sessionId) {
        res.end(
          JSON.stringify({
            success: false,
            error: 'sessionId is required'
          })
        )
        return
      }

      if (!state.diffManager) {
        res.end(
          JSON.stringify({
            success: false,
            error: 'No diff manager initialized'
          })
        )
        return
      }

      const result = await state.diffManager.completeSession(sessionId, finalContent)
      res.end(JSON.stringify(result))
    })

    app.post('/diffPreview/cancel', async (req, res) => {
      const { sessionId } = req.body || {}

      if (!sessionId) {
        res.statusCode = 400
        res.end(
          JSON.stringify({
            success: false,
            error: 'sessionId is required'
          })
        )
        return
      }

      if (!state.diffManager) {
      // Nothing to cancel — be idempotent.
        res.end(JSON.stringify({ success: true, message: 'no-op (no diff manager initialized)' }))
        return
      }

      // Idempotent: try smart-session cancel first, then legacy. If neither
      // session exists, return 200 success no-op (StrictMode/dev double-fire safe).
      let smart = null
      if (state.diffManager.smartSessions && state.diffManager.smartSessions.has(sessionId)) {
        smart = await state.diffManager.cancelSmartSession(sessionId)
      }

      let legacy = null
      if (state.diffManager.activeSessions && state.diffManager.activeSessions.has(sessionId)) {
        legacy = await state.diffManager.cancelSession(sessionId)
      }

      if (!smart && !legacy) {
        res.end(JSON.stringify({ success: true, message: 'no-op (session not found)' }))
        return
      }

      res.end(JSON.stringify(smart || legacy))
    })

    // Smart diff preview endpoints — chunk-based inline rendering (Cursor-style).
    // Source of truth for chunks lives in the Next.js client; the extension only
    // renders what arrives. The disk file is never modified until accept-all.
    //
    // Status code contract (verified against the Next.js client):
    //   - 400 on missing/invalid required fields with body: { error: 'Missing required field: <name>' }
    //   - 404 when session or chunk never existed (reason: 'session_not_found' / 'CHUNK_NOT_FOUND')
    //   - 410 Gone when the session existed but is now closed (cancelled, expired,
    //         manual edit, completed, etc.) — body includes a `reason` so the front
    //         can distinguish "died mid-flight" from "never existed"
    //   - 409 Conflict when a chunk is asked to flip into the opposite terminal
    //         state (accept on rejected, reject on accepted)
    //   - 200 on success — including idempotent retries of the same operation
    //   - never 200 with empty body
    const mapSmartErrorCodeToStatus = (code) => {
      if (code === 'SESSION_NOT_FOUND' || code === 'CHUNK_NOT_FOUND') return 404
      if (code === 'SESSION_GONE') return 410
      if (code === 'CHUNK_CONFLICT') return 409
      return 500
    }

    app.post('/diffPreview/smart/start', async (req, res) => {
      const body = req.body || {}
      const requiredFields = ['sessionId', 'filePath', 'newContent', 'chunks']
      for (const field of requiredFields) {
        if (body[field] === undefined || body[field] === null) {
          res.statusCode = 400
          res.end(
            JSON.stringify({ success: false, error: `Missing required field: ${field}` })
          )
          return
        }
      }
      if (!Array.isArray(body.chunks) || body.chunks.length === 0) {
        res.statusCode = 400
        res.end(JSON.stringify({ success: false, error: 'chunks must be a non-empty array' }))
        return
      }

      if (!state.diffManager) {
        state.diffManager = new DiffManager()
      }

      const result = await state.diffManager.startSmartSession(
        body.sessionId,
        body.filePath,
        body.newContent,
        body.chunks,
        body.explanation || ''
      )

      if (!result.success) {
        res.statusCode = 500
        res.end(JSON.stringify(result))
        return
      }

      res.end(
        JSON.stringify({
          success: true,
          sessionId: result.sessionId,
          chunksCount: result.chunksCount
        })
      )
    })

    app.get('/diffPreview/smart/summary/:sessionId', (req, res) => {
      const { sessionId } = req.params

      if (!state.diffManager) {
        res.statusCode = 404
        res.end(
          JSON.stringify({ success: false, reason: 'session_not_found', error: 'Session not found' })
        )
        return
      }

      const summary = state.diffManager.getSmartSummary(sessionId)
      if (!summary) {
      // Truly never existed — front uses this to distinguish from a session
      // that died mid-flight.
        res.statusCode = 404
        res.end(
          JSON.stringify({ success: false, reason: 'session_not_found', error: 'Session not found' })
        )
        return
      }

      if (summary.closed) {
      // Session existed but is gone (cancelled, expired, completed, manual edit, etc.).
      // 410 Gone with the reason lets the front surface a meaningful state instead
      // of treating this the same as never-existed.
      // total/accepted/rejected/chunks come from the close-time snapshot so the
      // front can render real per-chunk counts/decisions and craft a correct
      // partial-vs-all-accepted message to the model.
        res.statusCode = 410
        res.end(
          JSON.stringify({
            success: false,
            reason: summary.reason,
            sessionId: summary.sessionId,
            closedAt: summary.closedAt,
            filePath: summary.filePath,
            total: summary.total,
            accepted: summary.accepted,
            rejected: summary.rejected,
            chunks: summary.chunks
          })
        )
        return
      }

      res.end(JSON.stringify({ summary }))
    })

    app.post('/diffPreview/smart/accept', async (req, res) => {
      const { sessionId, chunkId, acceptAll } = req.body || {}

      if (!sessionId) {
        res.statusCode = 400
        res.end(
          JSON.stringify({ success: false, error: 'Missing required field: sessionId' })
        )
        return
      }
      if (!acceptAll && !chunkId) {
        res.statusCode = 400
        res.end(
          JSON.stringify({
            success: false,
            error: 'Either chunkId or acceptAll must be provided'
          })
        )
        return
      }

      if (!state.diffManager) {
        res.statusCode = 404
        res.end(JSON.stringify({ success: false, error: 'Session not found' }))
        return
      }

      const result = acceptAll
        ? await state.diffManager.acceptAllSmart(sessionId)
        : await state.diffManager.acceptChunk(sessionId, chunkId)

      if (!result.success) {
        res.statusCode = mapSmartErrorCodeToStatus(result.code)
        res.end(JSON.stringify(result))
        return
      }

      res.end(JSON.stringify(result))
    })

    app.post('/diffPreview/smart/reject', async (req, res) => {
      const { sessionId, chunkId, rejectAll } = req.body || {}

      if (!sessionId) {
        res.statusCode = 400
        res.end(
          JSON.stringify({ success: false, error: 'Missing required field: sessionId' })
        )
        return
      }
      if (!rejectAll && !chunkId) {
        res.statusCode = 400
        res.end(
          JSON.stringify({
            success: false,
            error: 'Either chunkId or rejectAll must be provided'
          })
        )
        return
      }

      if (!state.diffManager) {
        res.statusCode = 404
        res.end(JSON.stringify({ success: false, error: 'Session not found' }))
        return
      }

      const result = rejectAll
        ? await state.diffManager.rejectAllSmart(sessionId, 'cancelled')
        : await state.diffManager.rejectChunk(sessionId, chunkId)

      if (!result.success) {
        res.statusCode = mapSmartErrorCodeToStatus(result.code)
        res.end(JSON.stringify(result))
        return
      }

      res.end(JSON.stringify(result))
    })

    // SSE endpoint for smart-diff session changes. Replaces the webView's
    // adaptive polling loop with push-based delta updates so Tab/Esc in the
    // editor land in the card with sub-frame latency instead of 100–800 ms.
    //
    // Flow:
    //   1. Client opens EventSource on this path.
    //   2. We immediately emit one `summary` event so the client renders the
    //      current state without an extra HTTP roundtrip.
    //   3. We subscribe to DiffManager.onSessionChange and forward every event
    //      that matches this sessionId.
    //   4. On `session-closed` we send the final summary and disconnect — the
    //      hook on the client treats the disconnect as completion.
    //   5. Heartbeat every 25 s keeps proxies / OS-level idle timeouts happy.
    //
    // The hook on the front (useDiffSessionEvents) keeps the polling endpoint
    // as a fallback for older extensions that don't expose this path.
    app.get('/diffPreview/smart/events/:sessionId', (req, res) => {
      const { sessionId } = req.params

      res.setHeader('Content-Type', 'text/event-stream')
      res.setHeader('Cache-Control', 'no-cache, no-transform')
      res.setHeader('Connection', 'keep-alive')
      res.setHeader('X-Accel-Buffering', 'no')
      // Permit any origin — the front may come from a Next dev server on a
      // different port than the extension's polka listener.
      res.setHeader('Access-Control-Allow-Origin', '*')

      const send = (type, payload) => {
        try {
          res.write(`event: ${type}\n`)
          res.write(`data: ${JSON.stringify(payload)}\n\n`)
        } catch (e) {
        // Connection probably already closed — fall through to the cleanup
        // path below; the req 'close' listener will run.
        }
      }

      if (!state.diffManager) {
        state.diffManager = new DiffManager()
      }

      // Initial state. If the session never existed OR is already closed, the
      // summary will reflect that and the client can short-circuit immediately.
      const initial = state.diffManager.getSmartSummary(sessionId)
      send('summary', { sessionId, summary: initial })
      if (initial && initial.closed) {
      // No point subscribing — the session is already terminal.
        try { res.end() } catch (_) { /* noop */ }
        return
      }

      const disposable = state.diffManager.onSessionChange((evt) => {
        if (!evt || evt.sessionId !== sessionId) return
        send(evt.type || 'change', evt)
        if (evt.type === 'session-closed') {
          try { disposable.dispose() } catch (_) { /* noop */ }
          clearInterval(heartbeat)
          try { res.end() } catch (_) { /* noop */ }
        }
      })

      const heartbeat = setInterval(() => {
        try {
          res.write(': heartbeat\n\n')
        } catch (_) {
        /* noop */
        }
      }, 25000)

      req.on('close', () => {
        try { disposable.dispose() } catch (_) { /* noop */ }
        clearInterval(heartbeat)
      })
    })

    // SSE endpoint for streaming diff
    app.get('/diffPreview/streamSSE/:sessionId', async (req, res) => {
      const { sessionId } = req.params

      res.setHeader('Content-Type', 'text/event-stream')
      res.setHeader('Cache-Control', 'no-cache')
      res.setHeader('Connection', 'keep-alive')

      // Send initial connection message
      res.write('data: {"type": "connected"}\n\n')

      // Store the SSE connection for this session
      if (!state.diffManager) {
        state.diffManager = new DiffManager()
      }

      // Keep connection alive with periodic heartbeat
      const heartbeat = setInterval(() => {
        res.write('data: {"type": "heartbeat"}\n\n')
      }, 30000)

      // Clean up on client disconnect
      req.on('close', () => {
        clearInterval(heartbeat)
      })
    })

    app.listen(state.nextjsPort, async (err) => {
      if (err) throw vscode.window.showErrorMessage(err)
      console.log(`extension driver > Running on localhost:${state.nextjsPort}`)
    })
  }

  return vscodeDriver
}

module.exports = { createDriver }
