# CLOCKIT — Scanner Unit Management UI Specification

**Document type:** UI implementation specification  
**Product:** CLOCKIT — Industrial Inspection & Anomaly Detection Platform  
**Scope:** Scanner Unit management workflow based on the four supplied wireframes  
**Version:** 1.0  
**Date:** 26 November 2026

---

## 1. Purpose

This document defines the UI and interaction requirements for creating, selecting, configuring, and editing Scanner Units.

The four supplied screens establish the intended workflow:

1. **Scanner Unit management page** — create and manage Scanner Units.
2. **Scanner Unit selection page** — view and select an existing Scanner Unit.
3. **Scanner Unit configuration popup** — view the selected Scanner Unit's modules and add a module.
4. **Module add/edit interface** — configure an Analysis Module, its outputs, model, and dataset files.

The wireframes establish the layout and user flow, not the final styling. Preserve their information hierarchy while delivering a polished, consistent industrial application interface.

## 2. Terminology

### Scanner Unit
A named inspection configuration that groups one or more Analysis Modules into a reusable workflow. It is a container, not an AI model.

### Analysis Module
An independently configurable inspection capability within a Scanner Unit, such as surface anomaly detection, crack detection, scratch detection, dimensional measurement, or component detection.

### Model Configuration
The model and settings used by an Analysis Module: model family, supported training strategy, preprocessing, parameters, dataset requirements, artifact/version, and supported outputs.

Modules must not be permanently bound to one AI model. Changing model configuration should not require recreating the Scanner Unit.

### Dataset
A collection of uploaded and validated files used to configure, train, validate, or evaluate a model. Upload, validation, training, evaluation, and deployment are distinct operations.

## 3. Primary workflow

1. User opens Scanner Unit management.
2. User creates a Scanner Unit or selects an existing one.
3. Selecting a Scanner Unit opens its configuration popup.
4. User adds or edits an Analysis Module.
5. User configures module details, model, dataset, and outputs.
6. User saves the module.
7. Saved module appears in the Scanner Unit popup.
8. User may add/edit other modules or close the popup.

Keep the user anchored in Scanner Unit management. Module editing should be a focused subtask rather than navigation into an unrelated area. On narrow screens, dialogs may become full-screen pages.

## 4. Global application shell

### 4.1 Sidebar
Use the existing application navigation. Keep it persistent on desktop, with a clearly indicated active destination. Icon-only mode requires tooltips/accessibility labels. On smaller screens, use a collapsible drawer. The sidebar must not obscure dialogs.

Do not invent a new navigation taxonomy if the repository already has one.

### 4.2 Main content
- Page title and optional concise description.
- Consistent page padding, alignment, and spacing.
- Loading, empty, error, and populated states.
- Avoid decorative metrics or charts unrelated to this workflow.

### 4.3 Visual direction
Implement a professional industrial UI:
- Neutral surfaces and high-contrast readable text.
- One restrained accent color.
- Subtle borders and restrained shadows.
- Consistent corner radius, typography, spacing, and control sizes.
- Clear interactive, disabled, and display-only states.
- Avoid excessive gradients, glassmorphism, oversized cards, and decorative animations.

Wireframe outlines are structural placeholders, not the final styling.

## 5. Screen 1 — Scanner Unit management

### Purpose
The main page for creating and managing Scanner Units.

### Layout
- Persistent sidebar.
- Main content area.
- Heading: **Scanner Units**.
- Short description explaining that Scanner Units group inspection modules into reusable workflows.
- Primary **Create Scanner Unit** action, corresponding to the plus button in the wireframe.
- List or grid of saved Scanner Units.

### Scanner Unit entry
Each entry may display:
- Name.
- Short description.
- Number of modules.
- Last updated timestamp.
- Configuration status, only when derived from actual saved state.

Each entry should have an obvious selection/open interaction. Secondary actions may include Rename, Duplicate, and Delete in an overflow menu.

Deleting requires confirmation. If records have inspection history or dependent records, respect retention rules and explain consequences; do not silently delete historical data.

### Create dialog
Clicking **Create Scanner Unit** opens a compact dialog.

Fields:
- **Name** — required.
- **Description** — optional.

Actions:
- **Create Scanner Unit**
- **Cancel**

Validation:
- Name cannot be blank.
- Trim leading/trailing whitespace.
- Handle duplicate names according to existing application rules; if duplicates are allowed, warn appropriately.
- Show field-level errors.
- Disable submission during the request and prevent duplicate submissions.

On success, persist and add the Scanner Unit to the list, then open its configuration popup (Screen 3) as the recommended behavior.

### Empty state
When no Scanner Units exist:
- Explain briefly what a Scanner Unit is.
- Provide a primary Create Scanner Unit action.
- Do not show fabricated records.

