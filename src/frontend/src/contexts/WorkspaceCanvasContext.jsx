import { createContext, useContext, useState, useCallback } from 'react'

const WorkspaceCanvasContext = createContext(null)

export function WorkspaceCanvasProvider({ children }) {
  const [qasmString, setQasmString] = useState('')
  const [qasmValid, setQasmValid] = useState(false)
  const [isDirty, setIsDirty] = useState(false)
  const [currentTaskId, setCurrentTaskId] = useState(null)
  const [logLines, setLogLines] = useState([])

  const setQasm = useCallback((str, valid) => {
    setQasmString(str ?? '')
    setQasmValid(!!valid)
  }, [])

  const setDirty = useCallback((dirty) => {
    setIsDirty(!!dirty)
  }, [])

  const setTaskId = useCallback((taskId) => {
    setCurrentTaskId(taskId ?? null)
    if (!taskId) setLogLines((prev) => prev)
  }, [])

  const appendLog = useCallback((line) => {
    setLogLines((prev) => prev.slice(-999).concat(line))
  }, [])

  const clearLog = useCallback(() => {
    setLogLines([])
  }, [])

  const value = {
    qasmString,
    qasmValid,
    isDirty,
    setQasm,
    setDirty,
    currentTaskId,
    setTaskId,
    logLines,
    appendLog,
    clearLog,
  }
  return (
    <WorkspaceCanvasContext.Provider value={value}>
      {children}
    </WorkspaceCanvasContext.Provider>
  )
}

export function useWorkspaceCanvas() {
  const ctx = useContext(WorkspaceCanvasContext)
  return ctx
}
