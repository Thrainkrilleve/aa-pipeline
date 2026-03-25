# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.15] - 2026-03-24

### Fixed
- Fixed an issue where the Alliance Auth dashboard widget injected the full HTML base layout (menus and styles) inline into the page body.
- Fixed a visual bug in the dashboard widget where incomplete assignments displayed as gray "Assigned" instead of "In Progress" when Smart Filter checks silently passed.
- Fixed an issue where Assignments wouldn't flip to "In Progress" if the first passing step was dynamically evaluated (like a smart filter check) rather than explicitly submitted via a view.

---

## [0.1.14] - 2026-03-24

### Changed
- Added GitHub Actions CI/CD workflow to run migrations check and automatically publish passing releases to PyPI.

### Fixed
- Fixed an issue where `Q(states=None)` incorrectly matched flows with no state targeting when rendering workflows for users with no state.
- Improved `get_assigned_for_user` to use explicit Enum members for `IN_PROGRESS` and `ASSIGNED` status lookups.

---

## [0.1.13] - 2026-03-24

### Fixed
- **Assigned flow not visible to users** — three bugs combined to cause this:
  - `get_assigned_for_user` used `exclude(assignments__status="completed")` which
    is not scoped to the current user in a multi-valued FK join. If *any* user
    completed a flow, it was excluded from every other user's assigned list.
    Fixed by combining both conditions into a single `filter()` call.
  - `recalculate_status()` was only called in `flow_detail` when *all* required
    steps were already done. Filter-check steps that silently auto-pass their
    criteria never triggered a status transition; the assignment stayed `Assigned`
    indefinitely. Fixed by calling `recalculate_status()` on every page visit
    (still guarded by `status != COMPLETED`).
  - Auto-assignment notifications had no URL — users received "Visit your
    Pipeline to get started" with no link and no way to find the flow if the
    sidebar item wasn't visible. Fixed: notification now includes a direct link
    to the assigned flow.

---

## [0.1.12] - 2026-03-24

### Added
- **Assignment Tracker in Flow Manager** — a new `manage/<slug>/assignments/`
  page lets admins and staff see every user's progress through a specific flow
  without leaving the in-app manager.
  - Summary cards at the top show totals for Assigned / In Progress / Completed.
  - Table rows show each user's username, main character, status badge,
    a progress bar (required steps only), time since assignment, and a
    per-step icon column (✔ complete, ○ incomplete, − optional incomplete).
  - Toggle between "Active only" and "All (including completed)" views.
  - Step legend above the table maps column numbers to step names.
  - The **Active** count badge on the Flow Manager index is now a direct link
    to this page.
  - An **Assignments** button is shown in the flow edit header for quick access.

---

## [0.1.11] - 2026-03-24

### Added
- **"Assign if missing groups" targeting** — `OnboardingFlow` now has an
  `assign_if_missing_groups` M2M field (visible in the admin under
  *Audience & Visibility*). Any user who does not hold any of the configured
  groups is automatically included in the flow's eligible audience. When the
  user later gains one of those groups, any unstarted (`ASSIGNED`) assignment
  is automatically cleaned up by the existing auto-assign task. Migration
  `0005_assign_if_missing_groups` adds the join table.

  Typical use: pair this field with *On-Completion Automation → add to groups*
  to create a self-closing loop — users get onboarded into a role and the
  flow disappears once they have it.

---

## [0.1.10] - 2026-03-19

### Fixed
- **Step Completions add form was unusable** — all fields including
  `assignment`, `step`, and `completed_by` were marked read-only, rendering
  the Add page blank. The add form now exposes those fields as editable
  dropdowns; the change (edit) form retains full read-only behaviour to
  preserve the audit record. `completed_by` defaults to the logged-in admin
  if not explicitly set.

---

## [0.1.9] - 2026-03-19

### Fixed
- **Step Completions missing for filter_check and service_check steps** —
  only acknowledgement steps self-recorded a `StepCompletion` row; filter and
  service steps were evaluated dynamically and never stored. When a flow is
  marked complete, completion records are now stamped for every step that
  doesn’t already have one (stored with `"auto_recorded": true` in the
  `metadata` field so they are distinguishable from user-clicked
  acknowledgements). This gives a full audit trail in the Step Completions
  admin for all step types.

---

## [0.1.8] - 2026-03-19

### Added
- **"Re-send Discord completion notifications" admin action** — select any
  `FlowAssignment` in the Django admin and re-fire the Discord webhook without
  resetting the assignment state. Useful for testing webhook message formatting.

