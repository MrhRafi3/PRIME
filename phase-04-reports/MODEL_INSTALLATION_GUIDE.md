# PRIME Local Model Installation Guide (Phase 04)

## 1. Local Storage Location

Approved MLX model directories live exclusively under:

```text
~/Library/Application Support/PRIME/models/<model-slug>/
```

Permissions are restricted (`0700` on `PRIME/` and `models/`). PRIME does **not** automatically download models at startup or runtime.

## 2. Currently Installed & Verified Models

1. **`qwen2.5-1.5b-4bit`** -> `~/Library/Application Support/PRIME/models/qwen2.5-1.5b-4bit/`
   - Source: `mlx-community/Qwen2.5-1.5B-Instruct-4bit` (`Apache-2.0`, ~840 MB on disk)
2. **`qwen3-1.7b-4bit`** -> `~/Library/Application Support/PRIME/models/qwen3-1.7b-4bit/`
   - Source: `mlx-community/Qwen3-1.7B-4bit` (`Apache-2.0`, ~940 MB on disk)

## 3. Manual / Approved Installation Workflow

If reinstalling or adding an approved catalog entry manually after user approval:

```bash
uv run python -c "
from pathlib import Path
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='mlx-community/Qwen2.5-1.5B-Instruct-4bit',
    local_dir=str(Path.home() / 'Library/Application Support/PRIME/models/qwen2.5-1.5b-4bit'),
)
"
```

Verify installation offline:

```bash
uv run prime ui
```

Open **Settings -> Local MLX Model** to switch between `qwen2.5-1.5b-4bit` and `qwen3-1.7b-4bit`, then click **Load Model** in the main HUD.
