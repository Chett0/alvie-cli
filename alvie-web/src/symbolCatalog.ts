// Import from shared config folder
import rawSymbolCatalog from '../../config/output_symbols.json'
import type { SymbolCatalog } from './types'

// Keep one local adapter so the viewer depends on the shared catalog in one place.
const symbolCatalog = rawSymbolCatalog as unknown as SymbolCatalog

export default symbolCatalog
