function ActorBadge({ actor = 'No actor' }) {
  return (
    <span
      className={`badge rounded-2 border actor-badge actor-${actor.toLowerCase().replace(' ', '-')}`}
    >
      {actor}
    </span>
  )
}

function SymbolBadge({ symbol, color }) {
  const colorClass = `${color?.replace('/', '-') ?? 'neutral'}-symbol`

  return (
    <span className={`badge rounded-2 border symbol-badge ${colorClass}`}>
      {symbol}
    </span>
  )
}

export { ActorBadge, SymbolBadge }
