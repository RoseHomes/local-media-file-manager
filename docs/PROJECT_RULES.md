# Project Rules

Single source of truth for the current project structure, code placement rules, UI text rules, and change workflow.

## 1. Project Structure

```text
local-media-file-manager/
|-- docs/
|   `-- PROJECT_RULES.md
|-- fanart_manager/
|-- sorter/
|   |-- admin.py
|   |-- config.py
|   |-- models.py
|   |-- urls.py
|   |-- apps/
|   |   |-- catalog/
|   |   |   |-- admin.py
|   |   |   |-- forms.py
|   |   |   |-- models.py
|   |   |   |-- services.py
|   |   |   `-- views.py
|   |   |-- fanart/
|   |   |   |-- forms.py
|   |   |   |-- models.py
|   |   |   |-- services.py
|   |   |   `-- views.py
|   |   |-- filemanage/
|   |   |   |-- forms.py
|   |   |   |-- models.py
|   |   |   |-- services.py
|   |   |   `-- views.py
|   |   `-- ui/
|   |       |-- context_processors.py
|   |       |-- forms.py
|   |       |-- models.py
|   |       |-- text.py
|   |       `-- views.py
|   |-- management/
|   |-- migrations/
|   |-- ui_text_data/
|   |   |-- en/
|   |   `-- th/
|   `-- tests/
|       |-- common.py
|       |-- test_catalog_imports.py
|       |-- test_fanart_workflow.py
|       |-- test_filemanage_workflow.py
|       |-- test_pages.py
|       `-- test_ui_text_catalogs.py
|-- templates/
|   |-- base.html
|   |-- catalog/
|   |-- fanart/
|   |-- filemanage/
|   `-- ui/
|-- static/
|   |-- catalog/
|   |   `-- js/
|   |-- fanart/
|   |   |-- css/
|   |   `-- js/
|   |-- filemanage/
|   |   `-- js/
|   |-- shared/
|   |   |-- css/
|   |   |-- js/
|   |   `-- src/
|   |-- ui/
|   |   `-- favicons/
|   `-- favicon.svg
|-- scripts/
|-- workspace/
|-- media/
|-- manage.py
`-- README.md
```

## 2. Domain Ownership

- `catalog`: game and character master data, import flows, saved lists, and related settings.
- `fanart`: inbox, album, staging queue, preview flow, and fanart settings.
- `filemanage`: generic file operations, previews, execution flows, and their settings.
- `ui`: interface text catalogs, theme state, shared UI assets, and global UI helpers.

## 3. Compatibility Surfaces

These root files stay intentionally small.

- `sorter/models.py` is the stable import surface for Django models.
- `sorter/admin.py` is the Django admin autodiscovery bridge.

Do not add new domain logic to those files unless the work is specifically about compatibility.

## 4. Placement Rules

1. Put models in `sorter/apps/<domain>/models.py`.
2. Put forms in `sorter/apps/<domain>/forms.py`.
3. Put behavior and business logic in `sorter/apps/<domain>/services.py`.
4. Put request handling in `sorter/apps/<domain>/views.py`.
5. Put templates in `templates/<domain>/`.
6. Keep `templates/base.html` for the shared shell only.
7. Put shared CSS build files in `static/shared/`.
8. Put page-specific JS or CSS in `static/<domain>/`.
9. If one page grows beyond a single small script, split it into focused files under `static/<domain>/js/` instead of rebuilding a page-level mega file.
10. Put UI-owned assets such as favicons in `static/ui/`.
11. Put focused tests in `sorter/tests/test_<feature>.py`.
12. Put user-facing text files in `sorter/ui_text_data/<locale>/` and split them by menu, page, or workflow.
13. Do not recreate deleted root wrappers such as `sorter/views.py`, `sorter/forms.py`, `sorter/services.py`, `sorter/ui_text.py`, or `sorter/context_processors.py`.

## 5. Coding Rules

### Views

- Views coordinate request handling, form validation, service calls, and rendering.
- Views should stay thin.
- Do not move long loops, deep path logic, or file-processing workflows into views.

### Services

- Services own business logic and workflow behavior.
- If the code answers `how should the system do this work?`, it belongs in a service.
- Long-running operation workflows, progress tracking, and status persistence belong in services plus models, not in in-memory view globals.
- If a workflow needs resumable or pollable state, store that state in a model or another durable layer rather than a process-local dictionary.

### Forms

- Forms own validation when possible.
- Put path validation, token validation, numeric ranges, and invalid option combinations in forms.

### Templates

- Templates render.
- Templates may contain small conditions and presentation loops.
- Do not grow templates into controllers with large inline scripts, large inline styles, or complicated client-side logic.
- If client behavior becomes significant, move it into a real static asset.

## 6. UI Text Rules

### Single Source Of Truth

- User-facing strings must live in `sorter/ui_text_data/en/` and `sorter/ui_text_data/th/`.
- This includes template copy, form labels, help text, validation messages, placeholders, modal labels, JS config text, flash messages, and API/runtime error payloads.
- Do not add duplicate hard-coded user-facing strings in views, forms, templates, page-level JS, or API responses.

### File Organization

- Split locale files by menu, page, or workflow.
- Do not grow one mega locale file.
- Keep related page UI text and page messages in the same bundle when they belong to the same flow.
- If code still needs a fallback value, keep that fallback non-user-facing whenever possible. Do not treat view/form hardcodes as the normal source of UI copy.

### Language Mode Rules

- `en`: render English for structural UI and supporting copy.
- `th`: render Thai for structural UI and supporting copy.
- `mixed`: render structural UI in English and supporting copy in Thai.

### Structural UI In Mixed Mode

Keep these in English.

- navigation labels
- page titles
- page headings
- section titles
- field labels
- action labels and button labels
- modal titles
- current control labels
- short counter labels
- short state labels and short badges

### Supporting Copy In Mixed Mode

Render these in Thai.

- intros under titles
- helper text
- prompts and hints
- placeholders
- empty states
- feedback messages
- validation messages
- flash messages
- modal descriptions
- long explanatory text

### Classification Rule

- Do not decide language by file name alone.
- Do not decide language by whether the text sits inside a select, modal, or card.
- Decide language by the role the text plays on the UI.
- If the text is a structural label, use English in `mixed`.
- If the text is explanatory or feedback copy, use Thai in `mixed`.

## 7. Thai Text Quality Rules

When adding or editing Thai locale files, always scan for broken output before closing the change.

Check for markers such as:

- `??`
- `&#...;`
- `\uXXXX`
- replacement characters such as `�`
- C1 control-range garbage characters
- mojibake or obviously broken non-Thai output

