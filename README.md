# aa-pipeline

> A structured journey system for [Alliance Auth](https://allianceauth.readthedocs.io/) — onboarding, training, certification, and vetting flows.

`aa-pipeline` provides fully configurable **Flows** made up of ordered **Steps**, with built-in support for Smart Filter checks, user acknowledgements, service account verification, and on-complete automation.

---

## Features

- **Three step types**
  - `filter_check` — automatically evaluated against configured Smart Filters
  - `acknowledgement` — user reads content and clicks Confirm
  - `service_check` — verifies an active service account (Discord, Mumble, TeamSpeak, etc.) via the runtime service registry
- **Flow lifecycle** — `draft` → `published` → `archived` (with restore to draft)
- **Flow types** — Onboarding, Training, Certification, Vetting, Industry, Other
- **Audience targeting** — States, Groups, Corporations, Alliances, Factions, Characters
- **Auto-assignment** — flows are assigned automatically when a user's profile, groups, or characters change
- **On-complete automation** — add users to groups and fire a signed webhook when a flow is completed
- **In-app flow manager** — create, edit, publish, archive, and reorder flows and steps without Django Admin
- **Smart Filter check editor** — attach and reorder Smart Filter checks per step in-app
- **Signed webhooks** — outgoing HTTP POST payloads include an `X-Pipeline-Signature` HMAC-SHA256 header for receiver verification
- **GDPR hook** — integrates with [aa-gdpr](https://apps.allianceauth.org/apps/detail/aa-gdpr) for data export and deletion
- **Alliance Auth theme compatible** — Bootstrap 5, dark-mode support, mobile responsive

---

## Requirements

- Python >= 3.10
- Alliance Auth >= 4.3.1, < 5

---

## Installation

See the [Alliance Auth plugin installation docs](https://allianceauth.readthedocs.io/en/v4.13.1/) for general guidance.

1. Add `aa-pipeline` to your `requirements.txt`:

   ```
   aa-pipeline[markdown] @ git+https://github.com/Thrainkrilleve/aa-pipeline.git@v0.1.7c
   ```

   The `[markdown]` extra installs `markdown` and `bleach` to enable Markdown rendering in step body text. Without it, body text is displayed as plain text.

2. Add `"pipeline"` to `INSTALLED_APPS` in your Alliance Auth settings file (e.g. `local.py`):

   ```python
   INSTALLED_APPS += [
       "pipeline",
   ]
   ```

3. Rebuild the image, run migrations, and collect static files:

   ```bash
   docker compose build
   docker compose exec allianceauth_gunicorn bash -c "auth migrate && auth collectstatic --noinput"
   docker compose up -d
   ```

4. In Django Admin, assign the `pipeline | Can access this app` permission to the groups or states that should see the Pipeline menu item.

---

## Updating

1. Update the version pin in your `requirements.txt`:

   ```
   aa-pipeline[markdown] @ git+https://github.com/Thrainkrilleve/aa-pipeline.git@v0.1.7c
   ```

2. Rebuild and apply any new migrations:

   ```bash
   docker compose build
   docker compose exec allianceauth_gunicorn bash -c "auth migrate && auth collectstatic --noinput"
   docker compose up -d
   ```

---

## Configuration

No required settings.

---

## Usage

### Setting up a flow

1. Click **Manage Flows** in the Pipeline menu (requires the `pipeline | Can manage flows` permission or superuser access).
2. Create a flow and set its **Status** to `Draft` while building.
3. Add and reorder steps using the step editor.
4. For `filter_check` steps, add Smart Filter checks in the *Smart Filter Checks* card on the step form.
   If your Smart Filters were registered before Pipeline was installed, sync them first:

   ```bash
   docker compose exec allianceauth_gunicorn python manage.py pipeline_sync_filters
   ```

5. Configure **Audience & Visibility** — the flow won't appear to users until at least one audience dimension is set.
6. Change **Status** to `Published`.

Users matching the configured audience will see the flow on their Pipeline page and will be auto-assigned if **Auto Assign** is enabled.

---

## Contributing

Issues and pull requests welcome at [GitHub](https://github.com/Thrainkrilleve/aa-pipeline).

---

## License

GPLv3 — see [LICENSE](LICENSE).
