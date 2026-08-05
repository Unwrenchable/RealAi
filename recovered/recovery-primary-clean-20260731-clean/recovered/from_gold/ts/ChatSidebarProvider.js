const vscode = require('vscode')
const { sendEvent } = require('./utils/telemetry')
const appVersion = require('../package.json').version
const { openExternalView } = require('./utils/nextjs_webview')
// const getRemoteVersion = require('./utils/online_version')

class ChatSidebarProvider {
  constructor(context, port) {
    this._view = null
    this._context = context
    this.refreshToken = context.secrets.get('refreshToken')
    this._uuid = context.globalState.get('uuid')
    this._port ??= port
    this._url = `http://localhost:54112/${this._port}/`
  }

  static getChatInstance(context, port) {
    if (!ChatSidebarProvider._instance && context) {
      ChatSidebarProvider._instance = new ChatSidebarProvider(context, port)
      console.log('Congratulations, your extension "codegpt" is now active!')
    }
    return ChatSidebarProvider._instance
  }

  get view() {
    return this._view
  }

  get clearChat() {
    this._view.webview.postMessage({ type: 'clearChat' })
  }

  resolveWebviewView(webviewView) {
    this._view = webviewView
    webviewView.webview.options = {
      // Allow scripts in the webview
      enableScripts: true
    }

    this._update()

    webviewView.webview.html = this._getHtmlForWebview(webviewView.webview)
  }

  async _update() {
    if (!this._view) {
      return
    }

    // TODO: remove, trae la version de vscode desde el r2
    // const newVersion = await getRemoteVersion()

    this._view.webview.html = this._getHtmlForWebview(this._view.webview)

    this._view.webview.onDidReceiveMessage(async (data) => {
      if (data.command === 'openUrl') {
        vscode.env.openExternal(vscode.Uri.parse(data.url))
      }

      if (data.command === 'download') {
        vscode.commands.executeCommand('extension.open', 'DanielSanMedium.dscodegpt')
      }
      if (data.command === 'openWebviewUrl') {
        openExternalView(data.url)
      }
    })
  }

