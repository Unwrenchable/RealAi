const vscode = require('vscode')
const state = require('../state')
const nodeFetch = require('node-fetch')
const { sendEvent } = require('../utils/telemetry.js')
const { getDistinctId, getSession } = require('../utils/distinctId')

const fetch = async (url, options) => {
  try {
    return await nodeFetch(url, options)
  } catch (error) {
    console.error('Error al realizar la solicitud:', error)
    throw error
  }
}

class DiffCodeLensProvider {
  constructor() {
    this.decorationRange = null
  }

  setDecorationRange(range) {
    this.decorationRange = range
  }

  provideCodeLenses(document, token) {
    if (!this.decorationRange) {
      return []
    }

    const start = new vscode.Position(this.decorationRange.start.line, 0)
    const end = new vscode.Position(this.decorationRange.end.line, 0)
    const range = new vscode.Range(start, end)

    return [
      new vscode.CodeLens(range, {
        title: 'Accept',
        command: 'codegpt.acceptDiff'
      }),
      new vscode.CodeLens(range, {
        title: 'Reject',
        command: 'codegpt.rejectDiff'
      })
    ]
  }
}

/**
 * Create and register the inline-diff command group:
 *   codegpt.inlineCodeEditCodeGPT, codegpt.acceptDiff, codegpt.rejectDiff
 * Shares mutable state (decorations/selection/lines/CodeLens) across the 3 commands.
 *
 * @param {Object} deps
 * @param {import('vscode').ExtensionContext} deps.context
 * @returns {{ commandInlineCodeEditCodeGPT: vscode.Disposable, acceptDiffCommand: vscode.Disposable, rejectDiffCommand: vscode.Disposable }}
 */