### Loading and error states
Show loading skeletons/spinners while loading. If loading fails, show a useful error and Retry. Do not mistake request failure for an empty state.

## 6. Screen 2 — Scanner Unit selection

The second wireframe shows a list of Scanner Units (e.g., Scanner One and Scanner Two) for selection.

The sketches may represent a separate selection view, but the preferred implementation is the populated management list on Screen 1. Avoid redundant routes if selection can be handled there. If the existing app requires a separate page, implement the same behavior.

Requirements:
- Clearly clickable Scanner Unit entries.
- Selecting one opens Screen 3.
- Nested menu actions must not trigger row selection.
- Show a loading state while its module configuration is fetched.
- On fetch failure, remain on the selection view and provide retry.

## 7. Screen 3 — Scanner Unit configuration popup

### Purpose
After selecting a Scanner Unit, display its Analysis Modules and an option to add one.

### Layout
- Scanner Unit name.
- Optional description.
- List of saved modules.
- Primary **Add Module** button.
- Close action.

Use a centered modal/dialog on desktop with sensible maximum width; on smaller screens, use a full-screen dialog.

### Module row
Show, where available:
- Module name.
- Short purpose/description.
- Selected model name.
- Configuration state derived from saved data.

Possible states (only if actually supported):
- Draft
- Needs dataset
- Ready
- Training
- Failed

### Actions
- **Add Module** opens Screen 4 in create mode.
- **Edit** opens Screen 4 with saved values.
- Optional overflow actions may include Duplicate or Remove.

Removing a module requires confirmation. Do not silently delete artifacts, dataset versions, or inspection history.

### Empty state
Explain that modules define what a Scanner Unit inspects and provide an Add Module action.

### Close and unsaved changes
Closing returns to Scanner Unit management. Saved changes must not be discarded. If the child editor has unsaved changes, warn before closing.

## 8. Screen 4 — Analysis Module add/edit

### Purpose
Create or edit an Analysis Module for the selected Scanner Unit.

Organize the form into sections:
1. Module details.
2. AI model selection.
3. Dataset and files.
4. Output configuration.
5. Save/cancel actions.

Use a scrollable, readable form. Avoid cramming all fields into one horizontal row.

### 8.1 Module details
Fields:
- **Module name** — required.
- **Description** — optional.
- **Inspection purpose/category** — optional, if supported.

Examples: Surface Anomaly Detection, Crack Detection, Scratch Detection.

Validate required fields and preserve input on errors.

### 8.2 AI model selection
Populate the model selector from the real model registry/capability metadata.

Show enough information for users to choose safely:
- Display name and model family.
- Supported task.
- Dataset and annotation requirements.
- Supported training/configuration strategies.
- Important limitations.

Distinguish model states such as:
- Available and integrated.
- Downloaded but not integrated.
- Planned or unavailable.

Only models that can actually execute in the current environment should be selectable for a functional module. Changing model selection must re-evaluate dataset and output compatibility, warn about incompatible settings, and avoid silently discarding data. Do not imply all models share training methods.

### 8.3 Dataset and file upload
Provide an upload panel with:
- Browse files.
- Drag and drop where supported.
- File names and sizes.
- Upload/processing status.
- Remove selected files before submission.
- Clear validation errors.
- ZIP dataset support where the backend supports it.

Explain the selected model's actual data requirements. Examples:
- Normal-only anomaly detection may use normal images for training.
- Supervised detection typically requires annotated images and boxes.
- Segmentation may require masks.

These are examples; requirements must be driven by the model capability manifest.

#### Dataset states
Represent the lifecycle:
- Not uploaded
- Uploading
- Uploaded
- Validating
- Validation failed
- Validated
- Ready for training/configuration

Upload completion is not dataset validation; validation is not training.

#### Validation feedback
Show backend validation results such as unsupported files, corrupt archives/images, empty dataset, duplicate warnings, missing annotations, incorrect folder structure, or unsupported image dimensions.

Never mark a dataset valid merely because the upload completed.

### 8.4 Output configuration
Show checkboxes only for outputs supported by the selected module/model. Potential outputs include:
- Anomaly score.
- Anomaly localization/heatmap.
- Defect class.
- Bounding boxes.
- Segmentation mask.
- Confidence score.
- Measurement result.

These are examples, not a universal output list.

For each output:
- Human-readable label.
- Brief explanation or tooltip.
- Omit or disable unsupported outputs.
- Preserve selected outputs when editing.
- Validate required selections.

Anomaly score, confidence, severity, and final inspection decision are different concepts. Do not label an uncalibrated score as a probability.

### 8.5 Save actions
Provide:
- **Save Module** (or **Save Changes** in edit mode).
- **Cancel**.

