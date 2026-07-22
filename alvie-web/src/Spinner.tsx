interface SpinnerProps {
  // Bootstrap contextual colour (e.g. "primary", "light", "danger").
  variant?: string
  // "sm" renders the small button-sized spinner; undefined is the default size.
  size?: 'sm'
  // Accessible label announced to assistive technology.
  label?: string
  className?: string
}

// Thin wrapper around Bootstrap's spinner so every network call shows the
// same loading indicator.
function Spinner({
  variant = 'primary',
  size,
  label = 'Loading…',
  className = '',
}: SpinnerProps) {
  const classes = [
    'spinner-border',
    size === 'sm' ? 'spinner-border-sm' : '',
    `text-${variant}`,
    className,
  ]
    .filter(Boolean)
    .join(' ')

  return (
    <span className={classes} role="status" aria-hidden={label ? undefined : true}>
      {label && <span className="visually-hidden">{label}</span>}
    </span>
  )
}

export default Spinner
