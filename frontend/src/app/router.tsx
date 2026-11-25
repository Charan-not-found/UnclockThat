import { createBrowserRouter } from 'react-router-dom'
import MainLayout from '../components/layout/MainLayout'
import Dashboard from '../pages/Dashboard/Dashboard'
import Inspection from '../pages/Inspection/Inspection'
import InspectionHistory from '../pages/InspectionHistory/InspectionHistory'
import Models from '../pages/Models/Models'
import Placeholder from '../pages/Placeholder/Placeholder'
export const router = createBrowserRouter([{ path:'/', element:<MainLayout/>, children:[
 { index:true, element:<Dashboard/> }, { path:'inspect', element:<Inspection/> }, { path:'history', element:<InspectionHistory/> }, { path:'models', element:<Models/> },
 { path:'pipelines', element:<Placeholder title="Pipeline Builder"/> }, { path:'datasets', element:<Placeholder title="Datasets"/> }, { path:'training', element:<Placeholder title="Training Center"/> },
 { path:'analytics', element:<Placeholder title="Analytics & Reports"/> }, { path:'settings', element:<Placeholder title="Settings"/> } ] }])