### Fixed
- **MySQL migration error on fresh installs** — `0004_alter_general_options_and_more`
  auto-generated by Django failed with `(1091, "Can't DROP INDEX
  pipeline_flowassignment_flow_user_unique")`. Root cause: models used
  `unique_together` but `0001_initial` had already created named
  `UniqueConstraint`s in the database; Django treated these as different and
  emitted a `RemoveConstraint` that MySQL could not resolve. Fixed by aligning
  both model `Meta` classes to use `UniqueConstraint` (matching what `0001`
  created), and replacing the auto-generated migration with a clean `0004` that
  only performs `AlterModelOptions` (adds the `manage_flows` permission) — no
  database index operations.
- **Discord webhook `KeyError` on placeholder with extra whitespace** —
  `{flow_name }` (trailing space) in a webhook message caused a `KeyError`
  at send time. Placeholders are now whitespace-normalised before formatting
  so `{ username }`, `{flow_name }`, etc. all resolve correctly.
- **Discord webhook `KeyError: 'user'`** — added `{user}` and `{flow}` as
  accepted aliases for `{username}` and `{flow_name}` respectively.

---

## [0.1.7] - 2026-03-18

### Added
- **Discord completion webhooks** — attach one or more Discord incoming webhooks
  per flow. When a user completes all required steps, each enabled webhook
  receives a formatted embed (user, flow name, completion timestamp). The
  `FlowDiscordWebhook` model is managed via an inline on the flow's Admin page
  (Server Settings → Integrations → Webhooks URL).
- **`fire_discord_completion_notification` Celery task** — POSTs to each
  enabled Discord webhook independently so one failing channel does not
  suppress the others. Retries up to 3 times on failure.

### Fixed
- **Audience fields blank when editing a flow** — the manage page used two
  separate `<form>` elements; the flow-settings form did not include the M2M
  audience fields, so every save wiped the configured audience. Merged into a
  single form so all fields are submitted together.

---

## [0.1.6] - 2026-03-18

### Added
- **Smart Filter check management in the step editor** — when editing a
  `filter_check` step, a *Smart Filter Checks* card now appears below the step
  settings form. Managers can add checks (filter, optional label, display order)
  and delete them without leaving the in-app UI. The card is hidden via JS when
  the step type is changed to `acknowledgement` or `service_check`.
- **Step reordering** — up/down chevron buttons in the flow editor let managers
  move steps without editing each one individually (`manage_step_reorder` view
  and URL pattern).
- **Assignment statistics on the manage index** — the flow table now shows
  *Active* (assigned + in-progress) and *Completed* user counts, annotated in
  a single database query.
- **Restore archived flows** — the publish toggle now handles all three states:
  Published → Draft, Archived → Draft (restore), Draft → Published. An archived
  flow can be recovered without recreating it.

### Changed
- **Webhook is now fully implemented** — `fire_completion_webhook` Celery task
  POSTs a JSON payload (`user_id`, `username`, `flow_id`, `flow_name`,
  `flow_slug`, `completed_at`) to the configured URL. The request includes an
  `X-Pipeline-Signature: sha256=<hmac>` header so receivers can verify
  authenticity. The task retries on HTTP or network errors.
- **`FlowStep.effective_type` is now a `cached_property`** — service registry
  lookups are performed at most once per step instance per request cycle,
  eliminating two redundant `apps.get_app_config()` calls per step on every
  page load.
- **Manage index no longer issues N+1 queries** — `step_count`, `active_count`,
  and `completed_count` are computed with a single annotated queryset instead
  of a separate `COUNT(*)` hit per row.

### Fixed
- **Service check fallback always firing** — `is_service_installed()` was
  calling `apps.is_installed()` which requires the full dotted module path
  (e.g. `"allianceauth.services.modules.discord"`), not the short app label
  (`"discord"`). All call sites in `service_registry.py` now use
  `apps.get_app_config(label)` inside a `try/except LookupError`, so installed
  services are correctly detected.
- **Draft preview returning 403 for flow managers** — `flow_detail` previously
  only allowed `is_staff` or `is_superuser` to preview draft flows. Users
  holding the `manage_flows` permission can now preview drafts too.

---

## [0.1.5] - 2026-03-18

### Fixed
- **Visible template comment** — a multi-line Django `{# … #}` comment block in
  `flow_detail.html` was rendering as literal text to the user. Removed.
- **Progress strip gap** — Alliance Auth's base template wraps `{% block content %}`
  in a `<div class="my-3">` which pushed the progress strip away from the page
  top. Fixed with `margin-top: -1rem` on `.pipeline-progress-strip` in
  `pipeline.css`.

### Changed
- **Audience fields replaced with scrollable multi-selects** — all six audience
  fields (`states`, `groups`, `corporations`, `alliances`, `factions`,
  `characters`) in the flow form were changed from `CheckboxSelectMultiple` to
  `SelectMultiple` with a fixed `size="7"`. Each field now has a live filter
  input above it and a Ctrl/Cmd hint below it.
- Previously missing `factions` and `characters` audience fields added to
  `flow_form.html`.

