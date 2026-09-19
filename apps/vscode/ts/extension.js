const vscode = require('vscode')
const language = require('./utils/language.js')
const ChatSidebarProvider = require('./ChatSidebarProvider')
const fs = require('fs')
const fsPromises = require('fs').promises
const path = require('path')
const { v4: uuidv4 } = require('uuid')
const { sendEvent } = require('./utils/telemetry.js')
const ConfigurationManager = require('./internal/ConfigManager')
const CodeGPTCopilotProvider = require('./CodeGPTCopilotProvider')
const { log } = require('./loggers')
const nodeFetch = require('node-fetch')
const DiffManager = require('./DiffManager')
const axios = require('axios')

const fetch = async (url, options) => {
  try {
    return await nodeFetch(url, options)
  } catch (error) {
    console.error('Error al realizar la solicitud:', error)
    throw error
  }
}

const state = require('./state')
const portfinder = require('portfinder')
const { fork } = require('child_process')
const { getDistinctId, getSession } = require('./utils/distinctId')

const hasWorkspace = vscode.workspace.workspaceFolders !== undefined
state.provider = hasWorkspace ? getConfig({ config: 'CodeGPT.apiKey' }) : 'CodeGPT Plus Beta'

function getConfig({ config, defaultValue = '' }) {
  return vscode.workspace.getConfiguration().get(config) || defaultValue
}

/**
 * Gets the root path of the first workspace folder.
 * Uses the modern workspaceFolders API instead of the deprecated rootPath.
 * @returns {string|undefined} The workspace root path or undefined if no workspace is open
 */
function getWorkspaceRoot() {
  const folders = vscode.workspace.workspaceFolders
  return folders && folders.length > 0 ? folders[0].uri.fsPath : undefined
}

