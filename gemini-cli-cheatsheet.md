# Gemini CLI Cheatsheet

The [Gemini CLI](https://github.com/google-gemini/gemini-cli) is an open-source AI agent that brings the power of Gemini directly into your terminal, allowing you to perform a wide range of tasks such as coding, problem-solving, and task management using natural language. This cheatsheet provides a quick reference for installing, configuring, and using the Gemini CLI, with a focus on users authenticating via a Gemini API key.

![Gemini CLI Architecture](/static/blog/gemini-cli-cheatsheet/architecture.png)

## 🚀 Getting Started

### Installation

**Install Globally:**
```bash
npm install -g @google/gemini-cli
```

**Run without Installing:**
```bash
npx @google/gemini-cli
```

### Authentication with a Gemini API Key

Authenticate with an API key before first use. See the [authentication guide](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/authentication.md) for details.

1.  **Get Your Key:** Get an API key from [Google AI Studio](https://aistudio.google.com/app/apikey).

2.  **Set Your Key:** Make the key available to the CLI with one of these methods.

    **Method 1: Shell Environment Variable**
    Set the `GEMINI_API_KEY` environment variable. To use it across terminal sessions, add this line to your shell's profile (e.g., `~/.bashrc`, `~/.zshrc`).
    ```bash
    export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    ```
    
    **Method 2: Environment File**
    Create a `.env` file in `~/.gemini/` for global use or `./.gemini/` for a specific project. The CLI automatically loads it.
    ```
    # In .gemini/.env
    GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    ```
### Basic Invocation

**Interactive Mode (REPL):**
Start a conversational session.
```bash
gemini
```

**Non-Interactive Mode:**
Pass a prompt and get a single response.
```bash
gemini -p "Summarize the main points of the attached file. @./summary.txt"
```

**Piping to the CLI:**
Pipe content to the CLI.
```bash
echo "Count to 10" | gemini
```

**Sandbox Mode:**
Run tools in a secure sandbox (requires Docker or Podman).
```bash
gemini --sandbox -p "your prompt"
```

**Other Flags:**

- `-m, --model <model>`: Use a specific model.
- `-i, --prompt-interactive <prompt>`: Start an interactive session with an initial prompt.
- `-d, --debug`: Enable debug output.
- `--yolo`: Auto-approve all tool calls.
- `--checkpointing`: Save a project snapshot before file modifications. Use `/restore` to revert changes.

[Full list of flags](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/configuration.md#command-line-arguments).

## ⚙️ Configuration

### Settings Files (`settings.json`)

Customize the CLI by creating a `settings.json` file. Settings are applied with the following precedence:
1.  **Project:** `.gemini/settings.json` (overrides user and system settings).
2.  **User:** `~/.gemini/settings.json` (overrides system settings).
3.  **System:** `/etc/gemini-cli/settings.json` (applies to all users, has lowest precedence).

**Example `settings.json`:**
```json
{
  "theme": "GitHub",
  "autoAccept": false,
  "sandbox": "docker",
  "vimMode": true,
  "checkpointing": { "enabled": true },
  "fileFiltering": { "respectGitIgnore": true },
  "usageStatisticsEnabled": true,
  "includeDirectories": ["../shared-library", "~/common-utils"],
  "chatCompression": { "contextPercentageThreshold": 0.6 },
  "customThemes": {
    "MyCustomTheme": {
      "name": "MyCustomTheme", "type": "custom",
      "Background": "#181818", "Foreground": "#F8F8F2",
      "LightBlue": "#82AAFF", "AccentBlue": "#61AFEF", "AccentPurple": "#C678DD",
      "AccentCyan": "#56B6C2", "AccentGreen": "#98C379", "AccentYellow": "#E5C07B",
      "AccentRed": "#E06C75", "Comment": "#5C6370", "Gray": "#ABB2BF"
    }
  }
}
```
*   `autoAccept`: Auto-approve safe, read-only tool calls.
*   `sandbox`: Isolate tool execution (e.g., `true`, `"docker"`, or `"podman"`).
*   `vimMode`: Enable Vim-style editing for the input prompt.
*   `checkpointing`: Enable the `/restore` command to undo file changes.
*   `includeDirectories`: Define a multi-directory workspace.
*   `chatCompression`: Configure automatic chat history compression.
*   `customThemes`: Define your own color themes.
*   `usageStatisticsEnabled`: Set to `false` to disable usage statistics.

All details in the [configuration guide](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/configuration.md).

### Context Files (`GEMINI.md`)

Use `GEMINI.md` files to provide instructions to the model and tailor it to your project. Use `/init` to generate a starting `GEMINI.md` file for your project.

**Hierarchical Loading:**
The CLI combines `GEMINI.md` files from multiple locations. More specific files override general ones. The loading order is:
1.  **Global Context:** `~/.gemini/GEMINI.md` (for instructions that apply to all your projects).
2.  **Project/Ancestor Context:** The CLI searches from your current directory up to the project root for `GEMINI.md` files.
3.  **Sub-directory Context:** The CLI also scans subdirectories for `GEMINI.md` files, allowing for component-specific instructions.

Use `/memory show` to see the final combined context being sent to the model.

**Modularizing Context with Imports:**
You can organize `GEMINI.md` files by importing other Markdown files with the `@file.md` syntax. This only supports `.md` files.

**Example `GEMINI.md` using imports:**
```markdown
# Main Project Context: My Awesome App

## General Instructions
- All Python code must be PEP 8 compliant.
- Use 2-space indentation for all new files.

## Component-Specific Style Guides
@./src/frontend/react-style-guide.md
@./src/backend/fastapi-style-guide.md
```

More in the [Full context file guide](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/configuration.md#context-files-geminimd).

### Ignoring Files with `.geminiignore`
Create a `.geminiignore` file in your project root to exclude files and directories from Gemini's tools, similar to `.gitignore`.
```
# .geminiignore
/backups/
*.log
secret-config.json
```

## 🛠️ Working with Tools

### Some Built-in Tools

*   **File System Tools:** For interacting with files and directories - `list_directory(path="/src")`, `glob(pattern="src/**/*.ts")`, `read_file(path="/path/to/file.txt")`, `write_file(file_path="/path/to/new_file.js", content="console.log('hello');")`, `replace(file_path="...", old_string="...", new_string="...")`, `search_file_content(pattern="myFunction", include="*.js")`
*   **Shell Tool:** Executes shell commands. **Use with caution.** To restrict commands, use `excludeTools` in `settings.json`. For example: `"excludeTools": ["run_shell_command(rm)"]`
*   **Web Tools:** For retrieving content and searching online - `google_web_search(query="Gemini API rate limits")`, `web_fetch(prompt="Summarize https://my-blog.com/article")`
*   **Memory Tool:** For saving and recalling information across sessions - `save_memory(fact="My preferred CSS framework is Tailwind CSS.")`

### Custom Tools via MCP Servers

Extend the CLI with your own tools by running Model Context Protocol (MCP) servers. Manage servers via `settings.json` or with the `gemini mcp <add|list|remove>` commands.

**Capabilities:**
*   **OAuth 2.0 Support:** Securely connect to remote servers.
*   **Rich Content Returns:** Tools can return multi-modal content like text and images.
*   **Prompts as Commands:** Expose predefined prompts from your server as new slash commands in the CLI.

**Example `mcpServers` configuration:**
```json
"mcpServers": {
  "myPythonServer": {
    "command": "python",
    "args": ["-m", "my_mcp_server", "--port", "8080"],
    "cwd": "./mcp_tools/python",
    "env": {
      "DATABASE_URL": "$DB_URL_FROM_ENV"
    },
    "timeout": 15000,
    "trust": false,
    "includeTools": ["safe_tool_1", "safe_tool_2"],
    "excludeTools": ["dangerous_tool"]
  }
}
```

**Transport (choose one):**
*   `command`, `args`, `cwd`: Launch a local process via Stdio
*   `url`: SSE endpoint (e.g., `"http://localhost:8080/sse"`)
*   `httpUrl`: HTTP streaming endpoint (e.g., `"http://localhost:8080/mcp"`)

**Optional:**
*   `env`: Environment variables. Use `$VAR_NAME` syntax to reference shell variables.
*   `headers`: Key-value map of HTTP headers for `url`/`httpUrl` transports.
*   `timeout`: Request timeout in milliseconds (default: 10 minutes).
*   `trust`: Bypass all tool confirmations for this server.
*   `includeTools`/`excludeTools`: Whitelist/blacklist specific tools. `excludeTools` takes precedence.

Using OAuth take a look at [mcp-server.md](https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md#oauth-support-for-remote-mcp-servers)


## ⚡ Core Commands

### Helpful Slash Commands (`/`)

| Command | Description |
|---|---|
| `/compress` | Replace the entire chat context with a summary to save tokens. |
| `/copy` | Copy the last response to the clipboard. |
| `/mcp` | List configured MCP servers and their available tools. |
| `/clear` | Clear the terminal screen and context (`Ctrl+L` also works). |
| `/tools` | List available tools. |
| `/extensions` | List active extensions. |
| `/stats` | Show session token usage and savings. |
| `/memory show` | Show the combined context from all `GEMINI.md` files. |
| `/memory refresh` | Reload all `GEMINI.md` files. |
| `/chat save <tag>` | Save the current conversation with a tag. |
| `/chat resume <tag>`| Resume a saved conversation. |
| `/chat list`| List saved conversation tags. |
| `/restore` | List or restore a project state checkpoint. |
| `/auth` | Change the current authentication method. |
| `/bug` | File an issue or bug report about the Gemini CLI. |
| `/help` | Display help information and available commands. |
| `/theme` | Change the CLI's visual theme. |
| `/quit` | Exit the Gemini CLI. |
| `/ide` | Manage integration with your IDE (e.g., `install`, `enable`). |
| `/settings`| Open a friendly editor to change your `settings.json` file. |
| `/vim` | Toggle Vim mode for input editing. |
| `/init` | Generate a starting `GEMINI.md` context file for your project. |
| `/directory` | Manage directories in a multi-directory workspace (e.g., `add`, `show`). |

### Context Commands (`@`)

Reference files or directories in your prompt. The CLI respects `.gitignore` and `.geminiignore`. You can also reference images, PDFs, audio, and video files.

**Include a single file:**
```
> Explain this code to me. @./src/main.js
```
**Include an image:**
```
> Describe what you see in this screenshot. @./ux-mockup.png
```
**Include a whole directory (recursively):**
```
> Refactor the code in this directory to use async/await. @./src/
```

### Shell Commands (`!`)

Run shell commands directly in the CLI.

**Run a single command:**
```
> !git status
```

**Toggle Shell Mode:**
Enter `!` by itself to switch to a persistent shell mode. Type `!` again to exit.

### Keyboard Shortcuts
| Shortcut | Description |
|---|---|
| `Ctrl+L` | Clear the screen. |
| `Ctrl+V` | Paste text or an image from the clipboard. |
| `Ctrl+Y` | Toggle YOLO mode (auto-approve all tool calls). |
| `Ctrl+X` | Open the current prompt in an external editor. |

## ✨ Advanced Features

### IDE Integration (VS Code)
Connect the CLI to VS Code for a more powerful, context-aware experience.
- **Workspace Context:** Automatically gets your recent files, cursor position, and selected text.
- **Native Diffing:** View and approve code changes directly in your editor's diff viewer.
- **Commands:** Use `/ide install` to set up and `/ide enable` to connect.

### Custom Commands

Create custom commands using TOML files. Store them in `~/.gemini/commands/` (global) or `<project>/.gemini/commands/` (project-specific). See the [custom commands guide](https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/commands.md#custom-commands) for more details.

**Example: `~/.gemini/commands/test/gen.toml`**
```toml
# Invoked as: /test:gen "Create a test for the login button"
description = "Generates a unit test based on a description."
prompt = """
You are an expert test engineer. Based on the following requirement, please write a comprehensive unit test using the Jest testing framework.

Requirement: {{args}}
"""
```

### Extensions

Create extensions to add functionality. Place them in `<workspace>/.gemini/extensions/` or `~/.gemini/extensions/`. Each extension is a directory with a `gemini-extension.json` file that can configure MCP servers, tools, and context files. For more details, see the [extensions guide](https://github.com/google-gemini/gemini-cli/blob/main/docs/extension.md).

For example:

```
<workspace>/.gemini/extensions/my-extension/gemini-extension.json
```

```json
{
  "name": "my-extension",
  "version": "1.0.0",
  "mcpServers": {
    "my-server": {
      "command": "node my-server.js"
    }
  },
  "contextFileName": "GEMINI.md",
  "excludeTools": ["run_shell_command"]
}
```


### Checkpointing & Restore

When `checkpointing` is on, the CLI saves a project snapshot before tools modify files.

**Enable in `settings.json` or with a flag:**
```bash
gemini --checkpointing
```

**Restore to a previous state:**
```bash
# List available checkpoints
/restore

# Restore a specific checkpoint
/restore <checkpoint_file_name>
```
