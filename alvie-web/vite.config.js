import { createReadStream, stat } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const parsedOutputDirectory = fileURLToPath(
  new URL('../parsed-output', import.meta.url),
)

// Mirror the read-only /parsed-output route provided by Nginx in Docker.
const serveParsedOutput = {
  name: 'serve-parsed-output',
  configureServer(server) {
    server.middlewares.use('/parsed-output', (request, response, next) => {
      const pathname = new URL(request.url ?? '/', 'http://localhost').pathname
      const fileName = decodeURIComponent(pathname).replace(/^\/+/, '')

      // Only serve JSON files directly inside the shared directory.
      if (!fileName.endsWith('.json') || fileName.includes('/')) return next()

      const filePath = resolve(parsedOutputDirectory, fileName)
      stat(filePath, (error, details) => {
        if (error || !details.isFile()) return next()

        response.setHeader('Content-Type', 'application/json; charset=utf-8')
        createReadStream(filePath).pipe(response)
      })
    })
  },
}

export default defineConfig({
  plugins: [react(), serveParsedOutput],
})