If Thai text is broken, restore it to real Thai text before finishing.

## 8. Workflow For New Changes

Before implementation starts, answer these questions.

1. Which domain owns this work?
2. Which layers will change: model, form, service, view, template, static asset, tests, docs?
3. What is the source of truth for the behavior or data?
4. Which existing flows could regress?
5. Which tests should prove the change is safe?
6. Are new user-facing strings needed?
7. Where will those strings live in `en` and `th`?
8. Does the change follow the `en / th / mixed` language rules?

## 9. Safe Change Order

1. Move code or assets to the correct home.
2. Update imports, render paths, static paths, and locale references.
3. Run tests.
4. Delete obsolete files or bridges only after the new path works.
5. Update docs in the same change.

## 10. Test Rules

1. Put shared helpers in `sorter/tests/common.py`.
2. Put broad page render coverage in `sorter/tests/test_pages.py`.
3. Put domain behavior in focused test files such as `test_fanart_workflow.py`, `test_catalog_imports.py`, and `test_filemanage_workflow.py`.
4. Keep locale quality checks in `test_ui_text_catalogs.py`.
5. Do not reintroduce a single mega test file.

## 11. Definition Of Done

A change is not done until all of the following are true.

- files live in the correct domain or shared location
- no new mega-file was introduced
- long-running operation state is not trapped in view-local process memory when the UI needs to poll or reopen it
- views stay thin
- business logic lives in services where appropriate
- validation lives in forms where appropriate
- user-facing strings live in locale files, not scattered through code
- the `en / th / mixed` language rules were followed
- Thai locale files were checked for broken output markers
- tests cover the changed risk
- docs were updated if structure or rules changed

