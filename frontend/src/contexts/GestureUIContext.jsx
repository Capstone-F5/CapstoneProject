import { createContext, useContext } from 'react'

const GestureUIContext = createContext({ gestureEnabled: true, fingerEnabled: true })

export function GestureUIProvider({ enabled, fingerEnabled, children }) {
  return (
    <GestureUIContext.Provider value={{ gestureEnabled: enabled, fingerEnabled }}>
      {children}
    </GestureUIContext.Provider>
  )
}

export function useGestureUIEnabled() {
  return useContext(GestureUIContext).gestureEnabled
}

export function useFingerUIEnabled() {
  return useContext(GestureUIContext).fingerEnabled
}
