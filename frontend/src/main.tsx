import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import App from './App';
import Dashboard from './pages/Dashboard';
import Predict from './pages/Predict';
import Predictions from './pages/Predictions';
import SpeciesPage from './pages/SpeciesPage';
import System from './pages/System';
import './index.css';

const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'predict', element: <Predict /> },
      { path: 'predictions', element: <Predictions /> },
      { path: 'species', element: <SpeciesPage /> },
      { path: 'system', element: <System /> },
    ],
  },
]);

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
