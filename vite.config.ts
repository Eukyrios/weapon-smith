import { defineConfig, type Plugin } from 'vite'
import fs from 'node:fs'
import path from 'node:path'

/**
 * Serve <dir>/index.html for a bare directory URL.
 *
 * GitHub Pages does this itself, so /catalogue/ resolves once deployed — that
 * folder now holds the forwarding pages for the site's old addresses. Vite's
 * dev server does not, and would 404 on an address that works in production.
 * Without this, dev and production disagree about the same URL — which hides
 * the problem until deploy.
 */
function dirIndex(): Plugin {
  return {
    name: 'dir-index',
    configureServer(server) {
      server.middlewares.use((req, _res, next) => {
        const url = req.url?.split('?')[0]
        if (url && url.endsWith('/') && fs.existsSync(path.join('.' + url, 'index.html'))) {
          req.url = url + 'index.html'
        }
        next()
      })
    },
  }
}

/**
 * The site is generated HTML committed at the repo root, because GitHub Pages
 * serves it straight from there with no build step. Vite is here for `npm run
 * dev` and for the TypeScript the data is authored in — not to build the site.
 */
export default defineConfig({
  root: '.',
  publicDir: false,
  // Multi-page, not an app: without this Vite answers a missing file with
  // index.html and a 200, so a mistyped image path renders as HTML instead of
  // failing. 'mpa' makes a 404 an honest 404.
  appType: 'mpa',
  plugins: [dirIndex()],
  server: { open: '/' },
})
