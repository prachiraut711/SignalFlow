import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/Layout';
import { Dashboard } from './pages/Dashboard';
import { Signals } from './pages/Signals';
import { SignalDetail } from './pages/SignalDetail';
import { Events } from './pages/Events';
import { Services } from './pages/Services';

const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="signals" element={<Signals />} />
        <Route path="signals/:id" element={<SignalDetail />} />
        <Route path="events" element={<Events />} />
        <Route path="services" element={<Services />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
};

export default App;
