# Sprint Sarthi Pro

A complete, responsive sprint-planning front end built with **React, TypeScript, and Vite**.

This version is designed to solve the layout problems in the earlier screen:

- The application uses the full browser width; there is no fixed desktop container leaving empty space.
- The main workspace and right rail resize independently.
- The dashboard becomes one column before the form becomes cramped.
- The desktop sidebar can collapse, while tablet and mobile devices use a drawer.
- Sidebar items include descriptions, counters, active states, a workspace switcher, a quick-create action, and sprint-readiness information.
- Every sidebar option opens a populated module instead of a blank placeholder.
- Font sizes, controls, spacing, contrast, keyboard focus, empty states, and mobile behaviour have been designed for day-to-day usability.

## Technology

- React 19
- TypeScript
- Vite 8
- Lucide React icons
- Plain organized CSS with design tokens
- No Tailwind, Bootstrap, or paid UI dependency

## 1. Requirements

Use one of the Node.js versions supported by the included Vite release:

- Node.js 20.19 or newer within the Node 20 line
- Node.js 22.12 or newer
- A newer supported Node.js release

Check your installation in Git Bash:

```bash
node --version
npm --version
```

## 2. Run on Windows using Git Bash

Extract the project, open Git Bash inside the extracted folder, and run:

```bash
cd /c/Users/YOUR_NAME/Downloads/sprint-sarthi-pro
npm install
npm run dev
```

The browser opens automatically. The default development address is:

```text
http://localhost:5173
```

You can also run the included Windows-friendly helper:

```bash
bash start-git-bash.sh
```

The helper validates Node.js, installs dependencies when `node_modules` is missing, and starts Vite.

## 3. Production build

Run a TypeScript check and production build:

```bash
npm run build
```

The optimized files are generated in:

```text
dist/
```

Preview that production build locally:

```bash
npm run preview
```

Run only the TypeScript check:

```bash
npm run check
```

Remove the generated `dist` folder:

```bash
npm run clean
```

## 4. Project structure

```text
sprint-sarthi-pro/
├── public/
│   └── favicon.svg
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Avatar.tsx
│   │   │   ├── Button.tsx
│   │   │   ├── CommandPalette.tsx
│   │   │   ├── Logo.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── NewSprintModal.tsx
│   │   │   ├── Panel.tsx
│   │   │   ├── ProgressRing.tsx
│   │   │   ├── StatusBadge.tsx
│   │   │   └── ToastStack.tsx
│   │   ├── dashboard/
│   │   │   ├── AICopilot.tsx
│   │   │   ├── ActivityFeed.tsx
│   │   │   ├── RecentWork.tsx
│   │   │   ├── RequirementsWorkspace.tsx
│   │   │   ├── SprintPulse.tsx
│   │   │   ├── StatsGrid.tsx
│   │   │   └── WelcomeHero.tsx
│   │   ├── layout/
│   │   │   ├── AppShell.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Topbar.tsx
│   │   └── pages/
│   │       ├── DashboardPage.tsx
│   │       └── ModulePage.tsx
│   ├── data/
│   │   ├── dashboard.ts
│   │   ├── modulePages.ts
│   │   └── navigation.ts
│   ├── hooks/
│   │   ├── useHashRoute.ts
│   │   ├── useLocalStorage.ts
│   │   ├── useOutsideClick.ts
│   │   └── useToast.ts
│   ├── services/
│   │   └── mockApi.ts
│   ├── styles/
│   │   ├── components.css
│   │   ├── dashboard.css
│   │   ├── global.css
│   │   ├── index.css
│   │   ├── layout.css
│   │   ├── modules.css
│   │   ├── responsive.css
│   │   └── tokens.css
│   ├── types/
│   │   └── index.ts
│   ├── utils/
│   │   └── formatters.ts
│   ├── App.tsx
│   └── main.tsx
├── .gitignore
├── index.html
├── package.json
├── start-git-bash.sh
├── tsconfig.app.json
├── tsconfig.json
├── tsconfig.node.json
└── vite.config.ts
```

## 5. Included user interactions

The project includes working front-end behaviour for:

- Responsive full-width application shell
- Collapsible desktop sidebar
- Tablet and mobile navigation drawer
- Dark and light themes
- Workspace and project switching
- Hash-based page routing with browser back and forward support
- Search command palette using `Ctrl + K`
- Notification and profile menus
- Jira synchronization simulation
- Requirements validation
- Three-step requirement intake workflow
- Browser draft persistence with `localStorage`
- Drag-and-drop file selection
- File-size validation, duplicate protection, and removal
- Dynamic planning-readiness calculation
- Sprint creation modal
- AI model selection
- Simulated AI conversation and prompt suggestions
- Search and status filters on module pages
- Toast notifications
- Responsive tables and usable empty states

## 6. Main places to customize

### Branding, colours, radii, and dimensions

Edit:

```text
src/styles/tokens.css
```

Important variables include:

```css
--sidebar-expanded: 288px;
--sidebar-collapsed: 88px;
--topbar-height: 72px;
--primary-500: #8b5cf6;
--primary-600: #7c3aed;
```

### Responsive behaviour

Edit:

```text
src/styles/responsive.css
```

The page has dedicated behaviour for ultrawide monitors, desktop screens, laptops, tablets, and phones.

### Sidebar options

Edit:

```text
src/data/navigation.ts
```

Every item has an ID, label, description, icon, and optional badge.

### Dashboard demo data

Edit:

```text
src/data/dashboard.ts
```

### Content for the other sidebar pages

Edit:

```text
src/data/modulePages.ts
```

### Default requirement form values

Edit `initialDraft` in:

```text
src/App.tsx
```

## 7. Connect a real backend

The current project is intentionally front-end only. Mock requests are isolated in:

```text
src/services/mockApi.ts
```

Replace these functions with your API client when backend endpoints are available:

```ts
syncWithJira()
saveSprintDraft(draft)
createSprint(draft)
askAssistant(prompt)
```

A simple production pattern is:

```ts
const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/sprints`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(draft),
});

if (!response.ok) {
  throw new Error('Unable to create sprint');
}

return response.json();
```

Do not place Jira credentials, OpenAI keys, Anthropic keys, or other secrets inside Vite environment variables. Vite variables are included in the browser bundle. Keep secrets on your backend and call them through secured server endpoints.

## 8. Reset the saved demo state

The form, theme, selected project, sidebar state, and file metadata are stored in browser `localStorage`.

Open the browser developer console and run:

```js
localStorage.removeItem('sprint-sarthi-draft-v3');
localStorage.removeItem('sprint-sarthi-files-v3');
localStorage.removeItem('sprint-sarthi-theme');
localStorage.removeItem('sprint-sarthi-project');
localStorage.removeItem('sprint-sarthi-sidebar-collapsed');
location.reload();
```

## 9. Troubleshooting

### `npm` or `node` is not recognized

Install a supported Node.js release, close Git Bash, and open it again.

### Port 5173 is already in use

Vite automatically tries another available port because `strictPort` is disabled. Read the terminal output for the actual address.

### The browser shows an older design

Stop Vite, clear the Vite cache, and restart:

```bash
rm -rf node_modules/.vite
npm run dev
```

Then perform a hard refresh with `Ctrl + Shift + R`.

### Dependency installation is corrupted

```bash
rm -rf node_modules package-lock.json
npm cache verify
npm install
npm run dev
```

### Git Bash path contains spaces

Quote the path:

```bash
cd "/c/Users/YOUR_NAME/My Projects/sprint-sarthi-pro"
```
