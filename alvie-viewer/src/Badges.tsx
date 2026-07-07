import type { Actor } from './types'

interface ActorBadgeProps {
  actor?: Actor
}

interface SymbolBadgeProps {
  symbol: string
  color?: string
}

function ActorBadge({ actor = 'No actor' }: ActorBadgeProps) {
  return (
    <span
      className={`badge rounded-2 border actor-badge actor-${actor.toLowerCase().replace(' ', '-')}`}
    >
      {actor}
    </span>
  )
}

function SymbolBadge({ symbol, color }: SymbolBadgeProps) {
  const colorClass = `${color?.replace('/', '-') ?? 'neutral'}-symbol`

  return (
    <span className={`badge rounded-2 border symbol-badge ${colorClass}`}>
      {symbol}
    </span>
  )
}

export { ActorBadge, SymbolBadge }
