# ALVIE VIEWER

### Starting

```bash
npm create vite@latest alvie-cli-viewer -- --template react
cd alvie-cli-viewer
npm install
npm install bootstrap
```

#### Commands

```bash
# while developing
npm run dev 

# before realising
npm run build 

# verify release
npm run preview
```

Add `dist` to alvie-cli main project and start a python server in the root of the project to test the release.

### Regex search

Example

```bash
# Search for hypotheses 1-3
\bhypothesis [1-3]\b

# Search for runs 11000 - 12000
\brun 11\d{3}\b

# Search for multiple patterns
<regex1>|<regex2>|<regex3>
```