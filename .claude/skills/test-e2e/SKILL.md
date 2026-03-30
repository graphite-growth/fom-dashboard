
---
name: test-e2e
description: Run end-to-end tests using Playwright MCP browser tools. Tests login, auth, dashboard layout, API, and logout. Requires Docker Compose running.
category: infrastructure
argument-hint: "[optional: login, auth, dashboard, api, dropdown, logout]"
mcp-dependencies:
  - playwright
data-inputs:
  - Running Docker Compose stack (nginx port 80, frontend port 3000, backend port 8000)
  - DEV_AUTH=true environment variable
outputs:
  - Console test results table (Pass/Fail per section)
  - Screenshots on failure
scope: project-specific
model-recommendation: sonnet
allowed-tools: Bash(docker *), mcp__playwright__browser_navigate, mcp__playwright__browser_snapshot, mcp__playwright__browser_take_screenshot, mcp__playwright__browser_click, mcp__playwright__browser_type, mcp__playwright__browser_press_key, mcp__playwright__browser_fill_form, mcp__playwright__browser_console_messages, mcp__playwright__browser_network_requests, mcp__playwright__browser_wait_for, mcp__playwright__browser_hover, mcp__playwright__browser_select_option, mcp__playwright__browser_evaluate, mcp__playwright__browser_tabs, Read, Grep, Glob, TodoWrite
---

# E2E Testing with Playwright MCP

The app runs via Docker Compose with three containers: nginx proxy (port 80), frontend (port 3000), and backend (port 8000).

## Prerequisites

Before testing, verify the app is running:

```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

If no containers are running, tell the user to start them:
```
docker compose build && docker compose up -d
```

## Base URL

Always use `http://localhost` (nginx proxy on port 80).

## Test Suite

If `$ARGUMENTS` specifies a particular area, run only that section. Otherwise, run all sections in order.

### 1. Login Page (`login`)

1. Navigate to `http://localhost/login`
2. Verify the page renders with:
   - "Login to your account" heading
   - "Login with Google" button/link pointing to `/api/v1/auth/login`
3. Take a screenshot

### 2. Authentication (`auth`)

1. Navigate to `http://localhost/login`
2. Click "Login with Google" — with `DEV_AUTH=true`, this creates a fake session (dev@example.com) and redirects to `/app`
3. Verify you land on `http://localhost/app`
4. Verify the user "Dev User" / "dev@example.com" appears in the sidebar

### 3. Dashboard Layout (`dashboard`)

Requires: authenticated session (run auth test first if needed)

1. On `/app`, verify:
   - Sidebar with app logo and name ("quick-app")
   - "Dashboard" heading in the main content area
   - "Request Hello" card with Name input, Result display, GET and PUT buttons
   - User info at the bottom of the sidebar (name + email)
2. Take a screenshot of the full dashboard

### 4. API Functionality (`api`)

Requires: authenticated session

1. Click the **GET: /api/hello** button
   - Verify result shows: `{"message": "Hello, world!!!", "method": "GET"}`
2. Type a name (e.g., "Claude") in the Name input
3. Click the **GET: /api/hello** button again
   - Verify result shows: `{"message": "Hello, Claude!"}`
4. Click the **PUT: /api/hello** button
   - Verify result shows: `{"message": "Hello, world!", "method": "PUT"}`
5. Take a screenshot showing a result

### 5. User Dropdown (`dropdown`)

Requires: authenticated session

1. Click the user button at the bottom of the sidebar (shows name + email)
2. Verify the dropdown menu appears with:
   - User avatar/initials, name, email
   - Separator
   - "Log out" menu item with icon
3. Take a screenshot of the open dropdown

### 6. Logout (`logout`)

Requires: authenticated session with dropdown open

1. Click "Log out" from the dropdown menu
2. Verify redirect to `http://localhost/login`
3. Verify the login page renders correctly

## Reporting

Use a TodoWrite to track each test section. After all tests complete, provide a summary table:

| Test | Status | Details |
|------|--------|---------|
| Login page | Pass/Fail | ... |
| Authentication | Pass/Fail | ... |
| Dashboard layout | Pass/Fail | ... |
| API functionality | Pass/Fail | ... |
| User dropdown | Pass/Fail | ... |
| Logout | Pass/Fail | ... |

If any test fails, include console errors (`browser_console_messages`) and network failures (`browser_network_requests`) in the report.

## Cleanup

If **all tests passed**, remove artifacts generated during the run:

```bash
rm -f test-*.png
rm -rf .playwright-mcp/
```

If any test **failed**, keep the screenshots and logs so the user can inspect them.

## Tips

- Use `browser_snapshot` to get the accessibility tree for finding element refs
- Use `browser_take_screenshot` for visual verification
- Check `browser_console_messages` if something looks broken
- If a page doesn't load, check `browser_network_requests` for failed requests
- The DEV_AUTH bypass only works when the backend has `DEV_AUTH=true` in its environment