  _getHtmlForWebview(webview) {
    // Manejo del fetch fuera del template literal
    const fetchScript = `
      const setStatus = (element, mark, hint) => {
        if(!element) return
        element.textContent = mark
        element.style.color = mark === '✓' ? '' : '#ff6b6b'
        if(hint) element.title = hint
      }

      const showConnectionError = (serverMark, portMark, message) => {
        connectionError.style.display = 'grid';
        loadingText.style.display = 'none';
        iframe.style.display = 'none'

        setStatus(document.getElementById('nextStatus'), serverMark, message)
        setStatus(document.getElementById('portStatus'), portMark, message)

        const portErrorMessage = document.getElementById('portErrorMessage')
        if(portErrorMessage) {
          portErrorMessage.style.display = 'block'
          portErrorMessage.textContent = message
        }

        const errorLink = document.getElementById('errorLink')
        const downloadLink = document.getElementById('Download')
        downloadLink?.addEventListener('click', function(event) {
          event.preventDefault()
          vscode.postMessage({
            command: 'download',
          })
        })
        errorLink?.addEventListener('click', function(event) {
          event.preventDefault()
          vscode.postMessage({
            command: 'openWebviewUrl',
            url: 'https://docs.codegpt.co/docs/tutorial-basics/troubleshooting'
          })
        })
      }

      fetch('http://localhost:54112/api/distinct_id').then(response => {
        if(response.status === 200){
          const errorHandlingDiv = document.getElementById('errorHandlingDiv')
          errorHandlingDiv.style.display = 'none'
          iframe.style.display = 'block'

          setStatus(document.getElementById('nextStatus'), '✓')
          setStatus(document.getElementById('portStatus'), '✓')
        } else {
          // El server respondió: está corriendo y el puerto abierto. El fallo
          // es interno — marcarlo ✗ acá mentía y desorientaba el diagnóstico.
          showConnectionError('✓', '✓',
            'Server is running but responded with HTTP ' + response.status +
            ' (internal error). Open the "CodeGPT Server" output channel in VS Code for details.')
        }
      }).catch(() => {
        showConnectionError('✗', '✗', 'Server is not running on localhost:54112')
      })
    `

    fetch('http://localhost:54112/api/distinct_id')
      .then(async (response) => {
        if (!response.ok) {
          console.log('Error fetching distinct_id')
          throw new Error('Error fetching distinct_id')
        }
        const res = await response.json()
        const userId = res.distinct_id
        this._context.globalState.set('codeGPTUserId', userId)
        console.log('new codegpt connection')
        sendEvent(
          'userConnection',
          {
            platform: process.platform, // "darwin"
            arch: process.arch, // "arm64"
            versions: process.versions, // package versions ej: [{ node: "18.18.2", ... }]
            VSCODE_PID: process.env?.VSCODE_PID, // je: "59512"
            XPC_SERVICE_NAME: process.env?.XPC_SERVICE_NAME, // ej: "application.com.
            editorVersion: vscode.version, // "1.89.0-insider"
            vscodeMachineId: vscode.env.machineId, // ej: "9c95..." (64 caracteres)
            vscodeSessionId: vscode.env.sessionId, // ej: "806e..." (48 caracteres)
            vscodeAppName: vscode.env.appName, // ej: "Visual Studio Code - Insiders"
            vscodeLanguage: vscode.env.language, // ej: "en"
            vscodeIsNewAppInstall: vscode.env.isNewAppInstall, // boolean
            vscodeappHost: vscode.env.appHost, // ej: "desktop",
            codegpt_version: appVersion,
            source: 'vscode'
          },
          userId
        )
      })
      .catch(() => {
        const userId = this._context.globalState.get('codeGPTUserId')
        sendEvent(
          'error',
          {
            errorType: 'nextConnectionError',
            errorSource: 'starterError',
            platform: process.platform, // "darwin"
            arch: process.arch, // "arm64"
            versions: process.versions, // package versions ej: [{ node: "18.18.2", ... }]
            VSCODE_PID: process.env?.VSCODE_PID, // je: "59512"
            XPC_SERVICE_NAME: process.env?.XPC_SERVICE_NAME, // ej: "application.com.microsoft.VSCodeInsiders.96737695.96737701"
            editorVersion: vscode.version, // "1.89.0-insider"
            vscodeMachineId: vscode.env.machineId, // ej: "9c95..." (64 caracteres)
            vscodeSessionId: vscode.env.sessionId, // ej: "806e..." (48 caracteres)
            vscodeAppName: vscode.env.appName, // ej: "Visual Studio Code - Insiders"
            vscodeLanguage: vscode.env.language, // ej: "en"
            vscodeIsNewAppInstall: vscode.env.isNewAppInstall, // boolean
            vscodeappHost: vscode.env.appHost, // ej: "desktop"
            codegpt_version: appVersion,
            source: 'vscode'
          },
          userId
        )
      })

    const nonce = this._getNonce()
    // const nodeVersion = Number(process.versions.node.replace('.', ''))
    // const vscodeVersion = Number(vscode.version.replace('.', ''))

    return `
  <!DOCTYPE html>
  <html lang="en">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self' http://localhost:54112; frame-src ${this._url}; img-src https: data:; style-src 'unsafe-inline' ${webview.cspSource}; script-src 'nonce-${nonce}';">
    <title>VSCode Webview</title>
    <style>
      * { box-sizing: border-box; }
      html {
        font-size: 16px;
      }
      html, body, iframe {
        border: 0;
        padding: 0;
        margin: 0;
        transform: none;
        font-weight: normal;
        width: 100%;
        height: 100%;
        min-width: auto;
        min-height: auto;
        max-width: none;
        outline: 0;
        display: block;
      }
      body {
        font-size: 1rem;
      }
      .animate-opening {
        animation: fadeIn 0.33s ease;
      }
      p {
        margin: 0;
        padding: 0;
      }
      .container {
        padding: 0 0.5rem 0.5rem 0.5rem;
        display: grid;
        gap: .5rem;
        width: 20rem;
      }
      .card {
        padding: 1.5rem;
        display: grid;
        gap: .5rem;
        width: 20rem;
        background-color: #393f466b;
        border-radius: 1rem;
      }
      .flex-row {
        display: flex;
        flex-direction: row;
        justify-content: space-between;
      }
      .grid {
          display: grid;
          grid-template-columns: auto 3rem 3rem 4rem;
          gap: 0.5rem;
          grid-template-rows: auto;
          text-align: right;
          color: white;
      }
      .grid:last-child {
        border-bottom: 1px solid #2e3339;
        padding-bottom: .5rem;
      }
      .grid span:first-child {
        text-align: left;
      }
      @keyframes fadeIn {
        from {
          opacity: 0;
          transform: translateY(10px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }
    </style>
  </head>
  <body style="font-size: 12px; background: black; position: relative; margin: 0; padding: 0; border: 0;">
    <iframe id="myIframe" src="${this._url}" style="position:relative; width: 100%; height: 100vh; border: none; z-index: 9;" sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-downloads allow-modals" allow="clipboard-read; clipboard-write; clipboard-read *; clipboard-write *"></iframe>

    <div id="errorHandlingDiv" style="top:0;left:0;right:0;bottom:0;width: 100vw; height: 100vh; display: flex;flex-direction: column;justify-content: center;align-items: center;position: absolute;color: gray;font-size: 12px;text-align: center;z-index: 1;">

    <div style="display: grid; gap: .5rem; justify-content: center; align-items: center;">

      <div id="loadingText" style="display: grid; gap: .5rem; align-items: center; justify-content: center;">
        <svg fill='white' height="1rem" xmlns='http://www.w3.org/2000/svg' viewBox='0 0 301.9 40'><path d='M40,40V32H8V8H40V0H8A8,8,0,0,0,0,8V32a8,8,0,0,0,8,8Z' /><path d='M76,40a8,8,0,0,0,8-8V8a8,8,0,0,0-8-8H52a8,8,0,0,0-8,8V32a8,8,0,0,0,8,8ZM52,8H76V32H52Z' /><path d='M119.93,40a8,8,0,0,0,8-8V8a8,8,0,0,0-8-8H88V40ZM96,8h24V32H96Z' /><path d='M171.91,0h-32a8,8,0,0,0-8,8V32a8,8,0,0,0,8,8h32V32h-32V24h32V16h-32V8h32Z' /><path d='M215.9,0h-32a8,8,0,0,0-8,8V32a8,8,0,0,0,8,8h24a8,8,0,0,0,8-8V16h-24v8h16v8h-24V8h32Z' /><path d='M251.9,0h-32V40h8V24h24a8,8,0,0,0,8-8V8A8,8,0,0,0,251.9,0Zm-24,16V8h24v8Z' /><path d='M301.9,0h-40V8h16V40h8V8h16Z' /></svg>
        <div style="display: flex; gap: .5rem; align-items: center; justify-content: center;">
          <img width="14px" alt="loader" src="data:image/gif;base64,R0lGODlhAAEAAbMPAMrKyoiIiLGxsevr67+/v9TU1H9/fz8/P2pqalVVVSoqKpSUlKmpqRUVFf///wAAACH/C05FVFNDQVBFMi4wAwEAAAAh/wtYTVAgRGF0YVhNUDw/eHBhY2tldCBiZWdpbj0i77u/IiBpZD0iVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkIj8+IDx4OnhtcG1ldGEgeG1sbnM6eD0iYWRvYmU6bnM6bWV0YS8iIHg6eG1wdGs9IkFkb2JlIFhNUCBDb3JlIDUuNi1jMTExIDc5LjE1ODMyNSwgMjAxNS8wOS8xMC0wMToxMDoyMCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvIiB4bWxuczp4bXBNTT0iaHR0cDovL25zLmFkb2JlLmNvbS94YXAvMS4wL21tLyIgeG1sbnM6c3RSZWY9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9zVHlwZS9SZXNvdXJjZVJlZiMiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIENDIDIwMTUgKE1hY2ludG9zaCkiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6QUU4MEFBRTQxQkFCMTFFNjkyRTJENEE2MjgwNzUzNUUiIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6QUU4MEFBRTUxQkFCMTFFNjkyRTJENEE2MjgwNzUzNUUiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpBRTgwQUFFMjFCQUIxMUU2OTJFMkQ0QTYyODA3NTM1RSIgc3RSZWY6ZG9jdW1lbnRJRD0ieG1wLmRpZDpBRTgwQUFFMzFCQUIxMUU2OTJFMkQ0QTYyODA3NTM1RSIvPiA8L3JkZjpEZXNjcmlwdGlvbj4gPC9yZGY6UkRGPiA8L3g6eG1wbWV0YT4gPD94cGFja2V0IGVuZD0iciI/PgH//v38+/r5+Pf29fTz8vHw7+7t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" />
          <span>Loading</span>
        </div>
      </div>

    <div class="card" id="connectionError" style='display: none; text-align: left;'>

    <div>
      <svg fill='white' height="1rem" xmlns='http://www.w3.org/2000/svg' viewBox='0 0 301.9 40'><path d='M40,40V32H8V8H40V0H8A8,8,0,0,0,0,8V32a8,8,0,0,0,8,8Z' /><path d='M76,40a8,8,0,0,0,8-8V8a8,8,0,0,0-8-8H52a8,8,0,0,0-8,8V32a8,8,0,0,0,8,8ZM52,8H76V32H52Z' /><path d='M119.93,40a8,8,0,0,0,8-8V8a8,8,0,0,0-8-8H88V40ZM96,8h24V32H96Z' /><path d='M171.91,0h-32a8,8,0,0,0-8,8V32a8,8,0,0,0,8,8h32V32h-32V24h32V16h-32V8h32Z' /><path d='M215.9,0h-32a8,8,0,0,0-8,8V32a8,8,0,0,0,8,8h24a8,8,0,0,0,8-8V16h-24v8h16v8h-24V8h32Z' /><path d='M251.9,0h-32V40h8V24h24a8,8,0,0,0,8-8V8A8,8,0,0,0,251.9,0Zm-24,16V8h24v8Z' /><path d='M301.9,0h-40V8h16V40h8V8h16Z' /></svg>

      <small style='font-size: 12px;'>v${appVersion}</small>
    </div>

      <p style="
      margin: 0.5rem 0 0.75rem;
      text-align: left;
      width: 100%;
      max-width: 20rem;
      font-size: 1.25rem;
      letter-spacing: 0.1px;
      color: white;">Unable to connect to the extension services</p>

      <b style='margin-right: auto; letter-spacing: 0.33px; display: none;'>Minimum Specifications</b>

      <p class="grid header .grid" style="border-bottom: 1px solid #2e3339; padding-bottom: .5rem; color:gray;">
        <span>Requirement</span>
        <span>Required</span>
        <span>System</span>
        <span>Status</span>
      </p>

      <p class="grid">
        <span>VSCODE</span>
        <span>^1.82.0</span>
        <span>${vscode.version}</span>
        <span id="vscodeStatus">✓</span>
      </p>

      <p class="grid">
        <span>Vscode Node</span>
        <span>>=18.0.0</span>
        <span>${process.versions.node}</span>
        <span id="nodeStatus">✓</span>
      </p>

      <p class="grid">
        <span>Server</span>
        <span>localhost</span>
        <span></span>
        <span id="nextStatus">⏳</span>
      </p>

      <p class="grid">
        <span>Port</span>
        <span>54112</span>
        <span></span>
        <span id="portStatus">-</span>
      </p>

      <!-- Agregar este div para mostrar el error -->
      <div id="portErrorMessage" style="display: none; margin-top: 0.5rem; padding: 0.5rem; background-color: #ff6b6b20; border: 1px solid #ff6b6b; border-radius: 0.25rem; color: #ff6b6b; font-size: 0.75rem; word-wrap: break-word;">
      </div>

      <hr style='border: 0px; border-top: 1px solid #2e3339; width: 100%; margin: .5rem 0;'>

      <p id="errorLink" style=" border: 0; outline: none; color: gray; width: 100%; max-width: 100%; font-size: 0.75rem; cursor: pointer; text-decoration: underline; text-align: center;">
        Troubleshooting
      </p>

    </div>

  </div>

  <span
    style='with: 100;
      font-size: 12px;
      opacity: .8;
      position: absolute;
      bottom: .5rem;
    '
  >v${appVersion}</span>

    <script nonce="${nonce}">
      const vscode = acquireVsCodeApi();
      const iframe = document.getElementById('myIframe');
      const connectionError = document.getElementById('connectionError');
      const loadingText = document.getElementById('loadingText');
      const downloadButton = document.getElementById('Download');
      
      ${fetchScript}

      const promptTypeAllowed = [
        'askCodeGPT', 'explainCodeGPT', 'refactorCodeGPT', 'documentCodeGPT', 'fixCodeGPT', 'getCodeGPT', 'unitTestCodeGPT', 'clearChat', 'quickFixCodeGPT', 'selectionCodeGPT', 'copyFromTerminalCodeGPT'
      ]
      const postMessageFunction = () => {
        window.addEventListener('message', event => {
          if (promptTypeAllowed.includes(event?.data?.type)) {
            const promptType = event.data.type.replace('CodeGPT', '');
            iframe.contentWindow.postMessage({
              command: event.type,
              fileName: event.data.fileName,
              position: event.data.position,
              language: event.data.language,
              from: event.data.from,
              to: event.data.to,
              lines: event.data.lines,
              lineAt: event.data.lineAt,
              path: event.data.path,
              promptType,
              ...(event.data.selectedText ? { selectedText: event.data.selectedText } : {})
            }, '*');
          }
          if (event?.data?.type === 'syncProvider') {
            iframe.contentWindow.postMessage({
              promptType: 'syncProvider',
              value: event.data.value,
            }, '*');
          }
        });
      }
      // Escucha los mensajes enviados desde el iframe
      iframe.addEventListener('load', () => {
        postMessageFunction()
        setTimeout(() => {
        postMessageFunction()
        }, 5000);
      });

      // Drag & drop de imagen sobre el webview wrapper, reenvío al iframe.
      // Nota: VSCode requiere mantener Shift mientras se arrastra para que el
      // evento llegue al webview (PR microsoft/vscode#209211).
      const dropOverlay = document.createElement('div')
      dropOverlay.style.cssText = 'position:fixed;inset:0;display:none;align-items:center;justify-content:center;background:rgba(0,0,0,.6);color:#fff;font-size:14px;z-index:99999;pointer-events:none;border:2px dashed rgba(255,255,255,.4);text-align:center;padding:1rem;'
      dropOverlay.textContent = 'Hold Shift while dragging to drop image'
      document.body.appendChild(dropOverlay)

      const sendImageToIframe = (file) => {
        if (!file || !file.type || !file.type.startsWith('image/')) return
        if (file.size > 1024 * 1024 * 5) return
        const reader = new FileReader()
        reader.onload = () => {
          iframe.contentWindow.postMessage({
            promptType: 'droppedImage',
            base64: reader.result,
            name: file.name || ('dropped-' + Date.now() + '.png')
          }, '*')
        }
        reader.readAsDataURL(file)
      }
      const hasFiles = (e) => e.dataTransfer && e.dataTransfer.types && e.dataTransfer.types.indexOf && e.dataTransfer.types.indexOf('Files') !== -1
      let hideTimer = null
      const showOverlay = () => {
        dropOverlay.style.display = 'flex'
        if (hideTimer) { clearTimeout(hideTimer); hideTimer = null }
        // si no llegan más eventos de drag en 1500ms, asumimos que el usuario soltó fuera o canceló
        hideTimer = setTimeout(() => { dropOverlay.style.display = 'none'; hideTimer = null }, 1500)
      }
      const hideOverlay = () => {
        if (hideTimer) { clearTimeout(hideTimer); hideTimer = null }
        dropOverlay.style.display = 'none'
      }
      const onDragEnter = (e) => { if (hasFiles(e)) showOverlay() }
      const onDragOver = (e) => {
        if (!hasFiles(e)) return
        e.preventDefault()
        e.stopPropagation()
        showOverlay()
      }
      const onDrop = (e) => {
        hideOverlay()
        if (!e.dataTransfer || !e.dataTransfer.files || e.dataTransfer.files.length === 0) return
        const file = Array.from(e.dataTransfer.files).find((f) => f.type && f.type.startsWith('image/'))
        if (!file) return
        e.preventDefault()
        e.stopPropagation()
        sendImageToIframe(file)
      }
      window.addEventListener('dragenter', onDragEnter, true)
      window.addEventListener('dragover', onDragOver, true)
      window.addEventListener('drop', onDrop, true)
      window.addEventListener('dragend', hideOverlay, true)
      window.addEventListener('mouseup', hideOverlay, true)
    </script>
  </body>
</html>
`
  }

  _getNonce() {
    let text = ''
    const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    for (let i = 0; i < 32; i++) {
      text += possible.charAt(Math.floor(Math.random() * possible.length))
    }
    return text
  }

  static register(context) {
    const provider = ChatSidebarProvider.getChatInstance(context)
    context.subscriptions.push(
      vscode.window.registerWebviewViewProvider('codegpt-sidebar', provider, {
        webviewOptions: {
          retainContextWhenHidden: true
        }
      })
    )
  }

  changeUrl(url) {
    this._url = url
    // console.log("changeUrl", this._url, url);
    this._update()
  }
}

ChatSidebarProvider.viewType = 'miExtension.sidebar'

module.exports = ChatSidebarProvider