Behavior:
- Validate before saving.
- Show saving state.
- Prevent duplicate submission.
- On success, close editor and refresh the module list.
- On failure, preserve input and show an actionable error.
- In edit mode, update the existing module instead of creating a duplicate.

Saving module configuration must not automatically trigger training. Training, if supported, should be a separate explicit action.

### 8.6 Create and edit modes
Use one form for both modes.

**Create mode:** blank/default values; heading Add Analysis Module.

**Edit mode:** prefilled saved values; heading Edit Analysis Module; show model/dataset state; warn if a change invalidates a previously trained or deployed configuration.

## 9. Interaction, state, and feedback

### Required interaction map

| Action | Result |
|---|---|
| Click Create Scanner Unit | Open create dialog |
| Submit valid Scanner Unit | Persist and open its configuration |
| Cancel creation | Close without creating |
| Select Scanner Unit | Open its configuration |
| Add Module | Open module editor in create mode |
| Edit module | Open editor with saved values |
| Upload files | Upload and display progress |
| Upload completes | Trigger or offer validation |
| Change output selection | Update form configuration |
| Save module | Persist and refresh module list |
| Cancel module editor | Return to Scanner Unit popup |
| Close configuration popup | Return to management view |
| Delete/remove | Confirmation required |

### Unsaved changes
Track dirty state. If the user attempts to close or cancel with unsaved changes, show **Discard changes** and **Continue editing**. Do not lose changes silently.

### Loading
Provide feedback for loading Scanner Units, module configuration, creating Scanner Units, saving modules, uploading files, and validating datasets. Use button-level indicators and disable only conflicting controls.

### Errors
- Explain failure in plain language.
- Preserve user input where possible.
- Provide recovery options.
- Avoid raw stack traces or internal exception text.

### Success
Use concise confirmations (e.g., Scanner Unit created, Module saved, Dataset validation completed). Do not show success until the backend confirms.

## 10. Data and API integration

Use real application data; never hardcode Scanner One/Scanner Two as real records.

### Conceptual data relationships
Adapt names to the existing data model.

**Scanner Unit**
- Stable ID.
- Name.
- Description.
- Created/updated timestamps.
- Module references.

**Analysis Module**
- Stable ID.
- Parent Scanner Unit ID.
- Name and description.
- Model/configuration reference.
- Selected outputs.
- Dataset reference/version, if applicable.
- Configuration status.
- Created/updated timestamps.

### Model capability metadata
The UI should be driven by model metadata such as:
- Model ID/display name.
- Integration/availability state.
- Tasks and dataset requirements.
- Annotation requirements.
- Supported training strategies.
- Supported outputs.
- Preprocessing requirements.
- Hardware notes and limitations.

Expose only actions supported by the selected adapter.

### API
Use existing API/service conventions. The frontend requires equivalent operations for:
- List/create/read/update/delete Scanner Units.
- List/create/read/update/remove modules for a Scanner Unit.
- List available/integrated models.
- Upload dataset files.
- Retrieve dataset validation status/results.

Inspect the backend before inventing endpoint paths or response shapes. Map these interactions to the existing API contract.

### Persistence
Saved Scanner Units and modules must survive page reloads. Keep temporary form state separate from saved data. Refresh/invalidate relevant data after successful mutations.

## 11. Responsive behavior

### Desktop
- Persistent sidebar.
- Main content uses available width.
- Scanner Units presented in readable rows or responsive grid.
- Configuration popup centered and bounded.
- Module editor uses a structured form.

### Tablet
- Sidebar may collapse.
- Forms use one or two columns as space permits.
- Dialog adapts to viewport.

### Mobile
- Sidebar becomes a drawer.
- Scanner Unit entries become full-width.
- Dialogs become full-screen/sheet.
- Form fields stack.
- Upload panel remains touch-friendly.
- Actions remain visible and do not overlap content.

Do not simply shrink desktop controls to fit.

## 12. Accessibility

- Visible labels on inputs.
- Accessible names for icon-only controls.
- Keyboard access to all interactions.
- Dialog focus management and return focus on close.
- Visible focus indicators.
- Appropriate contrast.
- Status not conveyed by color alone.
- Clickable checkbox labels.
- Validation messages associated with inputs.
- Upload operation possible without drag and drop.
- Escape may close dialogs when safe; unsaved-change protection still applies.

## 13. Component architecture guidance

Suggested reusable components (adapt to the existing repository):

