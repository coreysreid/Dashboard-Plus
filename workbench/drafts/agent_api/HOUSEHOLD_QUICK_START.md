# Connect an AI assistant to Dashboard Plus

**A one-page household guide.** Checked **19 November 2026** against Dashboard Plus Settings → Helpers and decisions 0066, 0067, 0068, 0074, 0083, 0086 and 0087. You need Dashboard Plus and an AI assistant **desktop app that can run a local MCP server on the same computer**. The assistant app may call this an “MCP server” or a “local tool”. Its own settings screen may look different.

## 1. Choose what the assistant may see

Open Dashboard Plus, then **Settings → Helpers**. Under **Add a helper**, enter a name you will recognize, such as **Pantry helper**. Choose **Look only** if you want answers about your records; choose **Look and suggest new records** if you also want it to prepare additions for you. Tick only the parts it needs, such as **Household stock**. Nothing is ticked for you. Press **Make a key**.

Dashboard shows the **access key once**. Leave this page open until step 3 is complete. The key is a password: do not put it in a chat, email, screenshot, shared document or public file. If you lose it, make a new helper key and turn the old helper off.

## 2. Copy the connection settings

On that same page, find **Connect an AI assistant** and press **Copy these settings**. In your assistant **desktop app**, open its settings for **MCP servers** or **local tools** and paste the copied settings there. The block has a `dashboard-plus` entry with the command, the current Dashboard address and `YOUR-KEY-HERE`. If your app asks for one server at a time, use the `dashboard-plus` entry inside the copied block. Follow your app's save/restart step so it loads the new tool.

Use the settings block Dashboard gives you on **your own computer**: it contains the right Python command and address for this installation. Do not copy a command or address from someone else's example. The connector runs on this computer; a browser-only assistant that cannot start a local MCP server cannot use this setup.

## 3. Put the key in its place

In the **assistant app's MCP settings**, replace only `YOUR-KEY-HERE` in `DASHBOARD_PLUS_KEY` with the key shown by Dashboard. Keep the quotation marks and the rest of the settings. **Do not paste the key into the conversation with the assistant.** Save the settings, then close or clear any temporary editor you used. The assistant app may store its settings, including the key, in a readable file on this computer; protect that computer account as you would any saved password.

Keep Dashboard open and ask the assistant, “What can you see in Dashboard Plus?” It should have only the parts and access you chose. If it cannot connect after Dashboard is reopened, return to **Settings → Helpers**, copy the new settings block and replace the old block in the assistant app **while keeping your existing key**. Dashboard's address changes each time it opens. The connector checks that the address belongs to this Dashboard before sending the key.

## What happens next

- The assistant can read **ordinary fields** in the parts you ticked. It cannot read fields Dashboard marks **private**, or parts you did not tick. A private matter typed in an ordinary name or note may still be readable, so check what you enter there.
- With **Look and suggest new records**, it can put **new records** on **Review**. Nothing is added until you press **Accept** there. It cannot edit or delete existing records, decide Review for you, open Settings, export records or restore a backup.
- If your assistant uses an **online AI service**, that service sees the record content the assistant reads. A helper that runs entirely on this computer does not send it to an online AI service. Decide which parts to tick with that in mind.

## Turn it off

Go to **Settings → Helpers**, find the helper by name and press **Turn off access**. Its key stops working; its old suggestions and history remain. Also remove the `dashboard-plus` entry from your assistant app's MCP settings. If the key may have been seen by someone else, turn it off promptly and make a new helper. Turning access off does not pull back information an online assistant already received.