---

## [0.1.4] - 2026-03-18

### Added
- **`pipeline_sync_filters` management command** — populates the `CheckFilter`
  catalog by iterating all registered `secure_group_filters` hooks. Use this
  after installing new Smart Filter apps.

### Fixed
- **`manage/` 404** — URL patterns were ordered so that the `<slug:slug>/`
  catch-all matched `/manage/` before the manage routes. Fixed by moving all
  `manage/*` patterns above the slug patterns.
- **`StepCompletionAdmin` 500 on save** — the admin was attempting to
  auto-create assignments via a signal path that did not exist at save time.
  Resolved by registering `StepCompletionAdmin` with correct inline/fieldset
  configuration.
- **`CheckFilterAdmin` add form blank** — the add form showed no filter choices
  because the queryset was not being loaded. Fixed by overriding `get_form()`
  to populate the content-type queryset correctly.

---

## [0.1.3] - 2026-03-18

### Added
- **In-app flow manager** — superusers and users in the `manage_flows`
  permission group can now create, edit, publish/unpublish, and delete flows
  and their steps entirely within the app, without needing Django admin access.
  Accessible at `/pipeline/manage/`.

---

## [0.1.2] - 2026-03-18

### Fixed
- **`CheckFilter.content_type` `related_name` clash** — added
  `related_name="pipeline_checkfilter_set"` to avoid a Django system-check
  error when `allianceauth-secure-groups` (or the `workflows` app) is installed
  alongside Pipeline.

---

## [0.1.1] - 2026-03-18

### Changed
- Updated README installation instructions and pip install command.

---

## [0.1.0] - 2026-03-18

### Added
- Initial release of **aa-pipeline** — a structured journey/onboarding system
  for Alliance Auth.
- `OnboardingFlow` model with name, slug, description, type (`onboarding`,
  `training`, `certification`, `vetting`, `industry`, `other`), status
  lifecycle (`draft` → `published` → `archived`), and `auto_assign` flag.
- Audience targeting via M2M relations to AA States, Groups, Corporations,
  Alliances, Factions, and Characters — exactly matching the Wizard model
  pattern.
- `FlowStep` model with three step types:
  - `filter_check` — completion determined by Smart Filter evaluation.
  - `acknowledgement` — user reads body and clicks confirm.
  - `service_check` — checks whether the user has an active account in a
    registered AA service (Discord, Mumble, TeamSpeak, IPS Forum, XenForo,
    Openfire); falls back to acknowledgement mode when the service is not
    installed.
- `StepCheck` model — binds a `CheckFilter` (Smart Filter) to a `filter_check`
  step; multiple checks may be attached and all must pass.
- `CheckFilter` model — generic ContentType/object_id binding to any registered
  Smart Filter object, mirroring the `allianceauth-secure-groups` catalog
  pattern.
- `FlowAssignment` model — tracks per-user assignment status (`assigned` →
  `in_progress` → `completed`) with timestamps.
- `StepCompletion` model — records self-guided step completions
  (acknowledgements and service-check fallbacks) with a `metadata` JSON field.
- On-complete automation: add user to configured groups and fire a webhook URL
  when a flow is marked complete.
- `service_registry.py` — runtime lookup of installed AA service apps; guards
  all checks with `apps.get_app_config()` so no hard dependencies on optional
  service apps are introduced.
- Celery tasks: `process_autoassign_for_user` (auto-assign eligible flows when
  a user's profile changes) and `fire_completion_webhook`.
- Signals: auto-assignment triggers on `UserProfile`, `User.groups`, and
  `CharacterOwnership` changes; Smart Filter catalog maintenance on object
  create/delete.
- `FlowManager` — `get_visible_for_user()` and `get_auto_assignable_for_user()`
  queryset helpers.
- User-facing `flow_detail` view with sidebar step navigation, per-step
  progress indicators, Markdown body rendering (with Bleach sanitisation when
  available), and a sticky top progress strip.
- App index (`/pipeline/`) listing assigned and visible flows with completion
  percentages and a dashboard widget hook.
- Alliance Auth integration: menu entry, dashboard widget, URL registration,
  and GDPR data export hooks via `auth_hooks.py`.
- `basic_access` and `manage_flows` app-level permissions.
- Bootstrap 5 / Font Awesome UI consistent with the AA default theme.

[0.1.7]: https://github.com/Thrainkrilleve/aa-pipeline/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/Thrainkrilleve/aa-pipeline/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/Thrainkrilleve/aa-pipeline/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/Thrainkrilleve/aa-pipeline/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/Thrainkrilleve/aa-pipeline/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/Thrainkrilleve/aa-pipeline/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/Thrainkrilleve/aa-pipeline/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/Thrainkrilleve/aa-pipeline/releases/tag/v0.1.0