```text
ScannerUnitManagementPage
├── AppSidebar
├── PageHeader
├── ScannerUnitList
│   ├── ScannerUnitCard / ScannerUnitRow
│   └── ScannerUnitActionsMenu
├── CreateScannerUnitDialog
└── ScannerUnitConfigurationDialog
    ├── ScannerUnitSummary
    ├── AnalysisModuleList
    │   └── AnalysisModuleRow
    └── ModuleEditor
        ├── ModuleDetailsSection
        ├── ModelSelector
        ├── DatasetUploadSection
        ├── DatasetValidationStatus
        ├── OutputSelector
        └── ModuleFormActions
```

This is guidance, not an instruction to restructure the entire codebase. Inspect existing frontend patterns first. Keep business logic/API calls out of presentational components where the current architecture supports it.

## 14. Design consistency

Reuse design tokens and components for:
- Typography and spacing.
- Border/radius and surface colors.
- Primary, secondary, destructive, disabled button states.
- Inputs, checkboxes, dialogs.
- Status indicators.
- Hover, focus, and error states.

One visually dominant primary action per context. Destructive actions require confirmation. Use status text and visual indicator together. Empty states should be concise and action-oriented.

## 15. Out of scope

Unless already implemented and explicitly included, these four screens do not require:
- Live inspection execution.
- Inspection-result dashboards.
- Multi-module score aggregation.
- Training orchestration UI.
- Human-review workflows.
- Model deployment/rollback screens.
- User/role administration.
- Organization management.

Design the module editor so these can be added later without changing the core Scanner Unit concepts.

## 16. Implementation order

### Step 1 — Inspect repository
Before changes, identify:
- Frontend framework and entry points.
- Existing routes/sidebar/design system.
- API contracts.
- Scanner Unit/module data structures.
- Existing functionality.

Do not replace working architecture merely to match this document.

### Step 2 — Screen 1
Build sidebar, page header, Scanner Unit list, empty state, create dialog, and real list/create integration.

### Step 3 — Screen 3
Build Scanner Unit configuration dialog, module list, empty state, and add/edit entry points.

### Step 4 — Screen 4
Build module details, model selector, dataset upload and validation states, output selection, save/edit behavior.

### Step 5 — Screen 2
Implement a separate selection page only if the existing app architecture needs it; otherwise ensure the Screen 1 list provides the selection flow.

### Step 6 — Polish and verify
Responsive behavior, accessibility, loading/error states, unsaved-change handling, persistence, and end-to-end tests.

## 17. Acceptance criteria

### Scanner Unit management
- [ ] User can view persisted Scanner Units.
- [ ] User can create one.
- [ ] Required fields validate.
- [ ] New entry appears without reload.
- [ ] Empty, loading, and error states work.
- [ ] User can select a Scanner Unit.

### Configuration popup
- [ ] Selecting a Scanner Unit opens its configuration.
- [ ] Correct name is displayed.
- [ ] Modules load from persisted data.
- [ ] Empty state is handled.
- [ ] Add and edit actions work.

### Module editor
- [ ] Create and edit modes work.
- [ ] Existing values populate in edit mode.
- [ ] Model options reflect real model capability/availability.
- [ ] Upload is functional, not decorative.
- [ ] Dataset validation status is visible.
- [ ] Outputs reflect model/module capabilities.
- [ ] Saving persists and refreshes the list.
- [ ] Failed save preserves form values.
- [ ] Cancel and unsaved-change protection work.

### Quality
- [ ] No fake records shown as real.
- [ ] No inert buttons.
- [ ] No success claimed before backend confirmation.
- [ ] Desktop and mobile are usable.
- [ ] Keyboard and dialog focus behavior work.
- [ ] Existing unrelated functionality is not broken.

## 18. Instructions to the coding agent

Implement this Scanner Unit management UI in the existing CLOCKIT repository.

**Before changing code, inspect and report:**
1. Current frontend framework and structure.
2. Existing pages/components that can be reused.
3. Backend/API operations for Scanner Units, modules, models, and datasets.
4. Requirements already implemented, partially implemented, or missing.
5. API/data-model gaps.

Then implement the workflow in the order in Section 16.

Rules:
- Follow the supplied wireframes' flow and information hierarchy.
- Use real backend data and persistence.
- Reuse design tokens and components where possible.
- Keep Scanner Units, Analysis Modules, and Model Configurations distinct.
- Make every visible control functional.
- Do not fabricate model availability, training progress, validation results, or success states.
- Do not train automatically on module save.
- Avoid unnecessary dependencies or infrastructure.
- Do not break working features.
- Do not leave placeholder buttons, fake data, TODO-only interactions, or disconnected screens.
- If the backend cannot support a requirement, document the gap and use an honest unsupported/disabled state rather than simulating success.

**Definition of done:** A user can create a Scanner Unit, select it, add an Analysis Module, configure its model, upload its dataset, choose supported outputs, save it, reopen it, and see the saved configuration persist.
