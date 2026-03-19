# aa-pipeline

> A structured journey system for [Alliance Auth](https://allianceauth.readthedocs.io/) — generalised onboarding, training, certification, and vetting flows.

`aa-pipeline` is a complete reimagining of `allianceauth-workflows`. It replaces the concept of a "wizard" with fully configurable **Flows** made up of ordered **Steps**, with built-in support for Smart Filter checks, user acknowledgements, and service account verification.

---

## Features (Phase 1)

- **Three step types**
  - `filter_check` — automatically evaluated against Smart Filters (no manual action required)
  - `acknowledgement` — user reads content and clicks Confirm
  - `service_check` — verifies an active Discord / Mumble / TeamSpeak / etc. account via a runtime service registry
- **Flow lifecycle** — `draft` → `published` → `archived`
- **Flow types** — Onboarding, Training, Certification, Vetting, Industry, Other
- **Audience targeting** — States, Groups, Corporations, Alliances, Factions, Characters
- **Auto-assignment** — flows can be automatically assigned when a user's profile changes
- **On-complete automation** — add to groups, fire a webhook (Phase 4)
- **GDPR hook** — integrates with [aa-gdpr](https://apps.allianceauth.org/apps/detail/aa-gdpr) for data export and deletion
- **Alliance Auth theme compatible** — Bootstrap 5, dark-mode support, mobile responsive

---

## Requirements

- Python >= 3.10
- Alliance Auth >= 4.3.1, < 5

**Optional — Markdown rendering:**

To enable Markdown rendering for step body text, use the `[markdown]` extra in your `requirements.txt`:

```
aa-pipeline[markdown] @ git+https://github.com/Thrainkrilleve/aa-pipeline.git
```

This installs `markdown` and `bleach` automatically when running `docker compose build`. If installing manually, add both packages to your environment separately.

---

## Installation

### Docker (recommended)

1. Install:

   ```bash
   docker compose exec allianceauth_gunicorn pip install "aa-pipeline @ git+https://github.com/Thrainkrilleve/aa-pipeline.git"
   ```

2. Add to your `requirements.txt`:

   ```
   aa-pipeline[markdown] @ git+https://github.com/Thrainkrilleve/aa-pipeline.git@v0.1.6
   ```

3. Add `"pipeline"` to `INSTALLED_APPS` in your Alliance Auth settings file (e.g. `local.py`):

   ```python
   INSTALLED_APPS += [
       "pipeline",
   ]
   ```

4. Run migrations and collect static files:

   ```bash
   docker compose exec allianceauth_gunicorn bash -c "auth migrate && auth collectstatic --noinput"
   ```

5. Rebuild the image:

   ```bash
   docker compose build
   ```

6. Assign the `pipeline | Can access this app` permission to the groups or states that should see the menu item.

---

## Configuration

No required settings. Optional:

| Setting | Default | Description |
|---|---|---|
| *(none in Phase 1)* | | |

---

## Usage

1. In the Django Admin (or via the in-app **Manage Flows** button for users with the `manage_flows` permission), create a flow.
2. Set the **Status** to `Draft` while building.
3. Add steps with the inline step editor.
4. For `filter_check` steps, add **Smart Filter checks** — if your filters were registered before pipeline was installed, run the sync command first:

   ```bash
   docker compose exec allianceauth_gunicorn python manage.py pipeline_sync_filters
   ```

5. Configure **Audience & Visibility** (the flow won't appear until at least one audience dimension is set).
6. Change Status to `Published`.
7. Users matching the audience will see the flow on their Pipeline page.

---

## Contributing

Issues and pull requests welcome at [GitHub](https://github.com/Thrainkrilleve/aa-pipeline).

---

## License

GPLv3 — see [LICENSE](LICENSE).
