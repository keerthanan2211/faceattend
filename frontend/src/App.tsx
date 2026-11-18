import { Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import AdminGate from './pages/AdminGate';
import AttendancePage from './pages/AttendancePage';
import KioskPage from './pages/KioskPage';
import TechniciansPage from './pages/TechniciansPage';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<KioskPage />} />
        <Route path="technicians" element={<AdminGate><TechniciansPage /></AdminGate>} />
        <Route path="attendance" element={<AdminGate><AttendancePage /></AdminGate>} />
      </Route>
    </Routes>
  );
}
