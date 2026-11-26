import { createBrowserRouter } from 'react-router-dom'
import MainLayout from '../components/layout/MainLayout'

import Dashboard from '../pages/Dashboard/Dashboard'
import ScannerUnits from '../pages/ScannerUnits/ScannerUnits'
import Inspection from '../pages/Inspection/Inspection'
import MassTest from '../pages/MassTest/MassTest'
import InspectionHistory from '../pages/InspectionHistory/InspectionHistory'
import InspectionDetail from '../pages/InspectionDetail/InspectionDetail'
import ReviewQueue from '../pages/ReviewQueue/ReviewQueue'
import Models from '../pages/Models/Models'
import Datasets from '../pages/Datasets/Datasets'
import Training from '../pages/Training/Training'
import Analytics from '../pages/Analytics/Analytics'
import Administration from '../pages/Administration/Administration'
import Settings from '../pages/Settings/Settings'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <MainLayout />,
    children: [
      { index: true,             element: <Dashboard /> },
      { path: 'scanners',        element: <ScannerUnits /> },
      { path: 'test-sample',     element: <Inspection /> },
      { path: 'mass-test',       element: <MassTest /> },
      { path: 'inspect',         element: <Inspection /> },
      { path: 'history',         element: <InspectionHistory /> },
      { path: 'inspections/:id', element: <InspectionDetail /> },
      { path: 'review',          element: <ReviewQueue /> },
      { path: 'models',          element: <Models /> },
      { path: 'datasets',        element: <Datasets /> },
      { path: 'training',        element: <Training /> },
      { path: 'analytics',       element: <Analytics /> },
      { path: 'admin',           element: <Administration /> },
      { path: 'settings',        element: <Settings /> },
    ],
  },
])
