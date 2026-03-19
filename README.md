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

**Optional:**

```
pip install aa-pipeline[markdown]
```

Installs `markdown` and `bleach` so step body text is rendered as Markdown.

---

## Installation

1. Install the package:

   ```bash
   pip install aa-pipeline
   ```

2. Add to `INSTALLED_APPS` in your Alliance Auth settings:

   ```python
   INSTALLED_APPS += [
       "pipeline",
   ]
   ```

3. Run migrations:

   ```bash
   python manage.py migrate pipeline
   ```

4. Collect static files:

   ```bash
   python manage.py collectstatic
   ```

5. Assign the `pipeline | Can access this app` permission to the groups or states that should see the menu item.

---

## Configuration

No required settings. Optional:

| Setting | Default | Description |
|---|---|---|
| *(none in Phase 1)* | | |

---

## Usage

1. In the Django Admin, go to **Pipeline → Flows** and create a flow.
2. Set the **Status** to `Draft` while building.
3. Add steps with the inline step editor.
4. Configure **Audience & Visibility** (the flow won't appear until at least one audience dimension is set).
5. Change Status to `Published`.
6. Users matching the audience will see the flow on their Pipeline page.

---

## Contributing

Issues and pull requests welcome at [GitHub](https://github.com/Thrainkrilleve/aa-pipeline).

---

## License

GPLv3 — see [LICENSE](LICENSE).