function debounce(func, wait) {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

let syncProvider

const syncProviderHOF = (context) => {
  return debounce((provider) => {
    const chatSidebarProvider = ChatSidebarProvider.getChatInstance(context)
    chatSidebarProvider.view.webview.postMessage({
      type: 'syncProvider',
      value: provider,
      ok: true
    })
  }, 300) // 300ms de espera
}

const autoSelectSendHOF = (context) => {
  return async () => {
    const isAutoSelect = Boolean(await context.globalState.get('autoSelect'))
    const editor = vscode.window.activeTextEditor
    if (editor) {
      const document = editor.document
      const selectedText = document.getText(editor.selection)
      const fullText = document.getText()
      const fromLine = Math.min(editor.selection.start.line, editor.selection.end.line)
      const toLine = Math.max(editor.selection.start.line, editor.selection.end.line) + 1

      const sendMsg = (canRepeat = true) => {
        try {
          const chatSidebarProvider = ChatSidebarProvider.getChatInstance(context)
          chatSidebarProvider.view.webview.postMessage({
            type: 'selectionCodeGPT',
            ok: true,
            selectedText: selectedText || (isAutoSelect ? fullText : ''),
            fileName: path.basename(document.fileName),
            path: vscode.workspace.asRelativePath(document.uri.fsPath),
            language: document.languageId,
            from: selectedText
              ? new vscode.Position(fromLine, editor.selection.start.character)
              : null,
            to: selectedText ? new vscode.Position(toLine, editor.selection.end.character) : null,
            lines: document.lineCount,
            lineAt: document.lineAt(editor.selection.active)
          })
        } catch {
          if (canRepeat) {
            setTimeout(() => {
              sendMsg(false)
            }, 10000)
          }
        }
      }
      sendMsg()
    }
  }
}

const selectAllCommand = async () => {
  const editor = vscode.window.activeTextEditor
  if (!editor) {
    return
  }

  const document = editor.document
  const lastLine = document.lineCount - 1
  const lastChar = document.lineAt(lastLine).text.length

  editor.selection = new vscode.Selection(0, 0, lastLine, lastChar)
}

const { createDriver } = require('./driver')
const vscodeDriver = createDriver({ getWorkspaceRoot, hasWorkspace })

const getPort = () => {
  return new Promise((resolve, reject) => {
    portfinder.getPort(
      {
        port: 54113,
        stopPort: 54500
      },
      (err, port) => {
        if (err) {
          console.error(err)
          reject(err)
        } else {
          resolve(port)
        }
      }
    )
  })
}

const { migrateToSqlite } = require('./utils/migrate-sqlite')

const { fetchWithRetry, downloadAndExtract, deleteCodeGPTFolder } = require('./utils/retry')

const { registerSmartDiffCommands } = require('./commands/smart-diff')
const { createInlineDiffCommands } = require('./commands/inline-diff')
const { registerExternalLinkCommands } = require('./commands/external-links')
const { registerCommitMessageCommand } = require('./commands/commit-message')
const { createCodeActionCommands } = require('./commands/code-actions')

/**
 * @param {vscode.ExtensionContext} context
 */
async function activate(context) {
  const { commandInlineCodeEditCodeGPT, acceptDiffCommand, rejectDiffCommand } =
    createInlineDiffCommands({ context })

  const deleteAllGlobalState = async () => {
    // 1. Limpiar globalState
    context.globalState.keys().forEach((key) => context.globalState.update(key, undefined))

    // 2. Limpiar SecretStorage (OS keychain) — iterar providers conocidos
    try {
      const providers =
        context.extension.packageJSON.contributes.configuration[0].properties['CodeGPT.apiKey'].enum
      const secretSuffixes = [
        '_orgId',
        '_customLink',
        '_region',
        '_accessKeyId',
        '_secretAccessKey',
        '_sessionToken'
      ]
      for (const provider of providers) {
        await context.secrets.delete(`API_KEY_${provider}`)
        for (const suffix of secretSuffixes) {
          await context.secrets.delete(`${provider}${suffix}`)
        }
      }
      await context.secrets.delete('googleOauth')
    } catch (error) {
      console.error('[CodeGPT] Error clearing secrets:', error)
    }

    // 3. Borrar directorio ~/.codegpt/ (SQLite + WAL + SHM)
    deleteCodeGPTFolder()

    // 4. Reiniciar extension host
    vscode.commands.executeCommand('workbench.action.restartExtensionHost')
  }

  const deleteAllGlobalStateCommand = vscode.commands.registerCommand(
    'codegpt.resetCodeGPT',

    async () => {
      await deleteAllGlobalState()
    }
  )

  // Con node:sqlite en el runtime (VS Code >= 1.123, Electron 42+) el server
  // usa ese builtin y el binario nativo no se carga: el parche no aplica y
  // el problema de ABI desaparece por construcción.
  const hasNodeSqlite =
    typeof process.getBuiltinModule === 'function' && !!process.getBuiltinModule('node:sqlite')

  state.serverOutputChannel = vscode.window.createOutputChannel('CodeGPT Server')

  if (hasNodeSqlite) {
    state.serverOutputChannel.appendLine(
      '[sqlite] node:sqlite available in this runtime — native binary patch skipped'
    )
  } else {
    try {
      /// PATCH
      const libPatch =
        context.extensionPath +
        '/standalone/node_modules/better-sqlite3-multiple-ciphers/build/Release/'
      const modulesVersion = process.versions.modules
      const isPatched = await fsPromises
        .readFile(libPatch + `${modulesVersion}.txt`, 'utf8')
        .catch((e) => {
          console.error({ e })
          return 'nope'
        })
      console.log({ firstIsPatched: isPatched })
      if (isPatched !== 'yep') {
        const regex = /.*-v\d+-.*/

        const json = await fetchWithRetry(async () => {
          const { data } = await axios.get(
            'https://api.github.com/repos/m4heshd/better-sqlite3-multiple-ciphers/releases/latest',
            {
              timeout: 15000,
              headers: { 'User-Agent': 'CodeGPT-VSCode' }
            }
          )
          return data
        })

        const versions = json.assets
          .map((a) => {
            const file = a.browser_download_url.split('/').find((text) => regex.test(text))
            const parts = file.split('-')
            const version = parts[6].substring(1) // Remove the 'v' at the beginning
            const extra = parts[8]
            const osArch = (extra ? `${parts[7]}-${extra}` : parts[7]).replace('.tar.gz', '') // Remove the extension
            const [platform, arch] = osArch.split('-')
            return {
              platform,
              arch,
              version,
              downloadUrl: a.browser_download_url
            }
          })

        const arch = process.arch
        const platform = process.platform
        const url = versions.find(
          (v) => v.platform === platform && v.arch === arch && v.version === modulesVersion
        ).downloadUrl
        console.log({
          arch,
          platform,
          url
        })

        const dir = path.dirname(libPatch + `${modulesVersion}.txt`)
        await fsPromises.mkdir(dir, { recursive: true })

        // Descarga a un staging dir; solo si todo sale OK reemplazamos el binario.
        // Si la descarga falla, el binario previo (bundled o anterior) queda intacto.
        const stagingDir = libPatch + '.staging'
        await fsPromises.rm(stagingDir, { recursive: true, force: true })
        await fsPromises.mkdir(stagingDir, { recursive: true })
        try {
          await fetchWithRetry(() => downloadAndExtract(url, stagingDir))
          await fsPromises.copyFile(
            path.join(stagingDir, 'better_sqlite3.node'),
            path.join(libPatch, 'better_sqlite3.node')
          )
          await fsPromises.writeFile(libPatch + `${modulesVersion}.txt`, 'yep')
        } finally {
          await fsPromises.rm(stagingDir, { recursive: true, force: true }).catch(() => {})
        }
      }

      const waitUntilPatch = async () => {
        const isPatchedAlready = await fsPromises
          .access(libPatch + 'better_sqlite3.node', fs.constants.F_OK)
          .catch(() => false)
        console.log({ isPatchedAlready })
        if (isPatchedAlready === false) {
          await new Promise((resolve) => setTimeout(resolve, 1000))
          return waitUntilPatch()
        }
      }
      await waitUntilPatch()
      ///
    } catch (e) {
      console.error(e)
      // El parche fallaba en silencio total y el diagnóstico costaba días:
      // ahora queda visible para el usuario y medible en telemetría.
      const message = `[sqlite] Native binary patch FAILED for ABI ${process.versions.modules} (${process.platform}-${process.arch}): ${e?.message || e}`
      state.serverOutputChannel.appendLine(message)
      sendEvent(
        'sqlitePatchFailed',
        {
          modulesVersion: process.versions.modules,
          platform: process.platform,
          arch: process.arch,
          editorVersion: vscode.version,
          error: String(e?.message || e)
        },
        context.globalState.get('codeGPTUserId')
      )
    }
  }

  const isDev = context.extension.packageJSON.main === './src/extension.js' // ya no hay que tocar mas nada en este archivo :)

  if (isDev) {
    // comentado en prod
  } else {
    //  comentado en dev
    state.nextjsPort = await getPort()
    const startNextServer = () => {
      if (state.nextServerChild) return // already running

      portfinder.getPort(
        {
          port: 54112,
          stopPort: 54112
        },
        (err, port) => {
          if (err) {
            // Port is in use, server may already be running
            return
          }
          // Fork the server in a child process to avoid polluting
          // the Extension Host's process.env (see github.com/JudiniLabs/code-gpt-docs/issues/467)
          // __dirname is src/ in dev or dist/ in prod — worker is co-located in both cases
          const workerPath = path.join(__dirname, 'next-server-worker.js')
          state.nextServerChild = fork(workerPath, ['54112'], {
            cwd: path.join(__dirname, '..', 'standalone'),
            silent: true
          })

          // silent:true pipea stdout/stderr del worker; sin estos handlers el
          // error real del server (p. ej. SQLite que no carga) muere sin log
          state.nextServerChild.stdout?.on('data', (chunk) => {
            state.serverOutputChannel?.append(chunk.toString())
          })
          state.nextServerChild.stderr?.on('data', (chunk) => {
            state.serverOutputChannel?.append(chunk.toString())
          })

          state.nextServerChild.on('message', (msg) => {
            if (msg.type === 'started') {
              console.log('Next.js server started on port ' + msg.port)
            } else if (msg.type === 'error') {
              console.error('Next.js server error:', msg.message)
            }
          })

          state.nextServerChild.on('error', (err) => {
            console.error('Failed to fork Next.js server:', err)
            state.nextServerChild = null
          })

          state.nextServerChild.on('exit', (code) => {
            if (code !== 0) {
              console.error('Next.js server exited with code', code)
            }
            state.nextServerChild = null
          })
        }
      )
    }
    startNextServer()
    setInterval(() => {
      startNextServer()
    }, 1500)
  }

  // Initialize DiffManager
  state.diffManager = new DiffManager()
  context.subscriptions.push({
    dispose: () => {
      try {
        if (state.diffManager && typeof state.diffManager.dispose === 'function') {
          state.diffManager.dispose()
        }
      } catch (e) {
        console.error('[CodeGPT] Error disposing DiffManager:', e)
      }
    }
  })

  // Register custom URI scheme provider for diff views
  const diffContentProvider = {
    provideTextDocumentContent: (uri) => {
      const query = uri.query
      if (query) {
        const content = Buffer.from(query, 'base64').toString('utf8')
        return content
      }
      return ''
    }
  }

  context.subscriptions.push(
    vscode.workspace.registerTextDocumentContentProvider('codegpt-diff', diffContentProvider)
  )

  syncProvider = syncProviderHOF(context)
  state.autoSelectSend = autoSelectSendHOF(context)

  const autoSelect = await context.globalState.get('autoSelect')
  if (autoSelect === undefined) {
    await context.globalState.update('autoSelect', true)
  }

  const signedDistinctId = await getSession().then((session) => session?.signedDistinctId)

  const codeGPTUserId = await getDistinctId()

  const executeVscodeDriver = (context) => {
    try {
      vscodeDriver(context)
    } catch (e) {
      console.log(e)
      executeVscodeDriver(context)
    }
  }

  void executeVscodeDriver(context)

  // sidebar
  const chatSidebarProvider = ChatSidebarProvider.getChatInstance(context, state.nextjsPort)

  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider('codegpt-sidebar', chatSidebarProvider, {
      webviewOptions: {
        retainContextWhenHidden: true
      }
    })
  )

  // Open the chat sidebar automatically the first time the extension runs.
  const alreadyOpened = await context.globalState.get('codegpt.sidebarShown')
  if (!alreadyOpened) {
    await context.globalState.update('codegpt.sidebarShown', true)
    setTimeout(() => {
      try {
        openChatView()
      } catch (error) {
        console.error('Failed to open CodeGPT sidebar:', error)
      }
    }, 0)
  }

  // Registrar el comando para generar el mensaje del commit
  const generateCommitMessage = registerCommitMessageCommand()
  context.subscriptions.push(generateCommitMessage)

  const firstTimeConfig = async () => {
    const autocompleteEnabled = await context.globalState.get('autocompleteEnabled')
    if (!autocompleteEnabled) {
      await context.globalState.update('autocompleteEnabled', true)
    }
    const autocompleteProvider = await context.globalState.get('autocompleteProvider')
    if (!autocompleteProvider) {
      // CodeGPT Plus default — backend routes to Codestral (FIM-specialized)
      // for non-turbo models, which outperforms generic chat LLMs for inline completion
      await context.globalState.update('autocompleteProvider', 'CodeGPT Plus')
    }
    const autocompleteModel = await context.globalState.get('autocompleteModel')
    if (!autocompleteModel) {
      await context.globalState.update('autocompleteModel', 'CodeGPT Pro')
    } else if (autocompleteModel === 'Plus') {
      // Migration: legacy "Plus" → "CodeGPT Pro" for clarity in the UI
      await context.globalState.update('autocompleteModel', 'CodeGPT Pro')
    }
    const autocompleteMaxTokens = await context.globalState.get('autocompleteMaxTokens')
    if (!autocompleteMaxTokens) {
      await context.globalState.update('autocompleteMaxTokens', 300)
    }
    const autocompleteSuggestionDelay = await context.globalState.get('autocompleteSuggestionDelay')
    if (autocompleteSuggestionDelay == null) {
      // 150ms is the industry-consensus debounce for inline completion
      await context.globalState.update('autocompleteSuggestionDelay', 150)
    }
    const Ollama_customLink = await context.secrets.get('Ollama_customLink')
    if (!Ollama_customLink) {
      await context.secrets.store('Ollama_customLink', 'http://localhost:11434')
    }
  }

  await firstTimeConfig()

  const alreadySyncedSqlite = await context.globalState.get('alreadySyncedSqlite.')

  if (!alreadySyncedSqlite) {
    await migrateToSqlite(context)
    await context.globalState.update('alreadySyncedSqlite.', true)
  }

  const configManager = new ConfigurationManager()
  log('Registering CodeGPT Copilot provider')

  let enable = configManager.config.enable
  configManager.onUpdatedConfig(() => {
    enable = configManager.config.enable
  })

  // Modificar la parte donde se crea el status bar (alrededor de la línea 1300)
  let statusBar
  let copilotProviderInstance = null
  if (enable) {
    statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 0)
    statusBar.text = '$(codegpt-logotype)'
    statusBar.tooltip = 'CodeGPT - Ready 👌'

    // Añadir comando al status bar para mostrar opciones al hacer clic
    statusBar.command = 'codegpt.showAutocompleteOptions'

    copilotProviderInstance = new CodeGPTCopilotProvider(statusBar, log, context)

    context.subscriptions.push(
      vscode.languages.registerInlineCompletionItemProvider(
        { pattern: '**' },
        // @ts-expect-error
        copilotProviderInstance
      ),
      statusBar
    )

    if (await context.globalState.get('autocompleteEnabled')) {
      statusBar.text = '$(codegpt-logotype)'
      statusBar.tooltip = 'CodeGPT - Ready 👌'
      statusBar.show()
    } else {
      statusBar.text = '$(codegpt-logotype) (disabled)'
      statusBar.tooltip = 'CodeGPT - Autocomplete disabled'
      statusBar.show()
    }
  }

  // Añadir el comando para mostrar las opciones de autocomplete
  const showAutocompleteOptions = vscode.commands.registerCommand(
    'codegpt.showAutocompleteOptions',
    async () => {
      const items = [
        {
          label: '$(check) Enable Autocomplete',
          description: 'Turn on CodeGPT autocomplete suggestions',
          action: 'enable'
        },
        {
          label: '$(x) Disable Autocomplete',
          description: 'Turn off CodeGPT autocomplete suggestions',
          action: 'disable'
        }
      ]

      const selectedItem = await vscode.window.showQuickPick(items, {
        placeHolder: 'CodeGPT Autocomplete Options'
      })

      if (selectedItem) {
        switch (selectedItem.action) {
          case 'enable':
            await context.globalState.update('autocompleteEnabled', true)
            statusBar.show()
            statusBar.tooltip = 'CodeGPT - Ready 👌'
            statusBar.text = '$(codegpt-logotype)'
            vscode.window.showInformationMessage('CodeGPT Autocomplete enabled')
            break

          case 'disable':
            await context.globalState.update('autocompleteEnabled', false)
            statusBar.tooltip = 'CodeGPT - Autocomplete disabled'
            statusBar.text = '$(codegpt-logotype) (disabled)'
            break
        }

        // Actualizar el estado del servidor
        fetch('http://localhost:54112/api/autocomplete', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            enabled: await context.globalState.get('autocompleteEnabled')
          })
        }).catch((err) => console.error('Error updating autocomplete status:', err))
      }
    }
  )

  // Añadir el comando a las suscripciones
  context.subscriptions.push(showAutocompleteOptions)

  // Health metrics command — surface client + server autocomplete stats for diagnostics
  const showAutocompleteMetrics = vscode.commands.registerCommand(
    'codegpt.showAutocompleteMetrics',
    async () => {
      const clientMetrics = copilotProviderInstance?.getMetrics?.() ?? {
        requests: 0,
        cacheHitRate: 0,
        cancelRate: 0,
        errorRate: 0,
        acceptRate: 0,
        p50: 0,
        p95: 0,
        p99: 0
      }

      let serverMetrics = null
      try {
        const res = await fetch(`http://localhost:54112/${state.nextjsPort}/api/autocomplete/health`)
        serverMetrics = await res.json()
      } catch (e) {
        log(`Failed to fetch server health: ${e.message}`)
      }

      const channel = vscode.window.createOutputChannel('CodeGPT Autocomplete Metrics')
      channel.clear()
      channel.appendLine('=== CodeGPT Autocomplete — Health Snapshot ===')
      channel.appendLine('')
      channel.appendLine('## Client (VS Code)')
      channel.appendLine(JSON.stringify(clientMetrics, null, 2))
      channel.appendLine('')
      channel.appendLine('## Server (Next.js)')
      channel.appendLine(serverMetrics ? JSON.stringify(serverMetrics, null, 2) : '(unavailable)')
      channel.show()
    }
  )
  context.subscriptions.push(showAutocompleteMetrics)

  // Commands
  const getCode = vscode.commands.registerCommand('codegpt.getCode', async () => {
    const editor = vscode.window.activeTextEditor
    const { document } = editor
    let { languageId } = document

    // terraform exeption
    if (languageId === 'tf') {
      languageId = 'terraform'
    }
    let notebook = false
    if (languageId === 'python') {
      notebook = true
    }

    const cursorPosition = editor.selection.active
    const selection = new vscode.Selection(
      cursorPosition.line,
      0,
      cursorPosition.line,
      cursorPosition.character
    )
    const comment = document.getText(selection)
    const commentCharacter = language.detectLanguage(languageId)
    const oneShotPrompt = languageId
    const errorMessageCursor =
      'Create a comment and leave the cursor at the end of the comment line'
    if (comment === '') {
      vscode.window.showErrorMessage(errorMessageCursor)
      return
    }
    // el caracter existe
    const existsComment = comment.includes(commentCharacter)
    if (!existsComment) {
      vscode.window.showErrorMessage(errorMessageCursor)
      return
    }

    if (commentCharacter === false) {
      vscode.window.showErrorMessage('This language is not supported')
      return
    }
    const finalComment = comment.replaceAll(commentCharacter, oneShotPrompt + ': ')
    if (notebook) {
      getCodeGPTOutput(finalComment, 'getCodeGPT', context, languageId, [], notebook)
    } else {
      startCodeGPTCommand({ type: 'getCodeGPT' })
    }
  })

  const {
    startCodeGPTCommand,
    disposables: {
      commandSelectionCodeGPT,
      commandExplainCodeGPT,
      commandFindProblemsCodeGPT,
      commandUnitTestCodeGPT,
      commandfixCodeGPT,
      commandDocumentCodeGPT,
      commandRefactorCodeGPT,
      commandCopyFromTerminal
    }
  } = createCodeActionCommands({ context })

  // Escuchar cambios de pestañas activas
  vscode.window.onDidChangeActiveTextEditor(async () => {
    state.autoSelectSend()
  })

  // Escuchar cambios de texto en el editor activo
  vscode.window.onDidChangeTextEditorSelection(async (event) => {
    const isAutoSelect = Boolean(await context.globalState.get('autoSelect'))
    const fullText = vscode.window.activeTextEditor.document.getText()
    const lastFullText = await context.globalState.get('lastFullText')
    if (isAutoSelect && fullText !== lastFullText) {
      await context.globalState.update('lastFullText', fullText)
      state.autoSelectSend()
    }

    state.autoSelectSend()
  })

  const commandOnCompletionAccepted = vscode.commands.registerCommand(
    'codegpt.onCompletionAccepted',
    async (choiceText, toSent, autocompleteId) => {
      // Track accept rate locally for the metrics command
      copilotProviderInstance?.recordAccept?.(autocompleteId)
      // Report to server so its health snapshot can attribute accepts per
      // (provider, model). Fire-and-forget — never block the editor.
      if (autocompleteId) {
        fetch(`http://localhost:54112/${state.nextjsPort}/api/autocomplete/accept`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ autocompleteId })
        }).catch(() => {})
      }
      if (toSent) {
        console.log('event sent')
        const codeGPTUserId = await getDistinctId()
        const codeGPTVersion = context.extension.packageJSON.version
        const autocompleteProvider = await context.globalState.get('autocompleteProvider')
        const autocompleteModel = await context.globalState.get('autocompleteModel')
        const codeLanguage = vscode.window.activeTextEditor.document.languageId
        const language = vscode.env.language
        const session = await getSession()
        let accessToken = null
        try {
          accessToken = JSON.parse(session)?.accessToken
        } catch (e) {
          console.log(e)
        }
        sendEvent(
          'autoCompleteAccepted',
          {
            provider: autocompleteProvider,
            model: autocompleteModel,
            language,
            codeLanguage,
            autocompleteId,
            codeGPTVersion,
            userType: !accessToken ? 'anonymous' : 'registered'
          },
          codeGPTUserId,
          accessToken,
          signedDistinctId
        ).catch((err) => console.error(err))
      }

      const editor = vscode.window.activeTextEditor
      if (editor) {
        const document = editor.document
        const position = editor.selection.active // Get current cursor position

        const languageId = document.languageId
        const config = vscode.workspace.getConfiguration('editor', { languageId })
        const defaultFormatter = config.get('defaultFormatter')
        if (!defaultFormatter) return

        // Calculate the range of the inserted text (`choiceText`)
        const start = position.translate(0, -choiceText.length) // Start position before the inserted text
        const end = position // Current position (after insertion)

        const range = new vscode.Range(start, end)

        // Get formatting edits for the range without changing the selection
        const formattingEdits = await vscode.commands.executeCommand(
          'vscode.executeFormatRangeProvider',
          document.uri,
          range,
          {
            tabSize: editor.options.tabSize,
            insertSpaces: editor.options.insertSpaces
          }
        )

        if (formattingEdits && formattingEdits.length > 0) {
          // Apply the formatting edits directly
          await editor.edit((editBuilder) => {
            for (const edit of formattingEdits) {
              editBuilder.replace(edit.range, edit.newText)
            }
          })
        }
      }
    }
  )

  const [commandAboutCodeGPT, commandOpenInBrowserCodeGPT, commandOpenReviewCodeGPT] =
    registerExternalLinkCommands()

  const runJupyterNotebook = vscode.commands.registerCommand(
    'codegpt.runJupyterNotebook',
    async () => {
      const editor = vscode.window.activeTextEditor
      const selection = vscode.window.activeTextEditor.selection
      const selectedText = vscode.window.activeTextEditor.document.getText(selection)

      const { document } = editor
      const { languageId } = document

      if (languageId !== 'python') {
        vscode.window.showErrorMessage(
          'This language is not supported, Code Interpreter only runs on top of the Python language at the moment'
        )
        return
      }

      getCodeGPTOutput(selectedText, 'getCodeGPT', context, languageId, [], true)
    }
  )

  const signUpCodeGPT = vscode.commands.registerCommand('codegpt.signUpCodeGPT', async () => {
    const connectionId = uuidv4()

    vscode.env.openExternal(
      vscode.Uri.parse(
        `https://app.codegpt.co/signup?source=vscode&distinct_id=${codeGPTUserId}&connection_id=${connectionId}`
      )
    )

    const res = await fetch(`https://api.codegpt.co/api/v1/vscode/connection/${connectionId}`)

    const text = await res.text()

    const body = text.split('data: ')[1]

    const json = JSON.parse(body)

    const { access_token: accessToken, refresh_token: refreshToken, expires_at: expiresAt } = json

    await fetch('http://localhost:54112/api/migrate-sqlite', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        type: 'session',
        signed_distinct_id: signedDistinctId,
        access_token: accessToken,
        refresh_token: refreshToken,
        expires_at: expiresAt
      })
    })
  })

  // Smart diff commands — invoked by CodeLens, hover links, and the Next.js
  // client (via the /diffPreview/smart/* endpoints).
  const [diffAcceptSmart, diffRejectSmart, diffAcceptCurrent, diffRejectCurrent] =
    registerSmartDiffCommands()

  // subscribed events
  context.subscriptions.push(
    signUpCodeGPT,
    commandExplainCodeGPT,
    commandRefactorCodeGPT,
    commandDocumentCodeGPT,
    commandFindProblemsCodeGPT,
    // commandQuickFixCodeGPT,
    getCode,
    commandUnitTestCodeGPT,
    commandAboutCodeGPT,
    commandOpenInBrowserCodeGPT,
    runJupyterNotebook,
    commandSelectionCodeGPT,
    commandOnCompletionAccepted,
    commandCopyFromTerminal,
    commandOpenReviewCodeGPT,
    // commandInlineCodeEditCodeGPT,
    acceptDiffCommand,
    rejectDiffCommand,
    diffAcceptSmart,
    diffRejectSmart,
    diffAcceptCurrent,
    diffRejectCurrent,
    commandfixCodeGPT,
    deleteAllGlobalStateCommand
  )

  const isAutoSelect = Boolean(await context.globalState.get('autoSelect'))
  if (isAutoSelect) {
    setTimeout(() => {
      state.autoSelectSend()
    }, 3000)
  }
}

function openChatView() {
  vscode.commands.executeCommand('workbench.view.extension.codegpt-sidebar-view')
}

// This method is called when your extension is deactivated
function deactivate() {
  log('Deactivating CodeGPT Copilot provider')
  if (state.nextServerChild) {
    state.nextServerChild.kill()
    state.nextServerChild = null
  }
}


module.exports = {
  activate,
  deactivate
}