function createInlineDiffCommands({ context }) {
  let globalDecorations = null
  let globalSelection = null
  // let globalCodeLensProvider = null
  let globalCodeLensDisposable = null
  let globalLines = null

  function getFirstCodeBlockContent(str) {
    const codeBlockRegex = /```(\w+)?\s*([\s\S]*?)\s*```/
    const match = codeBlockRegex.exec(str)
    return match ? match[2] : null
  }

  // Function to show a loading message at the start and completed message at the end
  async function llmText(selectedText, prompt, progress) {
    console.log('llmText')
    progress.report({ message: 'Loading...' })

    const pathProvider = state.provider?.toLowerCase()?.replaceAll(' ', '')
    const model = await context.globalState.get(`${pathProvider}_model`)

    try {
      const llm = await fetch(`http://localhost:54112/${state.nextjsPort}/api/${pathProvider}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          referer: `http://localhost:54112/${state.nextjsPort}`,
          ...(model ? { model: model.model } : {}),
          ...(model && model.fromMarketplace ? { fromMarketplace: model.fromMarketplace } : {})
        },
        body: JSON.stringify({
          messages: [
            {
              role: 'system',
              content: prompt
            },
            {
              role: 'user',
              content: selectedText
            }
          ]
        })
      })

      console.log({ llmStatus: llm.status, model })

      /// /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
      // send telemetry
      const codeGPTVersion = context.extension.packageJSON.version
      const language = vscode.env.language

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

      const signedDistinctId = await getSession().then((session) => session?.signedDistinctId)

      const codeGPTUserId = await getDistinctId()

      console.log({ event: 'inlineCodeEditCodeGPT', isAnonymous, codeGPTUserId })

      await sendEvent(
        'inlineCodeEditCodeGPT',
        {
          prompt,
          language,
          codeGPTVersion,
          userType: isAnonymous ? 'anonymous' : 'registered'
        },
        codeGPTUserId,
        undefined,
        signedDistinctId
      )
      /// /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

      const text = await llm.text()
      if (!llm.ok) {
        vscode.window.showErrorMessage(`
      LLM Error: ${text}
      status: ${llm.status}
      model: "${model.model}"
      provider: "${pathProvider}"
      `)
        throw new Error('LLM Error')
      }

      progress.report({ message: 'Completed.' })

      return getFirstCodeBlockContent(text) || text
    } catch (error) {
      progress.report({ message: 'Error occurred while making the request to LLM.' })
      throw error
    }
  }

  // Register command to fix selection
  const commandInlineCodeEditCodeGPT = vscode.commands.registerCommand(
    'codegpt.inlineCodeEditCodeGPT',
    async () => {
      const editor = vscode.window.activeTextEditor
      if (!editor) {
        return
      }

      const userInput = await vscode.window.showInputBox({
        title: 'Inline Code Edit CodeGPT',
        prompt: 'What do you want to edit?'
      })

      if (!userInput) {
        return
      }

      vscode.window.withProgress(
        {
          location: vscode.ProgressLocation.Notification,
          title: 'CodeGPT',
          cancellable: false
        },
        async (progress) => {
          progress.report({ message: 'Loading...' })

          try {
            const selection = editor.selection
            const selectedText = editor.document.getText(selection)

            const compareString = await llmText(
              selectedText,
              `I am a helpful programming expert assistant. Follow the user's instructions with precision and attention to detail. Minimize any additional text, edit the code in the selected text.
						Don't add any explanations or comments. Just edit the code as the user asked.
						user: ${userInput}
						`,
              progress
            )

            // First, update the text in the editor
            await editor.edit((editBuilder) => {
              editBuilder.replace(selection, compareString)
            })

            const newLines = compareString.split('\n').length - 1
            const lastLineLength = compareString.split('\n').pop().length

            let newSelection = new vscode.Selection(
              selection.start,
              selection.start.translate(newLines, lastLineLength)
            )
            editor.selection = newSelection

            await vscode.commands.executeCommand('editor.action.formatDocument')

            newSelection = editor.selection

            const newSelectionText = editor.document.getText(newSelection)

            const { updatedText, decorations, lines } = getDiff(
              editor,
              selectedText,
              newSelectionText,
              newSelection
            )

            await editor.edit((editBuilder) => {
              editBuilder.replace(newSelection, selectedText)
            })

            newSelection = editor.selection

            const codeLensProvider = new DiffCodeLensProvider()
            codeLensProvider.setDecorationRange(newSelection)
            const codeLensDisposable = vscode.languages.registerCodeLensProvider(
              '*',
              codeLensProvider
            )

            // Save decorations globally and the CodeLens disposable.
            globalDecorations = decorations
            globalSelection = newSelection
            globalCodeLensProvider = codeLensProvider
            globalCodeLensDisposable = codeLensDisposable
            globalLines = lines // Save lines globally

            await applyUpdatedTextAndDecorations(editor, updatedText, decorations, newSelection)

            progress.report({ message: 'Completed.' })
          } catch (error) {
            progress.report({ message: 'Error occurred while processing the selection.' })
            console.error(error)
          }
        }
      )
    }
  )

  // Function to get the difference
  function getDiff(editor, text1, text2, selection) {
    const fakeDiff = require('fake-diff')

    const addedRanges = []
    const removedRanges = []
    let currentLine = selection.start.line

    // Usar git-diff para obtener las diferencias
    const diff = fakeDiff(text1, text2, { hideLines: false })
    const newLines = []

    // Procesar las diferencias
    if (diff) {
      const diffLines = diff.split('\n')
      diffLines.forEach((line) => {
        const added = line.startsWith('+') && !line.startsWith('+++')
        const removed = line.startsWith('-') && !line.startsWith('---')
        if (added || removed) {
          const content = line.substring(3) // Eliminar prefijo + o -
          newLines.push(content) // Almacenar sin eliminar espacios

          const start = new vscode.Position(currentLine, 0)
          const end = new vscode.Position(currentLine, content.length)

          if (added) {
            addedRanges.push(new vscode.Range(start, end))
          } else if (removed) {
            removedRanges.push(new vscode.Range(start, end))
          }

          currentLine++
        } else {
          // Agregar líneas sin cambios
          if (!line.includes('No newline at end of file')) {
            newLines.push(line.substring(3)) // Usar la línea original
            currentLine++
          }
        }
      })
    } else {
      // Si no hay diferencias, simplemente retornar el texto original
      return {
        updatedText: text2, // Asumiendo que text2 es el texto actualizado
        decorations: { added: [], removed: [] },
        lines: text2.split('\n')
      }
    }

    return {
      updatedText: newLines.join('\n'),
      decorations: { added: addedRanges, removed: removedRanges },
      lines: newLines // Retornar las nuevas líneas con indentación preservada
    }
  }

  // Function to apply updated text and decorations
  async function applyUpdatedTextAndDecorations(editor, updatedText, decorations, selection) {
    const grayDecorationType = vscode.window.createTextEditorDecorationType({
      backgroundColor: 'rgba(128, 128, 128, 0.3)',
      isWholeLine: true
    })

    const addedDecorationType = vscode.window.createTextEditorDecorationType({
      backgroundColor: 'rgba(0,255,0,0.25)',
      isWholeLine: true
    })

    const removedDecorationType = vscode.window.createTextEditorDecorationType({
      backgroundColor: 'rgba(255,0,0,0.25)',
      isWholeLine: true
    })

    const finalAddedDecorations = []
    const finalRemovedDecorations = []

    async function applyLineDecoration(range, finalDecorationType, finalDecorationList) {
      // Apply gray decoration
      editor.setDecorations(grayDecorationType, [range])

      // Wait for 35ms before applying the final decoration
      await new Promise((resolve) => setTimeout(resolve, 35))

      // Apply the final decoration
      finalDecorationList.push(range)
      editor.setDecorations(finalDecorationType, finalDecorationList)
    }

    await editor.edit((editBuilder) => {
      editBuilder.replace(selection, updatedText)
    })

    // await vscode.commands.executeCommand('editor.action.formatDocument');

    const allDecorations = [...decorations.added, ...decorations.removed]

    for (const range of allDecorations) {
      const isAdded = decorations.added.includes(range)
      const isRemoved = decorations.removed.includes(range)
      if (isAdded) {
        await applyLineDecoration(range, addedDecorationType, finalAddedDecorations)
      }
      if (isRemoved) {
        await applyLineDecoration(range, removedDecorationType, finalRemovedDecorations)
      }
    }

    // Ensure to clear any remaining gray decorations
    editor.setDecorations(grayDecorationType, [])

    // Capture the original decorations
    const currentDecorations = {
      added: finalAddedDecorations,
      removed: finalRemovedDecorations,
      addedDecorationType,
      removedDecorationType
    }

    const undoDisposable = vscode.workspace.onDidChangeTextDocument((event) => {
      if (event.document === editor.document) {
        // Remove decorations after undo operation
        clearDecorations(editor, currentDecorations)
        // Dispose the listener after usage
        undoDisposable.dispose()
      }
    })
  }

  // Function to clear decorations and disable CodeLens
  function clearDecorations(editor, currentDecorations) {
    if (
      currentDecorations &&
      currentDecorations.addedDecorationType &&
      currentDecorations.removedDecorationType
    ) {
      editor.setDecorations(currentDecorations.addedDecorationType, [])
      editor.setDecorations(currentDecorations.removedDecorationType, [])
    }

    globalDecorations = null
    globalSelection = null
    globalLines = null

    // Disposing the CodeLens
    if (globalCodeLensDisposable) {
      globalCodeLensDisposable.dispose()
      globalCodeLensDisposable = null
    }
  }

  const acceptDiffCommand = vscode.commands.registerCommand('codegpt.acceptDiff', async () => {
    const editor = vscode.window.activeTextEditor
    if (!editor || !globalDecorations || !globalSelection || !globalLines) {
      return
    }

    vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: 'CodeGPT',
        cancellable: false
      },
      async (progress) => {
        progress.report({ message: 'Loading...' })

        try {
          // Filter lines to keep only those that are not in red
          const startLine = globalSelection.start.line
          const linesToRemove = new Set(globalDecorations.removed.map((range) => range.start.line))

          const textToKeep =
            globalLines
              .filter((line, index) => !linesToRemove.has(startLine + index) && line !== undefined)
              .join('\n') + '\n'

          console.log({ globalLines, linesToRemove, textToKeep: textToKeep.split('\n') })

          // Range for the entire selection
          const entireRange = new vscode.Range(
            globalSelection.start.line,
            0,
            globalSelection.start.line + globalLines.length,
            0
          )

          console.log({ entireRange })

          // Replace the entire selected range with the filtered text
          await editor.edit((editBuilder) => {
            editBuilder.replace(entireRange, textToKeep)
          })

          // Clear decorations and the CodeLens
          clearDecorations(editor, globalDecorations)

          await vscode.commands.executeCommand('editor.action.formatDocument')

          /// /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
          // send telemetry
          const codeGPTVersion = context.extension.packageJSON.version
          const language = vscode.env.language

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

          const signedDistinctId = await getSession().then((session) => session?.signedDistinctId)

          const codeGPTUserId = await getDistinctId()

          console.log({ event: 'inlineCodeEditCodeGPTAccept', isAnonymous, codeGPTUserId })

          await sendEvent(
            'inlineCodeEditCodeGPTAccept',
            {
              // prompt,
              language,
              codeGPTVersion,
              userType: isAnonymous ? 'anonymous' : 'registered'
            },
            codeGPTUserId,
            undefined,
            signedDistinctId
          )
          /// /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

          progress.report({ message: 'Changes accepted.' })
        } catch (error) {
          progress.report({ message: 'Error occurred while accepting the changes.' })
        }
      }
    )
  })

  const rejectDiffCommand = vscode.commands.registerCommand('codegpt.rejectDiff', async () => {
    const editor = vscode.window.activeTextEditor
    if (!editor || !globalDecorations || !globalSelection || !globalLines) {
      return
    }

    vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: 'CodeGPT',
        cancellable: false
      },
      async (progress) => {
        progress.report({ message: 'Loading...' })

        try {
          // Filter lines to keep only those that are not in green
          const startLine = globalSelection.start.line
          const linesToRemove = new Set(globalDecorations.added.map((range) => range.start.line))
          const textToKeep =
            globalLines.filter((line, index) => !linesToRemove.has(startLine + index)).join('\n') +
            '\n'

          // Range for the entire selection
          const entireRange = new vscode.Range(
            globalSelection.start.line,
            0,
            globalSelection.start.line + globalLines.length,
            0
          )

          // Replace the entire selected range with the filtered text
          await editor.edit((editBuilder) => {
            editBuilder.replace(entireRange, textToKeep)
          })

          // Clear decorations and the CodeLens
          clearDecorations(editor, globalDecorations)
          await vscode.commands.executeCommand('editor.action.formatDocument')

          /// /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
          // send telemetry
          const codeGPTVersion = context.extension.packageJSON.version
          const language = vscode.env.language

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

          const signedDistinctId = await getSession().then((session) => session?.signedDistinctId)

          const codeGPTUserId = await getDistinctId()

          console.log({ event: 'inlineCodeEditCodeGPTReject', isAnonymous, codeGPTUserId })

          await sendEvent(
            'inlineCodeEditCodeGPTReject',
            {
              prompt,
              language,
              codeGPTVersion,
              userType: isAnonymous ? 'anonymous' : 'registered'
            },
            codeGPTUserId,
            undefined,
            signedDistinctId
          )
          /// /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

          progress.report({ message: 'Changes rejected.' })
        } catch (error) {
          progress.report({ message: 'Error occurred while rejecting the changes.' })
        }
      }
    )
  })

  return { commandInlineCodeEditCodeGPT, acceptDiffCommand, rejectDiffCommand }
}

module.exports = { createInlineDiffCommands }
