# Build CLOCKIT — Industrial Inspection Management UI

Build a modern, professional web application called **CLOCKIT**, a modular, multi-industry industrial anomaly detection and inspection management platform.

## Tech Stack
- React + Vite
- TypeScript
- Tailwind CSS
- React Router
- Recharts for analytics
- Lucide React for icons
- Axios for backend API integration

## Design Requirements
- Professional industrial SaaS dashboard.
- Clean, modern, minimal interface.
- Dark sidebar with a light main workspace.
- Neutral colors with blue as the primary accent; use red, amber, and green for inspection statuses.
- Responsive layout for desktop and tablet.
- Consistent spacing, typography, cards, tables, charts, and dialogs.
- Include loading states, empty states, error states, and confirmation dialogs.
- Avoid excessive gradients, unnecessary animations, and clutter.

## Required Pages

### 1. Dashboard
- Total inspections performed.
- Pass/fail statistics.
- Anomaly detection rate.
- Average quality score.
- Recent inspections.
- Anomaly distribution charts.
- Inspection activity timeline.
- Model performance overview.

### 2. Inspection Workspace
- Upload images or batches of images.
- Select an industry, product, and inspection pipeline.
- Configure inspection settings.
- Display processing progress.
- Show original image alongside anomaly heatmap and defect localization.
- Display detected defects, defect type, severity, confidence, and anomaly score.
- Show the final aggregated inspection score.
- Allow users to review and confirm results.

### 3. Inspection History
- Searchable and filterable inspection table.
- Filter by date, industry, product, status, and severity.
- View detailed inspection reports.
- Compare previous inspections.
- Export reports.

### 4. Pipeline Builder
- Create and edit inspection pipelines.
- Add, remove, reorder, and configure model modules.
- Support sequential and conditional execution.
- Visualize the pipeline as connected steps.
- Configure how outputs contribute to the final quality score.
- Save pipeline configurations.

### 5. Model Management
- List available AI models.
- Display model name, task, version, status, and accuracy metrics.
- Upload or register custom models.
- Enable/disable models.
- View model details and evaluation results.
- Support model versioning and rollback.

### 6. Dataset Management
- Upload custom datasets.
- Organize datasets by industry, product, and defect category.
- Display image counts and dataset statistics.
- Show training, validation, and testing splits.
- Validate dataset quality.
- Display dataset readiness for training.

### 7. Training Center
- Configure training jobs.
- Select dataset and model.
- Configure training parameters.
- Show training progress and logs.
- Display loss and metric charts.
- Compare candidate model performance.
- Allow approval before promoting a trained model.

### 8. Reports and Analytics
- Inspection trends.
- Defect frequency and severity distribution.
- Model performance comparisons.
- Quality score trends.
- Exportable inspection reports.

### 9. Settings
- Industry and product configuration.
- User and role management.
- Hardware/resource monitoring.
- Application preferences.
- API/backend connection status.

## Main Navigation
Use a persistent sidebar with:
- Dashboard
- New Inspection
- Inspection History
- Pipeline Builder
- Models
- Datasets
- Training Center
- Analytics & Reports
- Settings

Include a top navigation bar with breadcrumbs, notifications, and user profile.

## Suggested Frontend File Structure

src/
├── app/
│   ├── App.tsx
│   ├── router.tsx
│   └── providers.tsx
│
├── assets/
│   ├── images/
│   └── icons/
│
├── components/
│   ├── common/
│   │   ├── Button.tsx
│   │   ├── Modal.tsx
│   │   ├── DataTable.tsx
│   │   ├── StatusBadge.tsx
│   │   ├── StatCard.tsx
│   │   └── LoadingState.tsx
│   ├── layout/
│   │   ├── Sidebar.tsx
│   │   ├── Topbar.tsx
│   │   └── MainLayout.tsx
│   ├── charts/
│   └── inspection/
│
├── pages/
│   ├── Dashboard/
│   ├── Inspection/
│   ├── InspectionHistory/
│   ├── PipelineBuilder/
│   ├── Models/
│   ├── Datasets/
│   ├── Training/
│   ├── Analytics/
│   └── Settings/
│
├── features/
│   ├── inspection/
│   ├── pipelines/
│   ├── models/
│   ├── datasets/
│   └── training/
│
├── services/
│   ├── api.ts
│   ├── inspectionService.ts
│   ├── modelService.ts
│   ├── datasetService.ts
│   └── pipelineService.ts
│
├── hooks/
├── contexts/
├── types/
├── utils/
├── styles/
│   └── globals.css
└── main.tsx

## Important Implementation Rules
1. Build reusable components instead of duplicating UI.
2. Keep API calls separate from UI components.
3. Use TypeScript interfaces for all API responses and application data.
4. Use mock data initially so the frontend can be developed independently of the backend.
5. Keep the API layer ready to connect to FastAPI later.
6. Do not hardcode industry-specific workflows; pipelines and modules must be configurable.
7. Make the inspection workspace the central feature of the application.
8. Keep the interface functional: buttons, filters, navigation, dialogs, and forms must work.
9. Do not implement fake AI processing as if it were real. Clearly label mock results until the backend is connected.
10. Prioritize a polished, working hackathon prototype over unnecessary complexity.

## Development Order
1. Application layout, sidebar, and routing.
2. Dashboard.
3. Inspection workspace.
4. Inspection history and reports.
5. Pipeline builder.
6. Model and dataset management.
7. Training center.
8. Analytics and settings.

First establish the design system and application layout, then implement each page using reusable components and realistic mock data.