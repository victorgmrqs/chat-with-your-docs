import { useEffect, useState } from 'react'

import { SCREENS } from './registry'

type ScreenId = keyof typeof SCREENS

function currentScreen(): ScreenId | null {
  const id = window.location.hash.slice(1)
  return id in SCREENS ? (id as ScreenId) : null
}

export function Preview() {
  const [screen, setScreen] = useState(currentScreen)

  useEffect(() => {
    const onHashChange = () => setScreen(currentScreen())
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  if (screen) return SCREENS[screen].render()

  return (
    <main className="mx-auto flex max-w-140 flex-col gap-4 px-6 py-12">
      <h1 className="m-0 text-title font-bold">Design preview</h1>
      <p className="m-0 text-body-sm text-muted-foreground">
        The handoff screens composed from the components with static data (CWYD-10).
      </p>
      <ul className="m-0 flex list-none flex-col gap-2 p-0">
        {Object.entries(SCREENS).map(([id, { title }]) => (
          <li key={id}>
            <a href={`#${id}`} className="text-body text-primary hover:text-primary-hover">
              {title}
            </a>
          </li>
        ))}
      </ul>
    </main>
  )
}
