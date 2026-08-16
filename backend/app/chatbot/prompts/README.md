# Chatbot prompts

English instructions for the model. Customer-facing replies must stay **Vietnamese** (`answer_system.txt`).

| File | Used by |
|---|---|
| `intent_extraction_system.txt` | Intent router |
| `answer_system.txt` | Final answer generation |
| `context_labels.txt` | Context headers (`key=value`) |
| `notes/*.txt` | Assistant-only snippets; `{placeholders}` via `render_note` |

Edit the `.txt` files. Restart the API process to reload (values are loaded at import time).
