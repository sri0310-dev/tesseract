import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import SignalFeed from './pages/SignalFeed';
import Commodities from './pages/Commodities';
import CommodityDetail from './pages/CommodityDetail';
import SupplyDemand from './pages/SupplyDemand';
import Corridors from './pages/Corridors';
import Counterparty from './pages/Counterparty';
import Arbitrage from './pages/Arbitrage';
import DataManager from './pages/DataManager';
import './App.css';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<SignalFeed />} />
          <Route path="/commodities" element={<Commodities />} />
          <Route path="/commodities/:id" element={<CommodityDetail />} />
          <Route path="/supply-demand" element={<SupplyDemand />} />
          <Route path="/corridors" element={<Corridors />} />
          <Route path="/counterparty" element={<Counterparty />} />
          <Route path="/arbitrage" element={<Arbitrage />} />
          <Route path="/data" element={<DataManager />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
