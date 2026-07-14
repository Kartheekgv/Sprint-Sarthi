#!/usr/bin/env bash
set -e

printf '\nSprint Sarthi setup\n'
printf '%s\n' '-------------------'

if ! command -v node >/dev/null 2>&1; then
  echo 'Node.js was not found. Install a supported Node.js version and reopen Git Bash.'
  exit 1
fi

NODE_MAJOR=$(node -p "Number(process.versions.node.split('.')[0])")
NODE_MINOR=$(node -p "Number(process.versions.node.split('.')[1])")
SUPPORTED=false

if [ "$NODE_MAJOR" -eq 20 ] && [ "$NODE_MINOR" -ge 19 ]; then
  SUPPORTED=true
elif [ "$NODE_MAJOR" -eq 22 ] && [ "$NODE_MINOR" -ge 12 ]; then
  SUPPORTED=true
elif [ "$NODE_MAJOR" -gt 22 ]; then
  SUPPORTED=true
fi

if [ "$SUPPORTED" != true ]; then
  echo "Your Node.js version is $(node --version). Use Node.js 20.19+, 22.12+, or a newer supported release."
  exit 1
fi

if [ ! -d node_modules ]; then
  echo 'Installing dependencies...'
  npm install
fi

echo 'Starting the development server...'
npm run dev
