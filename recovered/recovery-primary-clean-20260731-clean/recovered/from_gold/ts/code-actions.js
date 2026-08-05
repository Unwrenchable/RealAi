const vscode = require('vscode')
const path = require('path')
const language = require('../utils/language.js')
const ChatSidebarProvider = require('../ChatSidebarProvider')
const { notify, notifyBar } = require('../utils/notify')

function openChatView() {
  vscode.commands.executeCommand('workbench.view.extension.codegpt-sidebar-view')
}

/**
 * Build the shared `startCodeGPTCommand` dispatcher and register the family of
 * code-action commands that forward to it (explain, fix, document, refactor,
 * unit test, find problems, selection, copy from terminal).
 *
 * The dispatcher posts a message to the chat sidebar webview describing what
 * was selected and what kind of action to take; the webview owns the prompt.
 *
 * @param {Object} deps
 * @param {import('vscode').ExtensionContext} deps.context
 * @returns {{ startCodeGPTCommand: Function, disposables: vscode.Disposable[] }}
 */
function createCodeActionCommands({ context }) {
  const startCodeGPTCommand = ({ type, errorText, openChat = true }) => {
    if (openChat) {
      openChatView()
    }

    if (type === 'copyFromTerminal') {
      const chatSidebarProvider = ChatSidebarProvider.getChatInstance(context)
      const selectedText = vscode.window.activeTerminal?.selection
      chatSidebarProvider.view.webview.postMessage({
        type: 'copyFromTerminalCodeGPT',
        ok: true,
        selectedText,
        fileName: 'Terminal',
        language: 'zsh',
        from: 1,
        to: 1,
        lines: 1,
        lineAt: 1
      })
      return
    }

    const selection = vscode.window.activeTextEditor.selection
    let selectedText = errorText || vscode.window.activeTextEditor.document.getText(selection)
    const chatSidebarProvider = ChatSidebarProvider.getChatInstance(context)

    if (type === 'getCodeGPT') {
      const editor = vscode.window.activeTextEditor
      const { document } = editor
      const { languageId } = document

      const cursorPosition = editor.selection.active
      const cursorSelection = new vscode.Selection(
        cursorPosition.line,
        0,
        cursorPosition.line,
        cursorPosition.character
      )
      const comment = document.getText(cursorSelection)
      const commentCharacter = language.detectLanguage(languageId)
      const oneShotPrompt = languageId
      const errorMessageCursor =
        'Create a comment and leave the cursor at the end of the comment line'
      if (comment === '') {
        vscode.window.showErrorMessage(errorMessageCursor)
        return
      }
      const existsComment = comment.includes(commentCharacter)
      if (!existsComment) {
        vscode.window.showErrorMessage(errorMessageCursor)
        return
      }

      const finalComment = comment.replaceAll(commentCharacter, oneShotPrompt + ': ')
      selectedText = finalComment
    }

    if (selectedText === '' && type !== 'selectionCodeGPT') {
      notify('To use this function, please select some text first.', 'error')
    } else {
      const editor = vscode.window.activeTextEditor
      const { document } = editor
      notifyBar('Copying to Chat textarea')
      if (!chatSidebarProvider.view) {
        openChatView()
        setTimeout(() => {
          chatSidebarProvider.view.webview.postMessage({
            type,
            ok: true,
            selectedText,
            fileName: path.basename(vscode.window.activeTextEditor.document.fileName),
            path: vscode.workspace.asRelativePath(document.uri.fsPath),
            language: vscode.window.activeTextEditor.document.languageId,
            from: vscode.window.activeTextEditor.selection.start,
            to: vscode.window.activeTextEditor.selection.end,
            lines: vscode.window.activeTextEditor.document.lineCount,
            lineAt: vscode.window.activeTextEditor.document.lineAt(selection.active)
          })
        }, 1000)
      } else {
        const innerEditor = vscode.window.activeTextEditor
        const innerDoc = innerEditor.document
        chatSidebarProvider.view.webview.postMessage({
          type,
          ok: true,
          selectedText,
          fileName: path.basename(vscode.window.activeTextEditor.document.fileName),
          path: vscode.workspace.asRelativePath(innerDoc.uri.fsPath),
          language: vscode.window.activeTextEditor.document.languageId,
          from: vscode.window.activeTextEditor.selection.start,
          to: vscode.window.activeTextEditor.selection.end,
          lines: vscode.window.activeTextEditor.document.lineCount,
          lineAt: vscode.window.activeTextEditor.document.lineAt(selection.active)
        })
      }
    }
  }

  const commandSelectionCodeGPT = vscode.commands.registerCommand(
    'codegpt.selectionCodeGPT',
    async () => {
      startCodeGPTCommand({ type: 'selectionCodeGPT' })
    }
  )

  const commandExplainCodeGPT = vscode.commands.registerCommand(
    'codegpt.explainCodeGPT',
    async () => {
      startCodeGPTCommand({ type: 'explainCodeGPT' })
    }
  )

  const commandFindProblemsCodeGPT = vscode.commands.registerCommand(
    'codegpt.findProblemsCodeGPT',
    async () => {
      startCodeGPTCommand({ type: 'fixCodeGPT' })
    }
  )

  const commandUnitTestCodeGPT = vscode.commands.registerCommand(
    'codegpt.unitTestCodeGPT',
    async () => {
      startCodeGPTCommand({ type: 'unitTestCodeGPT' })
    }
  )

  const commandfixCodeGPT = vscode.commands.registerCommand('codegpt.fixCodeGPT', async () => {
    startCodeGPTCommand({ type: 'fixCodeGPT' })
  })

  const commandDocumentCodeGPT = vscode.commands.registerCommand(
    'codegpt.documentCodeGPT',
    async () => {
      startCodeGPTCommand({ type: 'documentCodeGPT' })
    }
  )

  const commandRefactorCodeGPT = vscode.commands.registerCommand(
    'codegpt.refactorCodeGPT',
    async () => {
      startCodeGPTCommand({ type: 'refactorCodeGPT' })
    }
  )

  const commandCopyFromTerminal = vscode.commands.registerCommand(
    'codegpt.copyFromTerminal',
    async () => {
      startCodeGPTCommand({ type: 'copyFromTerminal' })
    }
  )

  return {
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
  }
}

module.exports = { createCodeActionCommands, openChatView }
